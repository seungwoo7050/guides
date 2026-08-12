import { lstat, readFile, readdir, realpath, rm, symlink } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const exerciseRoot = path.dirname(fileURLToPath(import.meta.url));
const reference = path.join(exerciseRoot, "reference");
const skeleton = path.join(exerciseRoot, "skeleton");
const workspace = path.join(exerciseRoot, "workspace");
const markerChecker = path.join(exerciseRoot, "check-stage-markers.mjs");

const learnerOwnedFiles = new Set([
  "app/page.tsx",
  "app/project-catalog.tsx",
  "app/styles.css",
  "app/api/health/route.ts",
  "lib/catalog-contract.ts",
  "lib/catalog-model.ts",
  "lib/request-coordinator.ts"
]);

const skeletonProtectedFiles = new Map([
  [
    "tests/implementation-contract.test.ts",
    path.join(skeleton, "tests", "implementation-contract.test.ts")
  ]
]);

const generatedDirectoryNames = new Set([
  ".next",
  ".turbo",
  ".cache",
  "coverage",
  "dist",
  "out",
  "playwright-report",
  "test-results"
]);

const workspaceDependencyLink = "node_modules";

const invokedPath = process.argv[1] ? path.resolve(process.argv[1]) : null;
if (invokedPath === fileURLToPath(import.meta.url)) await main();

async function main() {
  const action = process.argv[2] ?? "check";
  try {
    await runWorkspaceAction(action, workspace, { requireCanonicalRoot: true });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (message) console.error(message);
    process.exit(error?.exitCode ?? 1);
  }
}

export async function runWorkspaceAction(action, targetRoot, options = {}) {
  const plans = workspacePlans(targetRoot);
  if (!(action in plans)) {
    throw new WorkspaceActionError(
      "사용법: node check-workspace.mjs stage:01|stage:02|stage:03|stage:04|stage:05|check|build|test:e2e|smoke|verify",
      2
    );
  }
  if (!(await exists(targetRoot))) {
    throw new WorkspaceActionError(
      "workspace가 없습니다. 먼저 pnpm exercise:create를 실행하세요.",
      2
    );
  }

  try {
    await verifyWorkspaceBoundary(targetRoot, {
      requireCanonicalRoot: options.requireCanonicalRoot ?? false
    });
  } catch (error) {
    throw new WorkspaceActionError(error instanceof Error ? error.message : String(error), 1);
  }
  if (!options.quiet) {
    console.log("workspace의 learner source와 repository-owned 검증 경계를 확인했습니다.");
  }

  const dependencyLinkCreated = await linkDependencies(targetRoot);
  try {
    for (const step of plans[action]) {
      const result = spawnSync(step.command, step.args, {
        cwd: exerciseRoot,
        stdio: options.stdio ?? "inherit",
        encoding: options.stdio === "pipe" ? "utf8" : undefined,
        env: process.env
      });
      if (result.error) {
        throw new WorkspaceActionError(`${step.label} 실행 실패: ${result.error.message}`, 1);
      }
      if (result.status !== 0) {
        const details = options.stdio === "pipe" ? formatOutput(result) : "";
        throw new WorkspaceActionError(
          `${step.label}가 실패했습니다.${details ? `\n${details}` : ""}`,
          result.status ?? 1
        );
      }
    }
  } finally {
    if (dependencyLinkCreated) await rm(path.join(targetRoot, workspaceDependencyLink));
  }
}

// Learner source shape is intentionally flexible, but the commands and evidence used
// to judge it must remain repository-owned. This check runs before every workspace action.
export async function verifyWorkspaceBoundary(targetRoot, options = {}) {
  await verifyWorkspaceRoot(targetRoot, options);
  const referenceFiles = await collectFiles(reference);
  const actualFiles = await collectFiles(targetRoot, {
    rejectSymlinks: true,
    allowRootDependencyLink: true
  });
  const knownFiles = new Set(referenceFiles.keys());

  for (const [relative, source] of referenceFiles) {
    if (learnerOwnedFiles.has(relative)) continue;
    await assertSameProtectedFile(source, path.join(targetRoot, relative), relative);
  }

  for (const [relative, source] of skeletonProtectedFiles) {
    knownFiles.add(relative);
    await assertSameProtectedFile(source, path.join(targetRoot, relative), relative);
  }

  for (const relative of actualFiles.keys()) {
    if (knownFiles.has(relative)) continue;
    if (relative.startsWith("app/") || relative.startsWith("lib/")) continue;
    throw new Error(
      `workspace 검증 경계 밖에 새 파일을 둘 수 없습니다: ${relative}. 새 production source는 app/ 또는 lib/ 아래에 두세요.`
    );
  }

  await verifyDependencyBoundary(targetRoot);
}

async function verifyWorkspaceRoot(targetRoot, options) {
  const metadata = await lstat(targetRoot);
  if (!metadata.isDirectory() || metadata.isSymbolicLink()) {
    throw new Error("workspace root는 symlink가 아닌 일반 디렉터리여야 합니다.");
  }
  if (!options.requireCanonicalRoot) return;

  const [resolvedTarget, resolvedExercise] = await Promise.all([
    realpath(targetRoot),
    realpath(exerciseRoot)
  ]);
  if (resolvedTarget !== path.join(resolvedExercise, "workspace")) {
    throw new Error("workspace root가 project-catalog 실습 경계 밖을 가리킵니다.");
  }
}

async function verifyDependencyBoundary(targetRoot) {
  const target = path.join(targetRoot, workspaceDependencyLink);
  let metadata;
  try {
    metadata = await lstat(target);
  } catch (error) {
    if (error?.code === "ENOENT") return;
    throw error;
  }

  if (!metadata.isSymbolicLink()) {
    throw new Error("workspace node_modules는 기준 reference dependency를 가리키는 symlink여야 합니다.");
  }
  const resolved = await realpath(target);
  const expected = await realpath(path.join(reference, workspaceDependencyLink));
  if (resolved !== expected) {
    throw new Error("workspace node_modules symlink가 기준 reference dependency를 가리키지 않습니다.");
  }
}

async function assertSameProtectedFile(source, target, relative) {
  let metadata;
  try {
    metadata = await lstat(target);
  } catch (error) {
    if (error?.code === "ENOENT") {
      throw new Error(`repository-owned 보호 파일이 없습니다: ${relative}`);
    }
    throw error;
  }
  if (!metadata.isFile() || metadata.isSymbolicLink()) {
    throw new Error(`repository-owned 보호 경로는 일반 파일이어야 합니다: ${relative}`);
  }

  const [expected, actual] = await Promise.all([readFile(source), readFile(target)]);
  if (!expected.equals(actual)) {
    throw new Error(
      `repository-owned 보호 파일이 변경되었습니다: ${relative}. learner source만 수정하고 이 파일은 기준본으로 복원하세요.`
    );
  }
}

async function collectFiles(root, options = {}) {
  const files = new Map();
  await visit(root, "");
  return files;

  async function visit(directory, parent) {
    for (const entry of await readdir(directory, { withFileTypes: true })) {
      const relative = parent ? `${parent}/${entry.name}` : entry.name;
      const target = path.join(directory, entry.name);
      if (entry.isSymbolicLink()) {
        if (options.allowRootDependencyLink && relative === workspaceDependencyLink) continue;
        if (options.rejectSymlinks) {
          throw new Error(`workspace source와 검증 경계에 symlink를 허용하지 않습니다: ${relative}`);
        }
        continue;
      }
      if (entry.name === workspaceDependencyLink) {
        if (options.rejectSymlinks && relative !== workspaceDependencyLink) {
          throw new Error(`workspace의 중첩 node_modules를 허용하지 않습니다: ${relative}`);
        }
        continue;
      }
      if (isGenerated(relative)) {
        if (options.rejectSymlinks && entry.isDirectory()) {
          await assertNoSymlinks(target, relative);
        }
        continue;
      }
      if (entry.isDirectory()) {
        await visit(target, relative);
      } else if (entry.isFile()) {
        files.set(relative, target);
      } else if (options.rejectSymlinks) {
        throw new Error(`workspace에 지원하지 않는 파일 형식이 있습니다: ${relative}`);
      }
    }
  }
}

async function assertNoSymlinks(directory, parent) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const relative = `${parent}/${entry.name}`;
    const target = path.join(directory, entry.name);
    if (entry.isSymbolicLink()) {
      throw new Error(`workspace 생성물 경계에 symlink를 허용하지 않습니다: ${relative}`);
    }
    if (entry.isDirectory()) await assertNoSymlinks(target, relative);
  }
}

function isGenerated(relative) {
  const parts = relative.split("/");
  const basename = parts.at(-1) ?? relative;
  return (
    parts.some((part) => generatedDirectoryNames.has(part) || part.startsWith(".workspace-")) ||
    basename === "next-env.d.ts" ||
    basename === ".eslintcache" ||
    basename.endsWith(".tsbuildinfo") ||
    basename.endsWith(".pid")
  );
}

function workspacePlans(targetRoot) {
  return {
    "stage:01": [marker("01", targetRoot), script("typecheck", targetRoot), script("test:stage:01", targetRoot)],
    "stage:02": [marker("02", targetRoot), script("typecheck", targetRoot), script("test:stage:02", targetRoot)],
    "stage:03": [
      marker("03", targetRoot),
      script("typecheck", targetRoot),
      script("test:stage:03", targetRoot),
      script("build", targetRoot),
      script("test:e2e:stage:03", targetRoot)
    ],
    "stage:04": [
      marker("04", targetRoot),
      script("typecheck", targetRoot),
      script("test:stage:04", targetRoot),
      script("build", targetRoot),
      script("test:e2e:stage:04", targetRoot)
    ],
    "stage:05": [
      marker("05", targetRoot),
      script("typecheck", targetRoot),
      script("test", targetRoot),
      script("build", targetRoot),
      script("test:e2e", targetRoot),
      script("smoke", targetRoot)
    ],
    check: [marker("05", targetRoot), script("typecheck", targetRoot), script("test", targetRoot)],
    build: [script("build", targetRoot)],
    "test:e2e": [script("build", targetRoot), script("test:e2e", targetRoot)],
    smoke: [script("build", targetRoot), script("smoke", targetRoot)],
    verify: [
      marker("05", targetRoot),
      script("typecheck", targetRoot),
      script("test", targetRoot),
      script("build", targetRoot),
      script("test:e2e", targetRoot),
      script("smoke", targetRoot)
    ]
  };
}

function marker(stage, targetRoot) {
  return {
    command: process.execPath,
    args: [markerChecker, targetRoot, stage],
    label: `Stage ${stage} 표시 검사`
  };
}

function script(name, targetRoot) {
  return {
    command: "pnpm",
    args: ["--dir", targetRoot, name],
    label: `workspace ${name}`
  };
}

async function linkDependencies(targetRoot) {
  const referenceModules = path.join(reference, "node_modules");
  const workspaceModules = path.join(targetRoot, "node_modules");
  if (await exists(workspaceModules)) return false;
  if (!(await exists(referenceModules))) {
    throw new WorkspaceActionError(
      "의존성이 없습니다. 저장소 루트에서 ./prepare.sh를 먼저 실행하세요.",
      2
    );
  }
  await symlink(
    referenceModules,
    workspaceModules,
    process.platform === "win32" ? "junction" : "dir"
  );
  return true;
}

function formatOutput(result) {
  return [result.stdout, result.stderr].filter(Boolean).join("\n").trim();
}

class WorkspaceActionError extends Error {
  constructor(message, exitCode) {
    super(message);
    this.exitCode = exitCode;
  }
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
