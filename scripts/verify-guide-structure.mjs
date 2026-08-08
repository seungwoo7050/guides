import { access, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const requiredDocs = [
  "docs/00-roadmap.md",
  ...[
    "01-how-the-web-works", "02-html-forms-accessibility", "03-css-layout-responsive",
    "04-javascript-foundations", "05-dom-events-url-storage", "06-async-fetch-errors",
    "07-typescript-runtime-validation", "08-node-packages-workspaces"
  ].map((name) => `docs/01-web-foundations/${name}.md`),
  ...[
    "01-react-components-state", "02-react-forms-lists", "03-react-effects-async",
    "04-nextjs-routing-rendering", "05-nextjs-data-boundaries"
  ].map((name) => `docs/02-frontend/${name}.md`),
  ...[
    "01-http-api-model", "02-fastify-lifecycle", "03-zod-contracts", "04-service-repository-errors"
  ].map((name) => `docs/03-backend/${name}.md`),
  ...[
    "01-sql-relational-model", "02-postgresql-kysely", "03-migrations-transactions",
    "04-passwords-sessions-cookies", "05-authorization-csrf-cors"
  ].map((name) => `docs/04-data-and-security/${name}.md`),
  ...[
    "01-websocket-protocol", "02-realtime-state-conflicts", "03-canvas-rendering", "04-testing-quality"
  ].map((name) => `docs/05-realtime-and-quality/${name}.md`),
  ...[
    "01-browser-task-list", "02-notes-api", "03-shared-notes", "04-collaboration-board"
  ].map((name) => `docs/06-capstones/${name}.md`)
];
const requiredExercises = [
  "exercises/00-first-web-app/README.md",
  "exercises/01-runtime/README.md",
  "exercises/02-browser/README.md",
  "exercises/03-react-nextjs/README.md",
  "exercises/04-fastify-zod-api/README.md",
  "exercises/05-postgresql-kysely/README.md",
  "exercises/06-security/README.md",
  "exercises/07-websocket/README.md",
  "exercises/08-testing/README.md",
  "exercises/collaboration-board/README.md"
];
const requiredSupport = [
  ".nvmrc",
  "reference/prerequisites.md",
  "reference/glossary.md",
  "reference/troubleshooting.md",
  "scripts/lib/browser-harness.mjs",
  "scripts/serve-static.mjs",
  "scripts/verify-links.mjs",
  "scripts/verify-snippets.mjs",
  "scripts/verify-postgresql-exercise.mjs",
  "exercises/00-first-web-app/tests/verify.mjs",
  "exercises/02-browser/tests/verify.mjs",
  "exercises/03-react-nextjs/tests/run.mjs",
  "exercises/03-react-nextjs/tests/verify-browser.mjs",
  "exercises/collaboration-board/checks/verify-stage-specs.mjs",
  "exercises/collaboration-board/checks/verify-work.mjs",
  "exercises/collaboration-board/walkthrough-base/README.md",
  "scripts/verify-patches.mjs",
  "exercises/collaboration-board/skeleton/package.json",
  "exercises/collaboration-board/skeleton/pnpm-workspace.yaml",
  "exercises/collaboration-board/skeleton/apps/web/app/page.tsx",
  "exercises/collaboration-board/skeleton/apps/api/src/app.test.ts"
];
const obsoleteDocs = [
  "docs/00-javascript-typescript-foundations.md",
  "docs/01-runtime-and-workspace.md",
  "docs/02-browser-ui-platform.md",
  "docs/03-react-nextjs-frontend.md",
  "docs/04-fastify-zod-api.md",
  "docs/05-postgresql-kysely.md",
  "docs/06-auth-security.md",
  "docs/07-realtime-websocket-canvas.md",
  "docs/08-testing-quality.md",
  "docs/09-collaboration-board.md"
];
const requiredScripts = [
  "check", "check:walkthrough", "verify:foundations", "verify:runtime", "verify:react",
  "verify:api", "verify:database", "verify:security", "verify:realtime", "verify:testing",
  "verify:collaboration", "verify", "serve:static"
];
const errors = [];

for (const relative of [...requiredDocs, ...requiredExercises, ...requiredSupport]) {
  if (!await exists(relative)) errors.push(`필수 파일 누락: ${relative}`);
}
for (const relative of obsoleteDocs) {
  if (await exists(relative)) errors.push(`이전 경로가 남아 있음: ${relative}`);
}

for (const relative of requiredDocs) {
  if (!await exists(relative)) continue;
  const text = await readFile(path.join(root, relative), "utf8");
  checkHeadings(relative, text);
  if (relative !== "docs/00-roadmap.md") {
    if (!text.includes("## 완료 기준")) errors.push(`완료 기준 누락: ${relative}`);
    if (!text.includes("## 다음 단계")) errors.push(`다음 단계 누락: ${relative}`);
  }
}

for (const relative of requiredExercises) {
  if (!await exists(relative)) continue;
  const text = await readFile(path.join(root, relative), "utf8");
  checkHeadings(relative, text);
  if (!text.includes("skeleton")) errors.push(`skeleton 학습 흐름 누락: ${relative}`);
  if (!text.includes("완료")) errors.push(`완료 계약 누락: ${relative}`);
  if (relative !== "exercises/collaboration-board/README.md" && !text.includes("reference")) {
    errors.push(`reference 비교 흐름 누락: ${relative}`);
  }
}

const roadmap = await readFile(path.join(root, "docs/00-roadmap.md"), "utf8");
for (const phrase of ["대상 독자", "선행지식", "지원 환경", "종료 능력", "읽는 순서", "문서와 실습 대응", "범위 밖"]) {
  if (!roadmap.includes(phrase)) errors.push(`roadmap 계약 누락: ${phrase}`);
}

const packageJson = JSON.parse(await readFile(path.join(root, "package.json"), "utf8"));
const nvmrc = (await readFile(path.join(root, ".nvmrc"), "utf8")).trim();
if (nvmrc !== "22.16.0") errors.push(`.nvmrc 버전 불일치: ${nvmrc}`);
if (packageJson.engines?.node !== ">=22.16.0 <23") {
  errors.push(`Node.js engines 계약 불일치: ${packageJson.engines?.node ?? "<missing>"}`);
}
for (const name of requiredScripts) {
  if (!packageJson.scripts?.[name]) errors.push(`package script 누락: ${name}`);
}


const capstoneStarter = JSON.parse(await readFile(path.join(root, "exercises/collaboration-board/skeleton/package.json"), "utf8"));
if (!capstoneStarter.scripts?.["verify:01"]) errors.push("협업 보드 starter의 verify:01 script 누락");
for (const packagePath of [
  "apps/web/package.json", "apps/api/package.json",
  "packages/contracts/package.json", "packages/db/package.json"
]) {
  const manifestPath = path.join(root, "exercises/collaboration-board/skeleton", packagePath);
  const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
  if (!manifest.scripts?.typecheck) errors.push(`협업 보드 starter typecheck 누락: ${packagePath}`);
}

const markdownToScan = [
  "README.md", "CONTRIBUTING.md", "reference/command-reference.md",
  "reference/prerequisites.md", "reference/glossary.md", "reference/troubleshooting.md",
  ...requiredDocs, ...requiredExercises
];
for (const relative of markdownToScan) {
  if (!await exists(relative)) continue;
  const text = await readFile(path.join(root, relative), "utf8");
  for (const obsolete of obsoleteDocs) {
    if (text.includes(obsolete) || text.includes(path.basename(obsolete))) {
      errors.push(`이전 문서 경로 참조: ${relative} -> ${obsolete}`);
    }
  }
}

if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}
console.log(`${requiredDocs.length}개 문서, ${requiredExercises.length}개 실습과 저장소 검증 계약을 확인했습니다.`);

async function exists(relative) {
  try { await access(path.join(root, relative)); return true; }
  catch { return false; }
}

function checkHeadings(relative, text) {
  const headings = [];
  let inFence = false;
  for (const [index, line] of text.split(/\r?\n/).entries()) {
    if (/^```/.test(line)) { inFence = !inFence; continue; }
    if (inFence) continue;
    const match = /^(#{1,6})\s+(.+)$/.exec(line);
    if (match) headings.push({ line: index + 1, level: match[1].length });
  }
  const h1Count = headings.filter((heading) => heading.level === 1).length;
  if (h1Count !== 1) errors.push(`H1은 정확히 하나여야 함: ${relative} (${h1Count})`);
  let previous = 0;
  for (const heading of headings) {
    if (previous && heading.level > previous + 1) {
      errors.push(`제목 단계 건너뜀: ${relative}:${heading.line} H${previous} -> H${heading.level}`);
    }
    previous = heading.level;
  }
}
