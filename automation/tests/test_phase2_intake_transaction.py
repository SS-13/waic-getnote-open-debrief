import asyncio
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "sync_getnote_intake.py"
SPEC = importlib.util.spec_from_file_location("phase2_sync_getnote_intake", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def sample_config():
  return {
    "knowledgeBaseId": "JVl2k6DY",
    "rawDirectory": "1-raw/Joe主动收录/AI资讯",
    "ledgerPath": "3-processing/index/intake-ledger.jsonl",
    "baselineStatePath": "3-processing/index/intake-baseline.json",
    "curator": "Joe",
    "routes": [],
  }


def sample_note(content="第一版", updated_at="2026-08-03 08:00:00"):
  return {
    "note_id": "1916397389742706520",
    "title": "事务测试笔记",
    "content": content,
    "note_type": "plain_text",
    "created_at": "2026-08-03 08:00:00",
    "updated_at": updated_at,
    "tags": [],
  }


class RetryAndEndpointTest(unittest.IsolatedAsyncioTestCase):
  async def test_transient_failure_retries_only_the_ordinary_note_endpoint(self):
    calls = []

    async def runner(args):
      calls.append(args)
      if len(calls) == 1:
        raise OSError("temporary network failure")
      return json.dumps({"data": {"notes": [], "has_more": False}})

    client = MODULE.GetnoteClient(
      runner,
      max_attempts=2,
      retry_delay_seconds=0,
    )

    self.assertEqual(await client.list_notes("JVl2k6DY"), [])
    self.assertEqual(len(calls), 2)
    self.assertTrue(all(call == [
      "kb", "JVl2k6DY", "--all", "--no-content", "-o", "json",
    ] for call in calls))
    self.assertNotIn("bloggers", " ".join(calls[0]))
    self.assertNotIn("lives", " ".join(calls[0]))

  async def test_timeout_is_bounded_by_attempt_count(self):
    calls = 0

    async def runner(args):
      nonlocal calls
      calls += 1
      await asyncio.sleep(0.05)
      return "never reached"

    client = MODULE.GetnoteClient(
      runner,
      timeout_seconds=0.005,
      max_attempts=2,
      retry_delay_seconds=0,
    )

    with self.assertRaisesRegex(MODULE.IntakeError, "after 2 attempt"):
      await client.list_notes("JVl2k6DY")
    self.assertEqual(calls, 2)


class TransactionRecoveryTest(unittest.TestCase):
  def test_interrupted_publish_is_rolled_back_on_next_start(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      repo_root = root / "repo"
      runtime_root = root / "runtime"
      ledger_path = repo_root / "3-processing/index/intake-ledger.jsonl"
      MODULE.atomic_write(ledger_path, "old-ledger\n")
      changes = {
        "1-raw/new-version.md": b"new raw\n",
        "3-processing/index/intake-ledger.jsonl": b"new-ledger\n",
      }
      manifest_path = MODULE.prepare_file_transaction(
        repo_root,
        runtime_root,
        changes,
        create_only_paths={"1-raw/new-version.md"},
        transaction_id="interrupted",
      )
      manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
      manifest["status"] = "committing"
      MODULE.write_manifest(manifest_path, manifest)
      first_entry = manifest["entries"][0]
      staged_path = manifest_path.parent / first_entry["stagedPath"]
      MODULE.atomic_write_bytes(repo_root / first_entry["relativePath"], staged_path.read_bytes())

      recovered = MODULE.recover_pending_transactions(repo_root, runtime_root)

      self.assertEqual(recovered, ["interrupted"])
      self.assertFalse((repo_root / "1-raw/new-version.md").exists())
      self.assertEqual(ledger_path.read_text(encoding="utf-8"), "old-ledger\n")
      recovered_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
      self.assertEqual(recovered_manifest["status"], "rolled-back")

  def test_all_files_are_staged_and_validated_before_publish(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      repo_root = root / "repo"
      runtime_root = root / "runtime"
      target = repo_root / "1-raw/existing.md"
      MODULE.atomic_write(target, "Joe existing content\n")

      with self.assertRaisesRegex(MODULE.IntakeError, "create-only"):
        MODULE.prepare_file_transaction(
          repo_root,
          runtime_root,
          {"1-raw/existing.md": b"replacement\n"},
          create_only_paths={"1-raw/existing.md"},
        )

      self.assertEqual(target.read_text(encoding="utf-8"), "Joe existing content\n")


class SyncReliabilityTest(unittest.IsolatedAsyncioTestCase):
  async def test_baseline_mode_is_decided_after_interrupted_marker_recovery(self):
    class EmptyClient:
      async def verify_auth(self):
        return None

      async def list_notes(self, topic_id):
        return []

      async def get_note(self, note_id):
        raise AssertionError("empty baseline has no detail requests")

    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      repo_root = root / "repo"
      runtime_root = root / "runtime"
      marker_relative_path = sample_config()["baselineStatePath"]
      marker_content = (
        f"{MODULE.json_dumps(MODULE.build_baseline_state(sample_config(), [], completed_at='2026-08-02T08:00:00+00:00'), pretty=True)}\n"
      ).encode("utf-8")
      manifest_path = MODULE.prepare_file_transaction(
        repo_root,
        runtime_root,
        {marker_relative_path: marker_content},
        create_only_paths={marker_relative_path},
        transaction_id="interrupted-baseline",
      )
      manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
      manifest["status"] = "committing"
      MODULE.write_manifest(manifest_path, manifest)
      entry = manifest["entries"][0]
      staged_path = manifest_path.parent / entry["stagedPath"]
      MODULE.atomic_write_bytes(repo_root / marker_relative_path, staged_path.read_bytes())

      result = await MODULE.sync_notes(
        sample_config(),
        EmptyClient(),
        baseline=None,
        dry_run=False,
        only_note_id=None,
        now="2026-08-03T08:00:00+00:00",
        repo_root=repo_root,
        runtime_root=runtime_root,
      )

      self.assertEqual(result["recoveredTransactions"], ["interrupted-baseline"])
      self.assertTrue(result["baselineMode"])
      self.assertTrue(result["baselineStateChanged"])
      marker = json.loads((repo_root / marker_relative_path).read_text(encoding="utf-8"))
      self.assertEqual(marker["completedAt"], "2026-08-03T08:00:00+00:00")

  async def test_empty_full_baseline_marker_is_byte_stable(self):
    class EmptyClient:
      async def verify_auth(self):
        return None

      async def list_notes(self, topic_id):
        return []

      async def get_note(self, note_id):
        raise AssertionError("empty baseline has no detail requests")

    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      repo_root = root / "repo"
      runtime_root = root / "runtime"
      first = await MODULE.sync_notes(
        sample_config(),
        EmptyClient(),
        baseline=None,
        dry_run=False,
        only_note_id=None,
        now="2026-08-03T08:00:00+00:00",
        repo_root=repo_root,
        runtime_root=runtime_root,
      )
      marker_path = repo_root / sample_config()["baselineStatePath"]
      marker_before = marker_path.read_bytes()

      second = await MODULE.sync_notes(
        sample_config(),
        EmptyClient(),
        baseline=None,
        dry_run=False,
        only_note_id=None,
        now="2026-08-04T08:00:00+00:00",
        repo_root=repo_root,
        runtime_root=runtime_root,
      )

      marker = json.loads(marker_path.read_text(encoding="utf-8"))
      self.assertEqual(first["status"], "changed")
      self.assertTrue(first["baselineMode"])
      self.assertTrue(first["baselineStateChanged"])
      self.assertEqual(first["ordinaryNoteIds"], [])
      self.assertEqual(marker["ordinaryNoteCount"], 0)
      self.assertEqual(second["status"], "zero-change")
      self.assertFalse(second["baselineMode"])
      self.assertEqual(marker_path.read_bytes(), marker_before)

  async def test_tracer_only_full_scan_creates_marker_without_rewriting_intake(self):
    note = sample_note()

    class SingleNoteClient:
      async def verify_auth(self):
        return None

      async def list_notes(self, topic_id):
        return [note]

      async def get_note(self, note_id):
        return note

    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      repo_root = root / "repo"
      runtime_root = root / "runtime"
      tracer = await MODULE.sync_notes(
        sample_config(),
        SingleNoteClient(),
        baseline=True,
        dry_run=False,
        only_note_id=note["note_id"],
        now="2026-08-02T08:00:00+00:00",
        repo_root=repo_root,
        runtime_root=runtime_root,
      )
      raw_path = repo_root / tracer["paths"][0]
      ledger_path = repo_root / sample_config()["ledgerPath"]
      raw_before = raw_path.read_bytes()
      ledger_before = ledger_path.read_bytes()
      marker_path = repo_root / sample_config()["baselineStatePath"]
      self.assertFalse(marker_path.exists())

      full_scan = await MODULE.sync_notes(
        sample_config(),
        SingleNoteClient(),
        baseline=None,
        dry_run=False,
        only_note_id=None,
        now="2026-08-03T08:00:00+00:00",
        repo_root=repo_root,
        runtime_root=runtime_root,
      )

      self.assertTrue(full_scan["baselineMode"])
      self.assertTrue(full_scan["baselineStateChanged"])
      self.assertEqual(full_scan["newVersions"], 0)
      self.assertEqual(raw_path.read_bytes(), raw_before)
      self.assertEqual(ledger_path.read_bytes(), ledger_before)
      self.assertTrue(marker_path.is_file())

  async def test_full_baseline_stages_raw_ledger_and_marker_together(self):
    note = sample_note()
    second_note = {
      **sample_note("第二条"),
      "note_id": "1916286603207414544",
      "title": "第二条事务测试笔记",
    }
    notes_by_id = {
      note["note_id"]: note,
      second_note["note_id"]: second_note,
    }

    class SingleNoteClient:
      async def verify_auth(self):
        return None

      async def list_notes(self, topic_id):
        return [note, second_note]

      async def get_note(self, note_id):
        return notes_by_id[note_id]

    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      repo_root = root / "repo"
      runtime_root = root / "runtime"
      result = await MODULE.sync_notes(
        sample_config(),
        SingleNoteClient(),
        baseline=None,
        dry_run=False,
        only_note_id=None,
        now="2026-08-03T08:00:00+00:00",
        repo_root=repo_root,
        runtime_root=runtime_root,
      )

      manifest_path = runtime_root / "transactions" / result["transactionId"] / "manifest.json"
      manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
      transaction_paths = {entry["relativePath"] for entry in manifest["entries"]}
      self.assertEqual(transaction_paths, {
        *result["paths"],
        sample_config()["ledgerPath"],
        sample_config()["baselineStatePath"],
      })
      self.assertEqual(result["ordinaryNoteIds"], sorted(notes_by_id))
      self.assertTrue(result["ordinaryNoteIdsHash"].startswith("sha256:"))

  async def test_download_failure_is_runtime_state_not_zero_change(self):
    note = sample_note()

    class FailingClient:
      async def verify_auth(self):
        return None

      async def list_notes(self, topic_id):
        return [note]

      async def get_note(self, note_id):
        raise MODULE.IntakeError("download exhausted")

    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      repo_root = root / "repo"
      runtime_root = root / "runtime"

      with self.assertRaises(MODULE.IntakeBatchError):
        await MODULE.sync_notes(
          sample_config(),
          FailingClient(),
          baseline=False,
          dry_run=False,
          only_note_id=None,
          now="2026-08-03T08:00:00+00:00",
          repo_root=repo_root,
          runtime_root=runtime_root,
        )

      state = json.loads((runtime_root / "status.json").read_text(encoding="utf-8"))
      self.assertEqual(state["status"], "failed")
      self.assertEqual(state["failures"][0]["noteId"], note["note_id"])
      self.assertFalse((repo_root / sample_config()["ledgerPath"]).exists())
      self.assertTrue(list((runtime_root / "failures").glob("*.json")))

  async def test_only_one_local_writer_can_enter(self):
    calls = []

    class UnusedClient:
      async def verify_auth(self):
        calls.append("auth")

    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      repo_root = root / "repo"
      runtime_root = root / "runtime"
      with MODULE.LocalWriterLock(runtime_root / "intake.lock"):
        with self.assertRaisesRegex(MODULE.IntakeError, "already running"):
          await MODULE.sync_notes(
            sample_config(),
            UnusedClient(),
            baseline=False,
            dry_run=False,
            only_note_id=None,
            now="2026-08-03T08:00:00+00:00",
            repo_root=repo_root,
            runtime_root=runtime_root,
          )
      self.assertEqual(calls, [])

  async def test_revision_keeps_old_raw_and_canonical_lineage(self):
    class MutableClient:
      def __init__(self):
        self.note = sample_note()

      async def verify_auth(self):
        return None

      async def list_notes(self, topic_id):
        return [self.note]

      async def get_note(self, note_id):
        return self.note

    client = MutableClient()
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      repo_root = root / "repo"
      runtime_root = root / "runtime"
      first = await MODULE.sync_notes(
        sample_config(),
        client,
        baseline=True,
        dry_run=False,
        only_note_id=None,
        now="2026-08-03T08:00:00+00:00",
        repo_root=repo_root,
        runtime_root=runtime_root,
      )
      first_raw = repo_root / first["paths"][0]
      first_bytes = first_raw.read_bytes()
      client.note = sample_note("第二版", "2026-08-04 08:00:00")

      second = await MODULE.sync_notes(
        sample_config(),
        client,
        baseline=False,
        dry_run=False,
        only_note_id=None,
        now="2026-08-04T08:00:00+00:00",
        repo_root=repo_root,
        runtime_root=runtime_root,
      )

      ledger = MODULE.read_jsonl(repo_root / sample_config()["ledgerPath"])
      self.assertEqual(first["status"], "changed")
      self.assertEqual(second["status"], "changed")
      self.assertEqual(len(ledger), 2)
      self.assertEqual(len({record["canonicalSourceId"] for record in ledger}), 1)
      self.assertEqual(len({record["versionHash"] for record in ledger}), 2)
      first_record = next(record for record in ledger if record["changeType"] == "baseline")
      revision_record = next(record for record in ledger if record["changeType"] == "revision")
      self.assertEqual(revision_record["previousIntakeId"], first_record["intakeId"])
      self.assertEqual(revision_record["batchId"], second["batchId"])
      self.assertEqual(first_raw.read_bytes(), first_bytes)
      self.assertTrue((repo_root / second["paths"][0]).exists())

  async def test_new_note_after_baseline_is_classified_as_new_source(self):
    class SingleNoteClient:
      async def verify_auth(self):
        return None

      async def list_notes(self, topic_id):
        return [sample_note()]

      async def get_note(self, note_id):
        return sample_note()

    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      repo_root = root / "repo"
      runtime_root = root / "runtime"
      result = await MODULE.sync_notes(
        sample_config(),
        SingleNoteClient(),
        baseline=False,
        dry_run=False,
        only_note_id=None,
        now="2026-08-04T08:00:00+00:00",
        repo_root=repo_root,
        runtime_root=runtime_root,
      )

      ledger = MODULE.read_jsonl(repo_root / sample_config()["ledgerPath"])
      self.assertEqual(result["batchId"], ledger[0]["batchId"])
      self.assertEqual(ledger[0]["changeType"], "new-source")
      self.assertIsNone(ledger[0]["previousIntakeId"])


if __name__ == "__main__":
  unittest.main()
