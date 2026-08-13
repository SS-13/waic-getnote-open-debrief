import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "run_daily_intake.py"
SPEC = importlib.util.spec_from_file_location("run_daily_intake", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class DerivationFixture:
  def __init__(self, root: Path, *, triageStatus: str = "pending", assessed: bool = False):
    self.root = root
    self.rawRelativePath = "1-raw/Joe主动收录/AI资讯/2026-08-03__测试资料__001__abc123.md"
    self.registrySourceId = "raw:1001:abc123"
    self.intakeId = "INT-GETNOTE-1001-abc123"
    self.batchId = "BATCH-GETNOTE-fixture001"
    self._writeDirectories()
    self._writeRaw()
    self._writeLedger(triageStatus)
    self._writeBaseline()
    self._writeAssessments(assessed)
    self._writeWiki()

  def _writeDirectories(self):
    for relativePath in [
      "1-raw/Joe主动收录/AI资讯",
      "2-data",
      "3-processing/index",
      "3-processing/wiki",
    ]:
      (self.root / relativePath).mkdir(parents=True, exist_ok=True)

  def _writeRaw(self):
    content = (
      "---\n"
      'title: "测试资料"\n'
      "note_id: 1001\n"
      'ingested_at: "2026-08-03T00:00:00+00:00"\n'
      "content_source: getnote-user-note\n"
      "fidelity: structured\n"
      "version_hash: abc123\n"
      f"registry_source_id: {self.registrySourceId}\n"
      "---\n\n"
      "# 测试资料\n"
    )
    (self.root / self.rawRelativePath).write_text(content, encoding="utf-8")

  def _writeLedger(self, triageStatus: str):
    record = {
      "schemaVersion": "1.0",
      "intakeId": self.intakeId,
      "upstreamId": "1001",
      "knowledgeBaseId": "JVl2k6DY",
      "captureMode": "joe-approved-note",
      "curator": "Joe",
      "firstSeenAt": "2026-08-03T00:00:00+00:00",
      "upstreamCreatedAt": "2026-08-03 08:00:00",
      "upstreamUpdatedAt": "2026-08-03 08:00:00",
      "versionHash": "abc123",
      "registrySourceId": self.registrySourceId,
      "canonicalSourceId": "note:1001",
      "evidenceLineageId": "L-GETNOTE-1001",
      "relativePath": self.rawRelativePath,
      "status": "baseline",
      "triageStatus": triageStatus,
      "selectionPriority": "joe-selected",
      "topicIds": [],
      "questionIds": [],
      "subscriptionContent": False,
      "batchId": self.batchId,
      "changeType": "baseline",
      "previousIntakeId": None,
    }
    ledgerPath = self.root / "3-processing/index/intake-ledger.jsonl"
    ledgerPath.write_text(f"{MODULE.stableJson(record)}\n", encoding="utf-8")

  def _writeAssessments(self, assessed: bool):
    records = []
    if assessed:
      records.append({
        "schemaVersion": "1.0",
        "assessmentId": "SA-001",
        "sourceRef": self.registrySourceId,
        "canonicalSourceId": "note:1001",
        "evidenceLineageId": "L-GETNOTE-1001",
        "sourceClass": "user-note",
        "scores": {
          "identityAndOriginality": 12,
          "factDirectness": 12,
          "traceability": 12,
          "fidelityAndCompleteness": 9,
          "interestAndCorrection": 7,
          "recencyAndVersion": 8,
          "total": 60,
        },
        "confidenceBand": "C",
        "assessmentStatus": "provisional",
        "assessedBy": "AI",
        "assessedAt": "2026-08-03",
        "reviewTrigger": "new-evidence",
        "rationale": "Fixture assessment.",
        "limitation": "Fixture only.",
      })
    assessmentContent = "".join(f"{MODULE.stableJson(record)}\n" for record in records)
    (self.root / "3-processing/index/source-assessments.jsonl").write_text(assessmentContent, encoding="utf-8")
    (self.root / "3-processing/index/claim-confidence.jsonl").write_text("", encoding="utf-8")

  def _writeBaseline(self):
    noteIds = ["1001"]
    noteIdPayload = "".join(f"{noteId}\n" for noteId in noteIds)
    state = {
      "schemaVersion": "1.0",
      "status": "complete",
      "scope": "all",
      "knowledgeBaseId": "JVl2k6DY",
      "completedAt": "2026-08-03T00:00:00+00:00",
      "ordinaryNoteCount": len(noteIds),
      "ordinaryNoteIds": noteIds,
      "ordinaryNoteIdsHash": f"sha256:{MODULE.sha256(noteIdPayload)}",
      "generatorVersion": "phase2-v1",
    }
    (self.root / "3-processing/index/intake-baseline.json").write_text(
      f"{MODULE.stableJson(state, pretty=True)}\n",
      encoding="utf-8",
    )

  def _writeWiki(self):
    nowContent = (
      "---\n"
      "id: VIEW-NOW\n"
      "type: navigation-view\n"
      "status: active\n"
      "as_of: 2026-08-03\n"
      "---\n\n"
      "# NOW\n\n"
      "> 内容截至：2026-08-03\n\n"
      f"{MODULE.NOW_START_MARKER}\n"
      "placeholder\n"
      f"{MODULE.NOW_END_MARKER}\n\n"
      "人工内容保持不变。\n"
    )
    (self.root / "3-processing/wiki/NOW.md").write_text(nowContent, encoding="utf-8")
    (self.root / "3-processing/wiki/HOME.md").write_text("# HOME\n", encoding="utf-8")


class DailyIntakeDerivationTest(unittest.TestCase):
  def test_knowledge_date_uses_shanghai_day_boundary(self):
    self.assertEqual(
      MODULE.localDate("2026-08-02T22:58:17.767033+00:00"),
      "2026-08-03",
    )

  def test_pending_source_needs_no_fake_sqs_and_second_run_is_byte_stable(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      fixture = DerivationFixture(root, triageStatus="pending", assessed=False)

      first = MODULE.deriveArtifacts(root, "2026-08-03T01:00:00+00:00")
      managedPaths = [
        root / "3-processing/index/source-registry.jsonl",
        root / "3-processing/index/source-registry.snapshot.json",
        root / "3-processing/index/intake-batches.jsonl",
        root / "3-processing/wiki/NOW.md",
        root / "3-processing/index/governance-lint-report.json",
      ]
      before = {path: path.read_bytes() for path in managedPaths}
      second = MODULE.deriveArtifacts(root, "2026-08-04T01:00:00+00:00")

      self.assertEqual(first["status"], "changed")
      self.assertEqual(first["newVersions"], 1)
      self.assertEqual(second["status"], "zero-change")
      self.assertEqual(second["newVersions"], 0)
      self.assertEqual({path: path.read_bytes() for path in managedPaths}, before)
      nowContent = (root / MODULE.NOW_PATH).read_text(encoding="utf-8")
      self.assertIn("待分流，不要求 SQS", nowContent)
      report = json.loads((root / MODULE.LINT_REPORT_PATH).read_text(encoding="utf-8"))
      self.assertTrue(report["passed"])
      self.assertEqual(report["checks"]["pendingTriage"], 1)
      self.assertEqual(report["checks"]["missingRequiredAssessments"], 0)
      self.assertEqual(fixture.batchId, first["batchId"])

  def test_routed_source_without_assessment_fails_lint(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      DerivationFixture(root, triageStatus="routed", assessed=False)

      with self.assertRaises(MODULE.DerivationError):
        MODULE.deriveArtifacts(root, "2026-08-03T01:00:00+00:00")

      report = json.loads((root / MODULE.LINT_REPORT_PATH).read_text(encoding="utf-8"))
      kinds = {error["kind"] for error in report["errors"]}
      self.assertIn("unassessed-routed-intake-source", kinds)
      self.assertEqual(report["checks"]["missingRequiredAssessments"], 1)

  def test_routed_source_with_assessment_passes(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      DerivationFixture(root, triageStatus="routed", assessed=True)

      result = MODULE.deriveArtifacts(root, "2026-08-03T01:00:00+00:00")

      self.assertEqual(result["status"], "changed")
      self.assertEqual(result["missingRequiredAssessments"], 0)

  def test_lint_rejects_non_string_baseline_note_id(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      DerivationFixture(root)
      baselinePath = root / "3-processing/index/intake-baseline.json"
      state = json.loads(baselinePath.read_text(encoding="utf-8"))
      state["ordinaryNoteIds"] = [1001]
      baselinePath.write_text(f"{MODULE.stableJson(state, pretty=True)}\n", encoding="utf-8")

      with self.assertRaises(MODULE.DerivationError):
        MODULE.deriveArtifacts(root, "2026-08-03T01:00:00+00:00")

      report = json.loads((root / MODULE.LINT_REPORT_PATH).read_text(encoding="utf-8"))
      self.assertIn("intake-baseline-id-type", {error["kind"] for error in report["errors"]})

  def test_lint_rejects_baseline_duplicates_count_hash_and_missing_ledger_ids(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      DerivationFixture(root)
      baselinePath = root / "3-processing/index/intake-baseline.json"
      state = json.loads(baselinePath.read_text(encoding="utf-8"))
      state["ordinaryNoteIds"] = ["1001", "9999", "9999"]
      state["ordinaryNoteCount"] = 4
      state["ordinaryNoteIdsHash"] = "sha256:invalid"
      baselinePath.write_text(f"{MODULE.stableJson(state, pretty=True)}\n", encoding="utf-8")

      with self.assertRaises(MODULE.DerivationError):
        MODULE.deriveArtifacts(root, "2026-08-03T01:00:00+00:00")

      report = json.loads((root / MODULE.LINT_REPORT_PATH).read_text(encoding="utf-8"))
      errorKinds = {error["kind"] for error in report["errors"]}
      self.assertIn("duplicate-intake-baseline-id", errorKinds)
      self.assertIn("intake-baseline-id-count", errorKinds)
      self.assertIn("intake-baseline-id-hash", errorKinds)
      self.assertIn("missing-intake-baseline-ledger-id", errorKinds)

  def test_later_assessment_updates_now_without_rewriting_frozen_batch(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      fixture = DerivationFixture(root, triageStatus="pending", assessed=False)
      MODULE.deriveArtifacts(root, "2026-08-03T01:00:00+00:00")
      batchPath = root / MODULE.BATCH_LEDGER_PATH
      batchBefore = batchPath.read_bytes()

      fixture._writeAssessments(True)
      result = MODULE.deriveArtifacts(root, "2026-08-04T01:00:00+00:00")

      self.assertEqual(batchPath.read_bytes(), batchBefore)
      self.assertTrue(result["artifacts"]["now"])
      nowContent = (root / MODULE.NOW_PATH).read_text(encoding="utf-8")
      self.assertIn("C / 60 · provisional", nowContent)
      batches = MODULE.readJsonl(batchPath)
      self.assertEqual(batches[0]["counts"]["assessed"], 0)

  def test_external_data_source_does_not_rewrite_frozen_getnote_batch(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      DerivationFixture(root)
      MODULE.deriveArtifacts(root, "2026-08-03T01:00:00+00:00")
      batchPath = root / MODULE.BATCH_LEDGER_PATH
      batchBefore = batchPath.read_bytes()

      externalPath = root / "2-data/外部研究资料/外部论文.md"
      externalPath.parent.mkdir(parents=True, exist_ok=True)
      externalPath.write_text(
        "---\n"
        "title: 外部论文\n"
        "canonical_source_id: doi:10.0000/example\n"
        "fidelity: structured\n"
        "---\n\n"
        "# 外部论文\n",
        encoding="utf-8",
      )

      result = MODULE.deriveArtifacts(root, "2026-08-04T01:00:00+00:00")

      self.assertEqual(batchPath.read_bytes(), batchBefore)
      self.assertTrue(result["artifacts"]["registry"])
      report = json.loads((root / MODULE.LINT_REPORT_PATH).read_text(encoding="utf-8"))
      self.assertTrue(report["passed"])
      self.assertEqual(report["checks"]["dataEvidenceRecords"], 1)
      self.assertEqual(report["checks"]["registryRecords"], 2)

  def test_later_triage_change_warns_without_rewriting_frozen_batch(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      fixture = DerivationFixture(root, triageStatus="pending", assessed=False)
      MODULE.deriveArtifacts(root, "2026-08-03T01:00:00+00:00")
      batchPath = root / MODULE.BATCH_LEDGER_PATH
      batchBefore = batchPath.read_bytes()

      fixture._writeLedger("routed")
      fixture._writeAssessments(True)
      MODULE.deriveArtifacts(root, "2026-08-04T01:00:00+00:00")

      self.assertEqual(batchPath.read_bytes(), batchBefore)
      report = json.loads((root / MODULE.LINT_REPORT_PATH).read_text(encoding="utf-8"))
      self.assertTrue(report["passed"])
      warningKinds = {warning["kind"] for warning in report["warnings"]}
      self.assertIn("intake-batch-current-input-drift", warningKinds)
      nowContent = (root / MODULE.NOW_PATH).read_text(encoding="utf-8")
      self.assertIn("| `routed` | C / 60 · provisional |", nowContent)

  def test_angle_bracket_link_with_ascii_parentheses_passes_lint(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      fixture = DerivationFixture(root)
      oldRawPath = root / fixture.rawRelativePath
      fixture.rawRelativePath = "1-raw/Joe主动收录/AI资讯/Agent_(FDE).md"
      newRawPath = root / fixture.rawRelativePath
      oldRawPath.rename(newRawPath)
      ledgerPath = root / MODULE.INTAKE_LEDGER_PATH
      records = MODULE.readJsonl(ledgerPath)
      records[0]["relativePath"] = fixture.rawRelativePath
      ledgerPath.write_text(MODULE.renderJsonl(records), encoding="utf-8")

      result = MODULE.deriveArtifacts(root, "2026-08-03T01:00:00+00:00")

      self.assertEqual(result["status"], "changed")
      report = json.loads((root / MODULE.LINT_REPORT_PATH).read_text(encoding="utf-8"))
      self.assertTrue(report["passed"])
      self.assertFalse(any(error["kind"] == "broken-wiki-link" for error in report["errors"]))

  def test_next_day_batch_keeps_all_now_dates_in_sync(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      fixture = DerivationFixture(root)
      MODULE.deriveArtifacts(root, "2026-08-03T01:00:00+00:00")

      secondRelativePath = "1-raw/Joe主动收录/AI资讯/2026-08-04__次日资料__002__def456.md"
      secondSourceId = "raw:1002:def456"
      secondRaw = (
        "---\n"
        'title: "次日资料"\n'
        "note_id: 1002\n"
        'ingested_at: "2026-08-04T00:00:00+00:00"\n'
        "content_source: getnote-user-note\n"
        "fidelity: structured\n"
        "version_hash: def456\n"
        f"registry_source_id: {secondSourceId}\n"
        "---\n\n"
        "# 次日资料\n"
      )
      (root / secondRelativePath).write_text(secondRaw, encoding="utf-8")
      ledgerPath = root / MODULE.INTAKE_LEDGER_PATH
      records = MODULE.readJsonl(ledgerPath)
      records.append({
        **records[0],
        "intakeId": "INT-GETNOTE-1002-def456",
        "upstreamId": "1002",
        "firstSeenAt": "2026-08-04T00:00:00+00:00",
        "upstreamCreatedAt": "2026-08-04 08:00:00",
        "upstreamUpdatedAt": "2026-08-04 08:00:00",
        "versionHash": "def456",
        "registrySourceId": secondSourceId,
        "canonicalSourceId": "note:1002",
        "evidenceLineageId": "L-GETNOTE-1002",
        "relativePath": secondRelativePath,
        "status": "registered",
        "batchId": "BATCH-GETNOTE-fixture002",
        "changeType": "new-source",
      })
      ledgerPath.write_text(MODULE.renderJsonl(records), encoding="utf-8")

      result = MODULE.deriveArtifacts(root, "2026-08-04T01:00:00+00:00")
      nowPath = root / MODULE.NOW_PATH
      nowContent = nowPath.read_text(encoding="utf-8")
      manifestLine = next(
        line for line in nowContent.splitlines()
        if line.startswith("<!-- workbench:now:manifest ")
      )
      manifest = json.loads(manifestLine.removeprefix("<!-- workbench:now:manifest ").removesuffix(" -->"))

      self.assertEqual(result["batchId"], "BATCH-GETNOTE-fixture002")
      self.assertEqual(manifest["knowledgeAsOf"], "2026-08-04")
      self.assertIn("as_of: 2026-08-04", nowContent)
      self.assertIn("> 内容截至：2026-08-04", nowContent)
      nowBefore = nowPath.read_bytes()
      second = MODULE.deriveArtifacts(root, "2026-08-05T01:00:00+00:00")
      self.assertEqual(second["status"], "zero-change")
      self.assertEqual(nowPath.read_bytes(), nowBefore)

  def test_builder_repairs_stale_snapshot_without_rewriting_registry(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      DerivationFixture(root)
      builderPath = Path(__file__).resolve().parents[2] / "3-processing/governance/build-source-registry.mjs"
      command = [
        "node",
        str(builderPath),
        "--repo-root",
        str(root),
        "--generated-at",
        "2026-08-03T01:00:00+00:00",
      ]
      subprocess.run(command, check=True, capture_output=True, text=True)
      registryPath = root / MODULE.REGISTRY_PATH
      snapshotPath = root / MODULE.SNAPSHOT_PATH
      registryBefore = registryPath.read_bytes()
      snapshot = json.loads(snapshotPath.read_text(encoding="utf-8"))
      snapshot["recordCount"] = 999
      snapshotPath.write_text(json.dumps(snapshot), encoding="utf-8")

      completed = subprocess.run(command, check=True, capture_output=True, text=True)
      result = json.loads(completed.stdout)

      self.assertTrue(result["changed"])
      self.assertFalse(result["registryChanged"])
      self.assertTrue(result["snapshotChanged"])
      self.assertEqual(registryPath.read_bytes(), registryBefore)
      repaired = json.loads(snapshotPath.read_text(encoding="utf-8"))
      self.assertEqual(repaired["recordCount"], 1)

  def test_revision_keeps_both_raw_versions_in_one_canonical_lineage(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      fixture = DerivationFixture(root)
      revisedRelativePath = "1-raw/Joe主动收录/AI资讯/2026-08-04__测试资料修订__001__def456.md"
      revisedSourceId = "raw:1001:def456"
      revisedRaw = (
        "---\n"
        'title: "测试资料修订"\n'
        "note_id: 1001\n"
        'ingested_at: "2026-08-04T00:00:00+00:00"\n'
        "content_source: getnote-user-note\n"
        "fidelity: structured\n"
        "version_hash: def456\n"
        f"registry_source_id: {revisedSourceId}\n"
        "---\n\n"
        "# 测试资料修订\n"
      )
      (root / revisedRelativePath).write_text(revisedRaw, encoding="utf-8")
      ledgerPath = root / MODULE.INTAKE_LEDGER_PATH
      records = [json.loads(line) for line in ledgerPath.read_text(encoding="utf-8").splitlines()]
      records.append({
        **records[0],
        "intakeId": "INT-GETNOTE-1001-def456",
        "firstSeenAt": "2026-08-04T00:00:00+00:00",
        "upstreamUpdatedAt": "2026-08-04 08:00:00",
        "versionHash": "def456",
        "registrySourceId": revisedSourceId,
        "relativePath": revisedRelativePath,
        "status": "registered",
        "batchId": "BATCH-GETNOTE-fixture002",
        "changeType": "revision",
        "previousIntakeId": fixture.intakeId,
      })
      ledgerPath.write_text(
        "".join(f"{MODULE.stableJson(record)}\n" for record in records),
        encoding="utf-8",
      )

      result = MODULE.deriveArtifacts(root, "2026-08-04T01:00:00+00:00")
      registry = MODULE.readJsonl(root / MODULE.REGISTRY_PATH)
      batches = MODULE.readJsonl(root / MODULE.BATCH_LEDGER_PATH)

      self.assertEqual(result["newVersions"], 2)
      self.assertEqual(len(registry), 2)
      self.assertEqual({record["canonicalSourceId"] for record in registry}, {"note:1001"})
      self.assertEqual(len({record["sourceId"] for record in registry}), 2)
      self.assertEqual(len(batches), 2)
      self.assertEqual(batches[-1]["counts"]["revisions"], 1)
      self.assertTrue((root / fixture.rawRelativePath).exists())
      self.assertTrue((root / revisedRelativePath).exists())

  def test_derivation_changes_only_selected_staged_root(self):
    with tempfile.TemporaryDirectory() as liveDirectory, tempfile.TemporaryDirectory() as stageDirectory:
      liveRoot = Path(liveDirectory)
      stageRoot = Path(stageDirectory)
      DerivationFixture(liveRoot)
      DerivationFixture(stageRoot)
      liveNowBefore = (liveRoot / MODULE.NOW_PATH).read_bytes()

      MODULE.deriveArtifacts(stageRoot, "2026-08-03T01:00:00+00:00")

      self.assertEqual((liveRoot / MODULE.NOW_PATH).read_bytes(), liveNowBefore)
      self.assertFalse((liveRoot / MODULE.REGISTRY_PATH).exists())
      self.assertTrue((stageRoot / MODULE.REGISTRY_PATH).exists())

  def test_now_requires_exactly_one_machine_block(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      DerivationFixture(root)
      nowPath = root / MODULE.NOW_PATH
      nowPath.write_text("# NOW\n", encoding="utf-8")

      with self.assertRaises(MODULE.DerivationError):
        MODULE.deriveArtifacts(root, "2026-08-03T01:00:00+00:00", runLint=False)


if __name__ == "__main__":
  unittest.main()
