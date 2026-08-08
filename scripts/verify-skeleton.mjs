import { cp, lstat, mkdtemp, readFile, rm, symlink, writeFile } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repositoryRoot = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const exerciseRoot = path.join(repositoryRoot, "exercises", "project-catalog");
const reference = path.join(exerciseRoot, "reference");
const skeleton = path.join(exerciseRoot, "skeleton");
const markerChecker = path.join(exerciseRoot, "check-stage-markers.mjs");
const temporary = await mkdtemp(path.join(tmpdir(), "project-catalog-skeleton-"));

try {
  await cp(reference, temporary, {
    recursive: true,
    filter: (source) => !isGenerated(reference, source)
  });
  for (const relative of ["app", "lib", "tests"]) {
    await cp(path.join(skeleton, relative), path.join(temporary, relative), {
      recursive: true,
      force: true
    });
  }

  const referenceModules = path.join(reference, "node_modules");
  if (!(await exists(referenceModules))) {
    throw new Error("reference 의존성이 없습니다. pnpm install --frozen-lockfile을 먼저 실행하세요.");
  }
  await symlink(
    referenceModules,
    path.join(temporary, "node_modules"),
    process.platform === "win32" ? "junction" : "dir"
  );

  const source = await readSources([path.join(temporary, "app"), path.join(temporary, "lib")]);
  for (const stage of ["01", "02", "03", "04", "05"]) {
    if (!source.includes(`TODO(stage-${stage})`)) {
      throw new Error(`skeleton에서 Stage ${stage} 구현 표시를 찾지 못했습니다.`);
    }
  }

  runRequired("pnpm", ["--dir", temporary, "typecheck"], "skeleton 형 검사");
  runExpectedFailure(
    process.execPath,
    [markerChecker, temporary, "01"],
    "Stage 01 표시 검사가 미완성 skeleton을 거절해야 합니다."
  );

  const pagePath = path.join(temporary, "app", "page.tsx");
  const page = await readFile(pagePath, "utf8");
  await writeFile(pagePath, page.replaceAll("TODO(stage-01)", "DONE(stage-01)"));
  runRequired(
    process.execPath,
    [markerChecker, temporary, "01"],
    "Stage 01 표시 제거 검사"
  );
  runExpectedFailure(
    "pnpm",
    ["--dir", temporary, "test:stage:01"],
    "Stage 01 표시만 지운 구현은 행동 검사에 실패해야 합니다."
  );

  console.log("skeleton의 형 안정성, 단계 표시와 행동 미완성 상태를 확인했습니다.");
} finally {
  await rm(temporary, { recursive: true, force: true });
}

function runRequired(command, args, label) {
  const result = spawnSync(command, args, { encoding: "utf8" });
  if (result.error) throw new Error(`${label} 실행 실패: ${result.error.message}`);
  if (result.status !== 0) {
    throw new Error(`${label} 실패\n${result.stdout ?? ""}\n${result.stderr ?? ""}`);
  }
}

function runExpectedFailure(command, args, label) {
  const result = spawnSync(command, args, { encoding: "utf8" });
  if (result.error) throw new Error(`${label} 실행 실패: ${result.error.message}`);
  if (result.status === 0) throw new Error(label);
}

function isGenerated(projectRoot, source) {
  const relative = path.relative(projectRoot, source);
  if (!relative || relative.startsWith("..")) return false;
  return (
    relative.split(path.sep).some((part) =>
      ["node_modules", ".next", "coverage", "playwright-report", "test-results"].includes(part)
    ) || relative.endsWith(".tsbuildinfo")
  );
}

async function readSources(directories) {
  const chunks = [];
  for (const directory of directories) chunks.push(await readDirectory(directory));
  return chunks.join("\n");
}

async function readDirectory(directory) {
  const entries = await import("node:fs/promises").then(({ readdir }) =>
    readdir(directory, { withFileTypes: true })
  );
  const chunks = [];
  for (const entry of entries) {
    const target = path.join(directory, entry.name);
    if (entry.isDirectory()) chunks.push(await readDirectory(target));
    else if (/\.(?:ts|tsx|css)$/.test(entry.name)) chunks.push(await readFile(target, "utf8"));
  }
  return chunks.join("\n");
}

async function exists(target) {
  try {
    await lstat(target);
    return true;
  } catch {
    return false;
  }
}
