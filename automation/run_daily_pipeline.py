#!/usr/bin/env python3
"""Run Getnote intake and deterministic governance derivation as one pipeline."""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable


AUTOMATION_DIR = Path(__file__).resolve().parent
REPO_ROOT = AUTOMATION_DIR.parent
if str(AUTOMATION_DIR) not in sys.path:
  sys.path.insert(0, str(AUTOMATION_DIR))

from run_daily_intake import DerivationError, deriveArtifacts  # noqa: E402
from sync_getnote_intake import (  # noqa: E402
  DEFAULT_CONFIG_PATH,
  GetnoteClient,
  IntakeError,
  RUNTIME_DIRECTORY,
  atomic_write_bytes,
  baseline_state_required,
  load_config,
  sync_notes,
  write_failure_record,
  write_runtime_state,
)


MANAGED_FIXED_PATHS = (
  "3-processing/index/governance-lint-report.json",
  "3-processing/index/intake-baseline.json",
  "3-processing/index/intake-batches.jsonl",
  "3-processing/index/intake-ledger.jsonl",
  "3-processing/index/source-registry.jsonl",
  "3-processing/index/source-registry.snapshot.json",
  "3-processing/wiki/NOW.md",
  "3-processing/wiki/sources/README.md",
)


class PipelineError(RuntimeError):
  """Raised when intake and deterministic views cannot converge."""


def stableJson(value: Any, *, pretty: bool = False) -> str:
  if pretty:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
  return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def baselineRequired(repoRoot: Path, config: dict[str, Any]) -> bool:
  return baseline_state_required(repoRoot.resolve(), config)


def captureManagedState(
  repoRoot: Path,
  config: dict[str, Any],
) -> dict[str, bytes | None]:
  managedPaths = sorted({
    *MANAGED_FIXED_PATHS,
    str(config["baselineStatePath"]),
  })
  return {
    relativePath: (repoRoot / relativePath).read_bytes()
    if (repoRoot / relativePath).is_file()
    else None
    for relativePath in managedPaths
  }


def restoreManagedState(
  repoRoot: Path,
  snapshot: dict[str, bytes | None],
  createdRawPaths: list[str],
  rawDirectory: str,
) -> None:
  resolvedRepoRoot = repoRoot.resolve()
  resolvedRawRoot = (resolvedRepoRoot / rawDirectory).resolve()
  for relativePath in sorted(set(createdRawPaths), reverse=True):
    target = (resolvedRepoRoot / relativePath).resolve()
    try:
      target.relative_to(resolvedRawRoot)
    except ValueError as error:
      raise PipelineError(f"Rollback path is outside managed Raw: {relativePath}") from error
    if target.is_file():
      target.unlink()

  for relativePath, originalContent in snapshot.items():
    target = resolvedRepoRoot / relativePath
    if originalContent is None:
      if target.is_file():
        target.unlink()
    elif not target.is_file() or target.read_bytes() != originalContent:
      atomic_write_bytes(target, originalContent)


async def runPipeline(
  repoRoot: Path,
  config: dict[str, Any],
  *,
  now: str,
  runtimeRoot: Path | None = None,
  client: GetnoteClient | None = None,
  deriver: Callable[[Path, str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
  resolvedRepoRoot = repoRoot.resolve()
  resolvedRuntimeRoot = Path(
    runtimeRoot or (resolvedRepoRoot / RUNTIME_DIRECTORY)
  ).resolve()
  derive = deriver or (lambda root, generatedAt: deriveArtifacts(root, generatedAt))
  managedSnapshot = captureManagedState(resolvedRepoRoot, config)
  createdRawPaths: list[str] = []

  def captureAfterRecovery() -> None:
    nonlocal managedSnapshot
    managedSnapshot = captureManagedState(resolvedRepoRoot, config)

  try:
    intakeResult = await sync_notes(
      config,
      client or GetnoteClient(),
      baseline=None,
      dry_run=False,
      only_note_id=None,
      now=now,
      repo_root=resolvedRepoRoot,
      runtime_root=resolvedRuntimeRoot,
      after_recovery=captureAfterRecovery,
    )
    createdRawPaths = list(intakeResult.get("paths") or [])
    if intakeResult["status"] not in {"changed", "zero-change"}:
      raise PipelineError(f"Unexpected intake status: {intakeResult['status']}")
    useBaseline = intakeResult.get("baselineMode")
    if not isinstance(useBaseline, bool):
      raise PipelineError("Intake result has no explicit baseline mode")
    if useBaseline and baselineRequired(resolvedRepoRoot, config):
      raise PipelineError("Full baseline sync completed without a valid baseline marker")

    derivationResult = await asyncio.to_thread(derive, resolvedRepoRoot, now)
    if derivationResult.get("status") not in {"changed", "zero-change"}:
      raise PipelineError(f"Unexpected derivation status: {derivationResult!r}")

    intakeNewVersions = int(intakeResult.get("newVersions", 0))
    derivedNewVersions = int(derivationResult.get("newVersions", 0))
    if intakeNewVersions and derivedNewVersions < intakeNewVersions:
      raise PipelineError(
        "Intake/derivation version delta mismatch: "
        f"intake={intakeNewVersions}, derivation={derivedNewVersions}"
      )

    changed = (
      intakeResult["status"] == "changed"
      or derivationResult["status"] == "changed"
    )
    result = {
      "status": "changed" if changed else "zero-change",
      "runDate": now[:10],
      "knowledgeBaseId": config["knowledgeBaseId"],
      "baselineMode": useBaseline,
      "baselineStateChanged": intakeResult.get("baselineStateChanged", False),
      "ordinaryNotesSeen": intakeResult["ordinaryNotesSeen"],
      "ordinaryNoteIdsHash": intakeResult.get("ordinaryNoteIdsHash"),
      "newVersions": intakeNewVersions,
      "recoveredUnbatchedVersions": max(0, derivedNewVersions - intakeNewVersions),
      "batchId": derivationResult.get("batchId"),
      "registryRecords": derivationResult.get("registryRecords"),
      "intakeRecords": derivationResult.get("intakeRecords"),
      "pendingTriage": derivationResult.get("pendingTriage"),
      "missingRequiredAssessments": derivationResult.get("missingRequiredAssessments"),
      "subscriptionBloggerImport": False,
      "liveImport": False,
      "recoveredTransactions": intakeResult.get("recoveredTransactions", []),
      "artifacts": derivationResult.get("artifacts", {}),
    }
    write_runtime_state(resolvedRuntimeRoot, {
      "schemaVersion": "1.0",
      "status": result["status"],
      "completedAt": now,
      "stage": "pipeline-complete",
      **result,
    })
    return result
  except Exception as error:
    try:
      restoreManagedState(
        resolvedRepoRoot,
        managedSnapshot,
        createdRawPaths,
        str(config["rawDirectory"]),
      )
    except (OSError, PipelineError) as rollbackError:
      error = PipelineError(f"{error}; managed rollback failed: {rollbackError}")
    failurePayload = {
      "schemaVersion": "1.0",
      "status": "failed",
      "failedAt": now,
      "stage": "daily-pipeline",
      "knowledgeBaseId": config.get("knowledgeBaseId"),
      "error": str(error),
    }
    try:
      write_runtime_state(resolvedRuntimeRoot, failurePayload)
      write_failure_record(resolvedRuntimeRoot, failurePayload)
    except OSError:
      pass
    raise PipelineError(str(error)) from error


def parseArgs() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
  parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
  parser.add_argument("--runtime-root", type=Path)
  return parser.parse_args()


async def asyncMain() -> int:
  args = parseArgs()
  now = os.environ.get("WORKBENCH_NOW") or dt.datetime.now(dt.timezone.utc).isoformat()
  result = await runPipeline(
    args.repo_root,
    load_config(args.config),
    now=now,
    runtimeRoot=args.runtime_root,
  )
  print(stableJson(result))
  return 0


def main() -> int:
  try:
    return asyncio.run(asyncMain())
  except PipelineError as error:
    print(stableJson({"status": "failed", "error": str(error)}), file=sys.stderr)
    return 1


if __name__ == "__main__":
  raise SystemExit(main())
