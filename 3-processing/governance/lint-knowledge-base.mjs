import { access, readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, "../..");
const registryPath = path.join(repoRoot, "3-processing/index/source-registry.jsonl");
const snapshotPath = path.join(repoRoot, "3-processing/index/source-registry.snapshot.json");
const reportPath = path.join(repoRoot, "3-processing/index/governance-lint-report.json");
const wikiRoot = path.join(repoRoot, "3-processing/wiki");

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
  claim: ["id", "type", "status", "question_ids", "source_ids", "scope", "as_of"],
  concept: ["id", "type", "status", "claim_ids", "as_of"],
  question: ["id", "type", "status", "as_of", "event", "years"],
  release: ["id", "type", "status", "synthesis_ids", "output_paths", "as_of"],
  synthesis: ["id", "type", "status", "question_ids", "claim_ids", "as_of"],
  tension: ["id", "type", "status", "question_ids", "claim_ids", "as_of"],
};

async function walkMarkdownFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const paths = [];

  for (const entry of entries.sort((a, b) => a.name.localeCompare(b.name))) {
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
  const matcher = /\]\(([^)]+)\)/g;
  let match;

  while ((match = matcher.exec(content)) !== null) {
    const target = match[1].replace(/^</, "").replace(/>$/, "").split("#")[0];

    if (target && !target.startsWith("http://") && !target.startsWith("https://") && !target.startsWith("mailto:")) {
      links.push(target);
    }
  }

  return links;
}

async function lintKnowledgeBase() {
  const errors = [];
  const warnings = [];
  const registryContent = await readFile(registryPath, "utf8");
  const registry = registryContent.trim().split("\n").filter(Boolean).map((line) => JSON.parse(line));
  const snapshot = JSON.parse(await readFile(snapshotPath, "utf8"));
  const sourceIds = new Set();
  const canonicalGroups = new Map();

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

    if (record.canonicalSourceId) {
      canonicalGroups.set(record.canonicalSourceId, (canonicalGroups.get(record.canonicalSourceId) || 0) + 1);
    }

    if (!await pathExists(path.join(repoRoot, record.relativePath))) {
      errors.push({ kind: "missing-source-path", sourceId: record.sourceId, relativePath: record.relativePath });
    }
  }

  if (snapshot.recordCount !== registry.length) {
    errors.push({ kind: "snapshot-record-count", expected: registry.length, actual: snapshot.recordCount });
  }

  if (snapshot.uniqueSourceIds !== sourceIds.size) {
    errors.push({ kind: "snapshot-source-id-count", expected: sourceIds.size, actual: snapshot.uniqueSourceIds });
  }

  const duplicateCanonicalSourceIds = [...canonicalGroups.entries()]
    .filter(([, count]) => count > 1)
    .map(([sourceId]) => sourceId)
    .sort();

  if (JSON.stringify(duplicateCanonicalSourceIds) !== JSON.stringify([...snapshot.duplicateCanonicalSourceIds].sort())) {
    errors.push({ kind: "snapshot-lineage-groups", expected: duplicateCanonicalSourceIds.length, actual: snapshot.duplicateCanonicalSourceIds.length });
  }

  const wikiPaths = await walkMarkdownFiles(wikiRoot);
  const wikiIds = new Map();
  const wikiRecords = [];
  let checkedLinks = 0;

  for (const wikiPath of wikiPaths) {
    const content = await readFile(wikiPath, "utf8");
    const metadata = parseFrontmatter(content);
    const relativePath = path.relative(repoRoot, wikiPath);
    wikiRecords.push({ metadata, relativePath });

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
    } else if (!relativePath.includes("_schema") && !relativePath.includes("_indexes") && !relativePath.endsWith("wiki/HOME.md") && !metadata.id) {
      warnings.push({ kind: "wiki-page-without-id", relativePath });
    }

    for (const target of internalMarkdownLinks(content)) {
      checkedLinks += 1;
      if (!await pathExists(path.resolve(path.dirname(wikiPath), target))) {
        errors.push({ kind: "broken-wiki-link", relativePath, target });
      }
    }
  }

  const referenceFields = ["question_ids", "claim_ids", "tension_ids", "synthesis_ids", "concept_ids"];

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
        if (!await pathExists(path.join(repoRoot, outputPath))) {
          errors.push({ kind: "missing-release-output", relativePath, outputPath });
        }
      }
    }
  }

  const report = {
    generatedAt: new Date().toISOString(),
    passed: errors.length === 0,
    checks: {
      registryRecords: registry.length,
      uniqueSourceIds: sourceIds.size,
      duplicateCanonicalSourceIds: duplicateCanonicalSourceIds.length,
      wikiPages: wikiPaths.length,
      wikiIds: wikiIds.size,
      checkedLinks,
    },
    errors,
    warnings,
  };

  await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify(report, null, 2));

  if (!report.passed) {
    process.exitCode = 1;
  }
}

lintKnowledgeBase().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
