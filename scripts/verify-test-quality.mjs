import { cp, lstat, mkdtemp, readFile, rm, symlink, writeFile } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repositoryRoot = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const reference = path.join(repositoryRoot, "exercises", "project-catalog", "reference");
const referenceModules = path.join(reference, "node_modules");

if (!(await exists(referenceModules))) {
  throw new Error("reference 의존성이 없습니다. 먼저 ./prepare.sh를 실행하세요.");
}

console.log("검사기 기준 구현을 먼저 확인합니다.");
runRequired(reference, "test", "기준 unit test");
runRequired(reference, "build", "기준 production build");
runRequired(reference, "test:e2e", "기준 production browser test");

await mutation(
  "Stage 01 검사가 searchParams를 무시하는 구현을 거절합니다",
  async (project) => {
    await replaceOnce(
      path.join(project, "app", "page.tsx"),
      "const raw = await searchParams;",
      "await searchParams;\n  const raw = {};"
    );
  },
  [required("typecheck"), expectedFailure("test:stage:01")]
);

await mutation(
  "Stage 02 검사가 중복 식별자를 허용하는 구현을 거절합니다",
  async (project) => {
    await replaceOnce(
      path.join(project, "lib", "catalog-contract.ts"),
      "if (uniqueIds.size !== projects.length) {",
      "if (false) {"
    );
  },
  [required("typecheck"), expectedFailure("test:stage:02")]
);

await mutation(
  "Stage 03 unit 검사가 모든 generation을 최신으로 보는 구현을 거절합니다",
  async (project) => {
    await replaceOnce(
      path.join(project, "lib", "request-coordinator.ts"),
      "return candidate === generation;",
      "return true;"
    );
  },
  [required("typecheck"), expectedFailure("test:stage:03")]
);

await mutation(
  "Stage 03 browser 검사가 stale result guard 누락을 거절합니다",
  async (project) => {
    await replaceOnce(
      path.join(project, "app", "project-catalog.tsx"),
      "if (!coordinator.current.isCurrent(request.generation)) return;",
      "if (false) return;"
    );
  },
  [required("typecheck"), required("build"), expectedFailure("test:e2e:stage:03")]
);

await mutation(
  "Stage 04 browser 검사가 보이지 않는 focus indicator를 거절합니다",
  async (project) => {
    await replaceOnce(
      path.join(project, "app", "styles.css"),
      "outline: 3px solid #d76e00;",
      "outline: 0;"
    );
  },
  [required("typecheck"), required("build"), expectedFailure("test:e2e:stage:04")]
);

await mutation(
  "Stage 04 browser 검사가 사용자 제목을 바꾼 accessible name을 거절합니다",
  async (project) => {
    await replaceOnce(
      path.join(project, "app", "project-catalog.tsx"),
      "const articleLabel = `${project.title} 프로젝트`;",
      "const articleLabel = `${project.title.replace(\"상태\", \"스테이터스\")} 프로젝트`;"
    );
  },
  [required("typecheck"), required("build"), expectedFailure("test:e2e:stage:04")]
);

await mutation(
  "Stage 05 검사가 health의 추가 secret 필드를 거절합니다",
  async (project) => {
    await replaceOnce(
      path.join(project, "app", "api", "health", "route.ts"),
      'release: process.env.APP_RELEASE ?? "local"',
      'release: process.env.APP_RELEASE ?? "local",\n      secret: process.env.CATALOG_SERVER_ONLY_CANARY'
    );
  },
  [required("typecheck"), expectedFailure("test:stage:05")]
);

console.log("Stage 01–05 검사기가 대표적인 잘못된 구현을 실제로 거절했습니다.");

async function mutation(label, mutate, steps) {
  const temporary = await mkdtemp(path.join(tmpdir(), "project-catalog-mutation-"));
  try {
    await cp(reference, temporary, {
      recursive: true,
      filter: (source) => !isGenerated(reference, source)
    });
    await symlink(
      referenceModules,
      path.join(temporary, "node_modules"),
      process.platform === "win32" ? "junction" : "dir"
    );
    await mutate(temporary);

    for (const step of steps) {
      if (step.expectedFailure) runExpectedFailure(temporary, step.script, `${label}: ${step.script}`);
      else runRequired(temporary, step.script, `${label}: ${step.script}`);
    }
    console.log(`[PASS] ${label}`);
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
}

function required(script) {
  return { script, expectedFailure: false };
}

function expectedFailure(script) {
  return { script, expectedFailure: true };
}

function runRequired(project, script, label) {
  const result = runPnpm(project, script);
  if (result.error) throw new Error(`${label} 실행 실패: ${result.error.message}`);
  if (result.status !== 0) {
    throw new Error(`${label}가 기준상 성공해야 하지만 실패했습니다.\n${formatOutput(result)}`);
  }
}

function runExpectedFailure(project, script, label) {
  const result = runPnpm(project, script);
  if (result.error) throw new Error(`${label} 실행 실패: ${result.error.message}`);
  if (result.status === 0) {
    throw new Error(`${label}가 잘못된 구현을 통과시켰습니다.`);
  }
}

function runPnpm(project, script) {
  return spawnSync("pnpm", ["--dir", project, script], {
    encoding: "utf8",
    env: {
      ...process.env,
      CI: "1"
    },
    maxBuffer: 16 * 1024 * 1024
  });
}

async function replaceOnce(file, original, replacement) {
  const content = await readFile(file, "utf8");
  const first = content.indexOf(original);
  if (first < 0) throw new Error(`mutation 대상 문자열을 찾지 못했습니다: ${path.relative(repositoryRoot, file)}`);
  if (content.indexOf(original, first + original.length) >= 0) {
    throw new Error(`mutation 대상 문자열이 둘 이상입니다: ${path.relative(repositoryRoot, file)}`);
  }
  await writeFile(file, content.slice(0, first) + replacement + content.slice(first + original.length));
}

function isGenerated(projectRoot, source) {
  const relative = path.relative(projectRoot, source);
  if (!relative || relative.startsWith("..")) return false;
  return (
    relative.split(path.sep).some((part) =>
      ["node_modules", ".next", ".turbo", ".cache", "coverage", "dist", "out", "playwright-report", "test-results"].includes(part)
    ) || relative.endsWith(".tsbuildinfo") || relative.endsWith(".pid")
  );
}

function formatOutput(result) {
  const stdout = result.stdout ?? "";
  const stderr = result.stderr ?? "";
  const combined = `${stdout}\n${stderr}`.trim();
  return combined.length <= 12_000 ? combined : combined.slice(combined.length - 12_000);
}

async function exists(target) {
  try {
    await lstat(target);
    return true;
  } catch (error) {
    if (error?.code === "ENOENT") return false;
    throw error;
  }
}
