import { lstat, readFile, readdir, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repositoryRoot = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const failures = [];

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

await verifyPaths();
await verifyExecutableScripts();
await verifyPackageContracts();
await verifyVersions();
await verifyStageMarkers();
await verifyMarkdownLinks();
await verifyTextHygiene();
await verifyGeneratedOutputIsAbsent();

if (failures.length > 0) {
  console.error("저장소 계약 검증에 실패했습니다.");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log("저장소 구조, 문서 링크, 단계 계약, 버전과 생성물 경계를 확인했습니다.");

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
  if (makefile && !/prepare:\n\t\.\/prepare\.sh/u.test(makefile)) {
    failures.push("Makefile prepare target이 ./prepare.sh를 실행하지 않습니다.");
  }
  if (makefile && !/verify:\n\t\.\/verify\.sh/u.test(makefile)) {
    failures.push("Makefile verify target이 ./verify.sh를 실행하지 않습니다.");
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
    "test:stage:05",
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
  for (const name of ["test:e2e:stage:03", "test:e2e:stage:04", "test:e2e"]) {
    const command = referencePackage.scripts?.[name];
    if (typeof command === "string" && !command.includes("scripts/run-playwright.mjs")) {
      failures.push(`${name}이 고유 port 실행기를 사용하지 않습니다.`);
    }
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

  if (nvm !== "22.16.0") failures.push(`.nvmrc 기준이 22.16.0이 아닙니다: ${nvm ?? "<missing>"}`);
  if (rootPackage.packageManager !== "pnpm@10.32.1") {
    failures.push(`packageManager 기준이 pnpm@10.32.1이 아닙니다: ${rootPackage.packageManager ?? "<missing>"}`);
  }
  if (rootPackage.engines?.node !== ">=22.16.0 <23") {
    failures.push(`Node.js engine 범위가 예상과 다릅니다: ${rootPackage.engines?.node ?? "<missing>"}`);
  }

  const expectedDependencies = {
    next: ["dependencies", "15.5.21"],
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

async function verifyGeneratedOutputIsAbsent() {
  const findings = [];
  await scan(repositoryRoot);
  for (const finding of findings) failures.push(`검증 시작 전에 생성물이 남아 있습니다: ${finding}`);

  async function scan(directory) {
    for (const entry of await readdir(directory, { withFileTypes: true })) {
      const target = path.join(directory, entry.name);
      if (entry.isDirectory()) {
        if (entry.name === ".git" || entry.name === "node_modules") continue;
        if (generatedDirectoryNames.has(entry.name) || entry.name.startsWith(".workspace-")) {
          findings.push(relative(target));
          continue;
        }
        await scan(target);
      } else if (
        entry.isFile() &&
        (entry.name.endsWith(".tsbuildinfo") || entry.name === ".eslintcache" || entry.name.endsWith(".pid"))
      ) {
        findings.push(relative(target));
      }
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
