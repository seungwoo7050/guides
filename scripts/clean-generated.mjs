import { readdir, rm } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const generatedDirectories = new Set([
  ".next",
  ".pnpm-store",
  ".turbo",
  "coverage",
  "node_modules",
  "playwright-report",
  "test-results"
]);

let removed = 0;
await clean(root);
console.log(`웹 생성물 ${removed}개를 정리했습니다.`);

async function clean(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (entry.name === ".git") continue;
    const target = path.join(directory, entry.name);
    if (entry.isDirectory() && generatedDirectories.has(entry.name)) {
      await rm(target, { recursive: true, force: true });
      removed += 1;
      continue;
    }
    if (entry.isDirectory()) {
      await clean(target);
      continue;
    }
    if (entry.isFile() && (entry.name.endsWith(".tsbuildinfo") || entry.name === "next-env.d.ts")) {
      await rm(target, { force: true });
      removed += 1;
    }
  }
}
