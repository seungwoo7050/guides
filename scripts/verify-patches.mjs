import { createHash } from "node:crypto";
import { spawnSync } from "node:child_process";
import { cp, lstat, mkdtemp, readFile, readdir, rm, stat } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const expectedAuthor = "Seungwoo Kim <seungwoo7050@naver.com>";
const exercisePatchOrder = [];
const collaborationPatchOrder = [];
const collaborationCheckpoints = new Map([
  ["01-runtime.patch", "01 실행 환경"],
  ["02-browser.patch", "02 브라우저 화면"],
  ["03-react-nextjs.patch", "03 React·Next.js"],
  ["04-fastify-zod-api.patch", "04 Fastify·Zod API"],
  ["05b-postgresql-exports.patch", "05 PostgreSQL·Kysely"],
  ["06-security.patch", "06 인증·권한"],
  ["07-websocket.patch", "07 WebSocket"],
  ["08-testing.patch", "08 테스트"]
]);

await verifyExercises();
await verifyCollaborationBoard();
await verifyMetadata(exercisePatchOrder, "독립 실습");
await verifyMetadata(collaborationPatchOrder, "협업 보드");

async function verifyExercises() {
  const exercisesRoot = path.join(root, "exercises");
  const exercises = (await readdir(exercisesRoot, { withFileTypes: true }))
    .filter((entry) => entry.isDirectory() && /^0[1-8]-/.test(entry.name))
    .map((entry) => entry.name)
    .sort();

  if (exercises.length !== 8) {
    throw new Error(`독립 실습 8개가 필요하지만 ${exercises.length}개를 찾았습니다.`);
  }

  for (const exercise of exercises) {
    const directory = path.join(exercisesRoot, exercise);
    const patch = path.join(directory, "reference.patch");
    exercisePatchOrder.push(patch);
    const temporary = await mkdtemp(path.join(tmpdir(), `${exercise}-`));
    try {
      await cp(path.join(directory, "skeleton"), temporary, { recursive: true });
      run("git", ["apply", patch], temporary);
      await assertSameTree(temporary, path.join(directory, "reference"), exercise);
    } finally {
      await rm(temporary, { recursive: true, force: true });
    }
  }
  console.log("독립 실습 patch 8개를 확인했습니다.");
}

async function verifyCollaborationBoard() {
  const exercise = path.join(root, "exercises", "collaboration-board");
  const temporary = await mkdtemp(path.join(tmpdir(), "board-walkthrough-"));
  try {
    // The learner starter evolves independently. Historical patches always apply to this immutable base.
    await cp(path.join(exercise, "walkthrough-base"), temporary, { recursive: true });
    const patchDirectory = path.join(exercise, "patches");
    const patches = (await readdir(patchDirectory))
      .filter((name) => name.endsWith(".patch"))
      .sort();

    if (patches.length !== 10) {
      throw new Error(`누적 patch 10개가 필요하지만 ${patches.length}개를 찾았습니다.`);
    }

    const observedCheckpoints = [];
    for (const name of patches) {
      const patch = path.join(patchDirectory, name);
      collaborationPatchOrder.push(patch);
      run("git", ["apply", patch], temporary);
      const checkpoint = collaborationCheckpoints.get(name);
      if (checkpoint !== undefined) {
        await verifyInternalImports(temporary, checkpoint);
        observedCheckpoints.push(name);
      }
    }

    const missing = [...collaborationCheckpoints.keys()].filter((name) => !observedCheckpoints.includes(name));
    if (missing.length) throw new Error(`누적 단계 검사 지점을 찾지 못했습니다: ${missing.join(", ")}`);
    await assertSameTree(temporary, path.join(root, "projects", "collaboration-board"), "협업 보드");
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
  console.log("역사적 누적 patch 10개와 단계별 내부 의존성을 확인했습니다.");
}

async function verifyInternalImports(projectRoot, checkpoint) {
  const packageMap = await workspacePackages(projectRoot);
  const unresolved = [];
  const extensions = new Set([".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"]);
  for (const file of await walk(projectRoot)) {
    if (!extensions.has(path.extname(file))) continue;
    const source = await readFile(file, "utf8");
    for (const specifier of importSpecifiers(source)) {
      if (!isInternalSpecifier(specifier, packageMap)) continue;
      if (!await resolveInternalSpecifier(file, specifier, projectRoot, packageMap)) {
        unresolved.push(`${path.relative(projectRoot, file)} -> ${specifier}`);
      }
    }
  }
  if (unresolved.length) {
    throw new Error(`${checkpoint} checkpoint에 아직 존재하지 않는 내부 모듈 참조가 있습니다.\n${unresolved.map((item) => `- ${item}`).join("\n")}`);
  }
  console.log(`${checkpoint}: 내부 모듈 참조를 확인했습니다.`);
}

function importSpecifiers(source) {
  const found = new Set();
  const staticPattern = /\b(?:import|export)\s+(?:type\s+)?(?:[^'";]*?\s+from\s+)?["']([^"']+)["']/g;
  const dynamicPattern = /\bimport\s*\(\s*["']([^"']+)["']\s*\)/g;
  for (const pattern of [staticPattern, dynamicPattern]) {
    for (const match of source.matchAll(pattern)) found.add(match[1]);
  }
  return [...found];
}

function isInternalSpecifier(specifier, packageMap) {
  if (specifier.startsWith(".") || specifier.startsWith("/")) return true;
  return [...packageMap.keys()].some((name) => specifier === name || specifier.startsWith(`${name}/`));
}

async function resolveInternalSpecifier(file, specifier, projectRoot, packageMap) {
  if (specifier.startsWith(".")) return resolveModule(path.resolve(path.dirname(file), specifier));
  if (specifier.startsWith("/")) return resolveModule(path.resolve(projectRoot, `.${specifier}`));

  const packageName = [...packageMap.keys()]
    .sort((left, right) => right.length - left.length)
    .find((candidate) => specifier === candidate || specifier.startsWith(`${candidate}/`));
  if (!packageName) return false;

  const packageInfo = packageMap.get(packageName);
  const subpath = specifier.slice(packageName.length).replace(/^\//, "");
  if (subpath) {
    const exported = exportedPath(packageInfo.manifest.exports, `./${subpath}`);
    return resolveModule(path.resolve(packageInfo.root, exported ?? subpath));
  }

  const exported = exportedPath(packageInfo.manifest.exports, ".");
  const candidates = [
    exported,
    packageInfo.manifest.types,
    packageInfo.manifest.module,
    packageInfo.manifest.main,
    "src/index.ts",
    "src/index.tsx",
    "index.ts",
    "index.js"
  ].filter((value) => typeof value === "string");
  for (const candidate of candidates) {
    if (await resolveModule(path.resolve(packageInfo.root, candidate))) return true;
  }
  return false;
}

function exportedPath(exportsField, key) {
  if (typeof exportsField === "string" && key === ".") return exportsField;
  if (!exportsField || typeof exportsField !== "object") return null;
  const value = exportsField[key];
  if (typeof value === "string") return value;
  if (!value || typeof value !== "object") return null;
  for (const condition of ["types", "import", "default", "require"]) {
    if (typeof value[condition] === "string") return value[condition];
  }
  return null;
}

async function resolveModule(candidate) {
  const extensions = ["", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".json", ".css"];
  for (const extension of extensions) if (await isFile(`${candidate}${extension}`)) return true;
  for (const extension of extensions.slice(1)) {
    if (await isFile(path.join(candidate, `index${extension}`))) return true;
  }
  return false;
}

async function workspacePackages(projectRoot) {
  const packages = new Map();
  for (const file of await walk(projectRoot)) {
    if (path.basename(file) !== "package.json") continue;
    const manifest = JSON.parse(await readFile(file, "utf8"));
    if (typeof manifest.name === "string") packages.set(manifest.name, { root: path.dirname(file), manifest });
  }
  return packages;
}

async function verifyMetadata(files, label) {
  const lowerBound = Date.parse("2025-08-25T18:12:00+09:00");
  const upperBound = Date.parse("2025-11-09T17:26:00+09:00");
  const subject = /^Subject: \[PATCH(?: \d+\/\d+)?\] (?:feat|fix|docs|refactor|perf|test|build|ci|chore)\([a-z0-9][a-z0-9-]*\): .*[가-힣].*$/m;
  let previous = lowerBound;
  for (const file of files) {
    const source = await readFile(file, "utf8");
    const from = source.match(/^From: (.+)$/m)?.[1];
    const rawDate = source.match(/^Date: (.+)$/m)?.[1];
    if (from !== expectedAuthor) throw new Error(`${path.relative(root, file)}의 작성자가 올바르지 않습니다.`);
    if (!subject.test(source)) throw new Error(`${path.relative(root, file)}의 제목이 한국어 Conventional Commits 형식이 아닙니다.`);
    const date = Date.parse(rawDate ?? "");
    if (!Number.isFinite(date)) throw new Error(`${path.relative(root, file)}의 날짜를 해석할 수 없습니다.`);
    if (date <= previous || date >= upperBound) {
      throw new Error(`${path.relative(root, file)}의 날짜가 지정 범위에서 단조 증가하지 않습니다.`);
    }
    previous = date;
  }
  console.log(`${label} patch ${files.length}개의 작성자·제목·날짜 순서를 확인했습니다.`);
}

async function assertSameTree(actualDirectory, expectedDirectory, label) {
  const actual = await treeHash(actualDirectory);
  const expected = await treeHash(expectedDirectory);
  if (actual !== expected) {
    throw new Error(`${label}의 patch 적용 결과가 reference와 다릅니다.\nactual ${actual}\nexpected ${expected}`);
  }
}

function run(command, args, cwd) {
  const result = spawnSync(command, args, { cwd, encoding: "utf8" });
  if (result.status !== 0) throw new Error(`${command} ${args.join(" ")} 실패\n${result.stdout}\n${result.stderr}`);
}

async function treeHash(directory) {
  const hash = createHash("sha256");
  for (const file of await walk(directory)) {
    hash.update(path.relative(directory, file) + "\0");
    hash.update(await readFile(file));
  }
  return hash.digest("hex");
}

async function walk(directory) {
  const output = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if ([".git", "node_modules", ".next", "coverage", "playwright-report", "test-results"].includes(entry.name)) continue;
    if (entry.isFile() && (entry.name.endsWith(".tsbuildinfo") || entry.name === "next-env.d.ts")) continue;
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) output.push(...await walk(full));
    else if (entry.isSymbolicLink()) {
      if ((await lstat(full)).isSymbolicLink()) continue;
    } else if ((await stat(full)).isFile()) output.push(full);
  }
  return output.sort();
}

async function isFile(file) {
  try { return (await stat(file)).isFile(); }
  catch { return false; }
}
