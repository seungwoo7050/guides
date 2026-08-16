import { cp, lstat, mkdir, readdir, realpath } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const modulePath = fileURLToPath(import.meta.url);
const exerciseRoot = path.resolve(path.dirname(modulePath), "..");
const skeleton = path.join(exerciseRoot, "skeleton");
const destination = path.join(exerciseRoot, "work");

await assertDirectory(exerciseRoot, "exercise root");
await assertDirectory(skeleton, "skeleton");
await assertContainedRealPath(exerciseRoot, skeleton);
await rejectSymlinks(skeleton);

try {
  await mkdir(destination);
} catch (error) {
  if (error && typeof error === "object" && error.code === "EEXIST") {
    fail(`workspace가 이미 존재합니다: ${path.relative(exerciseRoot, destination)} (덮어쓰지 않음)`);
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
  fail(
    `workspace 복사가 중단되었습니다. 보존된 경로를 확인한 뒤 직접 정리하세요: ` +
    `${path.relative(exerciseRoot, destination)}\n${error instanceof Error ? error.message : String(error)}`
  );
}

console.log(`WORKSPACE CREATED ${path.relative(exerciseRoot, destination)}`);

async function assertDirectory(target, label) {
  const stat = await lstat(target);
  if (stat.isSymbolicLink() || !stat.isDirectory()) {
    throw new Error(`${label}이 실제 디렉터리가 아닙니다: ${target}`);
  }
}

async function assertContainedRealPath(root, target) {
  const [rootReal, targetReal] = await Promise.all([realpath(root), realpath(target)]);
  const relative = path.relative(rootReal, targetReal);
  if (relative === "" || (!relative.startsWith(`..${path.sep}`) && relative !== ".." && !path.isAbsolute(relative))) return;
  throw new Error(`exercise 밖 경로를 사용할 수 없습니다: ${target}`);
}

async function rejectSymlinks(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const target = path.join(directory, entry.name);
    if (entry.isSymbolicLink()) throw new Error(`symbolic link를 복사하지 않습니다: ${target}`);
    if (entry.isDirectory()) await rejectSymlinks(target);
  }
}

function fail(message) {
  console.error(message);
  process.exit(2);
}
