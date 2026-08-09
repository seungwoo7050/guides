import { access, readFile, readdir, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const errors = [];
const pairedExercises = [
  "01-runtime",
  "03-react-nextjs",
  "04-fastify-zod-api",
  "05-postgresql-kysely",
  "06-security",
  "07-websocket",
  "08-testing"
];

for (const name of pairedExercises) {
  const exercise = path.join(root, "exercises", name);
  for (const required of ["README.md", "skeleton", "reference", "reference.patch"]) {
    if (!await exists(path.join(exercise, required))) errors.push(`${name}: ${required} 누락`);
  }
  if (!await exists(path.join(exercise, "skeleton")) || !await exists(path.join(exercise, "reference"))) continue;
  const skeletonDirectory = path.join(exercise, "skeleton");
  const referenceDirectory = path.join(exercise, "reference");
  const skeleton = await treeDigest(skeletonDirectory);
  const reference = await treeDigest(referenceDirectory);
  if (skeleton === reference) errors.push(`${name}: skeleton과 reference가 동일합니다.`);
  const skeletonText = await combinedText(skeletonDirectory);
  const referenceText = await combinedText(referenceDirectory);
  if (!skeletonText.includes("TODO")) errors.push(`${name}: 학습자가 구현할 TODO 경계가 없습니다.`);
  if (referenceText.includes("TODO")) errors.push(`${name}: reference에 TODO가 남아 있습니다.`);
}

for (const name of ["04-fastify-zod-api", "05-postgresql-kysely", "06-security", "07-websocket", "08-testing"]) {
  for (const side of ["skeleton", "reference"]) {
    const packagePath = path.join(root, "exercises", name, side, "package.json");
    if (!await exists(packagePath)) continue;
    const manifest = JSON.parse(await readFile(packagePath, "utf8"));
    for (const script of ["typecheck", "test"]) {
      if (typeof manifest.scripts?.[script] !== "string") errors.push(`${name}/${side}: ${script} script 누락`);
    }
  }
  const sharedTest = path.join(root, "exercises", name, "reference", "src", "app.test.ts");
  if (name !== "05-postgresql-kysely" && name !== "08-testing" && !await exists(sharedTest)) {
    errors.push(`${name}: 실제 계약 test 누락`);
  }
}

const requiredPhrases = new Map([
  ["04-fastify-zod-api", ["invalid_request", "not_found", "internal_error", "statusCode).toBe(409"]],
  ["05-postgresql-kysely", ["reservation_audit", "afterReservation", "Promise.allSettled", "drop table"]],
  ["06-security", ["origin_forbidden", "httpOnly", "statusCode).toBe(401", "statusCode).toBe(403"]],
  ["07-websocket", ["board.snapshot", "board.patch", "viewer", "baseVersion"]],
  ["08-testing", ["decrement", "getByRole", "status"]]
]);
for (const [name, phrases] of requiredPhrases) {
  const source = await combinedText(path.join(root, "exercises", name, "reference"));
  for (const phrase of phrases) {
    if (!source.includes(phrase)) errors.push(`${name}: 검증 계약 단서 누락 (${phrase})`);
  }
}

const databaseRepository = await readFile(
  path.join(root, "exercises", "05-postgresql-kysely", "reference", "src", "repository.ts"),
  "utf8"
);
if (/\bsql\.raw\b/.test(databaseRepository)) {
  errors.push("05-postgresql-kysely: repository 사용자 값 경로에서 sql.raw 사용 금지");
}

for (const name of ["00-first-web-app", "02-browser"]) {
  for (const side of ["skeleton", "reference"]) {
    if (!await exists(path.join(root, "exercises", name, side))) errors.push(`${name}/${side} 누락`);
  }
  if (!await exists(path.join(root, "exercises", name, "tests", "verify.mjs"))) errors.push(`${name}: browser verifier 누락`);
}

if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}
console.log("독립 실습의 skeleton·reference·test·patch 계약을 확인했습니다.");

async function exists(target) {
  try { await access(target); return true; }
  catch { return false; }
}

async function treeDigest(directory) {
  const rows = [];
  for (const file of await walk(directory)) {
    rows.push(`${path.relative(directory, file)}\0${await readFile(file, "utf8")}`);
  }
  return rows.join("\n");
}

async function combinedText(directory) {
  let output = "";
  for (const file of await walk(directory)) {
    if (/\.(?:ts|tsx|js|mjs|sql)$/.test(file)) output += `\n${await readFile(file, "utf8")}`;
  }
  return output;
}

async function walk(directory) {
  const output = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (["node_modules", ".next", "coverage", "playwright-report", "test-results"].includes(entry.name)) continue;
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) output.push(...await walk(full));
    else if (entry.isFile() && (await stat(full)).isFile()) output.push(full);
  }
  return output.sort();
}
