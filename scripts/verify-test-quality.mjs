import { cp, lstat, mkdtemp, readFile, rm, symlink, writeFile } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  runWorkspaceAction,
  verifyWorkspaceBoundary
} from "../exercises/project-catalog/check-workspace.mjs";
import { createWorkspace } from "../exercises/project-catalog/create-workspace.mjs";

const repositoryRoot = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const exerciseRoot = path.join(repositoryRoot, "exercises", "project-catalog");
const reference = path.join(repositoryRoot, "exercises", "project-catalog", "reference");
const skeleton = path.join(exerciseRoot, "skeleton");
const referenceModules = path.join(reference, "node_modules");
const learnerSourceFiles = [
  "app/page.tsx",
  "app/project-catalog.tsx",
  "app/styles.css",
  "app/api/health/route.ts",
  "lib/catalog-contract.ts",
  "lib/catalog-model.ts",
  "lib/request-coordinator.ts"
];

if (!(await exists(referenceModules))) {
  throw new Error("reference 의존성이 없습니다. 먼저 ./prepare.sh를 실행하세요.");
}

try {
  await verifyTestQuality();
} finally {
  await cleanReferenceGeneratedOutput();
}

async function verifyTestQuality() {
  await verifyWorkspaceProtection();
  await verifyLearningContractMutations();

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
  "Stage 04 browser 검사가 사용자 제목을 제거한 accessible name을 거절합니다",
  async (project) => {
    await replaceOnce(
      path.join(project, "app", "project-catalog.tsx"),
      "const articleLabel = getArticleAccessibleLabel(project.title);",
      'const articleLabel = "프로젝트";'
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
  [required("typecheck"), expectedFailure("test")]
);

console.log("Stage 01–05 검사기가 대표적인 잘못된 구현을 실제로 거절했습니다.");
}

async function verifyWorkspaceProtection() {
  await withInitialWorkspace(async (project) => {
    await verifyWorkspaceBoundary(project);
    await expectWorkspaceActionFailure("stage:01", project, 1, "미완성 Stage 01");

    const pageBefore = await readFile(path.join(project, "app", "page.tsx"), "utf8");
    await expectWorkspaceCreationFailure(project, "기존 workspace 보존");
    const pageAfter = await readFile(path.join(project, "app", "page.tsx"), "utf8");
    if (pageAfter !== pageBefore) {
      throw new Error("workspace 재생성 거절이 기존 learner source를 변경했습니다.");
    }

    const page = path.join(project, "app", "page.tsx");
    await writeFile(page, `${await readFile(page, "utf8")}\n// learner-owned source change\n`);
    await writeFile(path.join(project, "lib", "learner-helper.ts"), "export const value = 1;\n");
    await verifyWorkspaceBoundary(project);

    const linkedWorkspace = path.join(path.dirname(project), "workspace-link");
    await symlink(project, linkedWorkspace, process.platform === "win32" ? "junction" : "dir");
    await expectBoundaryFailure(linkedWorkspace, "symlink workspace root");
    await expectWorkspaceCreationFailure(linkedWorkspace, "symlink workspace 덮어쓰기 방지");
  });

  await withInitialWorkspace(async (project) => {
    for (const relative of learnerSourceFiles) {
      await cp(path.join(reference, relative), path.join(project, relative), { force: true });
    }
    await runWorkspaceAction("stage:01", project, { quiet: true, stdio: "pipe" });
    await runWorkspaceAction("stage:01", project, { quiet: true, stdio: "pipe" });
  });

  const protectedMutations = [
    ["package script 변경", async (project) => {
      const target = path.join(project, "package.json");
      const value = JSON.parse(await readFile(target, "utf8"));
      value.scripts.test = "node -e process.exit(0)";
      await writeFile(target, `${JSON.stringify(value, null, 2)}\n`);
    }],
    ["public test 변경", async (project) => {
      const target = path.join(project, "tests", "stages", "01-runtime.test.ts");
      await writeFile(target, `${await readFile(target, "utf8")}\n// weakened public test\n`);
    }],
    ["smoke harness 변경", async (project) => {
      const target = path.join(project, "scripts", "smoke-production.mjs");
      await writeFile(target, `${await readFile(target, "utf8")}\n// bypass attempt\n`);
    }],
    ["overlay public test 변경", async (project) => {
      const target = path.join(project, "tests", "implementation-contract.test.ts");
      await writeFile(target, `${await readFile(target, "utf8")}\n// marker check bypass\n`);
    }],
    ["protected file 삭제", async (project) => {
      await rm(path.join(project, "tests", "projects.test.ts"));
    }],
    ["root verifier config 추가", async (project) => {
      await writeFile(path.join(project, "vitest.config.ts"), "export default {};\n");
    }],
    ["생성물 symlink 우회", async (project) => {
      await symlink(tmpdir(), path.join(project, ".next"), process.platform === "win32" ? "junction" : "dir");
    }],
    ["중첩 node_modules symlink 우회", async (project) => {
      await symlink(
        referenceModules,
        path.join(project, "app", "node_modules"),
        process.platform === "win32" ? "junction" : "dir"
      );
    }]
  ];

  for (const [label, mutateWorkspace] of protectedMutations) {
    await withInitialWorkspace(async (project) => {
      await mutateWorkspace(project);
      try {
        await verifyWorkspaceBoundary(project);
      } catch {
        return;
      }
      throw new Error(`workspace 보호 검사가 잘못된 변경을 허용했습니다: ${label}`);
    });
  }
  console.log("workspace learner source와 repository-owned 검사 경계의 positive/negative 계약을 확인했습니다.");
}

async function verifyLearningContractMutations() {
  await withRepositoryCopy(async (project) => {
    runLearningContractRequired(project, "학습 계약 기준본");
  });

  const token = (label) => "[" + `Implementation ${label}` + "]";
  const mutations = [
    ["README Stage 검증 명령 누락", async (project) => {
      const target = path.join(project, "README.md");
      const content = await readFile(target, "utf8");
      const row = content.split("\n").find((candidate) => candidate.startsWith("| 3 |"));
      if (!row) throw new Error("README Stage 03 mapping row를 찾지 못했습니다.");
      await writeFile(
        target,
        content.replace(row, row.replace("pnpm exercise:verify:03", "pnpm exercise:verify:XX"))
      );
    }],
    ["README Stage 물리 순서 역전", async (project) => {
      const target = path.join(project, "README.md");
      const lines = (await readFile(target, "utf8")).split("\n");
      const stageOne = lines.findIndex((line) => line.startsWith("| 1 |"));
      const stageFive = lines.findIndex((line) => line.startsWith("| 5 |"));
      if (stageOne < 0 || stageFive < 0) throw new Error("README Stage mapping row를 찾지 못했습니다.");
      [lines[stageOne], lines[stageFive]] = [lines[stageFive], lines[stageOne]];
      await writeFile(target, lines.join("\n"));
    }],
    ["Implementation anchor 중복", async (project) => {
      const target = path.join(project, "exercises", "project-catalog", "reference", "lib", "catalog-contract.ts");
      await writeFile(target, `${await readFile(target, "utf8")}\n// ${token("1")} duplicate\n`);
    }],
    ["Implementation top-level gap", async (project) => {
      const route = path.join(project, "exercises", "project-catalog", "reference", "app", "api", "health", "route.ts");
      await replaceOnce(route, token("6"), token("8"));
      const readme = path.join(project, "exercises", "project-catalog", "README.md");
      await replaceOnce(readme, "| 6 |", "| 8 |");
    }],
    ["README Implementation source 경로 불일치", async (project) => {
      const target = path.join(project, "exercises", "project-catalog", "README.md");
      await replaceOnce(
        target,
        "`lib/catalog-contract.ts` · `ContractError`",
        "`lib/catalog-model.ts` · `ContractError`"
      );
    }],
    ["Implementation anchor의 reference test 이동", async (project) => {
      const source = path.join(
        project,
        "exercises",
        "project-catalog",
        "reference",
        "lib",
        "catalog-contract.ts"
      );
      const sourceLines = (await readFile(source, "utf8")).split("\n");
      const markerIndex = sourceLines.findIndex((line) => line.includes(token("1")));
      if (markerIndex < 0) throw new Error("Implementation 1 source anchor를 찾지 못했습니다.");
      const [markerLine] = sourceLines.splice(markerIndex, 1);
      await writeFile(source, sourceLines.join("\n"));
      const target = path.join(
        project,
        "exercises",
        "project-catalog",
        "reference",
        "tests",
        "projects.test.ts"
      );
      await writeFile(target, `${await readFile(target, "utf8")}\n${markerLine}\n`);
    }],
    ["skeleton annotation 누출", async (project) => {
      const target = path.join(project, "exercises", "project-catalog", "skeleton", "app", "page.tsx");
      await writeFile(target, `${await readFile(target, "utf8")}\n// ${token("7")} forbidden\n`);
    }],
    ["reference test annotation 누출", async (project) => {
      const target = path.join(project, "exercises", "project-catalog", "reference", "tests", "projects.test.ts");
      await writeFile(target, `${await readFile(target, "utf8")}\n// ${token("7")} forbidden\n`);
    }],
    ["JSON sidecar annotation 누출", async (project) => {
      const target = path.join(project, "exercises", "project-catalog", "reference", "performance-budget.json");
      const value = JSON.parse(await readFile(target, "utf8"));
      value.annotation = token("7");
      await writeFile(target, `${JSON.stringify(value, null, 2)}\n`);
    }],
    ["README 구현 index 누락", async (project) => {
      const target = path.join(project, "exercises", "project-catalog", "README.md");
      const content = await readFile(target, "utf8");
      const line = content.split("\n").find((candidate) => candidate.startsWith("| 4-2 |"));
      if (!line) throw new Error("README Implementation 4-2 index row를 찾지 못했습니다.");
      await writeFile(target, content.replace(`${line}\n`, ""));
    }],
    ["root README 누락", async (project) => {
      await rm(path.join(project, "README.md"));
    }],
    ["exercise README 누락", async (project) => {
      await rm(path.join(project, "exercises", "project-catalog", "README.md"));
    }]
  ];

  for (const [label, mutateRepository] of mutations) {
    await withRepositoryCopy(async (project) => {
      await mutateRepository(project);
      runLearningContractExpectedFailure(project, label);
    });
  }
  console.log("README mapping과 Implementation annotation validator가 대표적인 계약 위반을 거절했습니다.");
}

async function withInitialWorkspace(useWorkspace) {
  const temporaryRoot = await mkdtemp(path.join(tmpdir(), "project-catalog-workspace-contract-"));
  const project = path.join(temporaryRoot, "workspace");
  try {
    await createWorkspace({
      referenceRoot: reference,
      skeletonRoot: skeleton,
      workspaceRoot: project
    });
    await useWorkspace(project);
  } finally {
    await rm(temporaryRoot, { recursive: true, force: true });
  }
}

async function expectWorkspaceCreationFailure(workspaceRoot, label) {
  try {
    await createWorkspace({
      referenceRoot: reference,
      skeletonRoot: skeleton,
      workspaceRoot
    });
  } catch (error) {
    if (error?.code === "WORKSPACE_EXISTS") return;
    throw new Error(`${label} 검사가 예상하지 못한 오류로 실패했습니다: ${error?.message ?? error}`);
  }
  throw new Error(`${label} 검사가 기존 workspace를 통과시켰습니다.`);
}

async function expectWorkspaceActionFailure(action, project, exitCode, label) {
  try {
    await runWorkspaceAction(action, project, { quiet: true, stdio: "pipe" });
  } catch (error) {
    if (error?.exitCode === exitCode) return;
    throw new Error(`${label} 검사의 종료 코드가 다릅니다: ${error?.exitCode ?? "<missing>"}`);
  }
  throw new Error(`${label} 검사는 실패해야 합니다.`);
}

async function expectBoundaryFailure(project, label) {
  try {
    await verifyWorkspaceBoundary(project);
  } catch {
    return;
  }
  throw new Error(`workspace 보호 검사가 ${label}을(를) 통과시켰습니다.`);
}

async function withRepositoryCopy(useRepository) {
  const temporaryRoot = await mkdtemp(path.join(tmpdir(), "project-catalog-learning-contract-"));
  const project = path.join(temporaryRoot, "repository");
  try {
    await cp(repositoryRoot, project, {
      recursive: true,
      filter: (source) => includeRepositoryContractFile(source)
    });
    await useRepository(project);
  } finally {
    await rm(temporaryRoot, { recursive: true, force: true });
  }
}

function includeRepositoryContractFile(source) {
  const relative = path.relative(repositoryRoot, source);
  if (!relative || relative.startsWith("..")) return true;
  const parts = relative.split(path.sep);
  const basename = parts.at(-1) ?? relative;
  return !(
    parts.some((part) =>
      [".git", ".guide", "node_modules", ".next", ".turbo", "coverage", "playwright-report", "test-results", "workspace"].includes(part)
    ) ||
    parts.some((part) => part.startsWith(".workspace-") || part.startsWith(".project-catalog-mutation-")) ||
    basename.endsWith(".tsbuildinfo") ||
    basename.endsWith(".pid") ||
    basename === "next-env.d.ts"
  );
}

function runLearningContractRequired(project, label) {
  const result = runLearningContract(project);
  if (result.error) throw new Error(`${label} 실행 실패: ${result.error.message}`);
  if (result.status !== 0) {
    throw new Error(`${label}가 성공해야 하지만 실패했습니다.\n${formatOutput(result)}`);
  }
}

function runLearningContractExpectedFailure(project, label) {
  const result = runLearningContract(project);
  if (result.error) throw new Error(`${label} 실행 실패: ${result.error.message}`);
  if (result.status === 0) throw new Error(`${label}을 학습 계약 validator가 통과시켰습니다.`);
}

function runLearningContract(project) {
  return spawnSync(
    process.execPath,
    [path.join(repositoryRoot, "scripts", "verify-repository.mjs"), "--learning-contract-root", project],
    { encoding: "utf8", maxBuffer: 4 * 1024 * 1024 }
  );
}

async function cleanReferenceGeneratedOutput() {
  for (const relative of [
    "next-env.d.ts",
    ".next",
    "coverage",
    "playwright-report",
    "test-results",
    "tsconfig.tsbuildinfo"
  ]) {
    await rm(path.join(reference, relative), { recursive: true, force: true });
  }
}

async function mutation(label, mutate, steps) {
  // Next.js 16의 Turbopack은 프로젝트 filesystem root 밖을 가리키는
  // node_modules symlink를 거절한다. 저장소 안에 격리 디렉터리를 만들면
  // pnpm workspace root와 reference 의존성이 같은 filesystem root에 남는다.
  const temporary = await mkdtemp(path.join(repositoryRoot, ".project-catalog-mutation-"));
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
