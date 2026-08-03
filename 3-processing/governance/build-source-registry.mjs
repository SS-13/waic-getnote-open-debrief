import { createHash } from "node:crypto";
import { mkdir, readdir, readFile, rename, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const DEFAULT_REPO_ROOT = path.resolve(scriptDir, "../..");

const SOURCE_ROOTS = [
  { directory: "1-raw", sourceLayer: "raw" },
  { directory: "2-data", sourceLayer: "data" },
];

const NON_EVIDENCE_FILENAMES = new Set(["README.md", "INDEX.md"]);

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
  if (["verbatim", "structured", "summary", "pointer", "unknown"].includes(metadata.fidelity)) {
    return metadata.fidelity;
  }

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

async function readOptionalFile(targetPath) {
  try {
    return await readFile(targetPath, "utf8");
  } catch (error) {
    if (error.code === "ENOENT") {
      return null;
    }
    throw error;
  }
}

function parseJsonl(content) {
  return (content || "").trim().split("\n").filter(Boolean).map((line) => JSON.parse(line));
}

async function atomicWrite(targetPath, content) {
  const tempPath = `${targetPath}.tmp-${process.pid}`;
  await writeFile(tempPath, content);
  await rename(tempPath, targetPath);
}

function snapshotCore(snapshot) {
  if (!snapshot) {
    return null;
  }

  const { generatedAt: _generatedAt, ...core } = snapshot;
  return core;
}

export async function buildRegistry({
  repoRoot = DEFAULT_REPO_ROOT,
  generatedAt = process.env.WORKBENCH_NOW || new Date().toISOString(),
} = {}) {
  const resolvedRepoRoot = path.resolve(repoRoot);
  const registryPath = path.join(resolvedRepoRoot, "3-processing/index/source-registry.jsonl");
  const snapshotPath = path.join(resolvedRepoRoot, "3-processing/index/source-registry.snapshot.json");
  const records = [];
  const previousRegistryContent = await readOptionalFile(registryPath);
  const existingRecords = parseJsonl(previousRegistryContent);
  const existingByPath = new Map(existingRecords.map((record) => [record.relativePath, record]));

  for (const sourceRoot of SOURCE_ROOTS) {
    const directory = path.join(resolvedRepoRoot, sourceRoot.directory);
    const paths = await walkMarkdownFiles(directory);

    for (const sourcePath of paths) {
      const relativePath = path.relative(resolvedRepoRoot, sourcePath).split(path.sep).join("/");

      if (NON_EVIDENCE_FILENAMES.has(path.basename(sourcePath))) {
        continue;
      }

      const content = await readFile(sourcePath, "utf8");
      const metadata = parseFrontmatter(content);
      const contentHash = hashContent(content);
      const noteId = metadata.note_id || null;

      const canonicalSourceId = metadata.canonical_source_id || (noteId ? `note:${noteId}` : null);
      const sourceId = metadata.registry_source_id || (
        noteId ? `${sourceRoot.sourceLayer}:${noteId}` : `file:${contentHash}`
      );
      const existingRecord = existingByPath.get(relativePath);

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
        reviewStatus: existingRecord?.reviewStatus || "registered",
        duplicateOf: existingRecord?.duplicateOf || null,
        registeredAt: existingRecord?.registeredAt
          || metadata.ingested_at
          || metadata.captured_at
          || metadata.published_at
          || metadata.date
          || "unknown",
      });
    }
  }

  records.sort((a, b) => compareCodePoints(a.relativePath, b.relativePath));

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
    }

    if (record.canonicalSourceId) {
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
    .map(([sourceId]) => sourceId)
    .sort(compareCodePoints);

  for (const record of records) {
    byLayer[record.sourceLayer] += 1;
    byFidelity[record.fidelity] = (byFidelity[record.fidelity] || 0) + 1;
  }

  const registryContent = `${records.map((record) => JSON.stringify(record)).join("\n")}\n`;
  const registryHash = hashContent(registryContent);
  const expectedSnapshotCore = {
    schemaVersion: "1.1",
    registryPath: "3-processing/index/source-registry.jsonl",
    registryHash,
    recordCount: records.length,
    uniqueSourceIds: sourceIds.size,
    uniqueNoteIds: noteIds.size,
    byLayer,
    byFidelity,
    duplicateSourceIds,
    duplicateCanonicalSourceIds,
    sourceRoots: SOURCE_ROOTS.map(({ directory }) => directory),
    note: "Generated deterministically from source frontmatter and content hashes. Semantic lineage lives in separate governance ledgers.",
  };
  const previousSnapshotContent = await readOptionalFile(snapshotPath);
  const previousSnapshot = previousSnapshotContent ? JSON.parse(previousSnapshotContent) : null;
  const registryChanged = registryContent !== (previousRegistryContent || "");
  const snapshotChanged = JSON.stringify(snapshotCore(previousSnapshot)) !== JSON.stringify(expectedSnapshotCore);

  if (!registryChanged && !snapshotChanged) {
    return {
      changed: false,
      registryChanged: false,
      snapshotChanged: false,
      registryHash,
      recordCount: records.length,
      uniqueNoteIds: noteIds.size,
      duplicateCanonicalSourceIds: duplicateCanonicalSourceIds.length,
      byLayer,
      byFidelity,
    };
  }

  await mkdir(path.dirname(registryPath), { recursive: true });
  if (registryChanged) {
    await atomicWrite(registryPath, registryContent);
  }
  await atomicWrite(snapshotPath, `${JSON.stringify({
    generatedAt,
    ...expectedSnapshotCore,
  }, null, 2)}\n`);

  return {
    changed: true,
    registryChanged,
    snapshotChanged,
    registryHash,
    recordCount: records.length,
    uniqueNoteIds: noteIds.size,
    duplicateCanonicalSourceIds: duplicateCanonicalSourceIds.length,
    byLayer,
    byFidelity,
  };
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
  const result = await buildRegistry(parseArgs(process.argv.slice(2)));
  console.log(JSON.stringify(result, null, 2));
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
}
