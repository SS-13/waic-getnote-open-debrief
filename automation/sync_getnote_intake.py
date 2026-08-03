#!/usr/bin/env python3
"""Sync Joe-approved Getnote notes into the auditable intake layer."""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import hashlib
import json
import os
import re
import sys
import tempfile
import uuid
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any, Awaitable, Callable

import fcntl


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = REPO_ROOT / "automation/getnote-intake.json"
GETNOTE_TIMEOUT_SECONDS = 60
GETNOTE_MAX_ATTEMPTS = 3
GETNOTE_RETRY_DELAY_SECONDS = 1.0
RUNTIME_DIRECTORY = Path(".cache/getnote-intake")
TRANSACTION_SCHEMA_VERSION = "1.0"
BASELINE_SCHEMA_VERSION = "1.0"
BASELINE_GENERATOR_VERSION = "phase2-v1"


class IntakeError(RuntimeError):
  """Raised when an intake run cannot complete safely."""


class IntakeBatchError(IntakeError):
  """Raised after one or more note downloads exhaust their retries."""

  def __init__(self, failures: list[dict[str, str]]):
    self.failures = failures
    note_ids = ", ".join(failure["noteId"] for failure in failures)
    super().__init__(f"Failed to download {len(failures)} note(s): {note_ids}")


class LocalWriterLock(AbstractContextManager["LocalWriterLock"]):
  """Hold a non-blocking, process-local filesystem writer lock."""

  def __init__(self, path: Path):
    self.path = path
    self.handle: Any = None

  def __enter__(self) -> "LocalWriterLock":
    self.path.parent.mkdir(parents=True, exist_ok=True)
    self.handle = self.path.open("a+", encoding="utf-8")
    try:
      fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as error:
      self.handle.close()
      self.handle = None
      raise IntakeError("Another Getnote intake writer is already running") from error
    self.handle.seek(0)
    self.handle.truncate()
    self.handle.write(f"pid={os.getpid()}\n")
    self.handle.flush()
    return self

  def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
    if self.handle is not None:
      fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
      self.handle.close()
      self.handle = None


def json_dumps(value: Any, *, pretty: bool = False) -> str:
  if pretty:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
  return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def load_config(path: Path) -> dict[str, Any]:
  try:
    config = json.loads(path.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError) as error:
    raise IntakeError(f"Cannot load intake config: {path}") from error
  required = [
    "knowledgeBaseId", "acceptedEndpoint", "rawDirectory", "ledgerPath",
    "baselineStatePath", "curator",
  ]
  missing = [field for field in required if not config.get(field)]
  if missing:
    raise IntakeError(f"Missing config fields: {', '.join(missing)}")
  if config["acceptedEndpoint"] != "knowledge-base-notes":
    raise IntakeError("Only the knowledge-base-notes endpoint is allowed")
  if config.get("subscriptionBloggerImport") is not False:
    raise IntakeError("subscriptionBloggerImport must remain false")
  if config.get("liveImport") is not False:
    raise IntakeError("liveImport must remain false")
  return config


async def default_runner(args: list[str]) -> str:
  process = await asyncio.create_subprocess_exec(
    "getnote",
    *args,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
  )
  try:
    stdout, stderr = await process.communicate()
  except asyncio.CancelledError:
    process.kill()
    await process.communicate()
    raise
  if process.returncode != 0:
    message = stderr.decode("utf-8", errors="replace").strip()
    raise IntakeError(message or f"getnote exited with {process.returncode}")
  return stdout.decode("utf-8")


class GetnoteClient:
  def __init__(
    self,
    runner: Callable[[list[str]], Awaitable[str]] = default_runner,
    *,
    timeout_seconds: float = GETNOTE_TIMEOUT_SECONDS,
    max_attempts: int = GETNOTE_MAX_ATTEMPTS,
    retry_delay_seconds: float = GETNOTE_RETRY_DELAY_SECONDS,
    sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
  ):
    if timeout_seconds <= 0:
      raise ValueError("timeout_seconds must be positive")
    if max_attempts < 1:
      raise ValueError("max_attempts must be at least 1")
    self.runner = runner
    self.timeout_seconds = timeout_seconds
    self.max_attempts = max_attempts
    self.retry_delay_seconds = max(0.0, retry_delay_seconds)
    self.sleep = sleep

  async def request(
    self,
    args: list[str],
    validator: Callable[[str], Any],
  ) -> Any:
    last_error: Exception | None = None
    for attempt in range(1, self.max_attempts + 1):
      try:
        output = await asyncio.wait_for(
          self.runner(args),
          timeout=self.timeout_seconds,
        )
        return validator(output)
      except (IntakeError, OSError, TimeoutError, json.JSONDecodeError) as error:
        last_error = error
        if attempt < self.max_attempts and self.retry_delay_seconds:
          await self.sleep(self.retry_delay_seconds)
    command = " ".join(args[:2])
    detail = "timed out" if isinstance(last_error, TimeoutError) else str(last_error)
    raise IntakeError(
      f"getnote {command} failed after {self.max_attempts} attempt(s): {detail}"
    ) from last_error

  async def verify_auth(self) -> None:
    def validate(output: str) -> None:
      if "Authenticated" not in output:
        raise IntakeError("Getnote CLI is not authenticated")

    await self.request(["auth", "status"], validate)

  async def list_notes(self, topic_id: str) -> list[dict[str, Any]]:
    def validate(output: str) -> list[dict[str, Any]]:
      payload = json.loads(output)
      data = payload.get("data", {})
      notes = data.get("notes")
      if not isinstance(notes, list):
        raise IntakeError("Getnote knowledge-base response has no notes list")
      if data.get("has_more") is not False:
        raise IntakeError("Getnote knowledge-base response does not prove a complete list")
      total = data.get("total")
      if total is not None and (isinstance(total, bool) or not isinstance(total, int) or total != len(notes)):
        raise IntakeError("Getnote knowledge-base total does not match the returned list")
      return notes

    return await self.request(
      ["kb", topic_id, "--all", "--no-content", "-o", "json"],
      validate,
    )

  async def get_note(self, note_id: str) -> dict[str, Any]:
    def validate(output: str) -> dict[str, Any]:
      payload = json.loads(output)
      note = payload.get("data", {}).get("note")
      if not isinstance(note, dict):
        raise IntakeError(f"Getnote note response is invalid: {note_id}")
      return note

    return await self.request(["note", note_id, "-o", "json"], validate)


def normalize_note_id(value: Any) -> str:
  if isinstance(value, bool) or value is None:
    raise IntakeError("note_id is missing")
  if isinstance(value, int):
    return str(value)
  if isinstance(value, str) and value.isdigit():
    return value
  raise IntakeError(f"Invalid note_id: {value!r}")


def normalize_tags(note: dict[str, Any]) -> list[str]:
  tags = []
  for tag in note.get("tags") or []:
    if isinstance(tag, dict) and tag.get("name"):
      tags.append(str(tag["name"]))
    elif isinstance(tag, str):
      tags.append(tag)
  return sorted(set(tags))


def source_url(note: dict[str, Any]) -> str | None:
  web_page = note.get("web_page") or {}
  if isinstance(web_page, dict) and web_page.get("url"):
    return str(web_page["url"])
  for attachment in note.get("attachments") or []:
    if isinstance(attachment, dict) and attachment.get("url"):
      return str(attachment["url"])
  return None


def upstream_content(note: dict[str, Any]) -> str:
  note_type = note.get("note_type")
  if note_type == "link":
    web_page = note.get("web_page") or {}
    return str(web_page.get("content") or "")
  for field in ("audio_original", "content"):
    if note.get(field):
      return str(note[field])
  return ""


def stable_upstream_content(note: dict[str, Any]) -> str:
  content = upstream_content(note)
  content = re.sub(r"!\[[^\]]*\]\([^)]+\)", "![image]", content)
  content = re.sub(
    r"(https://(?:get-notes\.umiwi\.com|pic-cdn\.trytalks\.com)/[^\s?)]+)\?[^\s)]*",
    r"\1",
    content,
  )
  return re.sub(r"\s+", " ", content).strip()


def version_hash(note: dict[str, Any]) -> str:
  identity = {
    "noteId": normalize_note_id(note.get("note_id", note.get("id"))),
    "title": note.get("title") or "",
    "noteType": note.get("note_type") or "",
    "createdAt": note.get("created_at") or "",
    "updatedAt": note.get("updated_at") or "",
    "tags": normalize_tags(note),
    "sourceUrl": source_url(note),
    "summary": note.get("content") or "",
    "upstreamContentHash": hashlib.sha256(stable_upstream_content(note).encode("utf-8")).hexdigest(),
  }
  return hashlib.sha256(json_dumps(identity).encode("utf-8")).hexdigest()


def route_note(note: dict[str, Any], config: dict[str, Any]) -> tuple[list[str], list[str]]:
  searchable = " ".join([
    str(note.get("title") or ""),
    *normalize_tags(note),
  ]).lower()
  topic_ids = []
  question_ids = []
  for route in config.get("routes") or []:
    terms = [str(term).lower() for term in route.get("terms") or []]
    if any(term in searchable for term in terms):
      topic_ids.append(str(route["topicId"]))
      question_ids.extend(str(value) for value in route.get("questionIds") or [])
  return sorted(set(topic_ids)), sorted(set(question_ids))


def safe_filename(value: str, max_length: int = 88) -> str:
  value = re.sub(r'[\\/:*?"<>|]+', "-", value)
  value = re.sub(r"\s+", "_", value).strip("_-.")
  return (value[:max_length].rstrip("_-.")) or "untitled"


def yaml_string(value: Any) -> str:
  return json.dumps("" if value is None else str(value), ensure_ascii=False)


def content_fidelity(note: dict[str, Any]) -> tuple[str, str]:
  note_type = str(note.get("note_type") or "unknown")
  if note_type == "plain_text":
    return "structured", "getnote-user-note"
  return "summary", "getnote-ai-summary"


def render_markdown(
  note: dict[str, Any],
  config: dict[str, Any],
  *,
  ingested_at: str,
  baseline: bool,
) -> tuple[str, str, dict[str, Any]]:
  note_id = normalize_note_id(note.get("note_id", note.get("id")))
  title = str(note.get("title") or "(无标题)")
  created_at = str(note.get("created_at") or "")
  updated_at = str(note.get("updated_at") or created_at)
  date = (created_at[:10] or ingested_at[:10])
  digest = version_hash(note)
  short_hash = digest[:12]
  registry_source_id = f"raw:{note_id}:{short_hash}"
  fidelity, content_source = content_fidelity(note)
  topic_ids, question_ids = route_note(note, config)
  relative_path = Path(config["rawDirectory"]) / (
    f"{date}__{safe_filename(title)}__{note_id[-6:]}__{short_hash}.md"
  )
  url = source_url(note)
  tags = normalize_tags(note)
  summary = str(note.get("content") or "").strip()
  if not summary:
    summary = "该笔记尚无可用的得到大脑整理内容，请沿来源链接回查。"
  topic_literal = "[" + ", ".join(topic_ids) + "]"
  question_literal = "[" + ", ".join(question_ids) + "]"
  tag_literal = "[" + ", ".join(yaml_string(tag) for tag in tags) + "]"
  source_url_line = f"source_url: {yaml_string(url)}\n" if url else ""
  body = (
    "---\n"
    f"title: {yaml_string(title)}\n"
    f"curator: {yaml_string(config['curator'])}\n"
    "source: getnote-ai-intake\n"
    f"note_id: {note_id}\n"
    f"knowledge_base_id: {config['knowledgeBaseId']}\n"
    f"captured_at: {yaml_string(created_at)}\n"
    f"upstream_updated_at: {yaml_string(updated_at)}\n"
    f"ingested_at: {yaml_string(ingested_at)}\n"
    f"original_url: https://www.biji.com/note/{note_id}\n"
    f"{source_url_line}"
    f"content_source: {content_source}\n"
    f"fidelity: {fidelity}\n"
    f"version_hash: {digest}\n"
    f"registry_source_id: {registry_source_id}\n"
    f"baseline: {'true' if baseline else 'false'}\n"
    f"topic_ids: {topic_literal}\n"
    f"question_ids: {question_literal}\n"
    f"tags: {tag_literal}\n"
    "---\n\n"
    f"# {title}\n\n"
    "## 来源边界\n\n"
    "- 本页保存 Joe 主动加入 `ai 资讯` 知识库的普通笔记及得到大脑整理。\n"
    "- 对链接笔记，正文是平台 AI 整理，不是原作者逐字原文，也不自动证明其中事实。\n"
    "- 第三方网页全文默认不复制入公开仓库；核验时请沿原始来源链接回查。\n\n"
    "## 得到大脑整理\n\n"
    f"{summary}\n"
  )
  ledger_record = {
    "schemaVersion": "1.0",
    "intakeId": f"INT-GETNOTE-{note_id}-{short_hash}",
    "upstreamId": note_id,
    "knowledgeBaseId": config["knowledgeBaseId"],
    "captureMode": "joe-approved-note",
    "curator": config["curator"],
    "firstSeenAt": ingested_at,
    "upstreamCreatedAt": created_at or None,
    "upstreamUpdatedAt": updated_at or None,
    "versionHash": digest,
    "registrySourceId": registry_source_id,
    "canonicalSourceId": f"note:{note_id}",
    "evidenceLineageId": f"L-GETNOTE-{note_id}",
    "relativePath": relative_path.as_posix(),
    "status": "baseline" if baseline else "registered",
    "triageStatus": "pending",
    "selectionPriority": "joe-selected",
    "topicIds": topic_ids,
    "questionIds": question_ids,
    "subscriptionContent": False,
  }
  return relative_path.as_posix(), body, ledger_record


def read_jsonl(path: Path) -> list[dict[str, Any]]:
  if not path.exists():
    return []
  records = []
  for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
    if not line.strip():
      continue
    try:
      records.append(json.loads(line))
    except json.JSONDecodeError as error:
      raise IntakeError(f"Invalid JSONL at {path}:{line_number}") from error
  return records


def baseline_state_required(repo_root: Path, config: dict[str, Any]) -> bool:
  baseline_path = resolve_repo_path(repo_root, str(config["baselineStatePath"]))
  if not baseline_path.is_file():
    return True
  try:
    state = json.loads(baseline_path.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return True
  return not (
    isinstance(state, dict)
    and state.get("status") == "complete"
    and state.get("scope") == "all"
    and state.get("knowledgeBaseId") == config["knowledgeBaseId"]
  )


def fsync_directory(path: Path) -> None:
  descriptor = os.open(path, os.O_RDONLY)
  try:
    os.fsync(descriptor)
  finally:
    os.close(descriptor)


def atomic_write_bytes(path: Path, content: bytes) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
  try:
    with os.fdopen(descriptor, "wb") as handle:
      handle.write(content)
      handle.flush()
      os.fsync(handle.fileno())
    os.replace(temp_name, path)
    fsync_directory(path.parent)
  except Exception:
    Path(temp_name).unlink(missing_ok=True)
    raise


def atomic_write(path: Path, content: str) -> None:
  atomic_write_bytes(path, content.encode("utf-8"))


def stable_jsonl(records: list[dict[str, Any]]) -> str:
  ordered = sorted(records, key=lambda record: (record["upstreamId"], record["versionHash"]))
  return "".join(f"{json_dumps(record)}\n" for record in ordered)


def latest_intake_record(records: list[dict[str, Any]]) -> dict[str, Any] | None:
  if not records:
    return None
  return max(records, key=lambda record: (
    str(record.get("upstreamUpdatedAt") or ""),
    str(record.get("firstSeenAt") or ""),
    str(record.get("intakeId") or ""),
  ))


def build_batch_id(now: str, intake_ids: list[str]) -> str:
  identity = {"capturedAt": now, "intakeIds": sorted(intake_ids)}
  return f"BATCH-GETNOTE-{hashlib.sha256(json_dumps(identity).encode('utf-8')).hexdigest()[:16]}"


def validate_intake_payloads(
  ledger_content: bytes,
  additions: list[tuple[str, str, dict[str, Any]]],
) -> None:
  try:
    ledger_lines = ledger_content.decode("utf-8").splitlines()
    records = [json.loads(line) for line in ledger_lines if line.strip()]
  except (UnicodeDecodeError, json.JSONDecodeError) as error:
    raise IntakeError("Generated intake ledger is not valid UTF-8 JSONL") from error
  version_keys = [
    (normalize_note_id(record.get("upstreamId")), str(record.get("versionHash") or ""))
    for record in records
  ]
  if len(version_keys) != len(set(version_keys)):
    raise IntakeError("Generated intake ledger contains duplicate note versions")
  records_by_id = {str(record.get("intakeId") or ""): record for record in records}
  if "" in records_by_id or len(records_by_id) != len(records):
    raise IntakeError("Generated intake ledger contains missing or duplicate intake IDs")
  for relative_path, body, record in additions:
    if records_by_id.get(record["intakeId"]) != record:
      raise IntakeError(f"Generated intake record is missing from ledger: {record['intakeId']}")
    if record["relativePath"] != relative_path:
      raise IntakeError(f"Raw path differs from intake ledger: {record['intakeId']}")
    required_markers = (
      f"note_id: {record['upstreamId']}\n",
      f"version_hash: {record['versionHash']}\n",
      f"registry_source_id: {record['registrySourceId']}\n",
    )
    if any(marker not in body for marker in required_markers):
      raise IntakeError(f"Generated Raw metadata differs from ledger: {record['intakeId']}")


def content_hash(content: bytes) -> str:
  return hashlib.sha256(content).hexdigest()


def ordinary_note_ids_hash(note_ids: list[str]) -> str:
  ordered_ids = sorted(normalize_note_id(note_id) for note_id in note_ids)
  if len(ordered_ids) != len(set(ordered_ids)):
    raise IntakeError("Baseline note IDs must be unique")
  payload = "".join(f"{note_id}\n" for note_id in ordered_ids)
  return f"sha256:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"


def build_baseline_state(
  config: dict[str, Any],
  note_ids: list[str],
  *,
  completed_at: str,
) -> dict[str, Any]:
  ordered_ids = sorted(normalize_note_id(note_id) for note_id in note_ids)
  return {
    "schemaVersion": BASELINE_SCHEMA_VERSION,
    "status": "complete",
    "scope": "all",
    "knowledgeBaseId": str(config["knowledgeBaseId"]),
    "completedAt": completed_at,
    "ordinaryNoteCount": len(ordered_ids),
    "ordinaryNoteIds": ordered_ids,
    "ordinaryNoteIdsHash": ordinary_note_ids_hash(ordered_ids),
    "generatorVersion": BASELINE_GENERATOR_VERSION,
  }


def baseline_state_matches(
  state: dict[str, Any],
  expected: dict[str, Any],
) -> bool:
  identity_fields = (
    "schemaVersion", "status", "scope", "knowledgeBaseId",
    "ordinaryNoteCount", "ordinaryNoteIds", "ordinaryNoteIdsHash", "generatorVersion",
  )
  return (
    isinstance(state.get("completedAt"), str)
    and bool(state["completedAt"])
    and all(state.get(field) == expected.get(field) for field in identity_fields)
  )


def file_hash(path: Path) -> str:
  return content_hash(path.read_bytes())


def resolve_repo_path(repo_root: Path, relative_path: str) -> Path:
  relative = Path(relative_path)
  if relative.is_absolute() or ".." in relative.parts:
    raise IntakeError(f"Transaction path must stay inside repository: {relative_path}")
  resolved_root = repo_root.resolve()
  resolved = (resolved_root / relative).resolve()
  try:
    resolved.relative_to(resolved_root)
  except ValueError as error:
    raise IntakeError(f"Transaction path escapes repository: {relative_path}") from error
  return resolved


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
  atomic_write(path, f"{json_dumps(manifest, pretty=True)}\n")


def validate_transaction(
  repo_root: Path,
  manifest_path: Path,
  manifest: dict[str, Any],
) -> None:
  entries = manifest.get("entries")
  if manifest.get("schemaVersion") != TRANSACTION_SCHEMA_VERSION or not isinstance(entries, list):
    raise IntakeError(f"Invalid transaction manifest: {manifest_path}")
  seen_paths: set[str] = set()
  transaction_dir = manifest_path.parent
  for entry in entries:
    relative_path = entry.get("relativePath")
    if not isinstance(relative_path, str) or relative_path in seen_paths:
      raise IntakeError(f"Duplicate or invalid transaction path: {relative_path!r}")
    seen_paths.add(relative_path)
    target = resolve_repo_path(repo_root, relative_path)
    staged_path = transaction_dir / str(entry.get("stagedPath") or "")
    if not staged_path.is_file() or file_hash(staged_path) != entry.get("contentHash"):
      raise IntakeError(f"Staged content failed validation: {relative_path}")
    originally_existed = entry.get("originallyExisted") is True
    if entry.get("createOnly") is True and originally_existed:
      raise IntakeError(f"Refusing to overwrite create-only path: {relative_path}")
    if originally_existed:
      backup_path = transaction_dir / str(entry.get("backupPath") or "")
      if not backup_path.is_file() or file_hash(backup_path) != entry.get("originalHash"):
        raise IntakeError(f"Transaction backup failed validation: {relative_path}")
    elif target.exists():
      raise IntakeError(f"Target appeared while staging transaction: {relative_path}")


def prepare_file_transaction(
  repo_root: Path,
  runtime_root: Path,
  changes: dict[str, bytes],
  *,
  create_only_paths: set[str] | None = None,
  transaction_id: str | None = None,
) -> Path:
  if not changes:
    raise IntakeError("Cannot prepare an empty file transaction")
  transaction_id = transaction_id or uuid.uuid4().hex
  transaction_dir = runtime_root / "transactions" / transaction_id
  if transaction_dir.exists():
    raise IntakeError(f"Transaction already exists: {transaction_id}")
  staged_dir = transaction_dir / "staged"
  backup_dir = transaction_dir / "backups"
  staged_dir.mkdir(parents=True)
  backup_dir.mkdir(parents=True)
  create_only_paths = create_only_paths or set()
  entries = []

  for index, (relative_path, content) in enumerate(changes.items()):
    target = resolve_repo_path(repo_root, relative_path)
    staged_relative = Path("staged") / f"{index:04d}.bin"
    staged_path = transaction_dir / staged_relative
    atomic_write_bytes(staged_path, content)
    originally_existed = target.is_file()
    original_hash = file_hash(target) if originally_existed else None
    backup_relative = None
    if originally_existed:
      backup_relative = Path("backups") / f"{index:04d}.bin"
      atomic_write_bytes(transaction_dir / backup_relative, target.read_bytes())
    entries.append({
      "relativePath": relative_path,
      "stagedPath": staged_relative.as_posix(),
      "backupPath": backup_relative.as_posix() if backup_relative else None,
      "contentHash": content_hash(content),
      "originalHash": original_hash,
      "originallyExisted": originally_existed,
      "createOnly": relative_path in create_only_paths,
    })

  manifest = {
    "schemaVersion": TRANSACTION_SCHEMA_VERSION,
    "transactionId": transaction_id,
    "status": "prepared",
    "entries": entries,
  }
  manifest_path = transaction_dir / "manifest.json"
  write_manifest(manifest_path, manifest)
  validate_transaction(repo_root, manifest_path, manifest)
  return manifest_path


def rollback_file_transaction(repo_root: Path, manifest_path: Path) -> None:
  manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
  transaction_dir = manifest_path.parent
  manifest["status"] = "rolling-back"
  write_manifest(manifest_path, manifest)
  rollback_errors = []
  for entry in reversed(manifest["entries"]):
    relative_path = entry["relativePath"]
    try:
      target = resolve_repo_path(repo_root, relative_path)
      current_hash = file_hash(target) if target.is_file() else None
      if entry["originallyExisted"]:
        if current_hash not in (None, entry["contentHash"], entry["originalHash"]):
          raise IntakeError(
            f"Refusing to overwrite externally changed file during rollback: {relative_path}"
          )
        backup_path = transaction_dir / entry["backupPath"]
        if not backup_path.is_file() or file_hash(backup_path) != entry["originalHash"]:
          raise IntakeError(f"Transaction backup is corrupt: {relative_path}")
        atomic_write_bytes(target, backup_path.read_bytes())
      elif current_hash is not None:
        if current_hash != entry["contentHash"]:
          raise IntakeError(
            f"Refusing to delete externally changed file during rollback: {relative_path}"
          )
        target.unlink()
        fsync_directory(target.parent)
    except (IntakeError, OSError) as error:
      rollback_errors.append(str(error))
  if rollback_errors:
    manifest["status"] = "rollback-blocked"
    manifest["rollbackErrors"] = rollback_errors
    write_manifest(manifest_path, manifest)
    raise IntakeError("Transaction rollback needs manual review: " + "; ".join(rollback_errors))
  manifest.pop("rollbackErrors", None)
  manifest["status"] = "rolled-back"
  write_manifest(manifest_path, manifest)


def compact_committed_transaction(manifest_path: Path) -> None:
  manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
  if manifest.get("status") != "committed" or manifest.get("payloadCleaned") is True:
    return
  transaction_dir = manifest_path.parent
  for entry in manifest["entries"]:
    for field in ("stagedPath", "backupPath"):
      relative_path = entry.get(field)
      if relative_path:
        (transaction_dir / relative_path).unlink(missing_ok=True)
  for directory_name in ("staged", "backups"):
    directory = transaction_dir / directory_name
    try:
      directory.rmdir()
    except FileNotFoundError:
      pass
  manifest["payloadCleaned"] = True
  write_manifest(manifest_path, manifest)


def publish_file_transaction(repo_root: Path, manifest_path: Path) -> None:
  manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
  validate_transaction(repo_root, manifest_path, manifest)
  transaction_dir = manifest_path.parent
  manifest["status"] = "committing"
  write_manifest(manifest_path, manifest)
  try:
    for entry in manifest["entries"]:
      relative_path = entry["relativePath"]
      target = resolve_repo_path(repo_root, relative_path)
      current_hash = file_hash(target) if target.is_file() else None
      if current_hash != entry["originalHash"]:
        raise IntakeError(f"Target changed after staging: {relative_path}")
      staged_path = transaction_dir / entry["stagedPath"]
      if file_hash(staged_path) != entry["contentHash"]:
        raise IntakeError(f"Staged content changed before publish: {relative_path}")
      atomic_write_bytes(target, staged_path.read_bytes())
    manifest["status"] = "committed"
    write_manifest(manifest_path, manifest)
  except BaseException:
    rollback_file_transaction(repo_root, manifest_path)
    raise
  try:
    compact_committed_transaction(manifest_path)
  except OSError:
    pass


def recover_pending_transactions(repo_root: Path, runtime_root: Path) -> list[str]:
  transactions_root = runtime_root / "transactions"
  if not transactions_root.exists():
    return []
  recovered = []
  for manifest_path in sorted(transactions_root.glob("*/manifest.json")):
    try:
      manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
      raise IntakeError(f"Cannot read transaction manifest: {manifest_path}") from error
    status = manifest.get("status")
    if status in ("committing", "rolling-back", "rollback-blocked"):
      rollback_file_transaction(repo_root, manifest_path)
      recovered.append(str(manifest.get("transactionId") or manifest_path.parent.name))
    elif status == "prepared":
      manifest["status"] = "rolled-back"
      write_manifest(manifest_path, manifest)
      recovered.append(str(manifest.get("transactionId") or manifest_path.parent.name))
    elif status == "committed":
      try:
        compact_committed_transaction(manifest_path)
      except OSError:
        pass
    elif status != "rolled-back":
      raise IntakeError(f"Unknown transaction status {status!r}: {manifest_path}")
  return recovered


def commit_file_transaction(
  repo_root: Path,
  runtime_root: Path,
  changes: dict[str, bytes],
  *,
  create_only_paths: set[str] | None = None,
  transaction_id: str | None = None,
) -> str:
  manifest_path = prepare_file_transaction(
    repo_root,
    runtime_root,
    changes,
    create_only_paths=create_only_paths,
    transaction_id=transaction_id,
  )
  publish_file_transaction(repo_root, manifest_path)
  return manifest_path.parent.name


def write_runtime_state(runtime_root: Path, payload: dict[str, Any]) -> None:
  runtime_root.mkdir(parents=True, exist_ok=True)
  atomic_write(runtime_root / "status.json", f"{json_dumps(payload, pretty=True)}\n")


def write_failure_record(runtime_root: Path, payload: dict[str, Any]) -> None:
  failure_id = f"{os.getpid()}-{uuid.uuid4().hex}"
  failure_path = runtime_root / "failures" / f"{failure_id}.json"
  atomic_write(failure_path, f"{json_dumps(payload, pretty=True)}\n")


async def sync_notes(
  config: dict[str, Any],
  client: GetnoteClient,
  *,
  baseline: bool | None,
  dry_run: bool,
  only_note_id: str | None,
  now: str,
  repo_root: Path | None = None,
  runtime_root: Path | None = None,
  after_recovery: Callable[[], None] | None = None,
) -> dict[str, Any]:
  resolved_repo_root = Path(repo_root or REPO_ROOT).resolve()
  resolved_runtime_root = Path(runtime_root or (resolved_repo_root / RUNTIME_DIRECTORY)).resolve()
  try:
    with LocalWriterLock(resolved_runtime_root / "intake.lock"):
      recovered = recover_pending_transactions(resolved_repo_root, resolved_runtime_root)
      if after_recovery:
        after_recovery()
      effective_baseline = (
        baseline_state_required(resolved_repo_root, config)
        if baseline is None
        else baseline
      )
      await client.verify_auth()
      index_notes = await client.list_notes(config["knowledgeBaseId"])
      index_by_id = {}
      for index_note in index_notes:
        index_note_id = normalize_note_id(index_note.get("note_id", index_note.get("id")))
        if index_note_id in index_by_id:
          raise IntakeError(f"Duplicate note_id in Getnote knowledge-base index: {index_note_id}")
        index_by_id[index_note_id] = index_note
      normalized_only_note_id = normalize_note_id(only_note_id) if only_note_id else None
      if normalized_only_note_id:
        if normalized_only_note_id not in index_by_id:
          raise IntakeError(
            f"Note is not in configured knowledge base: {normalized_only_note_id}"
          )
        target_ids = [normalized_only_note_id]
      else:
        target_ids = sorted(index_by_id)
      ordinary_note_ids = sorted(index_by_id)
      ordinary_note_ids_digest = ordinary_note_ids_hash(ordinary_note_ids)

      ledger_path = resolve_repo_path(resolved_repo_root, config["ledgerPath"])
      ledger = read_jsonl(ledger_path)
      if effective_baseline and any(
        record.get("changeType") != "baseline" and record.get("status") != "baseline"
        for record in ledger
      ):
        raise IntakeError(
          "Cannot establish a full baseline from an ambiguous non-baseline ledger"
        )
      known_versions = {
        (normalize_note_id(record.get("upstreamId")), str(record.get("versionHash") or ""))
        for record in ledger
      }
      additions = []
      download_failures = []

      for note_id in target_ids:
        try:
          note = await client.get_note(note_id)
          returned_note_id = normalize_note_id(note.get("note_id", note.get("id")))
          if returned_note_id != note_id:
            raise IntakeError(
              f"Getnote returned note {returned_note_id} while requesting {note_id}"
            )
          previous = latest_intake_record([
            existing
            for existing in ledger
            if normalize_note_id(existing.get("upstreamId")) == note_id
          ])
          relative_path, body, record = render_markdown(
            note,
            config,
            ingested_at=now,
            baseline=effective_baseline and previous is None,
          )
          version_key = (record["upstreamId"], record["versionHash"])
          if version_key in known_versions:
            continue
          if previous:
            record["changeType"] = "revision"
            record["previousIntakeId"] = previous.get("intakeId")
            record["status"] = "registered"
          elif effective_baseline:
            record["changeType"] = "baseline"
            record["previousIntakeId"] = None
            record["status"] = "baseline"
          else:
            record["changeType"] = "new-source"
            record["previousIntakeId"] = None
            record["status"] = "registered"
          additions.append((relative_path, body, record))
        except IntakeError as error:
          download_failures.append({"noteId": note_id, "error": str(error)})

      if download_failures:
        raise IntakeBatchError(download_failures)

      baseline_state_needed = False
      baseline_state_content: bytes | None = None
      baseline_state_path = str(config.get("baselineStatePath") or "")
      if effective_baseline and normalized_only_note_id is None:
        if not baseline_state_path:
          raise IntakeError("baselineStatePath is required for a full baseline")
        expected_baseline_state = build_baseline_state(
          config,
          ordinary_note_ids,
          completed_at=now,
        )
        baseline_target = resolve_repo_path(resolved_repo_root, baseline_state_path)
        if baseline_target.is_file():
          try:
            existing_baseline_state = json.loads(baseline_target.read_text(encoding="utf-8"))
          except (OSError, json.JSONDecodeError) as error:
            raise IntakeError("Existing intake baseline marker is invalid") from error
          if not isinstance(existing_baseline_state, dict) or not baseline_state_matches(
            existing_baseline_state,
            expected_baseline_state,
          ):
            raise IntakeError("Existing intake baseline marker conflicts with the full scan")
        else:
          baseline_state_needed = True
          baseline_state_content = (
            f"{json_dumps(expected_baseline_state, pretty=True)}\n".encode("utf-8")
          )

      batch_id = build_batch_id(
        now,
        [record["intakeId"] for _, _, record in additions],
      ) if additions else None
      for _, _, record in additions:
        record["batchId"] = batch_id

      transaction_id = None
      if not dry_run and (additions or baseline_state_needed):
        changes: dict[str, bytes] = {
          relative_path: body.encode("utf-8")
          for relative_path, body, _ in additions
        }
        if additions:
          ledger.extend(record for _, _, record in additions)
          ledger_content = stable_jsonl(ledger).encode("utf-8")
          validate_intake_payloads(ledger_content, additions)
          changes[config["ledgerPath"]] = ledger_content
        if baseline_state_needed and baseline_state_content is not None:
          changes[baseline_state_path] = baseline_state_content
        transaction_id = commit_file_transaction(
          resolved_repo_root,
          resolved_runtime_root,
          changes,
          create_only_paths={
            *[relative_path for relative_path, _, _ in additions],
            *([baseline_state_path] if baseline_state_needed else []),
          },
        )

      changed = bool(additions or baseline_state_needed)
      result = {
        "status": "dry-run" if dry_run else ("changed" if changed else "zero-change"),
        "knowledgeBaseId": config["knowledgeBaseId"],
        "baselineMode": effective_baseline,
        "ordinaryNotesSeen": len(index_notes),
        "ordinaryNoteIds": ordinary_note_ids,
        "ordinaryNoteIdsHash": ordinary_note_ids_digest,
        "newVersions": len(additions),
        "subscriptionBloggerImport": False,
        "liveImport": False,
        "paths": [relative_path for relative_path, _, _ in additions],
        "batchId": batch_id,
        "transactionId": transaction_id,
        "baselineStatePath": baseline_state_path or None,
        "baselineStateNeeded": baseline_state_needed,
        "baselineStateChanged": baseline_state_needed and not dry_run,
        "recoveredTransactions": recovered,
      }
      try:
        write_runtime_state(resolved_runtime_root, {
          "schemaVersion": "1.0",
          "status": result["status"],
          "completedAt": now,
          "knowledgeBaseId": config["knowledgeBaseId"],
          "baselineMode": effective_baseline,
          "ordinaryNotesSeen": len(index_notes),
          "ordinaryNoteIdsHash": ordinary_note_ids_digest,
          "newVersions": len(additions),
          "batchId": batch_id,
          "transactionId": transaction_id,
          "baselineStateChanged": baseline_state_needed and not dry_run,
          "recoveredTransactions": recovered,
        })
      except OSError as error:
        result["runtimeStateWarning"] = str(error)
      return result
  except Exception as error:
    failures = error.failures if isinstance(error, IntakeBatchError) else []
    failure_payload = {
      "schemaVersion": "1.0",
      "status": "failed",
      "failedAt": now,
      "knowledgeBaseId": config.get("knowledgeBaseId"),
      "error": str(error),
      "failures": failures,
    }
    try:
      write_runtime_state(resolved_runtime_root, failure_payload)
      write_failure_record(resolved_runtime_root, failure_payload)
    except OSError:
      pass
    if isinstance(error, IntakeError):
      raise
    raise IntakeError(str(error)) from error


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
  parser.add_argument("--baseline", action="store_true")
  parser.add_argument("--dry-run", action="store_true")
  parser.add_argument("--note-id")
  parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
  parser.add_argument("--runtime-root", type=Path)
  return parser.parse_args()


async def async_main() -> int:
  args = parse_args()
  config = load_config(args.config)
  now = os.environ.get("WORKBENCH_NOW") or dt.datetime.now(dt.timezone.utc).isoformat()
  result = await sync_notes(
    config,
    GetnoteClient(),
    baseline=args.baseline,
    dry_run=args.dry_run,
    only_note_id=args.note_id,
    now=now,
    repo_root=args.repo_root,
    runtime_root=args.runtime_root,
  )
  print(json_dumps(result, pretty=True))
  return 0


def main() -> int:
  try:
    return asyncio.run(async_main())
  except IntakeError as error:
    print(json_dumps({"status": "failed", "error": str(error)}, pretty=True), file=sys.stderr)
    return 1


if __name__ == "__main__":
  raise SystemExit(main())
