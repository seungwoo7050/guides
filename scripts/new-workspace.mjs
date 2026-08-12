import { cp, lstat, mkdir, readdir, realpath } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { exerciseSlugs } from "./lib/exercise-paths.mjs";

export { exerciseSlugs } from "./lib/exercise-paths.mjs";

const modulePath = fileURLToPath(import.meta.url);
const repositoryRoot = path.resolve(path.dirname(modulePath), "..");
const exerciseSlugPattern = /^[a-z0-9][a-z0-9-]*$/;

if (process.argv[1] && path.resolve(process.argv[1]) === modulePath) {
  const slug = process.argv[2];
  if (!slug || process.argv.length !== 3) {
    fail(`사용법: node scripts/new-workspace.mjs <exercise>\n허용 값: ${exerciseSlugs.join(", ")}`);
  }

  try {
    const destination = await createWorkspace({ root: repositoryRoot, slug });
    console.log(`WORKSPACE CREATED ${path.relative(repositoryRoot, destination)}`);
  } catch (error) {
    fail(error instanceof Error ? error.message : String(error));
  }
}

export async function createWorkspace({ root, slug, allowedSlugs = exerciseSlugs }) {
  if (typeof slug !== "string" || !exerciseSlugPattern.test(slug)) {
    throw new Error(`exercise 이름은 하나의 안전한 path segment여야 합니다: ${String(slug)}`);
  }
  if (!allowedSlugs.includes(slug)) {
    throw new Error(`알 수 없는 exercise: ${slug}`);
  }

  const resolvedRoot = path.resolve(root);
  const exercisesRoot = path.join(resolvedRoot, "exercises");
  const exerciseRoot = path.join(exercisesRoot, slug);
  const skeleton = path.join(exerciseRoot, "skeleton");
  const destination = path.join(exerciseRoot, "work");

  assertContainedPath(exercisesRoot, exerciseRoot);
  await assertDirectory(exercisesRoot, "exercises root");
  await assertDirectory(exerciseRoot, `exercise ${slug}`);
  await assertDirectory(skeleton, `skeleton ${slug}`);
  await assertContainedRealPath(exercisesRoot, skeleton);
  await rejectSymlinks(skeleton);

  try {
    await mkdir(destination);
  } catch (error) {
    if (error && typeof error === "object" && error.code === "EEXIST") {
      throw new Error(`workspace가 이미 존재합니다: ${path.relative(resolvedRoot, destination)} (덮어쓰지 않음)`);
    }
    throw error;
  }

  try {
    for (const entry of await readdir(skeleton, { withFileTypes: true })) {
      await cp(path.join(skeleton, entry.name), path.join(destination, entry.name), {
        recursive: true,
        dereference: false,
        errorOnExist: true,
        force: false,
        preserveTimestamps: true
      });
    }
    await rejectSymlinks(destination);
  } catch (error) {
    throw new Error(
      `workspace 복사가 중단되었습니다. 보존된 경로를 확인한 뒤 직접 정리하세요: ` +
      `${path.relative(resolvedRoot, destination)}\n${error instanceof Error ? error.message : String(error)}`
    );
  }

  return destination;
}

function assertContainedPath(root, target) {
  const relative = path.relative(root, target);
  if (relative && !relative.startsWith(".." + path.sep) && relative !== ".." && !path.isAbsolute(relative)) return;
  throw new Error(`exercises 밖 경로를 사용할 수 없습니다: ${target}`);
}

async function assertDirectory(target, label) {
  const stat = await lstat(target);
  if (stat.isSymbolicLink() || !stat.isDirectory()) {
    throw new Error(`${label}이 실제 디렉터리가 아닙니다: ${target}`);
  }
}

async function assertContainedRealPath(root, target) {
  const [rootReal, targetReal] = await Promise.all([realpath(root), realpath(target)]);
  const relative = path.relative(rootReal, targetReal);
  if (relative === "" || (!relative.startsWith(".." + path.sep) && relative !== ".." && !path.isAbsolute(relative))) {
    return;
  }
  throw new Error(`exercises 밖 경로를 사용할 수 없습니다: ${target}`);
}

async function rejectSymlinks(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const target = path.join(directory, entry.name);
    if (entry.isSymbolicLink()) {
      throw new Error(`symbolic link를 복사하지 않습니다: ${target}`);
    }
    if (entry.isDirectory()) await rejectSymlinks(target);
  }
}

function fail(message) {
  console.error(message);
  process.exit(2);
}
