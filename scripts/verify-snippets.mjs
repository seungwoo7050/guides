import { spawn } from "node:child_process";
import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { isLearnerWorkspace } from "./lib/exercise-paths.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const files = await collect(root);
const errors = [];
for (const file of files) {
  const relative = path.relative(root, file);
  const text = await readFile(file, "utf8");
  if (file.endsWith(".md")) {
    const fences = [...text.matchAll(/^```/gm)].length;
    if (fences % 2 !== 0) errors.push(`${relative}: 닫히지 않은 코드 블록`);
  }
  if (file.endsWith(".json")) {
    try { JSON.parse(text); } catch (error) { errors.push(`${relative}: 잘못된 JSON: ${error.message}`); }
  }
  if (/\.(mjs|js)$/.test(file)) {
    const result = await checkNodeSyntax(file);
    if (result) errors.push(`${relative}: ${result}`);
  }
}
if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}
console.log(`${files.length}개 텍스트 파일의 기본 문법을 확인했습니다.`);

function checkNodeSyntax(file) {
  return new Promise((resolve) => {
    const child = spawn(process.execPath, ["--check", file], { stdio: ["ignore", "ignore", "pipe"] });
    let stderr = "";
    child.stderr.on("data", (chunk) => { stderr += chunk.toString(); });
    child.once("exit", (code) => resolve(code === 0 ? "" : stderr.trim()));
  });
}
async function collect(directory) {
  const out = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (["node_modules", ".git", ".next", ".guide-tmp", "coverage", "dist", "target"].includes(entry.name)) continue;
    const full = path.join(directory, entry.name);
    if (entry.isDirectory() && isLearnerWorkspace(root, full)) continue;
    if (entry.isDirectory()) out.push(...await collect(full));
    else if (/\.(md|json|mjs|js|ts|tsx|yaml|yml|css|html|sql|patch)$/.test(entry.name)) out.push(full);
  }
  return out;
}
