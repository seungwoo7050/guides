import { createHash } from "node:crypto";
import { lstat, readFile, readdir, realpath } from "node:fs/promises";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const modulePath = fileURLToPath(import.meta.url);
const exerciseRoot = path.resolve(path.dirname(modulePath), "..");
const skeleton = path.join(exerciseRoot, "skeleton");
const work = path.join(exerciseRoot, "work");
const stageText = process.argv[2];
const stage = Number(stageText);

if (!Number.isInteger(stage) || stage < 1 || stage > 6 || process.argv.length !== 3) {
  fail("사용법: node exercises/commerce-checkout/checks/verify-work.mjs <1..6>");
}

await assertDirectory(skeleton, "skeleton");
await assertDirectory(work, "work");
await assertContainedRealPath(exerciseRoot, work);
await rejectSymlinks(work, new Set(["node_modules", ".git", "coverage", "dist"]));
await assertBaselineTestsUnchanged();
await rejectReferenceAccess();

const packageText = await readFile(path.join(work, "package.json"), "utf8");
if (/(?:^|[\/])reference(?:[\/]|$)/.test(packageText) || packageText.includes("../reference")) {
  fail("work/package.json에서 reference를 실행하거나 읽을 수 없습니다.");
}
const packageJson = JSON.parse(packageText);
const skeletonPackageJson = JSON.parse(await readFile(path.join(skeleton, "package.json"), "utf8"));
const script = `verify:0${stage}`;
if (!packageJson.scripts || typeof packageJson.scripts[script] !== "string") {
  fail(`work/package.json에 ${script} script가 없습니다.`);
}
for (const protectedScript of ["typecheck", "test", "verify:01", "verify:02", "verify:03", "verify:04", "verify:05", "verify:06"]) {
  if (packageJson.scripts?.[protectedScript] !== skeletonPackageJson.scripts?.[protectedScript]) {
    fail(`검증 script를 수정하지 않습니다: ${protectedScript}`);
  }
}

await run("corepack", ["pnpm", "--dir", work, "run", script], exerciseRoot);
console.log(`COMMERCE CHECKOUT STAGE ${String(stage).padStart(2, "0")} PASS`);

async function assertBaselineTestsUnchanged() {
  const baselineRoot = path.join(skeleton, "tests");
  const workRoot = path.join(work, "tests");
  for (const relative of await listFiles(baselineRoot)) {
    const expected = await digest(path.join(baselineRoot, relative));
    let actual;
    try {
      actual = await digest(path.join(workRoot, relative));
    } catch {
      fail(`baseline test가 삭제되었습니다: tests/${relative}`);
    }
    if (expected !== actual) fail(`baseline test를 수정하지 않습니다: tests/${relative}`);
  }
}

async function rejectReferenceAccess() {
  const sourceRoots = ["src", "tests"].map((name) => path.join(work, name));
  const forbidden = [
    /(?:^|[\\/])reference(?:[\\/]|$)/,
    /commerce-checkout[\\/]reference/,
    /readFile[^\n]*reference/,
    /import\([^\n]*reference/
  ];
  for (const sourceRoot of sourceRoots) {
    for (const relative of await listFiles(sourceRoot)) {
      const target = path.join(sourceRoot, relative);
      const content = await readFile(target, "utf8");
      if (forbidden.some((pattern) => pattern.test(content))) {
        fail(`reference 접근을 허용하지 않습니다: ${path.relative(work, target)}`);
      }
    }
  }
}

async function listFiles(directory, prefix = "") {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const relative = path.join(prefix, entry.name);
    const target = path.join(directory, entry.name);
    if (entry.isSymbolicLink()) fail(`symbolic link를 허용하지 않습니다: ${target}`);
    if (entry.isDirectory()) files.push(...await listFiles(target, relative));
    else if (entry.isFile()) files.push(relative);
  }
  return files.sort();
}

async function digest(file) {
  return createHash("sha256").update(await readFile(file)).digest("hex");
}

async function assertDirectory(target, label) {
  const stat = await lstat(target);
  if (stat.isSymbolicLink() || !stat.isDirectory()) fail(`${label}이 실제 디렉터리가 아닙니다: ${target}`);
}

async function assertContainedRealPath(root, target) {
  const [rootReal, targetReal] = await Promise.all([realpath(root), realpath(target)]);
  const relative = path.relative(rootReal, targetReal);
  if (relative === "" || (!relative.startsWith(`..${path.sep}`) && relative !== ".." && !path.isAbsolute(relative))) return;
  fail(`exercise 밖 경로를 사용할 수 없습니다: ${target}`);
}

async function rejectSymlinks(directory, skippedNames = new Set()) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (skippedNames.has(entry.name)) continue;
    const target = path.join(directory, entry.name);
    if (entry.isSymbolicLink()) fail(`symbolic link를 허용하지 않습니다: ${target}`);
    if (entry.isDirectory()) await rejectSymlinks(target, skippedNames);
  }
}

async function run(command, args, cwd) {
  await new Promise((resolve, reject) => {
    const child = spawn(command, args, { cwd, env: process.env, stdio: "inherit" });
    child.once("error", reject);
    child.once("exit", (code, signal) => {
      if (signal) reject(new Error(`${command}가 signal ${signal}로 종료되었습니다.`));
      else if (code !== 0) reject(new Error(`${command}가 exit ${code}로 종료되었습니다.`));
      else resolve();
    });
  }).catch((error) => fail(error instanceof Error ? error.message : String(error)));
}

function fail(message) {
  console.error(message);
  process.exit(2);
}
