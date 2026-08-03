#!/usr/bin/env python3
"""Derive auditable intake views inside a complete repository root."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = REPO_ROOT / "3-processing/governance/build-source-registry.mjs"
LINT_PATH = REPO_ROOT / "3-processing/governance/lint-knowledge-base.mjs"
BATCH_LEDGER_PATH = Path("3-processing/index/intake-batches.jsonl")
INTAKE_LEDGER_PATH = Path("3-processing/index/intake-ledger.jsonl")
REGISTRY_PATH = Path("3-processing/index/source-registry.jsonl")
SNAPSHOT_PATH = Path("3-processing/index/source-registry.snapshot.json")
ASSESSMENTS_PATH = Path("3-processing/index/source-assessments.jsonl")
NOW_PATH = Path("3-processing/wiki/NOW.md")
LINT_REPORT_PATH = Path("3-processing/index/governance-lint-report.json")
NOW_START_MARKER = "<!-- workbench:now:auto:start v1 -->"
NOW_END_MARKER = "<!-- workbench:now:auto:end -->"
GENERATOR_VERSION = "phase2-v1"
VALID_TRIAGE_STATUSES = {"pending", "routed", "integrated"}
LOCAL_TIMEZONE = ZoneInfo("Asia/Shanghai")


class DerivationError(RuntimeError):
  """Raised when deterministic views cannot be derived safely."""


def stableJson(value: Any, *, pretty: bool = False) -> str:
  if pretty:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
  return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(value: bytes | str) -> str:
  payload = value.encode("utf-8") if isinstance(value, str) else value
  return hashlib.sha256(payload).hexdigest()


def localDate(value: str) -> str:
  try:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
  except ValueError:
    return value[:10]
  if parsed.tzinfo is None:
    parsed = parsed.replace(tzinfo=dt.timezone.utc)
  return parsed.astimezone(LOCAL_TIMEZONE).date().isoformat()


def readJsonl(path: Path, *, required: bool = True) -> list[dict[str, Any]]:
  if not path.exists():
    if required:
      raise DerivationError(f"Missing required JSONL: {path}")
    return []
  records = []
  for lineNumber, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
    if not line.strip():
      continue
    try:
      record = json.loads(line)
    except json.JSONDecodeError as error:
      raise DerivationError(f"Invalid JSONL at {path}:{lineNumber}") from error
    if not isinstance(record, dict):
      raise DerivationError(f"JSONL record must be an object at {path}:{lineNumber}")
    records.append(record)
  return records


def renderJsonl(records: list[dict[str, Any]]) -> str:
  return "".join(f"{stableJson(record)}\n" for record in records)


def atomicWriteIfChanged(path: Path, content: str) -> bool:
  payload = content.encode("utf-8")
  if path.exists() and path.read_bytes() == payload:
    return False
  path.parent.mkdir(parents=True, exist_ok=True)
  descriptor, tempName = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
  try:
    with os.fdopen(descriptor, "wb") as handle:
      handle.write(payload)
      handle.flush()
      os.fsync(handle.fileno())
    os.replace(tempName, path)
  except Exception:
    Path(tempName).unlink(missing_ok=True)
    raise
  return True


def runNode(scriptPath: Path, repoRoot: Path, generatedAt: str) -> dict[str, Any]:
  process = subprocess.run(
    [
      "node",
      str(scriptPath),
      "--repo-root",
      str(repoRoot),
      "--generated-at",
      generatedAt,
    ],
    capture_output=True,
    check=False,
    text=True,
  )
  if process.returncode != 0:
    message = process.stderr.strip() or process.stdout.strip()
    raise DerivationError(message or f"Node command failed: {scriptPath.name}")
  try:
    payload = json.loads(process.stdout)
  except json.JSONDecodeError as error:
    raise DerivationError(f"Invalid JSON from {scriptPath.name}") from error
  if not isinstance(payload, dict):
    raise DerivationError(f"Invalid result from {scriptPath.name}")
  return payload


def classificationFor(record: dict[str, Any], seenUpstreamIds: set[str]) -> str:
  declared = record.get("changeType")
  if declared in {"baseline", "new-source", "new-version", "revision"}:
    return "new-version" if declared == "revision" else str(declared)
  upstreamId = str(record.get("upstreamId") or "")
  if record.get("status") == "baseline":
    return "baseline"
  return "new-version" if upstreamId in seenUpstreamIds else "new-source"


def deriveBatchId(records: list[dict[str, Any]]) -> str:
  declaredIds = {str(record.get("batchId")) for record in records if record.get("batchId")}
  if len(declaredIds) > 1:
    raise DerivationError("Records in one observed batch declare different batchId values")
  if declaredIds:
    return next(iter(declaredIds))
  identity = {
    "firstSeenAt": min(str(record.get("firstSeenAt") or "") for record in records),
    "intakeIds": sorted(str(record.get("intakeId") or "") for record in records),
  }
  return f"BAT-GETNOTE-{sha256(stableJson(identity))[:16]}"


def groupIntakeRecords(records: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
  grouped: dict[str, list[dict[str, Any]]] = {}
  for record in records:
    declaredBatchId = record.get("batchId")
    groupKey = f"id:{declaredBatchId}" if declaredBatchId else f"seen:{record.get('firstSeenAt', '')}"
    grouped.setdefault(groupKey, []).append(record)
  return sorted(
    [sorted(group, key=lambda item: str(item.get("intakeId") or "")) for group in grouped.values()],
    key=lambda group: (
      min(str(item.get("firstSeenAt") or "") for item in group),
      deriveBatchId(group),
    ),
  )


def buildBatches(
  intakeRecords: list[dict[str, Any]],
  registryRecords: list[dict[str, Any]],
  assessmentRecords: list[dict[str, Any]],
  existingBatches: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
  registryBySourceId = {
    str(record.get("sourceId")): record
    for record in registryRecords
    if record.get("sourceId")
  }
  assessedSourceIds = {
    str(record.get("sourceRef"))
    for record in assessmentRecords
    if record.get("sourceRef")
  }
  intakeIds = [str(record.get("intakeId") or "") for record in intakeRecords]
  if any(not intakeId for intakeId in intakeIds) or len(set(intakeIds)) != len(intakeIds):
    raise DerivationError("Intake IDs must be non-empty and unique")

  for record in intakeRecords:
    registrySourceId = str(record.get("registrySourceId") or "")
    registryRecord = registryBySourceId.get(registrySourceId)
    if not registryRecord:
      raise DerivationError(f"Intake source is missing from registry: {registrySourceId}")
    if registryRecord.get("relativePath") != record.get("relativePath"):
      raise DerivationError(f"Intake source path does not match registry: {registrySourceId}")
    triageStatus = str(record.get("triageStatus") or "")
    if triageStatus not in VALID_TRIAGE_STATUSES:
      raise DerivationError(f"Invalid triageStatus for {record.get('intakeId')}: {triageStatus}")

  orderedRecords = sorted(
    intakeRecords,
    key=lambda record: (
      str(record.get("firstSeenAt") or ""),
      str(record.get("intakeId") or ""),
    ),
  )
  seenUpstreamIds: set[str] = set()
  classifications: dict[str, str] = {}
  for record in orderedRecords:
    intakeId = str(record["intakeId"])
    classifications[intakeId] = classificationFor(record, seenUpstreamIds)
    seenUpstreamIds.add(str(record.get("upstreamId") or ""))

  rawEvidenceRecords = sum(record.get("sourceLayer") == "raw" for record in registryRecords)
  dataEvidenceRecords = sum(record.get("sourceLayer") == "data" for record in registryRecords)
  baseRawRecords = rawEvidenceRecords - len(intakeRecords)
  baseRegistryRecords = len(registryRecords) - len(intakeRecords)
  if baseRawRecords < 0 or baseRegistryRecords < 0:
    raise DerivationError("Intake count exceeds registry evidence count")

  existingBatches = existingBatches or []
  existingByBatchId = {
    str(batch.get("batchId")): batch
    for batch in existingBatches
    if batch.get("batchId")
  }
  if len(existingByBatchId) != len(existingBatches):
    raise DerivationError("Existing batch IDs must be non-empty and unique")
  batches = []
  cumulativeVersions = 0
  previousBatchId = None
  groups = groupIntakeRecords(intakeRecords)
  groupBatchIds = [deriveBatchId(group) for group in groups]
  if not set(existingByBatchId).issubset(groupBatchIds):
    raise DerivationError("Existing batch ledger references intake records that no longer exist")
  createdNewBatch = False
  for group in groups:
    batchId = deriveBatchId(group)
    groupIntakeIds = [str(record["intakeId"]) for record in group]
    existingBatch = existingByBatchId.get(batchId)
    if existingBatch:
      if createdNewBatch:
        raise DerivationError("Cannot insert a new batch before an existing immutable batch")
      expectedAdded = {
        "intakeIds": groupIntakeIds,
        "registrySourceIds": [str(record.get("registrySourceId") or "") for record in group],
        "relativePaths": [str(record.get("relativePath") or "") for record in group],
      }
      if stableJson(existingBatch.get("added") or {}) != stableJson(expectedAdded):
        raise DerivationError(f"Immutable batch identity changed: {batchId}")
      if existingBatch.get("previousBatchId") != previousBatchId:
        raise DerivationError(f"Immutable batch chain changed: {batchId}")
      batches.append(existingBatch)
      cumulativeVersions = int((existingBatch.get("after") or {}).get("intakeRecords", 0))
      previousBatchId = batchId
      continue

    createdNewBatch = True
    groupClassifications = [classifications[intakeId] for intakeId in groupIntakeIds]
    triageCounts = {
      status: sum(record.get("triageStatus") == status for record in group)
      for status in sorted(VALID_TRIAGE_STATUSES)
    }
    assessedCount = sum(
      str(record.get("registrySourceId") or "") in assessedSourceIds
      for record in group
    )
    assessedRequiredCount = sum(
      record.get("triageStatus") in {"routed", "integrated"}
      and str(record.get("registrySourceId") or "") in assessedSourceIds
      for record in group
    )
    requiredAssessmentCount = triageCounts["routed"] + triageCounts["integrated"]
    addedVersions = len(group)
    before = batches[-1]["after"] if batches else {
      "managedRawVersions": cumulativeVersions,
      "intakeRecords": cumulativeVersions,
      "rawEvidenceRecords": baseRawRecords + cumulativeVersions,
      "registryRecords": baseRegistryRecords + cumulativeVersions,
    }
    cumulativeVersions += addedVersions
    after = {
      "managedRawVersions": cumulativeVersions,
      "intakeRecords": cumulativeVersions,
      "rawEvidenceRecords": before["rawEvidenceRecords"] + addedVersions,
      "registryRecords": before["registryRecords"] + addedVersions,
    }
    batchRecord = {
      "schemaVersion": "1.0",
      "batchId": batchId,
      "previousBatchId": previousBatchId,
      "mode": "baseline" if all(value == "baseline" for value in groupClassifications) else "incremental",
      "knowledgeBaseId": str(group[0].get("knowledgeBaseId") or ""),
      "observedAt": min(str(record.get("firstSeenAt") or "") for record in group),
      "status": "completed",
      "inputHash": f"sha256:{sha256(renderJsonl(group))}",
      "counts": {
        "addedVersions": addedVersions,
        "assessed": assessedCount,
        "baselineVersions": groupClassifications.count("baseline"),
        "integrated": triageCounts["integrated"],
        "missingRequiredAssessments": requiredAssessmentCount - assessedRequiredCount,
        "newSources": groupClassifications.count("new-source"),
        "pendingTriage": triageCounts["pending"],
        "requiredAssessments": requiredAssessmentCount,
        "revisions": groupClassifications.count("new-version"),
        "routed": triageCounts["routed"],
      },
      "before": before,
      "after": after,
      "added": {
        "intakeIds": groupIntakeIds,
        "registrySourceIds": [str(record.get("registrySourceId") or "") for record in group],
        "relativePaths": [str(record.get("relativePath") or "") for record in group],
      },
      "subscriptionContent": any(record.get("subscriptionContent") is not False for record in group),
      "generatorVersion": GENERATOR_VERSION,
    }
    batches.append(batchRecord)
    previousBatchId = batchId

  return batches, classifications


def buildNowManifest(
  intakeRecords: list[dict[str, Any]],
  registryRecords: list[dict[str, Any]],
  assessmentRecords: list[dict[str, Any]],
  batches: list[dict[str, Any]],
  classifications: dict[str, str],
) -> dict[str, Any]:
  assessedSourceIds = {
    str(record.get("sourceRef"))
    for record in assessmentRecords
    if record.get("sourceRef")
  }
  triageCounts = {
    status: sum(record.get("triageStatus") == status for record in intakeRecords)
    for status in sorted(VALID_TRIAGE_STATUSES)
  }
  assessed = sum(
    str(record.get("registrySourceId") or "") in assessedSourceIds
    for record in intakeRecords
  )
  requiredAssessments = triageCounts["routed"] + triageCounts["integrated"]
  assessedRequired = sum(
    record.get("triageStatus") in {"routed", "integrated"}
    and str(record.get("registrySourceId") or "") in assessedSourceIds
    for record in intakeRecords
  )
  latestBatch = batches[-1] if batches else None
  return {
    "schemaVersion": "1.0",
    "generatedFrom": "3-processing/index/intake-batches.jsonl",
    "knowledgeAsOf": localDate(str(latestBatch.get("observedAt") or "")) if latestBatch else None,
    "latestBatchId": latestBatch.get("batchId") if latestBatch else None,
    "registryRecords": len(registryRecords),
    "rawEvidenceRecords": sum(record.get("sourceLayer") == "raw" for record in registryRecords),
    "dataEvidenceRecords": sum(record.get("sourceLayer") == "data" for record in registryRecords),
    "intakeRecords": len(intakeRecords),
    "ordinaryNoteIdentities": len({str(record.get("upstreamId")) for record in intakeRecords}),
    "intakeBatches": len(batches),
    "baselineVersions": sum(value == "baseline" for value in classifications.values()),
    "newSourceVersions": sum(value == "new-source" for value in classifications.values()),
    "revisionVersions": sum(value == "new-version" for value in classifications.values()),
    "pendingTriage": triageCounts["pending"],
    "routed": triageCounts["routed"],
    "integrated": triageCounts["integrated"],
    "assessed": assessed,
    "requiredAssessments": requiredAssessments,
    "missingRequiredAssessments": requiredAssessments - assessedRequired,
    "subscriptionRecords": sum(record.get("subscriptionContent") is not False for record in intakeRecords),
  }


def renderNowBlock(
  manifest: dict[str, Any],
  intakeRecords: list[dict[str, Any]],
  registryRecords: list[dict[str, Any]],
  assessmentRecords: list[dict[str, Any]],
  classifications: dict[str, str],
) -> str:
  registryBySourceId = {
    str(record.get("sourceId")): record
    for record in registryRecords
    if record.get("sourceId")
  }
  assessmentsBySourceId = {
    str(record.get("sourceRef")): record
    for record in assessmentRecords
    if record.get("sourceRef")
  }
  lines = [
    NOW_START_MARKER,
    "## 自动接入状态",
    "",
    f"<!-- workbench:now:manifest {stableJson(manifest)} -->",
    "",
    f"- 最近实质批次：`{manifest['latestBatchId'] or '暂无'}`",
    f"- 知识截止：`{manifest['knowledgeAsOf'] or '暂无'}`",
    f"- 证据库存：Raw `{manifest['rawEvidenceRecords']}`，Data `{manifest['dataEvidenceRecords']}`，Registry `{manifest['registryRecords']}`",
    f"- 普通笔记：身份 `{manifest['ordinaryNoteIdentities']}`，已存版本 `{manifest['intakeRecords']}`，历史基线 `{manifest['baselineVersions']}`，新增来源 `{manifest['newSourceVersions']}`，修订 `{manifest['revisionVersions']}`",
    f"- 分流状态：pending `{manifest['pendingTriage']}`，routed `{manifest['routed']}`，integrated `{manifest['integrated']}`",
    f"- 评分状态：已评分 `{manifest['assessed']}`，必须评分 `{manifest['requiredAssessments']}`，缺失 `{manifest['missingRequiredAssessments']}`",
    "",
    "> `pending` 表示尚未完成主题分流，不要求为了填表而虚构 SQS；进入 `routed` 或 `integrated` 后必须完成来源评分。零变化扫描不会新增批次或改写本区块。",
    "",
    "### 最近接入版本",
    "",
  ]
  if not intakeRecords:
    lines.append("当前没有已接入的普通笔记版本。")
  else:
    lines.extend(["| 版本 | 类型 | 分流 | SQS |", "|---|---|---|---|"])
    recentRecords = sorted(
      intakeRecords,
      key=lambda record: (
        str(record.get("firstSeenAt") or ""),
        str(record.get("intakeId") or ""),
      ),
      reverse=True,
    )[:5]
    labels = {
      "baseline": "历史基线",
      "new-source": "新增来源",
      "new-version": "修订版本",
    }
    for record in recentRecords:
      registrySourceId = str(record.get("registrySourceId") or "")
      registryRecord = registryBySourceId.get(registrySourceId, {})
      title = str(registryRecord.get("title") or record.get("upstreamId") or "未命名").replace("|", "\\|")
      relativePath = str(record.get("relativePath") or "")
      link = f"[查看 Raw](<../../{relativePath}>)" if relativePath else "无路径"
      assessment = assessmentsBySourceId.get(registrySourceId)
      triageStatus = str(record.get("triageStatus") or "")
      if assessment:
        score = (assessment.get("scores") or {}).get("total")
        sqs = f"{assessment.get('confidenceBand', '?')} / {score} · {assessment.get('assessmentStatus', 'unknown')}"
      elif triageStatus == "pending":
        sqs = "待分流，不要求 SQS"
      else:
        sqs = "缺失必需 SQS"
      versionType = labels.get(classifications.get(str(record.get("intakeId"))), "未知")
      lines.append(f"| {title} · {link} | {versionType} | `{triageStatus}` | {sqs} |")
  lines.extend(["", NOW_END_MARKER])
  return "\n".join(lines)


def replaceNowBlock(content: str, machineBlock: str) -> str:
  if content.count(NOW_START_MARKER) != 1 or content.count(NOW_END_MARKER) != 1:
    raise DerivationError("NOW must contain exactly one v1 machine block")
  start = content.index(NOW_START_MARKER)
  end = content.index(NOW_END_MARKER, start)
  if end < start:
    raise DerivationError("NOW machine block markers are out of order")
  end += len(NOW_END_MARKER)
  return f"{content[:start]}{machineBlock}{content[end:]}"


def replaceNowDates(content: str, knowledgeAsOf: str | None) -> str:
  if not knowledgeAsOf:
    return content
  if not content.startswith("---\n"):
    raise DerivationError("NOW must begin with YAML frontmatter")
  frontmatterEnd = content.find("\n---\n", 4)
  if frontmatterEnd < 0:
    raise DerivationError("NOW frontmatter is not closed")
  frontmatter = content[:frontmatterEnd]
  asOfLines = [line for line in frontmatter.splitlines() if line.startswith("as_of:")]
  if len(asOfLines) != 1:
    raise DerivationError("NOW frontmatter must contain exactly one as_of field")
  updatedFrontmatter = frontmatter.replace(asOfLines[0], f"as_of: {knowledgeAsOf}")
  content = f"{updatedFrontmatter}{content[frontmatterEnd:]}"

  deadlineLines = [line for line in content.splitlines() if line.startswith("> 内容截至：")]
  if len(deadlineLines) != 1:
    raise DerivationError("NOW must contain exactly one visible content deadline")
  return content.replace(deadlineLines[0], f"> 内容截至：{knowledgeAsOf}")


def deriveArtifacts(repoRoot: Path, generatedAt: str, *, runLint: bool = True) -> dict[str, Any]:
  resolvedRepoRoot = repoRoot.resolve()
  if not (resolvedRepoRoot / "1-raw").is_dir() or not (resolvedRepoRoot / "2-data").is_dir():
    raise DerivationError("--repo-root must be a complete repository root")

  previousBatchRecords = readJsonl(resolvedRepoRoot / BATCH_LEDGER_PATH, required=False)
  previousIntakeIds = {
    str(intakeId)
    for batch in previousBatchRecords
    for intakeId in (batch.get("added") or {}).get("intakeIds", [])
  }
  builderResult = runNode(BUILDER_PATH, resolvedRepoRoot, generatedAt)
  intakeRecords = readJsonl(resolvedRepoRoot / INTAKE_LEDGER_PATH, required=False)
  registryRecords = readJsonl(resolvedRepoRoot / REGISTRY_PATH)
  assessmentRecords = readJsonl(resolvedRepoRoot / ASSESSMENTS_PATH, required=False)
  batches, classifications = buildBatches(
    intakeRecords,
    registryRecords,
    assessmentRecords,
    previousBatchRecords,
  )
  batchChanged = atomicWriteIfChanged(
    resolvedRepoRoot / BATCH_LEDGER_PATH,
    renderJsonl(batches),
  )

  nowPath = resolvedRepoRoot / NOW_PATH
  if not nowPath.exists():
    raise DerivationError(f"Missing NOW view: {nowPath}")
  manifest = buildNowManifest(
    intakeRecords,
    registryRecords,
    assessmentRecords,
    batches,
    classifications,
  )
  nowBlock = renderNowBlock(
    manifest,
    intakeRecords,
    registryRecords,
    assessmentRecords,
    classifications,
  )
  nowContent = replaceNowBlock(nowPath.read_text(encoding="utf-8"), nowBlock)
  nowContent = replaceNowDates(nowContent, manifest["knowledgeAsOf"])
  nowChanged = atomicWriteIfChanged(nowPath, nowContent)

  lintResult = {"changed": False, "passed": True}
  if runLint:
    lintResult = runNode(LINT_PATH, resolvedRepoRoot, generatedAt)
    if lintResult.get("passed") is not True:
      raise DerivationError("Governance lint failed")

  currentIntakeIds = {str(record.get("intakeId")) for record in intakeRecords}
  newVersions = len(currentIntakeIds - previousIntakeIds)
  changed = any([
    builderResult.get("changed") is True,
    batchChanged,
    nowChanged,
    lintResult.get("changed") is True,
  ])
  latestBatchId = batches[-1]["batchId"] if batches else None
  return {
    "status": "changed" if changed else "zero-change",
    "newVersions": newVersions,
    "batchId": latestBatchId,
    "registryRecords": len(registryRecords),
    "intakeRecords": len(intakeRecords),
    "pendingTriage": manifest["pendingTriage"],
    "missingRequiredAssessments": manifest["missingRequiredAssessments"],
    "artifacts": {
      "registry": builderResult.get("changed") is True,
      "intakeBatches": batchChanged,
      "now": nowChanged,
      "lintReport": lintResult.get("changed") is True,
    },
  }


def parseArgs() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
  parser.add_argument("--generated-at")
  parser.add_argument("--skip-lint", action="store_true", help=argparse.SUPPRESS)
  return parser.parse_args()


def main() -> int:
  args = parseArgs()
  generatedAt = args.generated_at or os.environ.get("WORKBENCH_NOW") or dt.datetime.now(dt.timezone.utc).isoformat()
  try:
    result = deriveArtifacts(args.repo_root, generatedAt, runLint=not args.skip_lint)
    print(stableJson(result))
    return 0
  except DerivationError as error:
    print(stableJson({"status": "failed", "error": str(error)}), file=sys.stderr)
    return 1


if __name__ == "__main__":
  raise SystemExit(main())
