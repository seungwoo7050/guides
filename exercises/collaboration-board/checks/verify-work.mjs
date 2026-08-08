import { access, readFile, readdir } from "node:fs/promises";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const exerciseRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const [workArgument = "work", stageArgument, ...flags] = process.argv.slice(2);
const stage = Number(stageArgument);
const structureOnly = flags.includes("--structure-only");

if (!Number.isInteger(stage) || stage < 1 || stage > 8) {
  fail("사용법: node checks/verify-work.mjs <work-directory> <1-8> [--structure-only]");
}

const workRoot = path.resolve(exerciseRoot, workArgument);
const relativeWork = path.relative(exerciseRoot, workRoot);
if (!relativeWork || relativeWork.startsWith("..") || path.isAbsolute(relativeWork)) {
  fail("work directory는 exercises/collaboration-board 아래에 있어야 합니다.");
}
if (["skeleton", "patches", "specs", "checks"].includes(relativeWork.split(path.sep)[0])) {
  fail("skeleton·명세·검사기를 직접 수정하지 말고 별도 work directory를 사용합니다.");
}

const errors = [];
const stageScript = `verify:${String(stage).padStart(2, "0")}`;
const requiredByStage = new Map([
  [1, [
    ".env.example", "package.json", "pnpm-workspace.yaml", "tsconfig.base.json",
    "apps/web/package.json", "apps/web/app/layout.tsx", "apps/web/app/page.tsx",
    "apps/api/package.json", "apps/api/src/app.ts", "apps/api/src/index.ts",
    "packages/contracts/package.json", "packages/contracts/src/index.ts",
    "packages/db/package.json", "packages/db/src/index.ts"
  ]],
  [2, [
    "apps/web/app/login/page.tsx", "apps/web/app/boards/page.tsx",
    "apps/web/app/boards/[id]/page.tsx", "apps/web/app/admin/page.tsx",
    "apps/web/tests/e2e"
  ]],
  [3, [
    "packages/contracts/src/board.ts", "packages/contracts/src/http.ts",
    "packages/contracts/src/ws.ts", "apps/web/lib/api.ts"
  ]],
  [4, [
    "apps/api/src/routes", "apps/api/src/services", "apps/api/src/repositories"
  ]],
  [5, [
    "compose.test.yml", "packages/db/migrations", "packages/db/src/postgres.ts"
  ]],
  [6, [
    "apps/api/src/security", "apps/api/tests/security"
  ]],
  [7, [
    "apps/api/src/realtime", "apps/api/tests/websocket", "apps/web/components/BoardCanvas.tsx"
  ]],
  [8, [
    "tests/e2e", "tests/smoke.mjs"
  ]]
]);

for (let current = 1; current <= stage; current += 1) {
  for (const relative of requiredByStage.get(current) ?? []) {
    if (!await exists(relative)) errors.push(`단계 ${current}: 필수 경로 누락: ${relative}`);
  }
}

let rootPackage;
try {
  rootPackage = JSON.parse(await readFile(path.join(workRoot, "package.json"), "utf8"));
} catch (error) {
  errors.push(`package.json을 읽을 수 없음: ${error instanceof Error ? error.message : String(error)}`);
}

if (rootPackage) {
  for (let current = 1; current <= stage; current += 1) {
    const name = `verify:${String(current).padStart(2, "0")}`;
    if (!rootPackage.scripts?.[name]) errors.push(`누적 단계 script 누락: ${name}`);
  }
  if (stage === 8 && !rootPackage.scripts?.verify) errors.push("최종 script 누락: verify");
}

const packageContracts = [
  ["apps/web/package.json", "@capstone/web", ["typecheck"]],
  ["apps/api/package.json", "@capstone/api", ["typecheck", "test"]],
  ["packages/contracts/package.json", "@capstone/contracts", ["typecheck"]],
  ["packages/db/package.json", "@capstone/db", ["typecheck"]]
];
for (const [relative, expectedName, scripts] of packageContracts) {
  if (!await exists(relative)) continue;
  try {
    const manifest = JSON.parse(await readFile(path.join(workRoot, relative), "utf8"));
    if (manifest.name !== expectedName) errors.push(`${relative}: package name은 ${expectedName}이어야 함`);
    for (const script of scripts) {
      if (!manifest.scripts?.[script]) errors.push(`${relative}: script 누락: ${script}`);
    }
  } catch (error) {
    errors.push(`${relative}: JSON 오류: ${error instanceof Error ? error.message : String(error)}`);
  }
}

const stagePackageScripts = [
  [2, "apps/web/package.json", ["build", "test:e2e"]],
  [3, "apps/web/package.json", ["test"], "packages/contracts/package.json", ["test"]],
  [4, "apps/api/package.json", ["test"]],
  [5, "packages/db/package.json", ["test:postgres"]],
  [6, "apps/api/package.json", ["test:security"]],
  [7, "apps/api/package.json", ["test:websocket"]],
  [8, "apps/web/package.json", ["build"]]
];
for (const contract of stagePackageScripts) {
  const [minimumStage, ...pairs] = contract;
  if (stage < minimumStage) continue;
  for (let index = 0; index < pairs.length; index += 2) {
    const relative = pairs[index];
    const scripts = pairs[index + 1];
    try {
      const manifest = JSON.parse(await readFile(path.join(workRoot, relative), "utf8"));
      for (const script of scripts) {
        if (!manifest.scripts?.[script]) errors.push(`단계 ${minimumStage}: ${relative} script 누락: ${script}`);
      }
    } catch {
      // Earlier required-path errors already identify a missing or invalid manifest.
    }
  }
}

const unfinished = await findUnfinishedMarkers(workRoot);
for (const entry of unfinished) errors.push(`미완성 표식이 남아 있음: ${entry}`);

if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}

console.log(`단계 ${stage}의 구조와 검증 진입점을 확인했습니다: ${relativeWork}`);
if (structureOnly) process.exit(0);

await run("pnpm", ["run", stageScript], workRoot);
console.log(`단계 ${stage} 누적 검증을 통과했습니다: ${stageScript}`);

async function exists(relative) {
  try {
    await access(path.join(workRoot, relative));
    return true;
  } catch {
    return false;
  }
}

async function findUnfinishedMarkers(directory) {
  const matches = [];
  const ignored = new Set([".git", ".next", "node_modules", "coverage", "test-results", "playwright-report"]);
  async function walk(current) {
    for (const entry of await readdir(current, { withFileTypes: true })) {
      if (ignored.has(entry.name)) continue;
      const target = path.join(current, entry.name);
      if (entry.isDirectory()) {
        await walk(target);
        continue;
      }
      if (!entry.isFile() || !/\.(?:[cm]?[jt]sx?)$/.test(entry.name)) continue;
      const text = await readFile(target, "utf8");
      if (/TODO_STAGE|FIXME_STAGE|not implemented/i.test(text)) {
        matches.push(path.relative(workRoot, target));
      }
    }
  }
  await walk(directory);
  return matches;
}

function run(command, args, cwd) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { cwd, stdio: "inherit", shell: false });
    child.once("error", reject);
    child.once("exit", (code, signal) => {
      if (code === 0) resolve();
      else reject(new Error(`${command} ${args.join(" ")} 실패: ${signal ?? code}`));
    });
  });
}

function fail(message) {
  console.error(message);
  process.exit(2);
}
