import { createHash } from "node:crypto";
import { spawnSync } from "node:child_process";
import { cp, lstat, mkdtemp, readdir, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const mode = process.argv[2] ?? "--check";
if (!new Set(["--check", "--write"]).has(mode) || process.argv.length !== 3) {
  console.error("사용법: node scripts/generate-patches.mjs --check|--write");
  process.exit(2);
}

const author = "Seungwoo Kim <seungwoo7050@naver.com>";
const exerciseMetadata = [
  ["01-runtime", "Tue, 26 Aug 2025 19:12:00 +0900", "[PATCH] feat(runtime): 실행 환경과 작업 공간 구성"],
  ["02-browser", "Thu, 4 Sep 2025 20:08:00 +0900", "[PATCH] feat(browser): 접근 가능한 브라우저 화면 구현"],
  ["03-react-nextjs", "Sun, 7 Sep 2025 16:22:00 +0900", "[PATCH] feat(frontend): React와 Next.js 화면 구현"],
  ["04-fastify-zod-api", "Mon, 22 Sep 2025 20:37:00 +0900", "[PATCH] feat(api): Fastify API 계약 구현"],
  ["05-postgresql-kysely", "Tue, 30 Sep 2025 21:16:00 +0900", "[PATCH] feat(data): PostgreSQL 트랜잭션 구현"],
  ["06-security", "Tue, 7 Oct 2025 20:49:00 +0900", "[PATCH] fix(security): 세션과 권한 경계 보완"],
  ["07-websocket", "Wed, 15 Oct 2025 21:31:00 +0900", "[PATCH] feat(realtime): WebSocket 상태 동기화 구현"],
  ["08-testing", "Thu, 23 Oct 2025 20:26:00 +0900", "[PATCH] test(web): 기능별 검사 경계 구성"]
];
const collaborationPrefix = [
  "01-runtime.patch",
  "02-browser.patch",
  "03-contracts.patch",
  "03-react-nextjs.patch",
  "04-fastify-zod-api.patch",
  "05-postgresql-kysely.patch",
  "05b-postgresql-exports.patch",
  "06-security.patch",
  "07-websocket.patch"
];
const collaborationFinal = {
  date: "Sun, 9 Nov 2025 12:45:00 +0900",
  subject: "[PATCH] test(board): 통합 검사와 브라우저 흐름 추가",
  name: "08-testing.patch"
};

const rendered = [];
for (const [name, date, subject] of exerciseMetadata) {
  rendered.push({
    file: path.join(root, "exercises", name, "reference.patch"),
    source: await renderExercisePatch(name, date, subject)
  });
}
rendered.push({
  file: path.join(root, "exercises", "collaboration-board", "patches", collaborationFinal.name),
  source: await renderCollaborationFinalPatch()
});

const stale = [];
for (const artifact of rendered) {
  const current = await readFile(artifact.file, "utf8").catch(() => null);
  if (current === artifact.source) continue;
  if (mode === "--write") await writeFile(artifact.file, artifact.source);
  else stale.push(path.relative(root, artifact.file));
}

if (stale.length) {
  console.error(`파생 patch가 source와 다릅니다:\n${stale.map((file) => `- ${file}`).join("\n")}`);
  console.error("의도한 source 변경이라면 node scripts/generate-patches.mjs --write를 실행하십시오.");
  process.exit(1);
}

console.log(mode === "--write"
  ? `독립 reference patch 8개와 최종 collaboration delta를 갱신했습니다.`
  : `독립 reference patch 8개와 최종 collaboration delta가 최신입니다.`);

async function renderExercisePatch(name, date, subject) {
  const directory = path.join(root, "exercises", name);
  await assertNoUnexpectedSymlinks(path.join(directory, "skeleton"));
  await assertNoUnexpectedSymlinks(path.join(directory, "reference"));
  const temporary = await mkdtemp(path.join(tmpdir(), `${name}-patch-`));
  try {
    const oldTree = path.join(temporary, "old");
    const newTree = path.join(temporary, "new");
    await cp(path.join(directory, "skeleton"), oldTree, { recursive: true, filter: includeSource });
    await cp(path.join(directory, "reference"), newTree, { recursive: true, filter: includeSource });
    return message(date, subject, diffTrees(oldTree, newTree));
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
}

async function renderCollaborationFinalPatch() {
  const exercise = path.join(root, "exercises", "collaboration-board");
  const reference = path.join(exercise, "reference");
  const patchDirectory = path.join(exercise, "patches");
  await assertNoUnexpectedSymlinks(path.join(exercise, "walkthrough-base"));
  await assertNoUnexpectedSymlinks(reference);
  const temporary = await mkdtemp(path.join(tmpdir(), "collaboration-final-patch-"));
  try {
    const applied = path.join(temporary, "applied");
    const expected = path.join(temporary, "expected");
    await cp(path.join(exercise, "walkthrough-base"), applied, { recursive: true, filter: includeSource });
    for (const name of collaborationPrefix) {
      run("git", ["apply", path.join(patchDirectory, name)], applied);
    }
    await cp(reference, expected, { recursive: true, filter: includeSource });
    return message(collaborationFinal.date, collaborationFinal.subject, diffTrees(applied, expected));
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
}

function includeSource(source) {
  const parts = source.split(path.sep);
  if (parts.some((part) => [".git", "node_modules", ".next", "coverage", "playwright-report", "test-results"].includes(part))) {
    return false;
  }
  return !source.endsWith(".tsbuildinfo") && path.basename(source) !== "next-env.d.ts";
}

function diffTrees(oldDirectory, newDirectory) {
  const parent = path.dirname(oldDirectory);
  const oldName = path.basename(oldDirectory);
  const newName = path.basename(newDirectory);
  const result = spawnSync(
    "git",
    ["diff", "--no-index", "--binary", "--", oldName, newName],
    { cwd: parent, encoding: "utf8", maxBuffer: 64 * 1024 * 1024 }
  );
  if (![0, 1].includes(result.status ?? -1)) {
    throw new Error(`git diff 실패\n${result.stdout}\n${result.stderr}`);
  }
  return result.stdout
    .replaceAll(`a/${oldName}/`, "a/")
    .replaceAll(`a/${newName}/`, "a/")
    .replaceAll(`b/${oldName}/`, "b/")
    .replaceAll(`b/${newName}/`, "b/")
    .replace(/^ $/gm, "");
}

function message(date, subject, diff) {
  const id = createHash("sha1").update(`${date}\0${subject}\0${diff}`).digest("hex");
  return `From ${id} Mon Sep 17 00:00:00 2001\nFrom: ${author}\nDate: ${date}\nSubject: ${subject}\n\n${diff}--\n2.47.3\n`;
}

function run(command, args, cwd) {
  const result = spawnSync(command, args, { cwd, encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
  if (result.status !== 0) {
    throw new Error(`${command} ${args.join(" ")} 실패\n${result.stdout}\n${result.stderr}`);
  }
}

async function assertNoUnexpectedSymlinks(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (["node_modules", ".next", "coverage", "playwright-report", "test-results"].includes(entry.name)) continue;
    const target = path.join(directory, entry.name);
    if (entry.isSymbolicLink() || (await lstat(target)).isSymbolicLink()) {
      throw new Error(`patch source의 symbolic link를 허용하지 않습니다: ${path.relative(root, target)}`);
    }
    if (entry.isDirectory()) await assertNoUnexpectedSymlinks(target);
  }
}
