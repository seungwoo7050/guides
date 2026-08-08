import { readdir, rm } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repositoryRoot = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const exerciseRoot = path.join(repositoryRoot, "exercises", "project-catalog");
const projects = [
  path.join(exerciseRoot, "reference"),
  path.join(exerciseRoot, "workspace")
];

await rm(path.join(repositoryRoot, "node_modules"), { recursive: true, force: true });
for (const project of projects) {
  for (const relative of [
    "node_modules",
    ".next",
    "coverage",
    "playwright-report",
    "test-results",
    "tsconfig.tsbuildinfo"
  ]) {
    await rm(path.join(project, relative), { recursive: true, force: true });
  }
}

for (const entry of await readdir(exerciseRoot, { withFileTypes: true })) {
  if (entry.isDirectory() && entry.name.startsWith(".workspace-")) {
    await rm(path.join(exerciseRoot, entry.name), { recursive: true, force: true });
  }
}
