import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "sync_getnote_intake.py"
SPEC = importlib.util.spec_from_file_location("sync_getnote_intake", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class GetnoteClientTest(unittest.IsolatedAsyncioTestCase):
  async def test_list_notes_never_uses_subscription_endpoint(self):
    calls = []

    async def runner(args):
      calls.append(args)
      return json.dumps({"success": True, "data": {"notes": [], "has_more": False}})

    client = MODULE.GetnoteClient(runner)
    notes = await client.list_notes("JVl2k6DY")

    self.assertEqual(notes, [])
    self.assertEqual(calls, [["kb", "JVl2k6DY", "--all", "--no-content", "-o", "json"]])
    self.assertNotIn("bloggers", " ".join(calls[0]))

  async def test_list_notes_requires_explicit_complete_page(self):
    responses = [
      {"data": {"notes": [], "has_more": True}},
      {"data": {"notes": []}},
      {"data": {"notes": [], "has_more": False, "total": 1}},
    ]

    for response in responses:
      async def runner(args, payload=response):
        return json.dumps(payload)

      client = MODULE.GetnoteClient(runner, max_attempts=1)
      with self.assertRaises(MODULE.IntakeError):
        await client.list_notes("JVl2k6DY")


class IntakeRenderingTest(unittest.TestCase):
  def setUp(self):
    self.config = {
      "knowledgeBaseId": "JVl2k6DY",
      "rawDirectory": "1-raw/Joe主动收录/AI资讯",
      "curator": "Joe",
      "routes": [
        {
          "topicId": "TP003",
          "questionIds": ["Q002"],
          "terms": ["治理", "政策"],
        }
      ],
    }
    self.note = {
      "note_id": 1916397389742706520,
      "title": "北京智能体政策解读",
      "content": "这是得到大脑 AI 整理。",
      "note_type": "link",
      "created_at": "2026-07-23 13:22:31",
      "updated_at": "2026-07-23 13:22:31",
      "tags": [{"name": "北京智能体政策"}],
      "web_page": {
        "url": "https://example.com/article",
        "content": "THIRD PARTY FULL TEXT MUST NOT BE STORED",
      },
    }

  def test_note_id_remains_lossless_string(self):
    _, _, record = MODULE.render_markdown(
      self.note,
      self.config,
      ingested_at="2026-08-03T00:00:00+00:00",
      baseline=True,
    )

    self.assertEqual(record["upstreamId"], "1916397389742706520")
    self.assertEqual(record["canonicalSourceId"], "note:1916397389742706520")

  def test_linked_page_full_text_is_hashed_but_not_stored(self):
    _, markdown, record = MODULE.render_markdown(
      self.note,
      self.config,
      ingested_at="2026-08-03T00:00:00+00:00",
      baseline=True,
    )

    self.assertNotIn("THIRD PARTY FULL TEXT MUST NOT BE STORED", markdown)
    self.assertIn("这是得到大脑 AI 整理。", markdown)
    self.assertIn("fidelity: summary", markdown)
    self.assertEqual(record["topicIds"], ["TP003"])
    self.assertEqual(record["questionIds"], ["Q002"])
    self.assertEqual(record["triageStatus"], "pending")

  def test_curator_is_not_written_as_source_author(self):
    _, markdown, record = MODULE.render_markdown(
      self.note,
      self.config,
      ingested_at="2026-08-03T00:00:00+00:00",
      baseline=True,
    )

    self.assertIn('curator: "Joe"', markdown)
    self.assertNotIn('author: "Joe"', markdown)
    self.assertEqual(record["curator"], "Joe")

  def test_version_changes_when_upstream_full_text_changes(self):
    first = MODULE.version_hash(self.note)
    revised = dict(self.note)
    revised["web_page"] = dict(self.note["web_page"], content="REVISED FULL TEXT")

    self.assertNotEqual(first, MODULE.version_hash(revised))

  def test_signed_image_url_does_not_create_new_version(self):
    first_note = dict(self.note)
    first_note["web_page"] = dict(
      self.note["web_page"],
      content="正文\n![图片](https://get-notes.umiwi.com/path/image?Expires=1&Signature=one)",
    )
    second_note = dict(self.note)
    second_note["web_page"] = dict(
      self.note["web_page"],
      content="正文\n![图片](https://get-notes.umiwi.com/path/image?Expires=2&Signature=two)",
    )

    self.assertEqual(MODULE.version_hash(first_note), MODULE.version_hash(second_note))

  def test_atomic_write_replaces_complete_content(self):
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / "nested" / "record.jsonl"
      MODULE.atomic_write(path, "first\n")
      MODULE.atomic_write(path, "second\n")

      self.assertEqual(path.read_text(encoding="utf-8"), "second\n")


class ConfigTest(unittest.TestCase):
  def test_subscription_import_must_be_disabled(self):
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / "config.json"
      path.write_text(json.dumps({
        "knowledgeBaseId": "JVl2k6DY",
        "acceptedEndpoint": "knowledge-base-notes",
      "rawDirectory": "raw",
      "ledgerPath": "ledger.jsonl",
      "baselineStatePath": "baseline.json",
      "curator": "Joe",
        "subscriptionBloggerImport": True,
        "liveImport": False,
      }), encoding="utf-8")

      with self.assertRaises(MODULE.IntakeError):
        MODULE.load_config(path)


class SyncTransactionTest(unittest.IsolatedAsyncioTestCase):
  async def test_duplicate_upstream_note_id_fails_instead_of_overwriting(self):
    note = {
      "note_id": "1916397389742706520",
      "title": "重复 ID",
      "content": "内容",
      "note_type": "plain_text",
      "created_at": "2026-08-03 00:00:00",
      "updated_at": "2026-08-03 00:00:00",
    }
    config = {
      "knowledgeBaseId": "JVl2k6DY",
      "rawDirectory": "1-raw/Joe主动收录/AI资讯",
      "ledgerPath": "3-processing/index/intake-ledger.jsonl",
      "baselineStatePath": "3-processing/index/intake-baseline.json",
      "curator": "Joe",
      "routes": [],
    }

    class DuplicateClient:
      async def verify_auth(self):
        return None

      async def list_notes(self, topic_id):
        return [note, dict(note)]

      async def get_note(self, note_id):
        raise AssertionError("duplicate index must fail before detail download")

    with tempfile.TemporaryDirectory() as directory:
      with mock.patch.object(MODULE, "REPO_ROOT", Path(directory)):
        with self.assertRaisesRegex(MODULE.IntakeError, "Duplicate note_id"):
          await MODULE.sync_notes(
            config,
            DuplicateClient(),
            baseline=False,
            dry_run=False,
            only_note_id=None,
            now="2026-08-03T00:00:00+00:00",
          )

  async def test_same_version_is_a_byte_stable_no_op(self):
    note = {
      "note_id": "1916397389742706520",
      "title": "北京智能体政策解读",
      "content": "这是得到大脑 AI 整理。",
      "note_type": "link",
      "created_at": "2026-07-23 13:22:31",
      "updated_at": "2026-07-23 13:22:31",
      "tags": [{"name": "治理"}],
      "web_page": {"url": "https://example.com/article", "content": "原网页内容"},
    }
    config = {
      "knowledgeBaseId": "JVl2k6DY",
      "rawDirectory": "1-raw/Joe主动收录/AI资讯",
      "ledgerPath": "3-processing/index/intake-ledger.jsonl",
      "baselineStatePath": "3-processing/index/intake-baseline.json",
      "curator": "Joe",
      "routes": [{"topicId": "TP003", "questionIds": ["Q002"], "terms": ["治理"]}],
    }

    class FakeClient:
      async def verify_auth(self):
        return None

      async def list_notes(self, topic_id):
        self.topic_id = topic_id
        return [note]

      async def get_note(self, note_id):
        return note

    with tempfile.TemporaryDirectory() as directory:
      repo_root = Path(directory)
      with mock.patch.object(MODULE, "REPO_ROOT", repo_root):
        first = await MODULE.sync_notes(
          config,
          FakeClient(),
          baseline=True,
          dry_run=False,
          only_note_id=note["note_id"],
          now="2026-08-03T00:00:00+00:00",
        )
        raw_path = repo_root / first["paths"][0]
        ledger_path = repo_root / config["ledgerPath"]
        baseline_path = repo_root / config["baselineStatePath"]
        raw_before = raw_path.read_bytes()
        ledger_before = ledger_path.read_bytes()
        self.assertFalse(baseline_path.exists())

        second = await MODULE.sync_notes(
          config,
          FakeClient(),
          baseline=False,
          dry_run=False,
          only_note_id=note["note_id"],
          now="2026-08-04T00:00:00+00:00",
        )

        self.assertEqual(first["status"], "changed")
        self.assertEqual(second["status"], "zero-change")
        self.assertEqual(raw_path.read_bytes(), raw_before)
        self.assertEqual(ledger_path.read_bytes(), ledger_before)


if __name__ == "__main__":
  unittest.main()
