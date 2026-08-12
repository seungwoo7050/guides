import { access, readFile } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { exerciseSlugs } from "./lib/exercise-paths.mjs";

export const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

export const learningExerciseOrder = Object.freeze([
  "00-first-web-app",
  "02-browser",
  "01-runtime",
  "03-react-nextjs",
  "04-fastify-zod-api",
  "05-postgresql-kysely",
  "06-security",
  "07-websocket",
  "08-testing",
  "collaboration-board"
]);

export const testAnnotationAllowlist = new Set([
  "exercises/08-testing/reference/src/app.test.ts",
  "exercises/08-testing/reference/src/counter.test.ts",
  "exercises/08-testing/reference/tests/counter.spec.ts",
  "exercises/08-testing/reference/playwright.config.ts",
  "exercises/collaboration-board/reference/apps/api/src/app.test.ts",
  "exercises/collaboration-board/reference/apps/api/src/ws.test.ts",
  "exercises/collaboration-board/reference/apps/web/components/LoginForm.test.tsx",
  "exercises/collaboration-board/reference/packages/contracts/src/contracts.test.ts",
  "exercises/collaboration-board/reference/packages/db/src/postgres.test.ts",
  "exercises/collaboration-board/reference/packages/db/src/repository.test.ts",
  "exercises/collaboration-board/reference/playwright.config.ts",
  "exercises/collaboration-board/reference/tests/e2e/board.spec.ts",
  "exercises/collaboration-board/reference/tests/smoke.mjs"
]);

const implementationHeadings = new Map([
  ...exerciseSlugs
    .filter((slug) => slug !== "collaboration-board")
    .map((slug) => [slug, "Reference 구현 순서"]),
  ["collaboration-board", "기준 구현의 학습용 구성 순서"]
]);

const exactWorkIgnoreRules = exerciseSlugs.map((slug) => `/exercises/${slug}/work/`);
const derivedPatchPattern = /(?:^|\/)(?:reference\.patch|patches\/[^/]+\.patch)$/;
const learningContractInfrastructure = new Set([
  "scripts/verify-learning-contract.mjs",
  "scripts/test-learning-contract.mjs"
]);
const markerPattern = /\[Implementation ([^\]\r\n]+)\]/g;
const canonicalLabelPattern = /^(?:0|[1-9][0-9]*(?:-[1-9][0-9]*)?)$/;
const implementationZeroScopes = new Set([
  "01-runtime",
  "03-react-nextjs",
  "04-fastify-zod-api",
  "05-postgresql-kysely",
  "06-security",
  "07-websocket",
  "08-testing",
  "collaboration-board"
]);

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const errors = await verifyLearningContract(root);
  if (errors.length) {
    console.error(errors.join("\n"));
    process.exit(1);
  }
  console.log("학습 순서, workspace, expected evidence와 Implementation annotation 계약을 확인했습니다.");
}

export async function verifyLearningContract(repositoryRoot) {
  const errors = [];
  const entries = await collectRepositoryEntries(repositoryRoot);
  const entryMap = new Map(entries.map((entry) => [entry.path, entry.source]));

  errors.push(...await validateRootMapping(repositoryRoot, entryMap));
  errors.push(...await validateExpectedEvidence(repositoryRoot, entryMap));
  errors.push(...await validateWorkspaceContract(repositoryRoot, entryMap));
  errors.push(...validateLegacyPathEntries(entries));

  const indexes = new Map();
  for (const slug of exerciseSlugs) {
    const relative = `exercises/${slug}/README.md`;
    const source = entryMap.get(relative);
    if (source === undefined) {
      errors.push(`Implementation index README 누락: ${relative}`);
      continue;
    }
    const heading = implementationHeadings.get(slug);
    const section = markdownSection(source, heading);
    if (section === undefined) {
      errors.push(`${relative}: Implementation index section 누락 (${heading})`);
      continue;
    }
    const rows = implementationRows(section);
    if (rows.length === 0) {
      errors.push(`${relative}: Implementation index row가 없습니다.`);
      continue;
    }
    indexes.set(slug, rows);
  }

  const authoritative = entries.filter((entry) =>
    !derivedPatchPattern.test(entry.path) && !learningContractInfrastructure.has(entry.path)
  );
  errors.push(...validateAnnotationEntries(authoritative, indexes));
  return errors;
}

async function validateRootMapping(repositoryRoot, entries) {
  const errors = [];
  const readme = entries.get("README.md") ?? "";
  const section = markdownSection(readme, "문서에서 최종 문제까지의 ordered mapping");
  if (section === undefined) {
    errors.push("README ordered mapping section 누락");
  } else {
    const table = markdownTable(section);
    const requiredColumns = ["순서", "문서", "관찰 예제", "직접 수행", "수정 위치", "검증", "완료 뒤 비교·다음"];
    if (!sameArray(table.header, requiredColumns)) {
      errors.push(`README ordered mapping header 불일치: ${table.header.join(" | ") || "<missing>"}`);
    }

    const observed = [];
    const linkPattern = /\(exercises\/([^/)]+)\/README\.md(?:#[^)]*)?\)/g;
    for (const match of section.matchAll(linkPattern)) observed.push(match[1]);
    if (!sameArray(observed, learningExerciseOrder)) {
      errors.push(
        `README exercise coverage/order 불일치\n` +
        `  기대: ${learningExerciseOrder.join(" -> ")}\n` +
        `  실제: ${observed.join(" -> ") || "<none>"}`
      );
    }
  }

  if (!readme.includes("현재 이 브랜치에는 별도 `examples/`가 없습니다")) {
    errors.push("README에 examples 부재가 의도한 학습 경계임을 명시해야 합니다.");
  }
  if (await exists(path.join(repositoryRoot, "examples"))) {
    errors.push("examples/가 존재합니다. 이 branch의 canonical contract는 별도 examples 없음입니다.");
  }
  return errors;
}

async function validateExpectedEvidence(repositoryRoot, entries) {
  const errors = [];
  const briefs = [
    ["02-notes-api", "docs/06-capstones/02-notes-api.md"],
    ["03-shared-notes", "docs/06-capstones/03-shared-notes.md"]
  ];

  for (const [slug, relative] of briefs) {
    const source = entries.get(relative) ?? "";
    const artifactSlug = slug.replace(/^0[23]-/, "");
    for (const phrase of [
      "self-directed expected-evidence brief",
      "자동 verifier 또는 reference 구현이 없습니다",
      "저장소 밖",
      "## Expected evidence rubric"
    ]) {
      if (!source.includes(phrase)) errors.push(`${relative}: expected-evidence 계약 누락 (${phrase})`);
    }
    for (const candidate of [
      `exercises/${slug}`,
      `projects/${slug}`,
      `exercises/${artifactSlug}`,
      `projects/${artifactSlug}`
    ]) {
      if (await exists(path.join(repositoryRoot, candidate))) {
        errors.push(`${relative}: self-directed brief 전용 repository 자료가 있으면 안 됩니다: ${candidate}`);
      }
    }
    for (const candidate of entries.keys()) {
      if (candidate === relative) continue;
      if (candidate.split("/").some((segment) => segment.includes(artifactSlug))) {
        errors.push(`${relative}: self-directed brief 전용 repository artifact가 있으면 안 됩니다: ${candidate}`);
      }
    }
  }

  if (!await exists(path.join(repositoryRoot, "exercises/collaboration-board/reference"))) {
    errors.push("collaboration-board의 canonical reference 경로가 없습니다: exercises/collaboration-board/reference");
  }
  if (await exists(path.join(repositoryRoot, "projects/collaboration-board"))) {
    errors.push("legacy collaboration reference 경로가 남아 있습니다: projects/collaboration-board");
  }
  errors.push(...validateCollaborationRunnerSource(entries.get("scripts/verify-collaboration-postgresql.mjs") ?? ""));
  return errors;
}

export function validateCollaborationRunnerSource(source) {
  const errors = [];
  const canonical = 'path.join(root, "exercises", "collaboration-board", "reference")';
  if (!source.includes(canonical)) {
    errors.push("collaboration PostgreSQL runner가 canonical exercise-local reference를 사용하지 않습니다.");
  }
  if (/path\.join\(root,\s*["']projects["'],\s*["']collaboration-board["']\)/.test(source)) {
    errors.push("collaboration PostgreSQL runner에 constructed legacy projects 경로가 남아 있습니다.");
  }
  return errors;
}

async function validateWorkspaceContract(repositoryRoot, entries) {
  const errors = [];
  const gitignore = entries.get(".gitignore") ?? "";
  const activeRules = gitignore
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith("#"));
  const observedWorkRules = activeRules.filter((line) => /(?:^|\/)work\/?$/.test(line));
  if (!sameArray(observedWorkRules, exactWorkIgnoreRules)) {
    errors.push(
      `.gitignore learner work 규칙 불일치\n` +
      `  기대: ${exactWorkIgnoreRules.join(", ")}\n` +
      `  실제: ${observedWorkRules.join(", ") || "<none>"}`
    );
  }

  const packageSource = entries.get("package.json") ?? "{}";
  let manifest;
  try {
    manifest = JSON.parse(packageSource);
  } catch (error) {
    errors.push(`package.json을 읽을 수 없습니다: ${error instanceof Error ? error.message : String(error)}`);
    return errors;
  }
  if (manifest.scripts?.["workspace:create"] !== "node scripts/new-workspace.mjs") {
    errors.push("workspace:create는 repository-owned safe helper를 호출해야 합니다.");
  }
  if (manifest.scripts?.["check:workspace-helper"] !== "node scripts/test-new-workspace.mjs") {
    errors.push("safe workspace helper self-test script가 누락됐습니다.");
  }
  if (!manifest.scripts?.check?.includes("pnpm check:workspace-helper")) {
    errors.push("공식 check가 safe workspace helper self-test를 호출하지 않습니다.");
  }

  for (const relative of ["scripts/new-workspace.mjs", "scripts/test-new-workspace.mjs", "scripts/lib/exercise-paths.mjs"]) {
    if (!entries.has(relative)) errors.push(`safe workspace helper 파일 누락: ${relative}`);
  }
  const helper = entries.get("scripts/new-workspace.mjs") ?? "";
  for (const evidence of ["errorOnExist: true", "force: false", "EEXIST", "rejectSymlinks", "allowedSlugs", "exerciseSlugPattern", "assertContainedRealPath(exercisesRoot"]) {
    if (!helper.includes(evidence)) errors.push(`safe workspace helper 계약 단서 누락: ${evidence}`);
  }

  const verifierPathContracts = [
    "exercises/00-first-web-app/tests/verify.mjs",
    "exercises/02-browser/tests/verify.mjs",
    "exercises/03-react-nextjs/tests/run.mjs"
  ];
  for (const relative of verifierPathContracts) {
    const source = entries.get(relative) ?? "";
    for (const evidence of ["repositoryRoot", "resolveTarget", 'startsWith(`exercises${path.sep}`)']) {
      if (!source.includes(evidence)) errors.push(`${relative}: repository-root learner work 경로 해석 계약 누락 (${evidence})`);
    }
  }

  const learnerDocs = [
    "README.md",
    "docs/00-roadmap.md",
    "reference/command-reference.md",
    ...exerciseSlugs.map((slug) => `exercises/${slug}/README.md`),
    "exercises/collaboration-board/skeleton/README.md"
  ];
  for (const relative of learnerDocs) {
    const source = entries.get(relative);
    if (source === undefined) {
      errors.push(`learner workspace 문서 누락: ${relative}`);
      continue;
    }
    if (/\brm\s+-rf\s+(?:\.\/)?work\b/.test(source) || /\bcp\s+-R\s+skeleton\s+work\b/.test(source)) {
      errors.push(`${relative}: destructive skeleton copy workflow가 남아 있습니다.`);
    }
  }
  for (const slug of exerciseSlugs) {
    const relative = `exercises/${slug}/README.md`;
    if (!(entries.get(relative) ?? "").includes(`pnpm workspace:create ${slug}`)) {
      errors.push(`${relative}: canonical safe workspace 명령 누락`);
    }
  }

  return errors;
}

export function validateLegacyPathEntries(entries) {
  const errors = [];
  for (const entry of entries) {
    if (learningContractInfrastructure.has(entry.path)) continue;
    if (derivedPatchPattern.test(entry.path)) continue;
    if (entry.path === "projects/collaboration-board" || entry.path.startsWith("projects/collaboration-board/")) {
      errors.push(`legacy collaboration path가 남아 있습니다: ${entry.path}`);
    }
    if (entry.source.includes("projects/collaboration-board")) {
      errors.push(`legacy collaboration path 참조가 남아 있습니다: ${entry.path}`);
    }
  }
  return errors;
}

export function validateAnnotationEntries(entries, indexes) {
  const errors = [];
  const anchors = new Map(exerciseSlugs.map((slug) => [slug, new Map()]));

  for (const entry of entries) {
    const relative = entry.path.replaceAll(path.sep, "/");
    for (const match of entry.source.matchAll(markerPattern)) {
      const label = match[1].trim();
      const scopeMatch = /^exercises\/([^/]+)\/(.+)$/.exec(relative);
      const scope = scopeMatch?.[1];
      const rest = scopeMatch?.[2] ?? "";

      if (!canonicalLabelPattern.test(label)) {
        if (/^0-[0-9]+$/.test(label)) {
          errors.push(`${relative}: Implementation 0-M은 허용되지 않습니다 (${label}).`);
        } else {
          errors.push(`${relative}: 잘못된 Implementation label (${label}).`);
        }
        continue;
      }
      if (!scope || !exerciseSlugs.includes(scope)) {
        errors.push(`${relative}: Implementation anchor가 exercise scope 밖에 있습니다 (${label}).`);
        continue;
      }

      const allowedRoot = rest === "README.md" || rest.startsWith("reference/");
      if (!allowedRoot || forbiddenAnnotationPath(relative)) {
        errors.push(`${relative}: Implementation anchor를 둘 수 없는 경로입니다 (${label}).`);
      }
      if (testLikePath(relative) && !testAnnotationAllowlist.has(relative)) {
        errors.push(`${relative}: learner-authored test allowlist 밖의 annotation입니다 (${label}).`);
      }

      const scopeAnchors = anchors.get(scope);
      const locations = scopeAnchors.get(label) ?? [];
      locations.push(relative);
      scopeAnchors.set(label, locations);
    }
  }

  for (const slug of exerciseSlugs) {
    const rows = indexes.get(slug);
    if (!rows) {
      errors.push(`${slug}: Implementation index가 없습니다.`);
      continue;
    }
    errors.push(...validateIndexRows(slug, rows));

    const expected = new Set(rows.map((row) => row.label));
    const observed = anchors.get(slug) ?? new Map();
    for (const [label, locations] of observed) {
      if (locations.length !== 1) {
        errors.push(`${slug}: [Implementation ${label}] authoritative anchor가 ${locations.length}개입니다: ${locations.join(", ")}`);
      }
      if (!expected.has(label)) {
        errors.push(`${slug}: README index에 없는 Implementation anchor입니다 (${label}).`);
      }
    }
    for (const label of expected) {
      if (!observed.has(label)) errors.push(`${slug}: [Implementation ${label}] authoritative anchor가 없습니다.`);
    }
  }

  return errors;
}

export function validateIndexRows(scope, rows) {
  const errors = [];
  const labels = rows.map((row) => row.label);
  const unique = new Set(labels);
  if (unique.size !== labels.length) errors.push(`${scope}: Implementation index label이 중복됩니다.`);

  for (const label of labels) {
    if (!canonicalLabelPattern.test(label)) {
      if (/^0-[0-9]+$/.test(label)) errors.push(`${scope}: Implementation 0-M은 허용되지 않습니다 (${label}).`);
      else errors.push(`${scope}: 잘못된 Implementation index label (${label}).`);
    }
  }
  if (labels.includes("0") && labels[0] !== "0") errors.push(`${scope}: Implementation 0은 index의 첫 단계여야 합니다.`);
  const zeroRow = rows.find((row) => row.label === "0");
  const expectsZero = implementationZeroScopes.has(scope);
  if (expectsZero && !zeroRow) errors.push(`${scope}: 실제 package/framework bootstrap을 설명하는 Implementation 0이 필요합니다.`);
  if (!expectsZero && zeroRow) errors.push(`${scope}: 실제 application bootstrap이 없으므로 Implementation 0을 둘 수 없습니다.`);
  if (zeroRow) {
    const source = zeroRow.line ?? "";
    const bootstrapEvidence = /(?:pnpm\s+install|corepack\s+enable|package\.json|workspace|framework|dependency|의존성)/i;
    const ordinaryOnly = /`(?:cd|mkdir|touch|cp|mv|rm|pwd|ls)(?:\s+[^`]*)?`/g;
    if (!bootstrapEvidence.test(source)) {
      errors.push(`${scope}: Implementation 0은 project/dependency/framework bootstrap 근거를 포함해야 합니다.`);
    }
    const stripped = source.replace(ordinaryOnly, "");
    if (!bootstrapEvidence.test(stripped)) {
      errors.push(`${scope}: 일반 shell/filesystem 명령만 Implementation 0으로 둘 수 없습니다.`);
    }
  }

  const top = labels
    .filter((label) => /^[1-9][0-9]*$/.test(label))
    .map(Number)
    .sort((left, right) => left - right);
  if (top.length === 0) {
    errors.push(`${scope}: top-level Implementation 단계가 없습니다.`);
  } else {
    const expectedTop = Array.from({ length: top.at(-1) }, (_, index) => index + 1);
    if (!sameArray(top, expectedTop)) errors.push(`${scope}: top-level Implementation 번호가 1부터 gap 없이 이어지지 않습니다.`);
  }

  const childMap = new Map();
  for (const label of labels) {
    const match = /^([1-9][0-9]*)-([1-9][0-9]*)$/.exec(label);
    if (!match) continue;
    const parent = Number(match[1]);
    const child = Number(match[2]);
    if (!top.includes(parent)) errors.push(`${scope}: parent 없는 substep입니다 (${label}).`);
    const children = childMap.get(parent) ?? [];
    children.push(child);
    childMap.set(parent, children);
  }
  for (const [parent, children] of childMap) {
    children.sort((left, right) => left - right);
    const expectedChildren = Array.from({ length: children.at(-1) }, (_, index) => index + 1);
    if (!sameArray(children, expectedChildren)) {
      errors.push(`${scope}: Implementation ${parent} substep이 1부터 gap 없이 이어지지 않습니다.`);
    }
  }

  const expectedOrder = labels.includes("0") ? ["0"] : [];
  for (const parent of top) {
    expectedOrder.push(String(parent));
    for (const child of (childMap.get(parent) ?? []).sort((left, right) => left - right)) {
      expectedOrder.push(`${parent}-${child}`);
    }
  }
  if (canonicalLabelsOnly(labels) && !sameArray(labels, expectedOrder)) {
    errors.push(`${scope}: Implementation index가 권장 construction order대로 정렬되지 않았습니다.`);
  }
  return errors;
}

function forbiddenAnnotationPath(relative) {
  if (derivedPatchPattern.test(relative)) return true;
  if (/(?:^|\/)(?:skeleton|checks|fixtures|patches|specs|walkthrough-base|work)(?:\/|$)/.test(relative)) return true;
  if (/(?:^|\/)(?:node_modules|\.next|coverage|dist|build|playwright-report|test-results)(?:\/|$)/.test(relative)) return true;
  return /(?:^|\/)(?:pnpm-lock\.yaml|package-lock\.json|yarn\.lock|bun\.lockb?|next-env\.d\.ts)$/.test(relative);
}

function testLikePath(relative) {
  return /(?:^|\/)(?:tests?)(?:\/|$)/.test(relative) ||
    /\.(?:test|spec)\.[cm]?[jt]sx?$/.test(relative) ||
    /(?:^|\/)(?:playwright|vitest)\.config\.[cm]?[jt]s$/.test(relative);
}

function implementationRows(section) {
  const rows = [];
  for (const line of section.split(/\r?\n/)) {
    if (!line.trim().startsWith("|")) continue;
    const cells = markdownCells(line);
    if (cells.length < 3) continue;
    const first = cells[0];
    const exact = /^\[Implementation ([^\]]+)\]$/.exec(first);
    const label = exact?.[1]?.trim() ?? (/^(?:0(?:-[0-9]+)?|[1-9][0-9]*(?:-[0-9]+)?)$/.test(first) ? first : undefined);
    if (label !== undefined) rows.push({ label, line });
  }
  return rows;
}

function markdownSection(source, heading) {
  const escaped = heading.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = new RegExp(`^## ${escaped}\\s*$`, "m").exec(source);
  if (!match) return undefined;
  const start = match.index + match[0].length;
  const tail = source.slice(start);
  const next = /^##\s+/m.exec(tail);
  return next ? tail.slice(0, next.index) : tail;
}

function markdownTable(section) {
  const lines = section.split(/\r?\n/).filter((line) => line.trim().startsWith("|"));
  if (lines.length < 2) return { header: [], rows: [] };
  return { header: markdownCells(lines[0]), rows: lines.slice(2).map(markdownCells) };
}

function markdownCells(line) {
  const trimmed = line.trim().replace(/^\|/, "").replace(/\|$/, "");
  return trimmed.split("|").map((cell) => cell.trim());
}

async function collectRepositoryEntries(repositoryRoot) {
  const result = spawnSync("git", ["ls-files", "--cached", "--others", "--exclude-standard", "-z"], {
    cwd: repositoryRoot,
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024
  });
  if (result.status !== 0) throw new Error(`repository file 목록을 읽지 못했습니다.\n${result.stderr}`);

  const entries = [];
  const files = [...new Set(result.stdout.split("\0").filter(Boolean))].sort();
  for (const relative of files) {
    const target = path.join(repositoryRoot, relative);
    if (!await exists(target)) continue;
    const buffer = await readFile(target);
    if (buffer.includes(0)) continue;
    entries.push({ path: relative.replaceAll(path.sep, "/"), source: buffer.toString("utf8") });
  }
  return entries;
}

async function exists(target) {
  try {
    await access(target);
    return true;
  } catch {
    return false;
  }
}

function canonicalLabelsOnly(labels) {
  return labels.every((label) => canonicalLabelPattern.test(label));
}

function sameArray(left, right) {
  return left.length === right.length && left.every((value, index) => value === right[index]);
}
