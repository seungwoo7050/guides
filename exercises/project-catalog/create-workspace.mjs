import { cp, lstat, mkdtemp, rename, rm, symlink } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const exerciseRoot = path.dirname(fileURLToPath(import.meta.url));
const reference = path.join(exerciseRoot, "reference");
const skeleton = path.join(exerciseRoot, "skeleton");
const workspace = path.join(exerciseRoot, "workspace");

if (await exists(workspace)) {
  console.error(`작업 공간이 이미 있습니다: ${workspace}`);
  console.error("기존 작업을 보존하거나 직접 삭제한 뒤 다시 실행하세요.");
  process.exit(2);
}

const temporary = await mkdtemp(path.join(exerciseRoot, ".workspace-"));
try {
  await cp(reference, temporary, {
    recursive: true,
    filter: (source) => !isGenerated(reference, source)
  });

  for (const relative of ["app", "lib", "tests"]) {
    const source = path.join(skeleton, relative);
    if (await exists(source)) {
      await cp(source, path.join(temporary, relative), {
        recursive: true,
        force: true
      });
    }
  }

  const referenceModules = path.join(reference, "node_modules");
  const workspaceModules = path.join(temporary, "node_modules");
  if (await exists(referenceModules) && !(await exists(workspaceModules))) {
    await symlink(
      referenceModules,
      workspaceModules,
      process.platform === "win32" ? "junction" : "dir"
    );
  }

  await rename(temporary, workspace);
  console.log(`작업 공간을 만들었습니다: ${workspace}`);
  console.log("pnpm exercise:verify:01로 Stage 01의 현재 실패를 확인하세요.");
} catch (error) {
  await rm(temporary, { recursive: true, force: true });
  throw error;
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

async function exists(target) {
  try {
    await lstat(target);
    return true;
  } catch {
    return false;
  }
}
