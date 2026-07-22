import { createHash } from "node:crypto";
import { mkdir, readdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, "../..");
const registryPath = path.join(repoRoot, "3-processing/index/source-registry.jsonl");
const snapshotPath = path.join(repoRoot, "3-processing/index/source-registry.snapshot.json");

const SOURCE_ROOTS = [
  { directory: "1-raw", sourceLayer: "raw" },
  { directory: "2-data", sourceLayer: "data" },
];

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

  const frontmatter = content.slice(4, end);
  const values = {};

  for (const line of frontmatter.split("\n")) {
    const match = line.match(/^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$/);

    if (!match) {
      continue;
    }

    const [, key, rawValue] = match;
    values[key] = rawValue.trim().replace(/^"(.*)"$/, "$1");
  }

  return values;
}

function inferEventYear(relativePath, title) {
  const text = `${relativePath} ${title ?? ""}`;
  const waicMatch = text.match(/WAIC[-_ ]?(20\d{2})/i);
  const yearMatch = text.match(/(?:^|\D)(20\d{2})(?:\D|$)/);
  const value = waicMatch?.[1] ?? yearMatch?.[1];

  return value ? Number(value) : null;
}

function inferFidelity(metadata, sourceLayer) {
  if (metadata.content_source === "manual-transcript") {
    return "verbatim";
  }

  if (metadata.content_source?.includes("transcript")) {
    return "verbatim";
  }

  if (sourceLayer === "data") {
    return "structured";
  }

  return "unknown";
}

function hashContent(content) {
  return createHash("sha256").update(content).digest("hex");
}

async function buildRegistry() {
  const records = [];
  const generatedAt = new Date().toISOString();

  for (const sourceRoot of SOURCE_ROOTS) {
    const directory = path.join(repoRoot, sourceRoot.directory);
    const paths = await walkMarkdownFiles(directory);

    for (const sourcePath of paths) {
      const relativePath = path.relative(repoRoot, sourcePath);

      if (relativePath === "1-raw/README.md" || relativePath === "1-raw/INDEX.md") {
        continue;
      }

      const content = await readFile(sourcePath, "utf8");
      const metadata = parseFrontmatter(content);
      const contentHash = hashContent(content);
      const noteId = metadata.note_id || null;

      const canonicalSourceId = noteId ? `note:${noteId}` : null;
      const sourceId = noteId
        ? `${sourceRoot.sourceLayer}:${noteId}`
        : `file:${contentHash}`;

      records.push({
        schemaVersion: "1.0",
        sourceId,
        canonicalSourceId,
        noteId,
        sourceLayer: sourceRoot.sourceLayer,
        relativePath,
        title: metadata.title || path.basename(sourcePath, ".md"),
        author: metadata.author || null,
        source: metadata.source || null,
        eventYear: inferEventYear(relativePath, metadata.title),
        publishedAt: metadata.published_at || metadata.date || null,
        capturedAt: metadata.captured_at || null,
        contentSource: metadata.content_source || null,
        fidelity: inferFidelity(metadata, sourceRoot.sourceLayer),
        contentHash,
        reviewStatus: "registered",
        duplicateOf: null,
        registeredAt: generatedAt,
      });
    }
  }

  records.sort((a, b) => a.relativePath.localeCompare(b.relativePath));

  const sourceIds = new Set();
  const noteIds = new Set();
  const canonicalSourceIds = new Map();
  const duplicateSourceIds = [];

  for (const record of records) {
    if (sourceIds.has(record.sourceId)) {
      duplicateSourceIds.push(record.sourceId);
    }

    sourceIds.add(record.sourceId);

    if (record.noteId) {
      noteIds.add(record.noteId);
      canonicalSourceIds.set(
        record.canonicalSourceId,
        (canonicalSourceIds.get(record.canonicalSourceId) || 0) + 1,
      );
    }
  }

  if (duplicateSourceIds.length > 0) {
    throw new Error(`Duplicate sourceId values: ${duplicateSourceIds.join(", ")}`);
  }

  const byLayer = Object.fromEntries(SOURCE_ROOTS.map(({ sourceLayer }) => [sourceLayer, 0]));
  const byFidelity = {};
  const duplicateCanonicalSourceIds = [...canonicalSourceIds.entries()]
    .filter(([, count]) => count > 1)
    .map(([sourceId]) => sourceId);

  for (const record of records) {
    byLayer[record.sourceLayer] += 1;
    byFidelity[record.fidelity] = (byFidelity[record.fidelity] || 0) + 1;
  }

  await mkdir(path.dirname(registryPath), { recursive: true });
  await writeFile(registryPath, `${records.map((record) => JSON.stringify(record)).join("\n")}\n`);
  await writeFile(snapshotPath, `${JSON.stringify({
    schemaVersion: "1.0",
    generatedAt,
    registryPath: "3-processing/index/source-registry.jsonl",
    recordCount: records.length,
    uniqueSourceIds: sourceIds.size,
    uniqueNoteIds: noteIds.size,
    byLayer,
    byFidelity,
    duplicateSourceIds,
    duplicateCanonicalSourceIds,
    sourceRoots: SOURCE_ROOTS.map(({ directory }) => directory),
    note: "Generated from source frontmatter and content hashes. Semantic lineage and review status require later review.",
  }, null, 2)}\n`);

  console.log(JSON.stringify({
    recordCount: records.length,
    uniqueNoteIds: noteIds.size,
    duplicateCanonicalSourceIds: duplicateCanonicalSourceIds.length,
    byLayer,
    byFidelity,
  }, null, 2));
}

buildRegistry().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
