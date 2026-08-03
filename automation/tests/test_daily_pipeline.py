import importlib.util
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "run_daily_pipeline.py"
SPEC = importlib.util.spec_from_file_location("run_daily_pipeline", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def config():
  return {
    "knowledgeBaseId": "JVl2k6DY",
    "rawDirectory": "1-raw/Joe主动收录/AI资讯",
    "ledgerPath": "3-processing/index/intake-ledger.jsonl",
    "baselineStatePath": "3-processing/index/intake-baseline.json",
    "curator": "Joe",
    "routes": [],
  }


def writeBaselineState(repoRoot: Path, noteIds: list[str] | None = None):
  noteIds = sorted(noteIds or ["1001"])
  payload = "".join(f"{noteId}\n" for noteId in noteIds)
  state = {
    "schemaVersion": "1.0",
    "status": "complete",
    "scope": "all",
    "knowledgeBaseId": "JVl2k6DY",
    "completedAt": "2026-08-03T00:00:00+00:00",
    "ordinaryNoteCount": len(noteIds),
    "ordinaryNoteIds": noteIds,
    "ordinaryNoteIdsHash": f"sha256:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}",
    "generatorVersion": "phase2-v1",
  }
  path = repoRoot / config()["baselineStatePath"]
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(f"{json.dumps(state, sort_keys=True)}\n", encoding="utf-8")


class PipelineTest(unittest.IsolatedAsyncioTestCase):
  async def test_tracer_ledger_without_marker_still_enters_baseline_mode(self):
    with tempfile.TemporaryDirectory() as directory:
      repoRoot = Path(directory)
      self.assertTrue(MODULE.baselineRequired(repoRoot, config()))

      ledgerPath = repoRoot / config()["ledgerPath"]
      ledgerPath.parent.mkdir(parents=True)
      ledgerPath.write_text('{"intakeId":"one"}\n', encoding="utf-8")
      self.assertTrue(MODULE.baselineRequired(repoRoot, config()))

  async def test_complete_full_scope_marker_exits_baseline_mode(self):
    with tempfile.TemporaryDirectory() as directory:
      repoRoot = Path(directory)
      writeBaselineState(repoRoot)

      self.assertFalse(MODULE.baselineRequired(repoRoot, config()))

  async def test_zero_change_still_checks_derivation_consistency(self):
    deriveCalls = []

    async def fakeSync(*args, **kwargs):
      return {
        "status": "zero-change",
        "baselineMode": False,
        "ordinaryNotesSeen": 1,
        "ordinaryNoteIdsHash": "sha256:fixture",
        "newVersions": 0,
        "recoveredTransactions": [],
      }

    def fakeDerive(repoRoot, now):
      deriveCalls.append((repoRoot, now))
      return {
        "status": "zero-change",
        "newVersions": 0,
        "batchId": "BAT-ONE",
        "registryRecords": 864,
        "intakeRecords": 1,
        "pendingTriage": 0,
        "missingRequiredAssessments": 0,
        "artifacts": {},
      }

    with tempfile.TemporaryDirectory() as directory:
      repoRoot = Path(directory)
      ledgerPath = repoRoot / config()["ledgerPath"]
      ledgerPath.parent.mkdir(parents=True)
      ledgerPath.write_text('{"intakeId":"one"}\n', encoding="utf-8")
      writeBaselineState(repoRoot)
      with (
        mock.patch.object(MODULE, "sync_notes", side_effect=fakeSync),
        mock.patch.object(MODULE, "write_runtime_state"),
      ):
        result = await MODULE.runPipeline(
          repoRoot,
          config(),
          now="2026-08-04T01:07:00+00:00",
          deriver=fakeDerive,
        )

    self.assertEqual(result["status"], "zero-change")
    self.assertEqual(len(deriveCalls), 1)

  async def test_stale_derivation_is_repaired_without_fake_new_version(self):
    async def fakeSync(*args, **kwargs):
      return {
        "status": "zero-change",
        "baselineMode": False,
        "ordinaryNotesSeen": 1,
        "ordinaryNoteIdsHash": "sha256:fixture",
        "newVersions": 0,
        "recoveredTransactions": [],
      }

    def fakeDerive(repoRoot, now):
      return {
        "status": "changed",
        "newVersions": 0,
        "batchId": "BAT-ONE",
        "registryRecords": 864,
        "intakeRecords": 1,
        "pendingTriage": 0,
        "missingRequiredAssessments": 0,
        "artifacts": {"now": True},
      }

    with tempfile.TemporaryDirectory() as directory:
      repoRoot = Path(directory)
      ledgerPath = repoRoot / config()["ledgerPath"]
      ledgerPath.parent.mkdir(parents=True)
      ledgerPath.write_text('{"intakeId":"one"}\n', encoding="utf-8")
      writeBaselineState(repoRoot)
      with (
        mock.patch.object(MODULE, "sync_notes", side_effect=fakeSync),
        mock.patch.object(MODULE, "write_runtime_state"),
      ):
        result = await MODULE.runPipeline(
          repoRoot,
          config(),
          now="2026-08-04T01:07:00+00:00",
          deriver=fakeDerive,
        )

    self.assertEqual(result["status"], "changed")
    self.assertEqual(result["newVersions"], 0)

  async def test_derivation_failure_is_recorded_and_nonzero(self):
    rawRelativePath = "1-raw/Joe\u4e3b\u52a8\u6536\u5f55/AI\u8d44\u8baf/new.md"

    async def fakeSync(*args, **kwargs):
      repoRoot = kwargs["repo_root"]
      rawPath = repoRoot / rawRelativePath
      rawPath.parent.mkdir(parents=True, exist_ok=True)
      rawPath.write_text("new raw\n", encoding="utf-8")
      ledgerPath = repoRoot / config()["ledgerPath"]
      ledgerPath.parent.mkdir(parents=True, exist_ok=True)
      ledgerPath.write_text('{"intakeId":"new"}\n', encoding="utf-8")
      writeBaselineState(repoRoot, ["1001", "1002"])
      return {
        "status": "changed",
        "baselineMode": True,
        "baselineStateChanged": True,
        "ordinaryNotesSeen": 2,
        "ordinaryNoteIdsHash": "sha256:fixture",
        "newVersions": 1,
        "recoveredTransactions": [],
        "paths": [rawRelativePath],
      }

    def failedDerive(repoRoot, now):
      registryPath = repoRoot / "3-processing/index/source-registry.jsonl"
      registryPath.write_text("partial registry\n", encoding="utf-8")
      nowPath = repoRoot / "3-processing/wiki/NOW.md"
      nowPath.parent.mkdir(parents=True, exist_ok=True)
      nowPath.write_text("partial NOW\n", encoding="utf-8")
      raise MODULE.DerivationError("lint failed")

    with tempfile.TemporaryDirectory() as directory:
      repoRoot = Path(directory)
      runtimeRoot = repoRoot / ".cache/getnote-intake"
      ledgerPath = repoRoot / config()["ledgerPath"]
      ledgerPath.parent.mkdir(parents=True)
      ledgerPath.write_text('{"intakeId":"existing"}\n', encoding="utf-8")
      registryPath = repoRoot / "3-processing/index/source-registry.jsonl"
      registryPath.write_text("original registry\n", encoding="utf-8")
      nowPath = repoRoot / "3-processing/wiki/NOW.md"
      nowPath.parent.mkdir(parents=True)
      nowPath.write_text("original NOW\n", encoding="utf-8")
      before = {
        ledgerPath: ledgerPath.read_bytes(),
        registryPath: registryPath.read_bytes(),
        nowPath: nowPath.read_bytes(),
      }
      with mock.patch.object(MODULE, "sync_notes", side_effect=fakeSync):
        with self.assertRaisesRegex(MODULE.PipelineError, "lint failed"):
          await MODULE.runPipeline(
            repoRoot,
            config(),
            now="2026-08-04T01:07:00+00:00",
            runtimeRoot=runtimeRoot,
            deriver=failedDerive,
          )

      state = json.loads((runtimeRoot / "status.json").read_text(encoding="utf-8"))
      self.assertEqual(state["status"], "failed")
      self.assertEqual(state["stage"], "daily-pipeline")
      self.assertEqual(
        {path: path.read_bytes() for path in before},
        before,
      )
      self.assertFalse((repoRoot / rawRelativePath).exists())
      self.assertFalse((repoRoot / config()["baselineStatePath"]).exists())

  async def test_first_full_baseline_is_byte_stable_on_second_pipeline_run(self):
    note = {
      "note_id": "1001",
      "title": "基线测试",
      "content": "同一内容",
      "note_type": "plain_text",
      "created_at": "2026-08-03 08:00:00",
      "updated_at": "2026-08-03 08:00:00",
      "tags": [],
    }

    class StaticClient:
      async def verify_auth(self):
        return None

      async def list_notes(self, topic_id):
        return [{"note_id": note["note_id"]}]

      async def get_note(self, note_id):
        return note

    deriveCalls = 0

    def fakeDerive(repoRoot, now):
      nonlocal deriveCalls
      deriveCalls += 1
      return {
        "status": "changed" if deriveCalls == 1 else "zero-change",
        "newVersions": 1 if deriveCalls == 1 else 0,
        "batchId": "BAT-ONE",
        "registryRecords": 1,
        "intakeRecords": 1,
        "pendingTriage": 1,
        "missingRequiredAssessments": 0,
        "artifacts": {},
      }

    with tempfile.TemporaryDirectory() as directory:
      repoRoot = Path(directory)
      runtimeRoot = repoRoot / ".cache/getnote-intake"
      first = await MODULE.runPipeline(
        repoRoot,
        config(),
        now="2026-08-03T01:00:00+00:00",
        runtimeRoot=runtimeRoot,
        client=StaticClient(),
        deriver=fakeDerive,
      )
      markerPath = repoRoot / config()["baselineStatePath"]
      markerBefore = markerPath.read_bytes()

      second = await MODULE.runPipeline(
        repoRoot,
        config(),
        now="2026-08-04T01:00:00+00:00",
        runtimeRoot=runtimeRoot,
        client=StaticClient(),
        deriver=fakeDerive,
      )

      self.assertTrue(first["baselineMode"])
      self.assertTrue(first["baselineStateChanged"])
      self.assertFalse(second["baselineMode"])
      self.assertEqual(second["status"], "zero-change")
      self.assertEqual(markerPath.read_bytes(), markerBefore)

  async def test_derivation_failure_rolls_back_real_baseline_transaction(self):
    note = {
      "note_id": "1001",
      "title": "失败回滚测试",
      "content": "不能留下半成品",
      "note_type": "plain_text",
      "created_at": "2026-08-03 08:00:00",
      "updated_at": "2026-08-03 08:00:00",
      "tags": [],
    }

    class StaticClient:
      async def verify_auth(self):
        return None

      async def list_notes(self, topic_id):
        return [{"note_id": note["note_id"]}]

      async def get_note(self, note_id):
        return note

    def failedDerive(repoRoot, now):
      raise MODULE.DerivationError("baseline lint failed")

    with tempfile.TemporaryDirectory() as directory:
      repoRoot = Path(directory)
      runtimeRoot = repoRoot / ".cache/getnote-intake"
      with self.assertRaisesRegex(MODULE.PipelineError, "baseline lint failed"):
        await MODULE.runPipeline(
          repoRoot,
          config(),
          now="2026-08-03T01:00:00+00:00",
          runtimeRoot=runtimeRoot,
          client=StaticClient(),
          deriver=failedDerive,
        )

      self.assertFalse((repoRoot / config()["baselineStatePath"]).exists())
      self.assertFalse((repoRoot / config()["ledgerPath"]).exists())
      rawRoot = repoRoot / config()["rawDirectory"]
      self.assertEqual(list(rawRoot.glob("*.md")) if rawRoot.exists() else [], [])


if __name__ == "__main__":
  unittest.main()
