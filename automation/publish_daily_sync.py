#!/usr/bin/env python3
"""Publish one daily Getnote intake from an isolated Git worktree."""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import fcntl
import hashlib
import json
import os
import sys
import tempfile
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterator


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REMOTE = "origin"
DEFAULT_BRANCH = "main"
DEFAULT_PIPELINE = "automation/run_daily_pipeline.py"
JOURNAL_SCHEMA_VERSION = "1.0"
JOURNAL_RELATIVE_PATH = Path(".cache/getnote-intake/publish-journal.json")
RECOVERABLE_JOURNAL_STATES = {
  "started",
  "pipeline-complete",
  "git-staged",
  "git-committed",
}

ALLOWED_EXACT_PATHS = {
  "3-processing/index/governance-lint-report.json",
  "3-processing/index/intake-baseline.json",
  "3-processing/index/intake-batches.jsonl",
  "3-processing/index/intake-ledger.jsonl",
  "3-processing/index/source-registry.jsonl",
  "3-processing/index/source-registry.snapshot.json",
  "3-processing/wiki/NOW.md",
  "3-processing/wiki/sources/README.md",
}
ALLOWED_PATH_PREFIXES = (
  "1-raw/Joe\u4e3b\u52a8\u6536\u5f55/AI\u8d44\u8baf/",
)


class PublishError(RuntimeError):
  """Raised when the isolated publisher cannot proceed safely."""


@dataclass(frozen=True)
class CommandResult:
  stdout: str
  stderr: str


async def run_command(args: list[str], cwd: Path) -> CommandResult:
  process = await asyncio.create_subprocess_exec(
    *args,
    cwd=cwd,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
  )
  stdout, stderr = await process.communicate()
  result = CommandResult(
    stdout.decode("utf-8", errors="replace"),
    stderr.decode("utf-8", errors="replace"),
  )
  if process.returncode != 0:
    detail = result.stderr.strip() or result.stdout.strip()
    raise PublishError(f"Command failed ({process.returncode}): {' '.join(args)}\n{detail}")
  return result


async def git_output(repo_root: Path, *args: str) -> str:
  result = await run_command(["git", *args], repo_root)
  return result.stdout.rstrip("\r\n")


def json_dumps(value: object) -> str:
  return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def fsync_directory(path: Path) -> None:
  descriptor = os.open(path, os.O_RDONLY)
  try:
    os.fsync(descriptor)
  finally:
    os.close(descriptor)


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
  try:
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
      handle.write(f"{json_dumps(payload)}\n")
      handle.flush()
      os.fsync(handle.fileno())
    os.replace(temp_name, path)
    fsync_directory(path.parent)
  except BaseException:
    Path(temp_name).unlink(missing_ok=True)
    raise


def load_journal(path: Path) -> dict[str, Any] | None:
  if not path.is_file():
    return None
  try:
    payload = json.loads(path.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError) as error:
    raise PublishError(f"Cannot read publisher journal: {path}") from error
  if not isinstance(payload, dict):
    raise PublishError(f"Publisher journal must be one JSON object: {path}")
  return payload


def write_journal(path: Path, journal: dict[str, Any], state: str, **updates: Any) -> dict[str, Any]:
  updated = {**journal, **updates, "state": state}
  atomic_write_json(path, updated)
  return updated


def clear_journal(path: Path) -> None:
  if path.is_file():
    path.unlink()
    fsync_directory(path.parent)


def validate_journal(
  journal: dict[str, Any],
  *,
  remote: str,
  branch: str,
  pipeline: str,
) -> None:
  required = {
    "schemaVersion",
    "runId",
    "state",
    "remote",
    "branch",
    "pipeline",
    "baseCommit",
    "startedAt",
  }
  missing = sorted(field for field in required if not journal.get(field))
  if missing:
    raise PublishError("Publisher journal is incomplete: " + ", ".join(missing))
  if journal["schemaVersion"] != JOURNAL_SCHEMA_VERSION:
    raise PublishError(f"Unsupported publisher journal schema: {journal['schemaVersion']}")
  if journal["state"] not in RECOVERABLE_JOURNAL_STATES:
    raise PublishError(f"Unsupported publisher journal state: {journal['state']}")
  expected_boundary = (remote, branch, pipeline)
  actual_boundary = (journal["remote"], journal["branch"], journal["pipeline"])
  if actual_boundary != expected_boundary:
    raise PublishError(
      "Publisher journal boundary differs from this run: "
      f"expected={expected_boundary!r}, actual={actual_boundary!r}"
    )


def file_sha256(path: Path) -> str:
  if not path.is_file():
    raise PublishError(f"Expected publisher-owned file is missing: {path}")
  return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def hash_owned_paths(repo_root: Path, paths: list[str]) -> dict[str, str]:
  allowed_paths = validate_allowed_paths(paths)
  return {
    relative_path: file_sha256(repo_root / relative_path)
    for relative_path in allowed_paths
  }


def validate_owned_paths(
  repo_root: Path,
  paths: list[str],
  expected_hashes: dict[str, str],
) -> list[str]:
  allowed_paths = validate_allowed_paths(paths)
  if sorted(expected_hashes) != allowed_paths:
    raise PublishError("Publisher journal paths differ from current managed paths")
  actual_hashes = hash_owned_paths(repo_root, allowed_paths)
  if actual_hashes != expected_hashes:
    raise PublishError("Publisher-owned path hashes changed after pipeline completion")
  return allowed_paths


def normalize_git_path(value: str) -> str:
  path = PurePosixPath(value)
  if path.is_absolute() or ".." in path.parts:
    raise PublishError(f"Unsafe Git path: {value}")
  return path.as_posix()


def is_allowed_path(value: str) -> bool:
  path = normalize_git_path(value)
  return path in ALLOWED_EXACT_PATHS or any(
    path.startswith(prefix) for prefix in ALLOWED_PATH_PREFIXES
  )


def validate_allowed_paths(paths: list[str]) -> list[str]:
  normalized = sorted({normalize_git_path(path) for path in paths if path})
  rejected = [path for path in normalized if not is_allowed_path(path)]
  if rejected:
    raise PublishError(f"Publisher path whitelist rejected: {', '.join(rejected)}")
  return normalized


def parse_porcelain_paths(output: str) -> list[str]:
  paths = []
  entries = output.split("\0")
  index = 0
  while index < len(entries):
    entry = entries[index]
    index += 1
    if not entry:
      continue
    if len(entry) < 4:
      raise PublishError(f"Invalid Git status entry: {entry!r}")
    status = entry[:2]
    paths.append(entry[3:])
    if "R" in status or "C" in status:
      if index >= len(entries) or not entries[index]:
        raise PublishError("Invalid Git rename/copy status")
      paths.append(entries[index])
      index += 1
  return paths


async def changed_paths(repo_root: Path) -> list[str]:
  output = await git_output(
    repo_root,
    "status",
    "--porcelain=v1",
    "-z",
    "--untracked-files=all",
  )
  return sorted(set(parse_porcelain_paths(output))) if output else []


async def align_clean_worktree_to_remote(
  repo_root: Path,
  remote_ref: str,
) -> tuple[str, bool]:
  local_head = await git_output(repo_root, "rev-parse", "HEAD")
  remote_head = await git_output(repo_root, "rev-parse", remote_ref)
  if local_head == remote_head:
    return remote_head, False

  merge_base = await git_output(repo_root, "merge-base", local_head, remote_head)
  if merge_base != local_head:
    raise PublishError(
      f"Worktree HEAD {local_head[:12]} and {remote_ref} {remote_head[:12]} "
      "have diverged or the worktree is locally ahead; refusing merge or rebase"
    )
  await git_output(repo_root, "switch", "--detach", remote_ref)
  aligned_head = await git_output(repo_root, "rev-parse", "HEAD")
  if aligned_head != remote_head:
    raise PublishError(f"Failed to align isolated worktree to {remote_ref}")
  return remote_head, True


def ensure_secondary_worktree(repo_root: Path) -> None:
  git_pointer = repo_root / ".git"
  if not git_pointer.is_file():
    raise PublishError(
      "Daily publishing is allowed only in an isolated secondary worktree; "
      "the primary Joe worktree is read-only for this operation"
    )


def parse_pipeline_result(output: str) -> dict[str, object]:
  try:
    result = json.loads(output)
  except json.JSONDecodeError as error:
    raise PublishError("Daily pipeline did not return one valid JSON object") from error
  if not isinstance(result, dict) or result.get("status") not in {"changed", "zero-change"}:
    raise PublishError(f"Unexpected daily pipeline result: {result!r}")
  return result


def resolve_lock_path(remote_url: str) -> Path:
  digest = hashlib.sha256(remote_url.encode("utf-8")).hexdigest()[:16]
  return Path(tempfile.gettempdir()) / f"waic-daily-sync-{digest}.lock"


@contextmanager
def single_writer_lock(lock_path: Path) -> Iterator[None]:
  lock_path.parent.mkdir(parents=True, exist_ok=True)
  with lock_path.open("a+", encoding="utf-8") as handle:
    try:
      fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as error:
      raise PublishError(f"Another daily publisher holds {lock_path}") from error
    handle.seek(0)
    handle.truncate()
    handle.write(f"pid={os.getpid()}\n")
    handle.flush()
    try:
      yield
    finally:
      fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def journal_result(journal: dict[str, Any]) -> dict[str, object]:
  result = journal.get("pipelineResult")
  if not isinstance(result, dict) or result.get("status") not in {"changed", "zero-change"}:
    raise PublishError("Publisher journal has no valid pipeline result")
  return result


def journal_paths(journal: dict[str, Any]) -> tuple[list[str], dict[str, str]]:
  paths = journal.get("paths")
  hashes = journal.get("pathHashes")
  if not isinstance(paths, list) or not all(isinstance(path, str) for path in paths):
    raise PublishError("Publisher journal has no valid managed path list")
  if not isinstance(hashes, dict) or not all(
    isinstance(path, str) and isinstance(value, str)
    for path, value in hashes.items()
  ):
    raise PublishError("Publisher journal has no valid managed path hashes")
  return paths, hashes


async def push_owned_commit(
  repo_root: Path,
  *,
  remote: str,
  branch: str,
  remote_ref: str,
  journal_path: Path,
  journal: dict[str, Any],
  resumed: bool,
) -> dict[str, object]:
  result = journal_result(journal)
  commit_sha = str(journal.get("commit") or "")
  base_commit = str(journal["baseCommit"])
  if not commit_sha:
    raise PublishError("Publisher journal has no owned commit")

  await git_output(repo_root, "fetch", "--prune", remote, branch)
  current_remote_head = await git_output(repo_root, "rev-parse", remote_ref)
  if current_remote_head == commit_sha:
    clear_journal(journal_path)
    return {
      **result,
      "commitCreated": True,
      "pushed": True,
      "pushRecovered": True,
      "resumed": True,
      "baseCommit": base_commit,
      "commit": commit_sha,
      "paths": journal.get("paths", []),
      "worktreeFastForwarded": bool(journal.get("worktreeFastForwarded")),
    }
  if current_remote_head != base_commit:
    raise PublishError(
      f"{remote}/{branch} advanced from {base_commit[:12]} to "
      f"{current_remote_head[:12]}; owned commit retained locally, push stopped"
    )

  await git_output(repo_root, "push", remote, f"HEAD:refs/heads/{branch}")
  clear_journal(journal_path)
  return {
    **result,
    "commitCreated": True,
    "pushed": True,
    "resumed": resumed,
    "baseCommit": base_commit,
    "commit": commit_sha,
    "paths": journal.get("paths", []),
    "worktreeFastForwarded": bool(journal.get("worktreeFastForwarded")),
  }


async def validate_committed_resume(
  repo_root: Path,
  journal: dict[str, Any],
  current_head: str,
) -> dict[str, Any]:
  base_commit = str(journal["baseCommit"])
  if journal["state"] == "started":
    raise PublishError("Repository advanced while the publisher journal has no completed pipeline")
  declared_commit = str(journal.get("commit") or "")
  if declared_commit and declared_commit != current_head:
    raise PublishError(
      f"Publisher journal owns commit {declared_commit[:12]}, not current HEAD {current_head[:12]}"
    )
  parent = await git_output(repo_root, "rev-parse", f"{current_head}^")
  if parent != base_commit:
    raise PublishError(
      f"Owned commit parent {parent[:12]} differs from journal base {base_commit[:12]}"
    )
  if await changed_paths(repo_root):
    raise PublishError("Owned commit recovery requires a clean checked-out worktree")

  expected_paths, expected_hashes = journal_paths(journal)
  commit_output = await git_output(
    repo_root,
    "diff-tree",
    "--no-commit-id",
    "--name-only",
    "-r",
    "-z",
    current_head,
  )
  committed_paths = validate_allowed_paths(commit_output.split("\0"))
  if committed_paths != sorted(expected_paths):
    raise PublishError("Owned commit paths differ from publisher journal")
  validate_owned_paths(repo_root, committed_paths, expected_hashes)
  return {**journal, "state": "git-committed", "commit": current_head}


async def commit_pipeline_result(
  repo_root: Path,
  *,
  remote: str,
  branch: str,
  remote_ref: str,
  pipeline: str,
  journal_path: Path,
  journal: dict[str, Any],
  resumed: bool,
) -> dict[str, object]:
  state = str(journal["state"])
  current_paths_for_commit: list[str] | None = None
  if state == "started":
    if resumed:
      dirty_before_pipeline = await changed_paths(repo_root)
      if dirty_before_pipeline:
        validate_allowed_paths(dirty_before_pipeline)
    pipeline_result = await run_command([sys.executable, pipeline], repo_root)
    result = parse_pipeline_result(pipeline_result.stdout)
    paths = await changed_paths(repo_root)

    if result["status"] == "zero-change" and not paths:
      clear_journal(journal_path)
      return {
        **result,
        "commitCreated": False,
        "pushed": False,
        "resumed": resumed,
        "baseCommit": journal["baseCommit"],
        "worktreeFastForwarded": bool(journal.get("worktreeFastForwarded")),
      }
    if not paths:
      raise PublishError("Pipeline reported changed but Git has no publishable changes")

    allowed_paths = validate_allowed_paths(paths)
    effective_result = dict(result)
    if result["status"] == "zero-change":
      effective_result["status"] = "changed"
      effective_result["recoveredInterruptedRun"] = True
    path_hashes = hash_owned_paths(repo_root, allowed_paths)
    journal = write_journal(
      journal_path,
      journal,
      "pipeline-complete",
      pipelineResult=effective_result,
      paths=allowed_paths,
      pathHashes=path_hashes,
    )
    current_paths_for_commit = allowed_paths
  elif state not in {"pipeline-complete", "git-staged"}:
    raise PublishError(f"Cannot create a commit from publisher journal state: {state}")

  result = journal_result(journal)
  expected_paths, expected_hashes = journal_paths(journal)
  current_paths = current_paths_for_commit or await changed_paths(repo_root)
  if sorted(current_paths) != sorted(expected_paths):
    raise PublishError(
      "Current Git changes differ from publisher journal: "
      f"expected={sorted(expected_paths)!r}, actual={sorted(current_paths)!r}"
    )
  allowed_paths = validate_owned_paths(repo_root, current_paths, expected_hashes)

  await git_output(repo_root, "add", "--", *allowed_paths)
  remaining = await changed_paths(repo_root)
  if sorted(remaining) != allowed_paths:
    raise PublishError("Git changes differ after staging publisher-owned paths")
  staged_output = await git_output(
    repo_root,
    "diff",
    "--cached",
    "--name-only",
    "-z",
  )
  staged_paths = validate_allowed_paths(staged_output.split("\0"))
  if staged_paths != allowed_paths:
    raise PublishError("Staged paths differ from publisher journal")
  journal = write_journal(journal_path, journal, "git-staged")

  new_versions = int(result.get("newVersions", 0))
  run_date = str(result.get("runDate") or dt.date.today().isoformat())
  commit_message = f"chore(intake): sync {new_versions} Getnote version(s) on {run_date}"
  await git_output(repo_root, "commit", "-m", commit_message)
  commit_sha = await git_output(repo_root, "rev-parse", "HEAD")
  journal = write_journal(
    journal_path,
    journal,
    "git-committed",
    commit=commit_sha,
  )
  return await push_owned_commit(
    repo_root,
    remote=remote,
    branch=branch,
    remote_ref=remote_ref,
    journal_path=journal_path,
    journal=journal,
    resumed=resumed,
  )


async def publish(
  repo_root: Path,
  *,
  remote: str,
  branch: str,
  pipeline: str,
  lock_path: Path | None = None,
  journal_path: Path | None = None,
) -> dict[str, object]:
  ensure_secondary_worktree(repo_root)
  remote_url = await git_output(repo_root, "config", "--get", f"remote.{remote}.url")
  if not remote_url:
    raise PublishError(f"Git remote is not configured: {remote}")

  with single_writer_lock(lock_path or resolve_lock_path(remote_url)):
    resolved_journal_path = journal_path or (repo_root / JOURNAL_RELATIVE_PATH)
    pipeline_path = normalize_git_path(pipeline)
    remote_ref = f"refs/remotes/{remote}/{branch}"
    journal = load_journal(resolved_journal_path)

    if journal is None:
      before = await changed_paths(repo_root)
      if before:
        raise PublishError(
          "Isolated worktree must be clean before daily sync: " + ", ".join(before)
        )
      await git_output(repo_root, "fetch", "--prune", remote, branch)
      initial_head, fast_forwarded = await align_clean_worktree_to_remote(
        repo_root,
        remote_ref,
      )
      journal = {
        "schemaVersion": JOURNAL_SCHEMA_VERSION,
        "runId": uuid.uuid4().hex,
        "state": "started",
        "remote": remote,
        "branch": branch,
        "pipeline": pipeline_path,
        "baseCommit": initial_head,
        "startedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "worktreeFastForwarded": fast_forwarded,
      }
      atomic_write_json(resolved_journal_path, journal)
      return await commit_pipeline_result(
        repo_root,
        remote=remote,
        branch=branch,
        remote_ref=remote_ref,
        pipeline=pipeline_path,
        journal_path=resolved_journal_path,
        journal=journal,
        resumed=False,
      )

    validate_journal(
      journal,
      remote=remote,
      branch=branch,
      pipeline=pipeline_path,
    )
    await git_output(repo_root, "fetch", "--prune", remote, branch)
    current_head = await git_output(repo_root, "rev-parse", "HEAD")
    current_remote_head = await git_output(repo_root, "rev-parse", remote_ref)
    base_commit = str(journal["baseCommit"])
    declared_commit = str(journal.get("commit") or "")

    if declared_commit and current_remote_head == declared_commit:
      if current_head != declared_commit:
        raise PublishError("Remote contains the owned commit but worktree HEAD differs")
      journal = await validate_committed_resume(repo_root, journal, current_head)
      clear_journal(resolved_journal_path)
      return {
        **journal_result(journal),
        "commitCreated": True,
        "pushed": True,
        "pushRecovered": True,
        "resumed": True,
        "baseCommit": base_commit,
        "commit": current_head,
        "paths": journal.get("paths", []),
        "worktreeFastForwarded": bool(journal.get("worktreeFastForwarded")),
      }

    if current_head != base_commit:
      journal = await validate_committed_resume(repo_root, journal, current_head)
      journal = write_journal(
        resolved_journal_path,
        journal,
        "git-committed",
        commit=current_head,
      )
      return await push_owned_commit(
        repo_root,
        remote=remote,
        branch=branch,
        remote_ref=remote_ref,
        journal_path=resolved_journal_path,
        journal=journal,
        resumed=True,
      )

    if current_remote_head != base_commit:
      raise PublishError(
        f"{remote}/{branch} advanced from journal base {base_commit[:12]} to "
        f"{current_remote_head[:12]}; recovery stopped"
      )
    return await commit_pipeline_result(
      repo_root,
      remote=remote,
      branch=branch,
      remote_ref=remote_ref,
      pipeline=pipeline_path,
      journal_path=resolved_journal_path,
      journal=journal,
      resumed=True,
    )


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
  parser.add_argument("--remote", default=DEFAULT_REMOTE)
  parser.add_argument("--branch", default=DEFAULT_BRANCH)
  parser.add_argument("--pipeline", default=DEFAULT_PIPELINE)
  parser.add_argument("--lock-path", type=Path)
  parser.add_argument("--journal-path", type=Path)
  return parser.parse_args()


async def async_main() -> int:
  args = parse_args()
  result = await publish(
    args.repo_root.resolve(),
    remote=args.remote,
    branch=args.branch,
    pipeline=args.pipeline,
    lock_path=args.lock_path,
    journal_path=args.journal_path,
  )
  print(json_dumps(result))
  return 0


def main() -> int:
  try:
    return asyncio.run(async_main())
  except PublishError as error:
    print(json_dumps({"status": "failed", "error": str(error)}), file=sys.stderr)
    return 1


if __name__ == "__main__":
  raise SystemExit(main())
