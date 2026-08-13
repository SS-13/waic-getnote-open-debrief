import { createHash } from "node:crypto";
import { access, readFile, readdir, rename, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const DEFAULT_REPO_ROOT = path.resolve(scriptDir, "../..");
const NOW_START_MARKER = "<!-- workbench:now:auto:start v1 -->";
const NOW_END_MARKER = "<!-- workbench:now:auto:end -->";
const NOW_MANIFEST_PREFIX = "<!-- workbench:now:manifest ";
const NON_EVIDENCE_FILENAMES = new Set(["README.md", "INDEX.md"]);
const VALID_TRIAGE_STATUSES = new Set(["pending", "routed", "integrated"]);

const REGISTRY_FIELDS = [
  "schemaVersion",
  "sourceId",
  "canonicalSourceId",
  "noteId",
  "sourceLayer",
  "relativePath",
  "title",
  "eventYear",
  "fidelity",
  "contentHash",
  "reviewStatus",
  "registeredAt",
];

const WIKI_REQUIRED_FIELDS = {
  briefing: ["id", "type", "status", "question_ids", "claim_ids", "source_ids", "as_of", "evidence_pack_hash", "review_status", "generation_version"],
  claim: ["id", "type", "status", "question_ids", "source_ids", "scope", "as_of"],
  concept: ["id", "type", "status", "claim_ids", "as_of"],
  question: ["id", "type", "status", "as_of", "event", "years"],
  release: ["id", "type", "status", "synthesis_ids", "output_paths", "as_of"],
  roundtable: ["id", "type", "status", "question_ids", "claim_ids", "source_ids", "briefing_ids", "as_of", "evidence_pack_hash", "review_status"],
  source: ["id", "type", "status", "registry_source_id", "canonical_source_id", "evidence_lineage_id", "assessment_id", "topic_ids", "question_ids", "as_of"],
  synthesis: ["id", "type", "status", "question_ids", "claim_ids", "as_of"],
  tension: ["id", "type", "status", "question_ids", "claim_ids", "as_of"],
  topic: ["id", "type", "status", "question_ids", "claim_ids", "as_of"],
};

function compareCodePoints(left, right) {
  return left < right ? -1 : left > right ? 1 : 0;
}

async function walkMarkdownFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const paths = [];

  for (const entry of entries.sort((a, b) => compareCodePoints(a.name, b.name))) {
    const entryPath = path.join(directory, entry.name);

    if (entry.isDirectory()) {
      paths.push(...await walkMarkdownFiles(entryPath));
    } else if (entry.isFile() && entry.name.endsWith(".md")) {
      paths.push(entryPath);
    }
  }

  return paths;
}

function parseFrontmatter(content) {
  if (!content.startsWith("---\n")) {
    return {};
  }

  const end = content.indexOf("\n---\n", 4);

  if (end === -1) {
    return {};
  }

  const metadata = {};

  for (const line of content.slice(4, end).split("\n")) {
    const match = line.match(/^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$/);

    if (match) {
      metadata[match[1]] = match[2].trim();
    }
  }

  return metadata;
}

function parseInlineList(value) {
  if (!value?.startsWith("[") || !value.endsWith("]")) {
    return [];
  }

  return value.slice(1, -1)
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseScalar(value) {
  return value?.replace(/^"(.*)"$/, "$1").replace(/^'(.*)'$/, "$1") ?? null;
}

function parseJsonl(content, targetPath, errors) {
  const records = [];

  for (const [index, line] of content.trim().split("\n").filter(Boolean).entries()) {
    try {
      records.push(JSON.parse(line));
    } catch {
      errors.push({ kind: "invalid-jsonl", targetPath, line: index + 1 });
    }
  }

  return records;
}

function hashContent(content) {
  return createHash("sha256").update(content).digest("hex");
}

function ordinaryNoteIdsHash(noteIds) {
  const payload = noteIds.map((noteId) => `${noteId}\n`).join("");
  return `sha256:${hashContent(payload)}`;
}

function shanghaiDate(value) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return String(value || "").slice(0, 10);
  }
  return new Date(parsed.getTime() + 8 * 60 * 60 * 1000).toISOString().slice(0, 10);
}

function sortObject(value) {
  if (Array.isArray(value)) {
    return value.map(sortObject);
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value).sort(compareCodePoints).map((key) => [key, sortObject(value[key])]),
    );
  }
  return value;
}

function stableJson(value) {
  return JSON.stringify(sortObject(value));
}

async function atomicWrite(targetPath, content) {
  const tempPath = `${targetPath}.tmp-${process.pid}`;
  await writeFile(tempPath, content);
  await rename(tempPath, targetPath);
}

async function countEvidenceFiles(repoRoot) {
  const counts = {};
  for (const [sourceLayer, directory] of [["raw", "1-raw"], ["data", "2-data"]]) {
    const paths = await walkMarkdownFiles(path.join(repoRoot, directory));
    counts[sourceLayer] = paths.filter((targetPath) => !NON_EVIDENCE_FILENAMES.has(path.basename(targetPath))).length;
  }
  return counts;
}

function parseNowManifest(content, errors) {
  if (content.split(NOW_START_MARKER).length - 1 !== 1 || content.split(NOW_END_MARKER).length - 1 !== 1) {
    errors.push({ kind: "now-machine-markers" });
    return null;
  }
  if (content.indexOf(NOW_START_MARKER) > content.indexOf(NOW_END_MARKER)) {
    errors.push({ kind: "now-machine-marker-order" });
    return null;
  }
  const machineBlock = content.slice(
    content.indexOf(NOW_START_MARKER),
    content.indexOf(NOW_END_MARKER) + NOW_END_MARKER.length,
  );
  const manifestLines = machineBlock.split("\n").filter((line) => line.startsWith(NOW_MANIFEST_PREFIX) && line.endsWith(" -->"));
  if (manifestLines.length !== 1) {
    errors.push({ kind: "now-machine-manifest-count", actual: manifestLines.length });
    return null;
  }
  try {
    return JSON.parse(manifestLines[0].slice(NOW_MANIFEST_PREFIX.length, -4));
  } catch {
    errors.push({ kind: "now-machine-manifest-json" });
    return null;
  }
}

function expectedBand(score) {
  if (score >= 85) return "A";
  if (score >= 70) return "B";
  if (score >= 55) return "C";
  if (score >= 35) return "D";
  return "E";
}

function isNumberInRange(value, minimum, maximum) {
  return typeof value === "number" && Number.isFinite(value) && value >= minimum && value <= maximum;
}

function collectSourceAliases(content) {
  return [...content.matchAll(/^\|\s*(SRC-[A-Z0-9-]+)\s*\|/gm)].map((match) => match[1]);
}

function lintSourceAssessments(records, sourceRefs, errors, warnings) {
  const requiredFields = [
    "schemaVersion", "assessmentId", "sourceRef", "canonicalSourceId", "evidenceLineageId",
    "sourceClass", "scores", "confidenceBand", "assessmentStatus", "assessedBy", "assessedAt",
    "reviewTrigger", "rationale", "limitation",
  ];
  const scoreFields = {
    identityAndOriginality: 20,
    factDirectness: 20,
    traceability: 20,
    fidelityAndCompleteness: 15,
    interestAndCorrection: 15,
    recencyAndVersion: 10,
  };
  const assessmentIds = new Set();
  const assessmentsBySourceRef = new Map();

  for (const record of records) {
    for (const field of requiredFields) {
      if (!(field in record) || record[field] === "" || record[field] === null) {
        errors.push({ kind: "source-assessment-field", assessmentId: record.assessmentId || null, field });
      }
    }

    if (assessmentIds.has(record.assessmentId)) {
      errors.push({ kind: "duplicate-source-assessment-id", assessmentId: record.assessmentId });
    }
    assessmentIds.add(record.assessmentId);

    if (!sourceRefs.has(record.sourceRef)) {
      errors.push({ kind: "invalid-source-ref", assessmentId: record.assessmentId, sourceRef: record.sourceRef });
    }

    const score = record.scores || {};
    let computedTotal = 0;
    for (const [field, maximum] of Object.entries(scoreFields)) {
      if (!isNumberInRange(score[field], 0, maximum)) {
        errors.push({ kind: "source-score-range", assessmentId: record.assessmentId, field, value: score[field] });
      } else {
        computedTotal += score[field];
      }
    }

    if (score.total !== computedTotal) {
      errors.push({ kind: "source-score-total", assessmentId: record.assessmentId, expected: computedTotal, actual: score.total });
    }

    if (record.confidenceBand !== expectedBand(score.total || 0)) {
      errors.push({ kind: "source-score-band", assessmentId: record.assessmentId, expected: expectedBand(score.total || 0), actual: record.confidenceBand });
    }

    if (record.assessmentStatus === "joe-reviewed") {
      for (const field of ["reviewedBy", "reviewedAt", "reviewDecision", "reviewRationale"]) {
        if (!record[field]) {
          errors.push({ kind: "source-review-field", assessmentId: record.assessmentId, field });
        }
      }
    }

    if (assessmentsBySourceRef.has(record.sourceRef)) {
      warnings.push({ kind: "multiple-source-assessments", sourceRef: record.sourceRef, assessmentIds: [assessmentsBySourceRef.get(record.sourceRef).assessmentId, record.assessmentId] });
    }
    assessmentsBySourceRef.set(record.sourceRef, record);
  }

  return assessmentsBySourceRef;
}

function lintClaimConfidence(records, assessmentsBySourceRef, wikiIds, errors, warnings) {
  const requiredFields = [
    "schemaVersion", "confidenceId", "claimId", "sourceRefs", "evidenceLineageIds", "claimImpact",
    "scores", "confidenceBand", "assessmentStatus", "assessedBy", "assessedAt", "reviewTrigger",
    "rationale", "limitation",
  ];
  const scoreFields = {
    directSupport: 25,
    sourceQuality: 20,
    independentLineages: 20,
    reproducibility: 15,
    currencyAndScope: 10,
  };
  const confidenceIds = new Set();

  for (const record of records) {
    for (const field of requiredFields) {
      if (!(field in record) || record[field] === "" || record[field] === null) {
        errors.push({ kind: "claim-confidence-field", confidenceId: record.confidenceId || null, field });
      }
    }

    if (confidenceIds.has(record.confidenceId)) {
      errors.push({ kind: "duplicate-claim-confidence-id", confidenceId: record.confidenceId });
    }
    confidenceIds.add(record.confidenceId);

    if (!wikiIds.has(record.claimId)) {
      errors.push({ kind: "invalid-confidence-claim", confidenceId: record.confidenceId, claimId: record.claimId });
    }

    const sourceRefs = Array.isArray(record.sourceRefs) ? record.sourceRefs : [];
    const declaredLineages = Array.isArray(record.evidenceLineageIds) ? record.evidenceLineageIds : [];
    const derivedLineages = [];

    for (const sourceRef of sourceRefs) {
      const assessment = assessmentsBySourceRef.get(sourceRef);
      if (!assessment) {
        errors.push({ kind: "unassessed-confidence-source", confidenceId: record.confidenceId, sourceRef });
      } else {
        derivedLineages.push(assessment.evidenceLineageId);
      }
    }

    if (new Set(derivedLineages).size !== derivedLineages.length || new Set(declaredLineages).size !== declaredLineages.length) {
      errors.push({ kind: "duplicate-evidence-lineage", confidenceId: record.confidenceId });
    }

    if (JSON.stringify([...new Set(derivedLineages)].sort()) !== JSON.stringify([...new Set(declaredLineages)].sort())) {
      errors.push({ kind: "evidence-lineage-mismatch", confidenceId: record.confidenceId });
    }

    const score = record.scores || {};
    let computedTotal = 0;
    for (const [field, maximum] of Object.entries(scoreFields)) {
      if (!isNumberInRange(score[field], 0, maximum)) {
        errors.push({ kind: "claim-score-range", confidenceId: record.confidenceId, field, value: score[field] });
      } else {
        computedTotal += score[field];
      }
    }

    if (!isNumberInRange(score.penalties, 0, 10)) {
      errors.push({ kind: "claim-score-range", confidenceId: record.confidenceId, field: "penalties", value: score.penalties });
    } else {
      computedTotal -= score.penalties;
    }

    if (score.total !== computedTotal) {
      errors.push({ kind: "claim-score-total", confidenceId: record.confidenceId, expected: computedTotal, actual: score.total });
    }

    if (record.confidenceBand !== expectedBand(score.total || 0)) {
      errors.push({ kind: "claim-score-band", confidenceId: record.confidenceId, expected: expectedBand(score.total || 0), actual: record.confidenceBand });
    }

    if (record.assessmentStatus === "joe-reviewed") {
      for (const field of ["reviewedBy", "reviewedAt", "reviewDecision", "reviewRationale"]) {
        if (!record[field]) {
          errors.push({ kind: "claim-review-field", confidenceId: record.confidenceId, field });
        }
      }

      if (!["confirmed", "adjusted", "rejected"].includes(record.reviewDecision)) {
        errors.push({ kind: "claim-review-decision", confidenceId: record.confidenceId, reviewDecision: record.reviewDecision });
      }
    }

    if ((record.confidenceBand === "A" || record.confidenceBand === "B" || record.claimImpact === "core" || record.claimImpact === "release") && record.assessmentStatus !== "joe-reviewed") {
      warnings.push({ kind: "unconfirmed-high-impact-claim", confidenceId: record.confidenceId, claimId: record.claimId, confidenceBand: record.confidenceBand, claimImpact: record.claimImpact });
    }
  }
}

async function lintIntakeLedger(records, registryBySourceId, wikiIds, repoRoot, errors, warnings) {
  const requiredFields = [
    "schemaVersion", "intakeId", "upstreamId", "knowledgeBaseId", "captureMode",
    "curator",
    "firstSeenAt", "versionHash", "registrySourceId", "canonicalSourceId",
    "evidenceLineageId", "relativePath", "status", "triageStatus", "selectionPriority",
    "topicIds", "questionIds", "subscriptionContent",
  ];
  const intakeIds = new Set();
  const versions = new Set();
  const registrySourceIds = new Set();

  for (const record of records) {
    for (const field of requiredFields) {
      if (!(field in record) || record[field] === "" || record[field] === null) {
        errors.push({ kind: "intake-field", intakeId: record.intakeId || null, field });
      }
    }

    if (intakeIds.has(record.intakeId)) {
      errors.push({ kind: "duplicate-intake-id", intakeId: record.intakeId });
    }
    intakeIds.add(record.intakeId);

    const versionKey = `${record.upstreamId}:${record.versionHash}`;
    if (versions.has(versionKey)) {
      errors.push({ kind: "duplicate-intake-version", intakeId: record.intakeId, versionKey });
    }
    versions.add(versionKey);

    if (registrySourceIds.has(record.registrySourceId)) {
      errors.push({ kind: "duplicate-intake-registry-source", intakeId: record.intakeId, registrySourceId: record.registrySourceId });
    }
    registrySourceIds.add(record.registrySourceId);

    if (record.knowledgeBaseId !== "JVl2k6DY") {
      errors.push({ kind: "invalid-intake-knowledge-base", intakeId: record.intakeId, knowledgeBaseId: record.knowledgeBaseId });
    }
    if (record.captureMode !== "joe-approved-note" || record.subscriptionContent !== false) {
      errors.push({ kind: "disallowed-intake-channel", intakeId: record.intakeId, captureMode: record.captureMode });
    }
    if (typeof record.upstreamId !== "string" || !/^\d+$/.test(record.upstreamId)) {
      errors.push({ kind: "invalid-intake-upstream-id", intakeId: record.intakeId, upstreamId: record.upstreamId });
    }
    if (!VALID_TRIAGE_STATUSES.has(record.triageStatus)) {
      errors.push({ kind: "invalid-intake-triage-status", intakeId: record.intakeId, triageStatus: record.triageStatus });
    }
    if (record.changeType !== undefined && !["baseline", "new-source", "revision"].includes(record.changeType)) {
      errors.push({ kind: "invalid-intake-change-type", intakeId: record.intakeId, changeType: record.changeType });
    }
    if (record.changeType === "revision" && !record.previousIntakeId) {
      errors.push({ kind: "missing-previous-intake", intakeId: record.intakeId });
    }
    if (record.previousIntakeId && !records.some((candidate) => candidate.intakeId === record.previousIntakeId)) {
      errors.push({ kind: "invalid-previous-intake", intakeId: record.intakeId, previousIntakeId: record.previousIntakeId });
    }
    if (!record.batchId || !record.changeType) {
      warnings.push({ kind: "legacy-intake-batch-metadata", intakeId: record.intakeId });
    }

    const registryRecord = registryBySourceId.get(record.registrySourceId);
    if (!registryRecord) {
      errors.push({ kind: "missing-intake-registry-source", intakeId: record.intakeId, registrySourceId: record.registrySourceId });
    } else if (registryRecord.relativePath !== record.relativePath) {
      errors.push({
        kind: "intake-registry-path-mismatch",
        intakeId: record.intakeId,
        expected: registryRecord.relativePath,
        actual: record.relativePath,
      });
    } else {
      if (registryRecord.noteId !== record.upstreamId) {
        errors.push({
          kind: "intake-registry-note-id-mismatch",
          intakeId: record.intakeId,
          expected: registryRecord.noteId,
          actual: record.upstreamId,
        });
      }
      if (registryRecord.canonicalSourceId !== record.canonicalSourceId) {
        errors.push({
          kind: "intake-registry-canonical-mismatch",
          intakeId: record.intakeId,
          expected: registryRecord.canonicalSourceId,
          actual: record.canonicalSourceId,
        });
      }
    }

    const intakePath = path.join(repoRoot, record.relativePath);
    if (!await pathExists(intakePath)) {
      errors.push({ kind: "missing-intake-path", intakeId: record.intakeId, relativePath: record.relativePath });
    } else {
      const intakeContent = await readFile(intakePath, "utf8");
      const intakeMetadata = parseFrontmatter(intakeContent);
      if (parseScalar(intakeMetadata.note_id) !== record.upstreamId) {
        errors.push({ kind: "intake-raw-note-id-mismatch", intakeId: record.intakeId, actual: parseScalar(intakeMetadata.note_id) });
      }
      if (parseScalar(intakeMetadata.version_hash) !== record.versionHash) {
        errors.push({ kind: "intake-raw-version-hash-mismatch", intakeId: record.intakeId, actual: parseScalar(intakeMetadata.version_hash) });
      }
      if (parseScalar(intakeMetadata.registry_source_id) !== record.registrySourceId) {
        errors.push({ kind: "intake-raw-source-id-mismatch", intakeId: record.intakeId, actual: parseScalar(intakeMetadata.registry_source_id) });
      }
    }

    for (const [field, ids] of [["topicIds", record.topicIds], ["questionIds", record.questionIds]]) {
      if (!Array.isArray(ids)) {
        errors.push({ kind: "invalid-intake-routing", intakeId: record.intakeId, field });
        continue;
      }
      for (const referencedId of ids) {
        if (!wikiIds.has(referencedId)) {
          errors.push({ kind: "missing-intake-routing-target", intakeId: record.intakeId, field, referencedId });
        }
      }
    }
  }
}

function lintIntakeBaseline(state, intakeRecords, errors) {
  const requiredFields = [
    "schemaVersion", "status", "scope", "knowledgeBaseId", "completedAt",
    "ordinaryNoteCount", "ordinaryNoteIds", "ordinaryNoteIdsHash", "generatorVersion",
  ];
  if (!state || typeof state !== "object" || Array.isArray(state)) {
    errors.push({ kind: "invalid-intake-baseline" });
    return;
  }
  for (const field of requiredFields) {
    if (!(field in state) || state[field] === "" || state[field] === null) {
      errors.push({ kind: "intake-baseline-field", field });
    }
  }
  if (state.schemaVersion !== "1.0" || state.status !== "complete" || state.scope !== "all" || state.knowledgeBaseId !== "JVl2k6DY") {
    errors.push({
      kind: "intake-baseline-boundary",
      schemaVersion: state.schemaVersion,
      status: state.status,
      scope: state.scope,
      knowledgeBaseId: state.knowledgeBaseId,
    });
  }

  const noteIds = Array.isArray(state.ordinaryNoteIds) ? state.ordinaryNoteIds : [];
  if (!Array.isArray(state.ordinaryNoteIds)) {
    errors.push({ kind: "intake-baseline-id-list" });
  }
  const invalidIds = noteIds.filter((noteId) => typeof noteId !== "string" || !/^\d+$/.test(noteId));
  for (const noteId of invalidIds) {
    errors.push({ kind: "intake-baseline-id-type", noteId });
  }
  if (new Set(noteIds).size !== noteIds.length) {
    errors.push({ kind: "duplicate-intake-baseline-id" });
  }
  if (invalidIds.length === 0) {
    const sortedNoteIds = [...noteIds].sort(compareCodePoints);
    if (stableJson(noteIds) !== stableJson(sortedNoteIds)) {
      errors.push({ kind: "intake-baseline-id-order" });
    }
    const expectedHash = ordinaryNoteIdsHash(noteIds);
    if (state.ordinaryNoteIdsHash !== expectedHash) {
      errors.push({ kind: "intake-baseline-id-hash", expected: expectedHash, actual: state.ordinaryNoteIdsHash });
    }
  }
  if (!Number.isInteger(state.ordinaryNoteCount) || state.ordinaryNoteCount < 0 || state.ordinaryNoteCount !== noteIds.length) {
    errors.push({ kind: "intake-baseline-id-count", expected: noteIds.length, actual: state.ordinaryNoteCount });
  }

  const ledgerNoteIds = new Set(intakeRecords.map((record) => record.upstreamId));
  for (const noteId of noteIds) {
    if (typeof noteId === "string" && !ledgerNoteIds.has(noteId)) {
      errors.push({ kind: "missing-intake-baseline-ledger-id", noteId });
    }
  }
}

function classifyIntakeRecords(records) {
  const classifications = new Map();
  const seenUpstreamIds = new Set();
  const ordered = [...records].sort((left, right) => {
    const leftKey = `${left.firstSeenAt || ""}\n${left.intakeId || ""}`;
    const rightKey = `${right.firstSeenAt || ""}\n${right.intakeId || ""}`;
    return compareCodePoints(leftKey, rightKey);
  });
  for (const record of ordered) {
    let classification = record.changeType;
    if (classification === "revision") {
      classification = "new-version";
    } else if (!classification) {
      classification = record.status === "baseline"
        ? "baseline"
        : seenUpstreamIds.has(record.upstreamId) ? "new-version" : "new-source";
    }
    classifications.set(record.intakeId, classification);
    seenUpstreamIds.add(record.upstreamId);
  }
  return classifications;
}

function lintIntakeBatches(
  batches,
  intakeRecords,
  registryRecords,
  errors,
  warnings,
) {
  const requiredFields = [
    "schemaVersion", "batchId", "previousBatchId", "mode", "knowledgeBaseId",
    "observedAt", "status", "inputHash", "counts", "before", "after", "added",
    "subscriptionContent", "generatorVersion",
  ];
  const intakeById = new Map(intakeRecords.map((record) => [record.intakeId, record]));
  const classifications = classifyIntakeRecords(intakeRecords);
  const seenBatchIds = new Set();
  const seenIntakeIds = new Set();
  let previousBatch = null;

  for (const batch of batches) {
    for (const field of requiredFields) {
      if (!(field in batch) || batch[field] === "" || batch[field] === undefined) {
        errors.push({ kind: "intake-batch-field", batchId: batch.batchId || null, field });
      }
    }
    if (seenBatchIds.has(batch.batchId)) {
      errors.push({ kind: "duplicate-intake-batch-id", batchId: batch.batchId });
    }
    seenBatchIds.add(batch.batchId);
    if (batch.knowledgeBaseId !== "JVl2k6DY" || batch.status !== "completed" || batch.subscriptionContent !== false) {
      errors.push({ kind: "invalid-intake-batch-boundary", batchId: batch.batchId });
    }
    if ((previousBatch?.batchId || null) !== batch.previousBatchId) {
      errors.push({ kind: "intake-batch-chain", batchId: batch.batchId, expected: previousBatch?.batchId || null, actual: batch.previousBatchId });
    }

    const added = batch.added || {};
    const addedIntakeIds = Array.isArray(added.intakeIds) ? added.intakeIds : [];
    const addedRegistrySourceIds = Array.isArray(added.registrySourceIds) ? added.registrySourceIds : [];
    const addedRelativePaths = Array.isArray(added.relativePaths) ? added.relativePaths : [];
    if (addedIntakeIds.length !== addedRegistrySourceIds.length || addedIntakeIds.length !== addedRelativePaths.length) {
      errors.push({ kind: "intake-batch-added-length", batchId: batch.batchId });
    }
    const groupRecords = [];
    for (const [index, intakeId] of addedIntakeIds.entries()) {
      if (seenIntakeIds.has(intakeId)) {
        errors.push({ kind: "duplicate-batched-intake", batchId: batch.batchId, intakeId });
      }
      seenIntakeIds.add(intakeId);
      const intakeRecord = intakeById.get(intakeId);
      if (!intakeRecord) {
        errors.push({ kind: "missing-batch-intake", batchId: batch.batchId, intakeId });
        continue;
      }
      groupRecords.push(intakeRecord);
      if (intakeRecord.registrySourceId !== addedRegistrySourceIds[index] || intakeRecord.relativePath !== addedRelativePaths[index]) {
        errors.push({ kind: "intake-batch-added-mismatch", batchId: batch.batchId, intakeId });
      }
      if (intakeRecord.batchId && intakeRecord.batchId !== batch.batchId) {
        errors.push({ kind: "intake-record-batch-mismatch", batchId: batch.batchId, intakeId, actual: intakeRecord.batchId });
      }
    }

    const currentInputHash = `sha256:${hashContent(groupRecords.map((record) => `${stableJson(record)}\n`).join(""))}`;
    if (batch.inputHash !== currentInputHash) {
      warnings.push({
        kind: "intake-batch-current-input-drift",
        batchId: batch.batchId,
        frozenInputHash: batch.inputHash,
        currentInputHash,
      });
    }

    const counts = batch.counts || {};
    const countFields = [
      "addedVersions", "assessed", "baselineVersions", "integrated",
      "missingRequiredAssessments", "newSources", "pendingTriage",
      "requiredAssessments", "revisions", "routed",
    ];
    for (const field of countFields) {
      if (!Number.isInteger(counts[field]) || counts[field] < 0) {
        errors.push({ kind: "intake-batch-count-value", batchId: batch.batchId, field, actual: counts[field] });
      }
    }
    if (counts.addedVersions !== groupRecords.length) {
      errors.push({ kind: "intake-batch-added-count", batchId: batch.batchId, expected: groupRecords.length, actual: counts.addedVersions });
    }
    if (counts.addedVersions !== counts.baselineVersions + counts.newSources + counts.revisions) {
      errors.push({ kind: "intake-batch-classification-total", batchId: batch.batchId });
    }
    if (counts.addedVersions !== counts.pendingTriage + counts.routed + counts.integrated) {
      errors.push({ kind: "intake-batch-triage-total", batchId: batch.batchId });
    }
    if (counts.requiredAssessments !== counts.routed + counts.integrated) {
      errors.push({ kind: "intake-batch-required-assessment-total", batchId: batch.batchId });
    }
    if (counts.assessed > counts.addedVersions || counts.missingRequiredAssessments > counts.requiredAssessments) {
      errors.push({ kind: "intake-batch-assessment-range", batchId: batch.batchId });
    }
    if (counts.requiredAssessments - counts.missingRequiredAssessments > counts.assessed) {
      errors.push({ kind: "intake-batch-assessment-total", batchId: batch.batchId });
    }
    const expectedMode = counts.baselineVersions === counts.addedVersions ? "baseline" : "incremental";
    if (batch.mode !== expectedMode) {
      errors.push({ kind: "intake-batch-mode", batchId: batch.batchId, expected: expectedMode, actual: batch.mode });
    }

    for (const field of ["managedRawVersions", "intakeRecords", "rawEvidenceRecords", "registryRecords"]) {
      const expectedBefore = previousBatch ? previousBatch.after?.[field] : batch.before?.[field];
      if (previousBatch && batch.before?.[field] !== expectedBefore) {
        errors.push({ kind: "intake-batch-before-chain", batchId: batch.batchId, field, expected: expectedBefore, actual: batch.before?.[field] });
      }
      if (batch.after?.[field] - batch.before?.[field] !== groupRecords.length) {
        errors.push({ kind: "intake-batch-delta", batchId: batch.batchId, field });
      }
    }
    previousBatch = batch;
  }

  for (const intakeId of intakeById.keys()) {
    if (!seenIntakeIds.has(intakeId)) {
      errors.push({ kind: "unbatched-intake", intakeId });
    }
  }
  if (previousBatch) {
    const rawEvidenceRecords = registryRecords.filter((record) => record.sourceLayer === "raw").length;
    const expectedAfter = {
      managedRawVersions: intakeRecords.length,
      intakeRecords: intakeRecords.length,
      rawEvidenceRecords,
    };
    const actualAfter = Object.fromEntries(
      Object.entries(expectedAfter).map(([field]) => [field, previousBatch.after?.[field]]),
    );
    if (stableJson(actualAfter) !== stableJson(expectedAfter)) {
      errors.push({ kind: "intake-batch-final-counts", batchId: previousBatch.batchId, expected: expectedAfter, actual: previousBatch.after });
    }
  } else if (intakeRecords.length > 0) {
    errors.push({ kind: "missing-intake-batches", intakeRecords: intakeRecords.length });
  }

  return { classifications, latestBatch: previousBatch };
}

async function pathExists(targetPath) {
  try {
    await access(targetPath);
    return true;
  } catch {
    return false;
  }
}

function internalMarkdownLinks(content) {
  const links = [];
  const matcher = /\]\((?:<([^>]+)>|([^)]+))\)/g;
  let match;

  while ((match = matcher.exec(content)) !== null) {
    const target = (match[1] || match[2]).split("#")[0];

    if (target && !target.startsWith("http://") && !target.startsWith("https://") && !target.startsWith("mailto:")) {
      links.push(target);
    }
  }

  return links;
}

export async function lintKnowledgeBase({
  repoRoot = DEFAULT_REPO_ROOT,
  generatedAt = process.env.WORKBENCH_NOW || new Date().toISOString(),
  writeReport = true,
} = {}) {
  const resolvedRepoRoot = path.resolve(repoRoot);
  const registryPath = path.join(resolvedRepoRoot, "3-processing/index/source-registry.jsonl");
  const snapshotPath = path.join(resolvedRepoRoot, "3-processing/index/source-registry.snapshot.json");
  const reportPath = path.join(resolvedRepoRoot, "3-processing/index/governance-lint-report.json");
  const wikiRoot = path.join(resolvedRepoRoot, "3-processing/wiki");
  const sourceAssessmentsPath = path.join(resolvedRepoRoot, "3-processing/index/source-assessments.jsonl");
  const claimConfidencePath = path.join(resolvedRepoRoot, "3-processing/index/claim-confidence.jsonl");
  const intakeBaselinePath = path.join(resolvedRepoRoot, "3-processing/index/intake-baseline.json");
  const intakeLedgerPath = path.join(resolvedRepoRoot, "3-processing/index/intake-ledger.jsonl");
  const intakeBatchesPath = path.join(resolvedRepoRoot, "3-processing/index/intake-batches.jsonl");
  const nowPath = path.join(wikiRoot, "NOW.md");
  const errors = [];
  const warnings = [];
  const registryContent = await readFile(registryPath, "utf8");
  const registry = parseJsonl(registryContent, "3-processing/index/source-registry.jsonl", errors);
  const snapshot = JSON.parse(await readFile(snapshotPath, "utf8"));
  const evidenceFileCounts = await countEvidenceFiles(resolvedRepoRoot);
  const sourceIds = new Set();
  const noteIds = new Set();
  const registryBySourceId = new Map();
  const canonicalGroups = new Map();
  const registryByLayer = { raw: 0, data: 0 };
  const registryByFidelity = {};

  for (const record of registry) {
    for (const field of REGISTRY_FIELDS) {
      if (!(field in record)) {
        errors.push({ kind: "registry-field", sourceId: record.sourceId || null, field });
      }
    }
    if (sourceIds.has(record.sourceId)) {
      errors.push({ kind: "duplicate-source-id", sourceId: record.sourceId });
    }
    sourceIds.add(record.sourceId);
    registryBySourceId.set(record.sourceId, record);
    if (record.noteId) {
      noteIds.add(record.noteId);
    }
    if (record.canonicalSourceId) {
      canonicalGroups.set(record.canonicalSourceId, (canonicalGroups.get(record.canonicalSourceId) || 0) + 1);
    }
    registryByLayer[record.sourceLayer] = (registryByLayer[record.sourceLayer] || 0) + 1;
    registryByFidelity[record.fidelity] = (registryByFidelity[record.fidelity] || 0) + 1;
    const sourcePath = path.join(resolvedRepoRoot, record.relativePath);
    if (!await pathExists(sourcePath)) {
      errors.push({ kind: "missing-source-path", sourceId: record.sourceId, relativePath: record.relativePath });
    } else {
      const actualHash = hashContent(await readFile(sourcePath));
      if (actualHash !== record.contentHash) {
        errors.push({ kind: "source-content-hash", sourceId: record.sourceId, expected: actualHash, actual: record.contentHash });
      }
    }
  }

  const duplicateCanonicalSourceIds = [...canonicalGroups.entries()]
    .filter(([, count]) => count > 1)
    .map(([sourceId]) => sourceId)
    .sort(compareCodePoints);
  const expectedSnapshotValues = {
    schemaVersion: "1.1",
    registryPath: "3-processing/index/source-registry.jsonl",
    registryHash: hashContent(registryContent),
    recordCount: registry.length,
    uniqueSourceIds: sourceIds.size,
    uniqueNoteIds: noteIds.size,
    byLayer: registryByLayer,
    byFidelity: registryByFidelity,
    duplicateSourceIds: [],
    duplicateCanonicalSourceIds,
    sourceRoots: ["1-raw", "2-data"],
  };
  for (const [field, expected] of Object.entries(expectedSnapshotValues)) {
    if (stableJson(snapshot[field]) !== stableJson(expected)) {
      errors.push({ kind: `snapshot-${field}`, expected, actual: snapshot[field] });
    }
  }
  for (const sourceLayer of ["raw", "data"]) {
    if (evidenceFileCounts[sourceLayer] !== registryByLayer[sourceLayer]) {
      errors.push({
        kind: "evidence-registry-count",
        sourceLayer,
        expected: evidenceFileCounts[sourceLayer],
        actual: registryByLayer[sourceLayer],
      });
    }
  }
  if (Object.values(registryByLayer).reduce((total, count) => total + count, 0) !== registry.length) {
    errors.push({ kind: "registry-layer-total" });
  }
  if (Object.values(registryByFidelity).reduce((total, count) => total + count, 0) !== registry.length) {
    errors.push({ kind: "registry-fidelity-total" });
  }

  const wikiPaths = await walkMarkdownFiles(wikiRoot);
  const wikiIds = new Map();
  const wikiRecords = [];
  const sourceAliases = new Set();
  let checkedLinks = 0;

  for (const wikiPath of wikiPaths) {
    const content = await readFile(wikiPath, "utf8");
    const metadata = parseFrontmatter(content);
    const relativePath = path.relative(resolvedRepoRoot, wikiPath).split(path.sep).join("/");
    wikiRecords.push({ metadata, relativePath });
    if (relativePath.includes("/_indexes/")) {
      for (const sourceAlias of collectSourceAliases(content)) {
        sourceAliases.add(sourceAlias);
      }
    }
    if (metadata.id) {
      if (wikiIds.has(metadata.id)) {
        errors.push({ kind: "duplicate-wiki-id", id: metadata.id, paths: [wikiIds.get(metadata.id), relativePath] });
      }
      wikiIds.set(metadata.id, relativePath);
    }
    if (metadata.type && WIKI_REQUIRED_FIELDS[metadata.type]) {
      for (const field of WIKI_REQUIRED_FIELDS[metadata.type]) {
        if (!metadata[field]) {
          errors.push({ kind: "wiki-field", relativePath, type: metadata.type, field });
        }
      }
    } else if (!relativePath.includes("/_schema/") && !relativePath.includes("/_indexes/") && !relativePath.endsWith("wiki/HOME.md") && !metadata.id) {
      warnings.push({ kind: "wiki-page-without-id", relativePath });
    }
    for (const target of internalMarkdownLinks(content)) {
      checkedLinks += 1;
      if (!await pathExists(path.resolve(path.dirname(wikiPath), target))) {
        errors.push({ kind: "broken-wiki-link", relativePath, target });
      }
    }
  }

  const referenceFields = ["question_ids", "topic_ids", "claim_ids", "tension_ids", "synthesis_ids", "concept_ids", "briefing_ids"];
  const sourcePageRegistryIds = new Set();
  for (const { metadata, relativePath } of wikiRecords) {
    for (const field of referenceFields) {
      for (const referencedId of parseInlineList(metadata[field])) {
        if (!wikiIds.has(referencedId)) {
          errors.push({ kind: "missing-wiki-reference", relativePath, field, referencedId });
        }
      }
    }
    if (metadata.type === "release") {
      for (const outputPath of parseInlineList(metadata.output_paths)) {
        if (!await pathExists(path.join(resolvedRepoRoot, outputPath))) {
          errors.push({ kind: "missing-release-output", relativePath, outputPath });
        }
      }
    }
    if (metadata.type === "source") {
      const registrySourceId = parseScalar(metadata.registry_source_id);
      const canonicalSourceId = parseScalar(metadata.canonical_source_id);
      const registryRecord = registryBySourceId.get(registrySourceId);
      if (sourcePageRegistryIds.has(registrySourceId)) {
        errors.push({ kind: "duplicate-source-page-registry-id", relativePath, registrySourceId });
      }
      sourcePageRegistryIds.add(registrySourceId);
      if (!registryRecord) {
        errors.push({ kind: "missing-source-page-registry-id", relativePath, registrySourceId });
      } else if (registryRecord.canonicalSourceId !== canonicalSourceId) {
        errors.push({ kind: "source-page-canonical-mismatch", relativePath, expected: registryRecord.canonicalSourceId, actual: canonicalSourceId });
      }
    }
  }

  const sourceAssessmentRecords = parseJsonl(await readFile(sourceAssessmentsPath, "utf8"), "3-processing/index/source-assessments.jsonl", errors);
  const claimConfidenceRecords = parseJsonl(await readFile(claimConfidencePath, "utf8"), "3-processing/index/claim-confidence.jsonl", errors);
  const intakeRecords = await pathExists(intakeLedgerPath)
    ? parseJsonl(await readFile(intakeLedgerPath, "utf8"), "3-processing/index/intake-ledger.jsonl", errors)
    : [];
  const intakeBatches = await pathExists(intakeBatchesPath)
    ? parseJsonl(await readFile(intakeBatchesPath, "utf8"), "3-processing/index/intake-batches.jsonl", errors)
    : [];
  let intakeBaseline = null;
  if (await pathExists(intakeBaselinePath)) {
    try {
      intakeBaseline = JSON.parse(await readFile(intakeBaselinePath, "utf8"));
    } catch {
      errors.push({ kind: "invalid-intake-baseline-json" });
    }
  } else {
    errors.push({ kind: "missing-intake-baseline" });
  }
  await lintIntakeLedger(intakeRecords, registryBySourceId, wikiIds, resolvedRepoRoot, errors, warnings);
  if (intakeBaseline) {
    lintIntakeBaseline(intakeBaseline, intakeRecords, errors);
  }
  const assessmentsBySourceRef = lintSourceAssessments(sourceAssessmentRecords, new Set([...sourceIds, ...sourceAliases]), errors, warnings);
  lintClaimConfidence(claimConfidenceRecords, assessmentsBySourceRef, wikiIds, errors, warnings);

  for (const intakeRecord of intakeRecords) {
    if (["routed", "integrated"].includes(intakeRecord.triageStatus) && !assessmentsBySourceRef.has(intakeRecord.registrySourceId)) {
      errors.push({ kind: "unassessed-routed-intake-source", intakeId: intakeRecord.intakeId, registrySourceId: intakeRecord.registrySourceId });
    }
  }
  const assessmentsById = new Map(sourceAssessmentRecords.map((record) => [record.assessmentId, record]));
  for (const { metadata, relativePath } of wikiRecords.filter(({ metadata }) => metadata.type === "source")) {
    const assessmentId = parseScalar(metadata.assessment_id);
    const assessment = assessmentsById.get(assessmentId);
    const registrySourceId = parseScalar(metadata.registry_source_id);
    if (!assessment) {
      errors.push({ kind: "missing-source-page-assessment", relativePath, assessmentId });
    } else if (assessment.sourceRef !== registrySourceId) {
      errors.push({ kind: "source-page-assessment-mismatch", relativePath, assessmentId, expected: registrySourceId, actual: assessment.sourceRef });
    }
  }

  const batchResult = lintIntakeBatches(intakeBatches, intakeRecords, registry, errors, warnings);
  const classifications = batchResult.classifications;
  const latestBatch = batchResult.latestBatch;
  const requiredAssessmentRecords = intakeRecords.filter((record) => ["routed", "integrated"].includes(record.triageStatus));
  const assessedIntakeRecords = intakeRecords.filter((record) => assessmentsBySourceRef.has(record.registrySourceId));
  const missingRequiredAssessments = requiredAssessmentRecords.filter((record) => !assessmentsBySourceRef.has(record.registrySourceId)).length;
  const expectedNowManifest = {
    schemaVersion: "1.0",
    generatedFrom: "3-processing/index/intake-batches.jsonl",
    knowledgeAsOf: latestBatch ? shanghaiDate(latestBatch.observedAt) : null,
    latestBatchId: latestBatch?.batchId || null,
    registryRecords: registry.length,
    rawEvidenceRecords: registryByLayer.raw,
    dataEvidenceRecords: registryByLayer.data,
    intakeRecords: intakeRecords.length,
    ordinaryNoteIdentities: new Set(intakeRecords.map((record) => record.upstreamId)).size,
    intakeBatches: intakeBatches.length,
    baselineVersions: [...classifications.values()].filter((value) => value === "baseline").length,
    newSourceVersions: [...classifications.values()].filter((value) => value === "new-source").length,
    revisionVersions: [...classifications.values()].filter((value) => value === "new-version").length,
    pendingTriage: intakeRecords.filter((record) => record.triageStatus === "pending").length,
    routed: intakeRecords.filter((record) => record.triageStatus === "routed").length,
    integrated: intakeRecords.filter((record) => record.triageStatus === "integrated").length,
    assessed: assessedIntakeRecords.length,
    requiredAssessments: requiredAssessmentRecords.length,
    missingRequiredAssessments,
    subscriptionRecords: intakeRecords.filter((record) => record.subscriptionContent !== false).length,
  };
  const nowContent = await readFile(nowPath, "utf8");
  const nowManifest = parseNowManifest(nowContent, errors);
  if (nowManifest && stableJson(nowManifest) !== stableJson(expectedNowManifest)) {
    errors.push({ kind: "now-machine-counts", expected: expectedNowManifest, actual: nowManifest });
  }
  if (expectedNowManifest.knowledgeAsOf) {
    const nowMetadata = parseFrontmatter(nowContent);
    const frontmatterAsOf = parseScalar(nowMetadata.as_of);
    if (frontmatterAsOf !== expectedNowManifest.knowledgeAsOf) {
      errors.push({ kind: "now-frontmatter-as-of", expected: expectedNowManifest.knowledgeAsOf, actual: frontmatterAsOf });
    }
    const deadlineMatches = [...nowContent.matchAll(/^> 内容截至：([^\n]+)$/gm)];
    if (deadlineMatches.length !== 1 || deadlineMatches[0][1].trim() !== expectedNowManifest.knowledgeAsOf) {
      errors.push({
        kind: "now-visible-as-of",
        expected: expectedNowManifest.knowledgeAsOf,
        actual: deadlineMatches.map((match) => match[1].trim()),
      });
    }
  }

  const reportCore = {
    passed: errors.length === 0,
    checks: {
      rawEvidenceRecords: evidenceFileCounts.raw,
      dataEvidenceRecords: evidenceFileCounts.data,
      registryRecords: registry.length,
      registryHash: hashContent(registryContent),
      uniqueSourceIds: sourceIds.size,
      uniqueNoteIds: noteIds.size,
      duplicateCanonicalSourceIds: duplicateCanonicalSourceIds.length,
      wikiPages: wikiPaths.length,
      wikiIds: wikiIds.size,
      checkedLinks,
      sourceAliases: sourceAliases.size,
      sourceAssessments: sourceAssessmentRecords.length,
      claimConfidence: claimConfidenceRecords.length,
      intakeRecords: intakeRecords.length,
      intakeBaselineStatus: intakeBaseline?.status || null,
      intakeBaselineScope: intakeBaseline?.scope || null,
      intakeBaselineNoteCount: intakeBaseline?.ordinaryNoteCount ?? null,
      intakeBaselineNoteIdsHash: intakeBaseline?.ordinaryNoteIdsHash || null,
      intakeBatches: intakeBatches.length,
      pendingTriage: expectedNowManifest.pendingTriage,
      routedIntakeRecords: expectedNowManifest.routed,
      integratedIntakeRecords: expectedNowManifest.integrated,
      assessedIntakeRecords: assessedIntakeRecords.length,
      requiredAssessmentRecords: requiredAssessmentRecords.length,
      missingRequiredAssessments,
      subscriptionIntakeRecords: expectedNowManifest.subscriptionRecords,
      nowLatestBatchId: expectedNowManifest.latestBatchId,
    },
    errors,
    warnings,
  };
  const previousReport = await pathExists(reportPath) ? JSON.parse(await readFile(reportPath, "utf8")) : null;
  const previousCore = previousReport ? {
    passed: previousReport.passed,
    checks: previousReport.checks,
    errors: previousReport.errors,
    warnings: previousReport.warnings,
  } : null;
  const reportChanged = !previousCore || stableJson(previousCore) !== stableJson(reportCore);
  const report = reportChanged ? { generatedAt, ...reportCore } : previousReport;
  if (writeReport && reportChanged) {
    await atomicWrite(reportPath, `${JSON.stringify(report, null, 2)}\n`);
  }
  return { changed: reportChanged, ...report };
}

function parseArgs(argv) {
  const options = {
    repoRoot: DEFAULT_REPO_ROOT,
    generatedAt: process.env.WORKBENCH_NOW || new Date().toISOString(),
  };
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--repo-root") {
      options.repoRoot = argv[++index];
    } else if (argument === "--generated-at") {
      options.generatedAt = argv[++index];
    } else {
      throw new Error(`Unknown argument: ${argument}`);
    }
  }
  if (!options.repoRoot || !options.generatedAt) {
    throw new Error("--repo-root and --generated-at require values");
  }
  return options;
}

async function main() {
  const result = await lintKnowledgeBase(parseArgs(process.argv.slice(2)));
  console.log(JSON.stringify(result, null, 2));
  if (!result.passed) {
    process.exitCode = 1;
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
}
