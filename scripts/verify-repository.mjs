import { lstat, readFile, readdir, stat } from "node:fs/promises";
import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const defaultRepositoryRoot = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const learningRootOption = process.argv.indexOf("--learning-contract-root");
if (learningRootOption >= 0 && !process.argv[learningRootOption + 1]) {
  throw new Error("--learning-contract-root에는 검사할 repository 경로가 필요합니다.");
}
const learningContractOnly = learningRootOption >= 0;
const repositoryRoot = learningContractOnly
  ? path.resolve(process.argv[learningRootOption + 1])
  : defaultRepositoryRoot;
const failures = [];
const generatedNextEnvironmentDeclaration =
  "exercises/project-catalog/reference/next-env.d.ts";

const requiredPaths = [
  ".gitignore",
  ".nvmrc",
  "README.md",
  "CONTRIBUTING.md",
  "Makefile",
  "prepare.sh",
  "verify.sh",
  "package.json",
  "pnpm-lock.yaml",
  "pnpm-workspace.yaml",
  "docs/00-roadmap-and-prerequisites.md",
  "docs/01-project-onboarding.md",
  "docs/02-ui-and-state-architecture.md",
  "docs/03-nextjs-data-effects-and-concurrency.md",
  "docs/04-testing-accessibility-and-performance.md",
  "docs/05-production-runtime-contract.md",
  "docs/90-practical-checklist.md",
  "exercises/project-catalog/README.md",
  "exercises/project-catalog/specs/01-project-onboarding.md",
  "exercises/project-catalog/specs/02-ui-state-architecture.md",
  "exercises/project-catalog/specs/03-data-effects-concurrency.md",
  "exercises/project-catalog/specs/04-testing-accessibility-performance.md",
  "exercises/project-catalog/specs/05-production-runtime-contract.md",
  "exercises/project-catalog/reference/package.json",
  "exercises/project-catalog/reference/performance-budget.json",
  "exercises/project-catalog/reference/playwright.config.ts",
  "exercises/project-catalog/reference/scripts/run-playwright.mjs",
  "exercises/project-catalog/reference/scripts/smoke-production.mjs",
  "exercises/project-catalog/skeleton/README.md",
  "exercises/project-catalog/create-workspace.mjs",
  "exercises/project-catalog/check-workspace.mjs",
  "exercises/project-catalog/check-stage-markers.mjs",
  "scripts/clean-generated.mjs",
  "scripts/snapshot-repository.mjs",
  "scripts/verify-repository.mjs",
  "scripts/verify-skeleton.mjs",
  "scripts/verify-test-quality.mjs"
];

const obsoletePaths = [
  "prepare-verify.sh",
  "make-out.txt",
  "docs/00-browser-and-react-foundations.md",
  "docs/02-ui-architecture.md",
  "docs/03-state-data-effects.md",
  "docs/04-testing-performance-deployment.md",
  "reference",
  "exercises/project-catalog/reference/tests/e2e/catalog.spec.ts"
];

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

if (learningContractOnly) {
  await verifyLearningMap();
  await verifyImplementationAnnotations();
} else {
  await verifyPaths();
  await verifyExecutableScripts();
  await verifyPackageContracts();
  await verifyVersions();
  await verifyStageMarkers();
  await verifyLearningMap();
  await verifyImplementationAnnotations();
  await verifyMarkdownLinks();
  await verifyTextHygiene();
  await verifyNextEnvironmentDeclarationContract();
  await verifyTrackedGeneratedOutputIsAbsent();
}

if (failures.length > 0) {
  console.error("저장소 계약 검증에 실패했습니다.");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log(
  learningContractOnly
    ? "README 학습 지도와 project-wide 구현 순서 계약을 확인했습니다."
    : "저장소 구조, 학습 지도, 구현 순서, 문서 링크, 단계 계약, 버전과 생성물 경계를 확인했습니다."
);

async function verifyPaths() {
  for (const relative of requiredPaths) {
    if (!(await exists(path.join(repositoryRoot, relative)))) {
      failures.push(`필수 경로가 없습니다: ${relative}`);
    }
  }

  for (const relative of obsoletePaths) {
    if (await exists(path.join(repositoryRoot, relative))) {
      failures.push(`대체된 경로가 남아 있습니다: ${relative}`);
    }
  }
}

async function verifyExecutableScripts() {
  if (process.platform === "win32") return;
  for (const relative of ["prepare.sh", "verify.sh"]) {
    const target = path.join(repositoryRoot, relative);
    if (!(await exists(target))) continue;
    const mode = (await stat(target)).mode;
    if ((mode & 0o111) === 0) failures.push(`실행 권한이 없습니다: ${relative}`);
  }
}

async function verifyPackageContracts() {
  const rootPackage = await readJson("package.json");
  const referencePackage = await readJson("exercises/project-catalog/reference/package.json");
  if (!rootPackage || !referencePackage) return;

  const rootScripts = [
    "check:repository",
    "check:reference",
    "check:skeleton",
    "check:test-quality",
    "check",
    "build",
    "test:e2e",
    "smoke",
    "verify",
    "exercise:create",
    "exercise:verify:01",
    "exercise:verify:02",
    "exercise:verify:03",
    "exercise:verify:04",
    "exercise:verify:05",
    "exercise:verify",
    "clean"
  ];
  for (const name of rootScripts) {
    if (typeof rootPackage.scripts?.[name] !== "string") {
      failures.push(`루트 package.json script가 없습니다: ${name}`);
    }
  }
  if (Object.prototype.hasOwnProperty.call(rootPackage.scripts ?? {}, "prepare")) {
    failures.push("package.json에 lifecycle prepare script를 두면 ./prepare.sh의 pnpm install이 재귀 실행될 수 있습니다.");
  }

  const makefile = await readText("Makefile");
  if (makefile && !/check:\n\tpnpm check/u.test(makefile)) {
    failures.push("Makefile check target이 pnpm check를 실행하지 않습니다.");
  }
  if (makefile && !/verify:\n\tpnpm verify/u.test(makefile)) {
    failures.push("Makefile verify target이 pnpm verify를 실행하지 않습니다.");
  }

  const readme = await readText("README.md");
  if (readme) {
    const prepareIndex = readme.indexOf("./prepare.sh");
    const verifyIndex = readme.indexOf("./verify.sh");
    if (prepareIndex < 0 || verifyIndex < 0 || prepareIndex > verifyIndex) {
      failures.push("README가 ./prepare.sh → ./verify.sh 실행 순서를 안내하지 않습니다.");
    }
  }

  const referenceScripts = [
    "typecheck",
    "test",
    "test:stage:01",
    "test:stage:02",
    "test:stage:03",
    "test:stage:04",
    "build",
    "test:e2e:stage:03",
    "test:e2e:stage:04",
    "test:e2e",
    "smoke"
  ];
  for (const name of referenceScripts) {
    if (typeof referencePackage.scripts?.[name] !== "string") {
      failures.push(`reference package.json script가 없습니다: ${name}`);
    }
  }
  const expectedE2EScripts = {
    "test:e2e:stage:03": "node scripts/run-playwright.mjs tests/e2e/03-data-concurrency.spec.ts",
    "test:e2e:stage:04":
      "node scripts/run-playwright.mjs tests/e2e/03-data-concurrency.spec.ts tests/e2e/04-accessibility-performance.spec.ts",
    "test:e2e": "node scripts/run-playwright.mjs"
  };
  for (const [name, expected] of Object.entries(expectedE2EScripts)) {
    const actual = referencePackage.scripts?.[name];
    if (actual !== expected) {
      failures.push(`${name}의 고유 port 실행 계약이 예상과 다릅니다: ${actual ?? "<missing>"}`);
    }
  }

  const playwrightRunner = await readText(
    "exercises/project-catalog/reference/scripts/run-playwright.mjs"
  );
  if (
    playwrightRunner &&
    (!playwrightRunner.includes("CATALOG_E2E_PORT") ||
      !playwrightRunner.includes("server.listen(0, host"))
  ) {
    failures.push("Playwright 실행기가 임시 port를 할당해 CATALOG_E2E_PORT로 전달하지 않습니다.");
  }

  const playwrightConfig = await readText("exercises/project-catalog/reference/playwright.config.ts");
  if (playwrightConfig && !playwrightConfig.includes("CATALOG_E2E_PORT")) {
    failures.push("Playwright 설정이 동적으로 할당한 CATALOG_E2E_PORT를 사용하지 않습니다.");
  }
  if (playwrightConfig && /\b30000\b/u.test(playwrightConfig)) {
    failures.push("Playwright 설정에 고정 E2E port 30000이 남아 있습니다.");
  }

  const workspace = await readText("pnpm-workspace.yaml");
  if (workspace && !workspace.includes("exercises/project-catalog/reference")) {
    failures.push("pnpm workspace가 project-catalog reference를 포함하지 않습니다.");
  }
}

async function verifyVersions() {
  const rootPackage = await readJson("package.json");
  const referencePackage = await readJson("exercises/project-catalog/reference/package.json");
  const nvm = (await readText(".nvmrc"))?.trim();
  const roadmap = await readText("docs/00-roadmap-and-prerequisites.md");
  if (!rootPackage || !referencePackage || roadmap === null) return;

  if (nvm !== "24.19.0") failures.push(`.nvmrc 기준이 24.19.0이 아닙니다: ${nvm ?? "<missing>"}`);
  if (rootPackage.packageManager !== "pnpm@10.32.1") {
    failures.push(`packageManager 기준이 pnpm@10.32.1이 아닙니다: ${rootPackage.packageManager ?? "<missing>"}`);
  }
  if (rootPackage.engines?.node !== ">=24.19.0 <25") {
    failures.push(`Node.js engine 범위가 예상과 다릅니다: ${rootPackage.engines?.node ?? "<missing>"}`);
  }

  const expectedDependencies = {
    next: ["dependencies", "16.3.0"],
    react: ["dependencies", "19.2.8"],
    "react-dom": ["dependencies", "19.2.8"],
    typescript: ["devDependencies", "5.9.3"],
    "@playwright/test": ["devDependencies", "1.61.1"],
    vitest: ["devDependencies", "3.2.7"]
  };
  for (const [name, [group, expected]] of Object.entries(expectedDependencies)) {
    const actual = referencePackage[group]?.[name];
    if (actual !== expected) failures.push(`${name} 버전이 ${expected}이 아닙니다: ${actual ?? "<missing>"}`);
    if (!roadmap.includes(expected)) failures.push(`roadmap에 ${name} 버전 ${expected}가 기록되지 않았습니다.`);
  }
}

async function verifyStageMarkers() {
  const skeletonRoot = path.join(repositoryRoot, "exercises/project-catalog/skeleton");
  const referenceRoot = path.join(repositoryRoot, "exercises/project-catalog/reference");
  const skeletonText = await concatenateTextFiles(skeletonRoot);
  const referenceText = await concatenateTextFiles(referenceRoot, { skipGenerated: true });

  for (const stage of ["01", "02", "03", "04", "05"]) {
    if (!skeletonText.includes(`TODO(stage-${stage})`)) {
      failures.push(`skeleton에 Stage ${stage} 구현 표시가 없습니다.`);
    }
  }
  const leaked = referenceText.match(/TODO\(stage-0[1-5]\)/g) ?? [];
  if (leaked.length > 0) failures.push(`reference에 미완성 단계 표시가 남아 있습니다: ${[...new Set(leaked)].join(", ")}`);
}

async function verifyLearningMap() {
  const readme = await readText("README.md");
  if (readme === null) {
    failures.push("README.md가 없어 학습 순서를 검증할 수 없습니다.");
    return;
  }

  const section = markdownSection(readme, "학습 순서");
  if (section === null) {
    failures.push("README에 canonical 학습 순서 section이 없습니다.");
    return;
  }

  const rows = markdownTableRows(section);
  const expectedRows = [
    {
      order: "0",
      doc: "docs/00-roadmap-and-prerequisites.md",
      direct: ["./prepare.sh", "pnpm exercise:create"],
      edit: ["—"],
      verify: ["pnpm check:repository"],
      next: ["pnpm exercise:verify:01", "docs/01-project-onboarding.md"]
    },
    {
      order: "1",
      doc: "docs/01-project-onboarding.md",
      direct: ["exercises/project-catalog/specs/01-project-onboarding.md", "Stage 01"],
      edit: ["exercises/project-catalog/workspace/app/page.tsx"],
      verify: ["pnpm exercise:verify:01"],
      next: ["exercises/project-catalog/reference/app/page.tsx", "Page", "Stage 02"]
    },
    {
      order: "2",
      doc: "docs/02-ui-and-state-architecture.md",
      direct: ["exercises/project-catalog/specs/02-ui-state-architecture.md", "Stage 02"],
      edit: [
        "exercises/project-catalog/workspace/lib/catalog-contract.ts",
        "exercises/project-catalog/workspace/lib/catalog-model.ts"
      ],
      verify: ["pnpm exercise:verify:02"],
      next: ["exercises/project-catalog/reference/lib/", "Stage 03"]
    },
    {
      order: "3",
      doc: "docs/03-nextjs-data-effects-and-concurrency.md",
      direct: ["exercises/project-catalog/specs/03-data-effects-concurrency.md", "Stage 03"],
      edit: [
        "exercises/project-catalog/workspace/lib/request-coordinator.ts",
        "exercises/project-catalog/workspace/app/project-catalog.tsx"
      ],
      verify: ["pnpm exercise:verify:03"],
      next: [
        "exercises/project-catalog/reference/lib/request-coordinator.ts",
        "runSearch",
        "rename",
        "ProjectEditor",
        "Stage 04"
      ]
    },
    {
      order: "4",
      doc: "docs/04-testing-accessibility-and-performance.md",
      direct: ["exercises/project-catalog/specs/04-testing-accessibility-performance.md", "Stage 04"],
      edit: [
        "exercises/project-catalog/workspace/app/project-catalog.tsx",
        "exercises/project-catalog/workspace/app/styles.css"
      ],
      verify: ["pnpm exercise:verify:04"],
      next: [
        "exercises/project-catalog/reference/app/project-catalog.tsx",
        "exercises/project-catalog/reference/app/styles.css",
        "ProjectEditor",
        "Stage 05"
      ]
    },
    {
      order: "5",
      doc: "docs/05-production-runtime-contract.md",
      direct: ["exercises/project-catalog/specs/05-production-runtime-contract.md", "Stage 05"],
      edit: ["exercises/project-catalog/workspace/app/api/health/route.ts"],
      verify: ["pnpm exercise:verify:05"],
      next: [
        "exercises/project-catalog/reference/app/api/health/route.ts",
        "GET",
        "전체 검증"
      ]
    },
    {
      order: "90",
      doc: "docs/90-practical-checklist.md",
      direct: ["Stage 01–05"],
      edit: ["—"],
      verify: ["pnpm exercise:verify"],
      next: ["guide-web-infrastructure"]
    }
  ];

  if (rows.some((row) => row.length !== 7)) {
    failures.push("README 학습 순서 표는 순서·문서·관찰 예제·직접 수행·수정 위치·검증·완료 뒤 비교·다음의 7개 열이어야 합니다.");
  }

  const dataRows = rows.filter((row) => expectedRows.some((expected) => expected.order === row[0]));
  if (rows.length !== expectedRows.length) {
    failures.push(`README 학습 순서 표에 예상하지 않은 행이 있습니다: ${rows.length}/${expectedRows.length}`);
  }
  if (dataRows.length !== expectedRows.length) {
    failures.push(`README 학습 순서 행 수가 예상과 다릅니다: ${dataRows.length}/${expectedRows.length}`);
  }
  const expectedOrder = expectedRows.map((row) => row.order);
  const actualOrder = dataRows.map((row) => row[0]);
  if (actualOrder.join(",") !== expectedOrder.join(",")) {
    failures.push(`README 학습 순서 행이 물리적 순서와 다릅니다: ${actualOrder.join(",")}`);
  }

  for (const expected of expectedRows) {
    const matches = dataRows.filter((row) => row[0] === expected.order);
    if (matches.length !== 1) {
      failures.push(`README 학습 순서 ${expected.order}번 행은 정확히 하나여야 합니다.`);
      continue;
    }
    const row = matches[0];
    if (!row[1].includes(expected.doc)) {
      failures.push(`README 학습 순서 ${expected.order}번 문서가 다릅니다: ${expected.doc}`);
    }
    if (row[2] !== "—") {
      failures.push(`README 학습 순서 ${expected.order}번은 별도 관찰 예제가 없음을 —로 표시해야 합니다.`);
    }
    verifyCellTokens(expected.order, "직접 수행", row[3], expected.direct);
    verifyCellTokens(expected.order, "수정 위치", row[4], expected.edit);
    verifyCellTokens(expected.order, "검증", row[5], expected.verify);
    verifyCellTokens(expected.order, "완료 뒤 비교·다음", row[6], expected.next);
  }
}

async function verifyImplementationAnnotations() {
  const scopeReadmePath = "exercises/project-catalog/README.md";
  const annotationRoot = "exercises/project-catalog/reference/";
  const requiredAnnotatedFiles = new Set([
    `${annotationRoot}app/page.tsx`,
    `${annotationRoot}app/project-catalog.tsx`,
    `${annotationRoot}app/styles.css`,
    `${annotationRoot}app/api/health/route.ts`,
    `${annotationRoot}lib/catalog-contract.ts`,
    `${annotationRoot}lib/catalog-model.ts`,
    `${annotationRoot}lib/request-coordinator.ts`
  ]);
  const scopeReadme = await readText(scopeReadmePath);
  const declaredAnchors = new Map();
  const validLabel = /^[1-9]\d*(?:-[1-9]\d*)?$/u;

  if (scopeReadme === null) {
    failures.push(`${scopeReadmePath}가 없어 권장 구현 순서 index를 검증할 수 없습니다.`);
  } else {
    const indexSection = markdownSection(scopeReadme, "권장 구현 순서");
    if (indexSection === null) {
      failures.push(`${scopeReadmePath}에 권장 구현 순서 section이 없습니다.`);
    } else {
      const indexRows = markdownTableRows(indexSection).filter((row) => validLabel.test(row[0] ?? ""));
      for (const row of indexRows) {
        const label = row[0];
        if (row.length !== 3 || row[1].length === 0 || row[2].length === 0) {
          failures.push(`README 구현 순서 ${label}번은 파일·symbol과 책임을 모두 설명해야 합니다.`);
        }
        if (declaredAnchors.has(label)) {
          failures.push(`README 구현 순서 ${label}번이 중복되었습니다.`);
          continue;
        }
        const declaredPath = row[1].match(/`([^`]+)`/u)?.[1];
        if (!declaredPath || !isAllowedAnnotationPath(declaredPath)) {
          failures.push(`README 구현 순서 ${label}번의 source 경로가 허용 범위가 아닙니다: ${declaredPath ?? "<missing>"}`);
          continue;
        }
        declaredAnchors.set(label, `${annotationRoot}${declaredPath}`);
      }

      const actualIndex = [...declaredAnchors.keys()];
      const sortedIndex = [...actualIndex].sort(compareImplementationLabels);
      if (actualIndex.join(",") !== sortedIndex.join(",")) {
        failures.push(`README 구현 순서 index가 recommended construction order와 다릅니다: ${actualIndex.join(",")}`);
      }
      if (declaredAnchors.size === 0) {
        failures.push("README 권장 구현 순서에 source anchor가 없습니다.");
      }
    }
  }

  const extensions = new Set([".md", ".mjs", ".js", ".ts", ".tsx", ".css", ".json", ".yaml", ".yml", ".sh"]);
  const files = await collectFiles(repositoryRoot, {
    extensions,
    skipGenerated: true,
    skipWorkspace: true
  });
  const occurrences = new Map();
  const markerPrefix = "[" + "Implementation ";
  const broadMarker = new RegExp("\\[" + "Implementation " + "([^\\]\\n]+)\\]", "gu");

  for (const file of files) {
    const content = await readFile(file, "utf8");
    const lines = content.split("\n");
    for (let lineIndex = 0; lineIndex < lines.length; lineIndex += 1) {
      for (const match of lines[lineIndex].matchAll(broadMarker)) {
        const label = match[1];
        const location = `${relative(file)}:${lineIndex + 1}`;
        if (!validLabel.test(label)) {
          failures.push(`허용되지 않은 Implementation marker입니다: ${location} [${label}]`);
          continue;
        }
        const entries = occurrences.get(label) ?? [];
        entries.push({ file: relative(file), line: lineIndex + 1, text: lines[lineIndex].trim() });
        occurrences.set(label, entries);
      }
    }
  }

  for (const [label, expectedFile] of declaredAnchors) {
    const entries = occurrences.get(label) ?? [];
    if (entries.length !== 1) {
      failures.push(`Implementation ${label} anchor는 scope 전체에서 정확히 한 번이어야 합니다: ${entries.length}`);
      continue;
    }
    if (entries[0].file !== expectedFile) {
      failures.push(`Implementation ${label} anchor 위치가 다릅니다: ${entries[0].file} (expected ${expectedFile})`);
    }
    if (!isAllowedAnnotationFile(entries[0].file)) {
      failures.push(`Implementation ${label} anchor가 reference production source 밖에 있습니다: ${entries[0].file}`);
    }
    if (
      !entries[0].text.startsWith(`// ${markerPrefix}`) &&
      !entries[0].text.startsWith(`/* ${markerPrefix}`)
    ) {
      failures.push(`Implementation ${label} anchor는 source comment여야 합니다: ${entries[0].file}:${entries[0].line}`);
    }
  }

  for (const [label, entries] of occurrences) {
    if (!declaredAnchors.has(label)) {
      for (const entry of entries) {
        failures.push(`scope 밖 또는 금지된 Implementation ${label} anchor입니다: ${entry.file}:${entry.line}`);
      }
    }
  }

  verifyAnnotationContinuity(occurrences);

  const annotatedFiles = new Set(
    [...occurrences.values()].flat().map((entry) => entry.file).filter(isAllowedAnnotationFile)
  );
  for (const requiredFile of requiredAnnotatedFiles) {
    if (!annotatedFiles.has(requiredFile)) {
      failures.push(`완성 learner source에 project-wide Implementation anchor가 없습니다: ${requiredFile}`);
    }
  }
}

function isAllowedAnnotationPath(declaredPath) {
  if (path.isAbsolute(declaredPath) || declaredPath.includes("\\")) return false;
  const normalized = path.posix.normalize(declaredPath);
  if (normalized !== declaredPath || normalized.startsWith("../")) return false;
  if (!/^(?:app|lib)\//u.test(normalized)) return false;
  return /\.(?:ts|tsx|css)$/u.test(normalized);
}

function isAllowedAnnotationFile(file) {
  if (!file.startsWith("exercises/project-catalog/reference/")) return false;
  return isAllowedAnnotationPath(file.slice("exercises/project-catalog/reference/".length));
}

function compareImplementationLabels(left, right) {
  const leftParts = left.split("-").map(Number);
  const rightParts = right.split("-").map(Number);
  return leftParts[0] - rightParts[0] || (leftParts[1] ?? 0) - (rightParts[1] ?? 0);
}

function verifyCellTokens(order, name, cell, tokens) {
  for (const token of tokens) {
    if (!cell.includes(token)) failures.push(`README 학습 순서 ${order}번 ${name}에 ${token}이(가) 없습니다.`);
  }
}

function verifyAnnotationContinuity(occurrences) {
  const labels = [...occurrences.keys()].filter((label) => /^(?:0|[1-9]\d*(?:-[1-9]\d*)?)$/u.test(label));
  const topLevels = labels
    .filter((label) => label !== "0" && !label.includes("-"))
    .map(Number)
    .sort((left, right) => left - right);
  const expectedTopLevels = Array.from({ length: topLevels.at(-1) ?? 0 }, (_, index) => index + 1);
  if (topLevels.join(",") !== expectedTopLevels.join(",")) {
    failures.push(`Implementation top-level 번호는 1부터 연속해야 합니다: ${topLevels.join(",")}`);
  }
  if ((occurrences.get("0") ?? []).length > 1) {
    failures.push("Implementation 0은 scope당 최대 한 번만 허용됩니다.");
  }

  const children = new Map();
  for (const label of labels.filter((candidate) => candidate.includes("-"))) {
    const [parent, child] = label.split("-").map(Number);
    if (!occurrences.has(String(parent))) {
      failures.push(`Implementation ${label}의 parent ${parent} anchor가 없습니다.`);
    }
    const values = children.get(parent) ?? [];
    values.push(child);
    children.set(parent, values);
  }
  for (const [parent, values] of children) {
    values.sort((left, right) => left - right);
    const expected = Array.from({ length: values.at(-1) ?? 0 }, (_, index) => index + 1);
    if (values.join(",") !== expected.join(",")) {
      failures.push(`Implementation ${parent} substep은 1부터 연속해야 합니다: ${values.join(",")}`);
    }
  }
}

function markdownSection(content, heading) {
  const marker = `## ${heading}`;
  const start = content.indexOf(marker);
  if (start < 0) return null;
  const bodyStart = start + marker.length;
  const rest = content.slice(bodyStart);
  const next = rest.search(/^## /mu);
  return next < 0 ? rest : rest.slice(0, next);
}

function markdownTableRows(section) {
  const rows = [];
  for (const line of section.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed.startsWith("|") || !trimmed.endsWith("|")) continue;
    const cells = trimmed.slice(1, -1).split("|").map((cell) => cell.trim());
    if (cells.every((cell) => /^:?-+:?$/u.test(cell))) continue;
    if (cells[0] === "순서") continue;
    rows.push(cells);
  }
  return rows;
}

async function verifyMarkdownLinks() {
  const markdownFiles = await collectFiles(repositoryRoot, {
    extensions: new Set([".md"]),
    skipGenerated: true,
    skipWorkspace: true
  });

  for (const file of markdownFiles) {
    const content = stripFencedCode(await readFile(file, "utf8"));
    const linkPattern = /!?\[[^\]]*\]\(([^)]+)\)/g;
    for (const match of content.matchAll(linkPattern)) {
      let target = match[1].trim();
      if (target.startsWith("<") && target.endsWith(">")) target = target.slice(1, -1);
      else target = target.split(/\s+["']/u, 1)[0];
      if (!target || target.startsWith("#")) continue;
      if (/^(?:https?:|mailto:|tel:|data:|javascript:)/i.test(target)) continue;
      if (target.startsWith("/")) continue;

      target = target.split("#", 1)[0].split("?", 1)[0];
      if (!target) continue;
      try {
        target = decodeURIComponent(target);
      } catch {
        failures.push(`URL decode에 실패한 링크: ${relative(file)} -> ${match[1]}`);
        continue;
      }

      const resolved = path.resolve(path.dirname(file), target);
      if (!isInsideRepository(resolved)) {
        failures.push(`저장소 밖을 가리키는 상대 링크: ${relative(file)} -> ${match[1]}`);
        continue;
      }
      if (!(await exists(resolved))) failures.push(`깨진 상대 링크: ${relative(file)} -> ${match[1]}`);
    }
  }
}

async function verifyTextHygiene() {
  const extensions = new Set([".md", ".mjs", ".js", ".ts", ".tsx", ".css", ".json", ".yaml", ".yml", ".sh"]);
  const files = await collectFiles(repositoryRoot, {
    extensions,
    skipGenerated: true,
    skipWorkspace: true,
    skipFiles: new Set(["pnpm-lock.yaml"])
  });

  for (const file of files) {
    const content = await readFile(file, "utf8");
    if (content.includes("\0")) failures.push(`NUL 문자가 포함된 텍스트 파일: ${relative(file)}`);
    const lines = content.split("\n");
    for (let index = 0; index < lines.length; index += 1) {
      if (/[ \t]+$/u.test(lines[index])) {
        failures.push(`줄 끝 공백: ${relative(file)}:${index + 1}`);
        break;
      }
    }
  }
}

async function verifyNextEnvironmentDeclarationContract() {
  const gitignore = await readText(".gitignore");
  const ignored = gitignore
    ?.split("\n")
    .map((line) => line.trim())
    .includes(generatedNextEnvironmentDeclaration);
  if (!ignored) {
    failures.push(
      `${generatedNextEnvironmentDeclaration}가 .gitignore에 정확한 경로로 등록되지 않았습니다.`
    );
  }
}

async function verifyTrackedGeneratedOutputIsAbsent() {
  let tracked;
  try {
    tracked = execFileSync("git", ["ls-files", "-z"], {
      cwd: repositoryRoot,
      encoding: "utf8"
    })
      .split("\0")
      .filter(Boolean);
  } catch (error) {
    failures.push(`Git 추적 파일을 확인하지 못했습니다: ${error.message}`);
    return;
  }

  for (const file of tracked) {
    const parts = file.split("/");
    const basename = parts.at(-1) ?? file;
    const generatedDirectory = parts
      .slice(0, -1)
      .some((part) => generatedDirectoryNames.has(part) || part.startsWith(".workspace-"));
    const generatedFile =
      basename.endsWith(".tsbuildinfo") ||
      basename === ".eslintcache" ||
      basename.endsWith(".pid") ||
      file === generatedNextEnvironmentDeclaration;
    if (generatedDirectory || generatedFile) {
      failures.push(`Git이 생성물을 추적하고 있습니다: ${file}`);
    }
  }
}

async function readJson(relativePath) {
  const content = await readText(relativePath);
  if (content === null) return null;
  try {
    return JSON.parse(content);
  } catch (error) {
    failures.push(`JSON 파싱 실패: ${relativePath}: ${error.message}`);
    return null;
  }
}

async function readText(relativePath) {
  const target = path.join(repositoryRoot, relativePath);
  try {
    return await readFile(target, "utf8");
  } catch (error) {
    if (error?.code === "ENOENT") return null;
    throw error;
  }
}

async function concatenateTextFiles(root, options = {}) {
  if (!(await exists(root))) return "";
  const files = await collectFiles(root, {
    extensions: new Set([".md", ".mjs", ".js", ".ts", ".tsx", ".css", ".json"]),
    skipGenerated: options.skipGenerated ?? false,
    skipWorkspace: false
  });
  const chunks = [];
  for (const file of files) chunks.push(await readFile(file, "utf8"));
  return chunks.join("\n");
}

async function collectFiles(root, options) {
  const files = [];
  if (!(await exists(root))) return files;
  await walk(root, async (target, entry) => {
    if (!entry.isFile()) return;
    if (options.skipFiles?.has(path.basename(target))) return;
    if (options.extensions.has(path.extname(entry.name))) files.push(target);
  }, options);
  return files;
}

async function walk(root, visit, options = {}) {
  const entries = await readdir(root, { withFileTypes: true });
  for (const entry of entries) {
    const target = path.join(root, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === ".git" || entry.name === "node_modules") continue;
      if (options.skipWorkspace && entry.name === "workspace") continue;
      if (options.skipGenerated && (generatedDirectoryNames.has(entry.name) || entry.name.startsWith(".workspace-"))) {
        continue;
      }
      await visit(target, entry);
      await walk(target, visit, options);
    } else {
      await visit(target, entry);
    }
  }
}

function stripFencedCode(content) {
  return content.replace(/^```[\s\S]*?^```\s*$/gm, "");
}

function relative(target) {
  return path.relative(repositoryRoot, target) || ".";
}

function isInsideRepository(target) {
  const rel = path.relative(repositoryRoot, target);
  return rel === "" || (!rel.startsWith("..") && !path.isAbsolute(rel));
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
