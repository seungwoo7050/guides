import { createHash } from "node:crypto";
import { lstat, readFile, readdir, writeFile } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repositoryRoot = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const output = process.argv[2];
if (!output) {
  console.error("사용법: node scripts/snapshot-repository.mjs <output-file>");
  process.exit(2);
}

const listing = spawnSync(
  "git",
  ["ls-files", "-z", "--cached", "--others", "--exclude-standard"],
  { cwd: repositoryRoot, encoding: "buffer" }
);
if (listing.error) throw listing.error;
if (listing.status !== 0) {
  throw new Error(`git ls-files 실패: ${listing.stderr?.toString("utf8") ?? ""}`);
}

const pathSet = new Set(
  listing.stdout
    .toString("utf8")
    .split("\0")
    .filter(Boolean)
);

const workspaceRoot = path.join(repositoryRoot, "exercises", "project-catalog", "workspace");
await collectWorkspaceSources(workspaceRoot, pathSet);

const paths = [...pathSet].sort((left, right) => left.localeCompare(right, "en"));
const records = [];
for (const relative of paths) {
  const target = path.join(repositoryRoot, relative);
  try {
    const info = await lstat(target);
    if (info.isDirectory()) continue;
    if (!info.isFile() && !info.isSymbolicLink()) {
      records.push({ path: relative, type: "other", mode: info.mode & 0o7777 });
      continue;
    }
    const content = await readFile(target);
    records.push({
      path: relative,
      type: info.isSymbolicLink() ? "symlink" : "file",
      mode: info.mode & 0o7777,
      sha256: createHash("sha256").update(content).digest("hex")
    });
  } catch (error) {
    if (error?.code !== "ENOENT") throw error;
    records.push({ path: relative, type: "missing" });
  }
}

await writeFile(output, `${records.map((record) => JSON.stringify(record)).join("\n")}\n`);

async function collectWorkspaceSources(directory, target) {
  let entries;
  try {
    entries = await readdir(directory, { withFileTypes: true });
  } catch (error) {
    if (error?.code === "ENOENT") return;
    throw error;
  }

  for (const entry of entries) {
    if (entry.name === "node_modules") continue;
    if ([".next", ".turbo", ".cache", "coverage", "dist", "out", "playwright-report", "test-results"].includes(entry.name)) {
      continue;
    }
    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) await collectWorkspaceSources(absolute, target);
    else target.add(path.relative(repositoryRoot, absolute));
  }
}
