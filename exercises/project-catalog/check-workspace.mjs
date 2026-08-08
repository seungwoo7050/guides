import { lstat, symlink } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const exerciseRoot = path.dirname(fileURLToPath(import.meta.url));
const reference = path.join(exerciseRoot, "reference");
const workspace = path.join(exerciseRoot, "workspace");
const markerChecker = path.join(exerciseRoot, "check-stage-markers.mjs");
const action = process.argv[2] ?? "check";

const plans = {
  "stage:01": [marker("01"), script("typecheck"), script("test:stage:01")],
  "stage:02": [marker("02"), script("typecheck"), script("test:stage:02")],
  "stage:03": [
    marker("03"),
    script("typecheck"),
    script("test:stage:03"),
    script("build"),
    script("test:e2e:stage:03")
  ],
  "stage:04": [
    marker("04"),
    script("typecheck"),
    script("test:stage:04"),
    script("build"),
    script("test:e2e:stage:04")
  ],
  "stage:05": [
    marker("05"),
    script("typecheck"),
    script("test"),
    script("build"),
    script("test:e2e"),
    script("smoke")
  ],
  check: [marker("05"), script("typecheck"), script("test")],
  build: [script("build")],
  "test:e2e": [script("build"), script("test:e2e")],
  smoke: [script("build"), script("smoke")],
  verify: [
    marker("05"),
    script("typecheck"),
    script("test"),
    script("build"),
    script("test:e2e"),
    script("smoke")
  ]
};

if (!(action in plans)) {
  console.error(
    "사용법: node check-workspace.mjs stage:01|stage:02|stage:03|stage:04|stage:05|check|build|test:e2e|smoke|verify"
  );
  process.exit(2);
}
if (!(await exists(workspace))) {
  console.error("workspace가 없습니다. 먼저 pnpm exercise:create를 실행하세요.");
  process.exit(2);
}

await linkDependencies();

for (const step of plans[action]) {
  const result = spawnSync(step.command, step.args, {
    cwd: exerciseRoot,
    stdio: "inherit",
    env: process.env
  });
  if (result.error) {
    console.error(`${step.label} 실행 실패: ${result.error.message}`);
    process.exit(1);
  }
  if (result.status !== 0) process.exit(result.status ?? 1);
}

function marker(stage) {
  return {
    command: process.execPath,
    args: [markerChecker, workspace, stage],
    label: `Stage ${stage} 표시 검사`
  };
}

function script(name) {
  return {
    command: "pnpm",
    args: ["--dir", workspace, name],
    label: `workspace ${name}`
  };
}

async function linkDependencies() {
  const referenceModules = path.join(reference, "node_modules");
  const workspaceModules = path.join(workspace, "node_modules");
  if (await exists(workspaceModules)) return;
  if (!(await exists(referenceModules))) {
    console.error("의존성이 없습니다. 저장소 루트에서 pnpm install --frozen-lockfile을 먼저 실행하세요.");
    process.exit(2);
  }
  await symlink(
    referenceModules,
    workspaceModules,
    process.platform === "win32" ? "junction" : "dir"
  );
}

async function exists(target) {
  try {
    await lstat(target);
    return true;
  } catch {
    return false;
  }
}
