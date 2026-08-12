import { access, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const specs = [
  "01-runtime-workspace.md",
  "02-browser-foundation.md",
  "03-contracts-frontend.md",
  "04-http-api.md",
  "05-postgresql.md",
  "06-security.md",
  "07-realtime.md",
  "08-quality.md"
];
const errors = [];
for (const name of specs) {
  const file = path.join(root, "specs", name);
  try { await access(file); } catch { errors.push(`단계 명세 누락: ${name}`); continue; }
  const text = await readFile(file, "utf8");
  for (const heading of ["## 목표", "## 구현할 변경", "## 실패 조건", "## 검증", "## 완료 계약"]) {
    if (!text.includes(heading)) errors.push(`${name}: ${heading} 누락`);
  }
  const stage = String(specs.indexOf(name) + 1).padStart(2, "0");
  if (
    !text.includes(`verify:${stage}`) ||
    !text.includes(`verify-work.mjs exercises/collaboration-board/work ${Number(stage)}`)
  ) {
    errors.push(`${name}: 누적 단계 검증 명령 누락`);
  }
}
for (const pathName of [
  "skeleton/package.json",
  "skeleton/pnpm-workspace.yaml",
  "skeleton/apps/web/app/page.tsx",
  "skeleton/apps/api/src/app.test.ts",
  "skeleton/packages/contracts/src/index.ts",
  "skeleton/packages/db/src/index.ts",
  "checks/verify-work.mjs",
  "walkthrough-base/README.md",
  "walkthrough-base/.gitignore",
  "patches",
  "reference"
]) {
  try { await access(path.resolve(root, pathName)); }
  catch { errors.push(`협업 보드 자료 누락: ${pathName}`); }
}
if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}
console.log(`${specs.length}개 협업 보드 단계 명세를 확인했습니다.`);
