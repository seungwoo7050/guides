import { access, readFile, readdir } from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const exerciseRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = path.resolve(exerciseRoot, "..", "..");
const postgresVerifier = path.join(repositoryRoot, "scripts", "verify-collaboration-postgresql.mjs");
const requireFromProject = createRequire(new URL("../../../projects/collaboration-board/package.json", import.meta.url));
const ts = requireFromProject("typescript");
const [workArgument = "work", stageArgument, ...flags] = process.argv.slice(2);
const stage = Number(stageArgument);
const structureOnly = flags.includes("--structure-only");

if (!Number.isInteger(stage) || stage < 1 || stage > 8) {
  fail("사용법: node checks/verify-work.mjs <work-directory> <1-8> [--structure-only]");
}

const workRoot = path.resolve(exerciseRoot, workArgument);
const relativeWork = path.relative(exerciseRoot, workRoot);
if (!relativeWork || relativeWork.startsWith("..") || path.isAbsolute(relativeWork)) {
  fail("work directory는 exercises/collaboration-board 아래에 있어야 합니다.");
}
if (["skeleton", "patches", "specs", "checks"].includes(relativeWork.split(path.sep)[0])) {
  fail("skeleton·명세·검사기를 직접 수정하지 말고 별도 work directory를 사용합니다.");
}

const errors = [];
const stageScript = `verify:${String(stage).padStart(2, "0")}`;
const canonicalTestFiles = [
  "apps/api/src/app.test.ts",
  "apps/api/src/config.test.ts"
];
const expectedStageScripts = new Map([
  [1, "pnpm typecheck && pnpm --filter @capstone/api test"],
  [2, "pnpm run verify:01 && pnpm --filter @capstone/web build && pnpm --filter @capstone/web test:e2e"],
  [3, "pnpm run verify:02 && pnpm --filter @capstone/web test && pnpm --filter @capstone/contracts test"],
  [4, "pnpm run verify:03 && pnpm --filter @capstone/api test"],
  [5, "pnpm run verify:04 && pnpm --filter @capstone/db test:postgres"],
  [6, "pnpm run verify:05 && pnpm --filter @capstone/api test:security"],
  [7, "pnpm run verify:06 && pnpm --filter @capstone/api test:websocket"],
  [8, "pnpm run verify:07 && pnpm --filter @capstone/web build && pnpm test:e2e && pnpm smoke"]
]);
const requiredByStage = new Map([
  [1, [
    ".env.example", "package.json", "pnpm-workspace.yaml", "tsconfig.base.json",
    "apps/web/package.json", "apps/web/app/layout.tsx", "apps/web/app/page.tsx",
    "apps/api/package.json", "apps/api/src/app.ts", "apps/api/src/index.ts",
    "packages/contracts/package.json", "packages/contracts/src/index.ts",
    "packages/db/package.json", "packages/db/src/index.ts"
  ]],
  [2, [
    "apps/web/app/login/page.tsx", "apps/web/app/boards/page.tsx",
    "apps/web/app/boards/[id]/page.tsx", "apps/web/app/admin/page.tsx",
    "apps/web/tests/e2e"
  ]],
  [3, [
    "packages/contracts/src/board.ts", "packages/contracts/src/http.ts",
    "packages/contracts/src/ws.ts", "apps/web/lib/api.ts"
  ]],
  [4, [
    "apps/api/src/routes", "apps/api/src/services", "apps/api/src/repositories"
  ]],
  [5, [
    "compose.test.yml", "packages/db/migrations", "packages/db/src/postgres.ts"
  ]],
  [6, [
    "apps/api/src/security", "apps/api/tests/security"
  ]],
  [7, [
    "apps/api/src/realtime", "apps/api/tests/websocket", "apps/web/components/BoardCanvas.tsx"
  ]],
  [8, [
    "tests/e2e", "tests/smoke.mjs"
  ]]
]);

for (let current = 1; current <= stage; current += 1) {
  for (const relative of requiredByStage.get(current) ?? []) {
    if (!await exists(relative)) errors.push(`단계 ${current}: 필수 경로 누락: ${relative}`);
  }
}

let rootPackage;
try {
  rootPackage = JSON.parse(await readFile(path.join(workRoot, "package.json"), "utf8"));
} catch (error) {
  errors.push(`package.json을 읽을 수 없음: ${error instanceof Error ? error.message : String(error)}`);
}

if (rootPackage) {
  if (rootPackage.scripts?.typecheck !== "pnpm -r typecheck") {
    errors.push("root typecheck script 계약 불일치: pnpm -r typecheck");
  }
  for (let current = 1; current <= stage; current += 1) {
    const name = `verify:${String(current).padStart(2, "0")}`;
    if (!rootPackage.scripts?.[name]) errors.push(`누적 단계 script 누락: ${name}`);
    else if (rootPackage.scripts[name] !== expectedStageScripts.get(current)) {
      errors.push(`누적 단계 script 계약 불일치: ${name}\n  기대값: ${expectedStageScripts.get(current)}`);
    }
  }
  if (stage === 8) {
    if (!rootPackage.scripts?.verify) errors.push("최종 script 누락: verify");
    else if (rootPackage.scripts.verify !== "pnpm run verify:08") errors.push("최종 script 계약 불일치: verify");
    if (rootPackage.scripts?.["test:e2e"] !== "playwright test") {
      errors.push("root test:e2e script 계약 불일치: playwright test");
    }
    if (rootPackage.scripts?.smoke !== "node tests/smoke.mjs") {
      errors.push("root smoke script 계약 불일치: node tests/smoke.mjs");
    }
  }
}

const packageContracts = [
  ["apps/web/package.json", "@capstone/web", ["typecheck"]],
  ["apps/api/package.json", "@capstone/api", ["typecheck", "test"]],
  ["packages/contracts/package.json", "@capstone/contracts", ["typecheck"]],
  ["packages/db/package.json", "@capstone/db", ["typecheck"]]
];
for (const [relative, expectedName, scripts] of packageContracts) {
  if (!await exists(relative)) continue;
  try {
    const manifest = JSON.parse(await readFile(path.join(workRoot, relative), "utf8"));
    if (manifest.name !== expectedName) errors.push(`${relative}: package name은 ${expectedName}이어야 함`);
    for (const script of scripts) {
      if (!manifest.scripts?.[script]) errors.push(`${relative}: script 누락: ${script}`);
      else if (!isAllowedPackageScript(relative, script, manifest.scripts[script])) {
        errors.push(`${relative}: ${script} script 계약 불일치\n  허용: ${packageScriptContract(relative, script).description}`);
      }
    }
  } catch (error) {
    errors.push(`${relative}: JSON 오류: ${error instanceof Error ? error.message : String(error)}`);
  }
}

const stagePackageScripts = [
  [2, "apps/web/package.json", ["build", "test:e2e"]],
  [3, "apps/web/package.json", ["test"], "packages/contracts/package.json", ["test"]],
  [4, "apps/api/package.json", ["test"]],
  [5, "packages/db/package.json", ["test:postgres"]],
  [6, "apps/api/package.json", ["test:security"]],
  [7, "apps/api/package.json", ["test:websocket"]],
  [8, "apps/web/package.json", ["build"]]
];
for (const contract of stagePackageScripts) {
  const [minimumStage, ...pairs] = contract;
  if (stage < minimumStage) continue;
  for (let index = 0; index < pairs.length; index += 2) {
    const relative = pairs[index];
    const scripts = pairs[index + 1];
    try {
      const manifest = JSON.parse(await readFile(path.join(workRoot, relative), "utf8"));
      for (const script of scripts) {
        if (!manifest.scripts?.[script]) errors.push(`단계 ${minimumStage}: ${relative} script 누락: ${script}`);
        else if (!isAllowedPackageScript(relative, script, manifest.scripts[script])) {
          errors.push(`단계 ${minimumStage}: ${relative}의 ${script} script 계약 불일치\n  허용: ${packageScriptContract(relative, script).description}`);
        }
      }
    } catch {
      // Earlier required-path errors already identify a missing or invalid manifest.
    }
  }
}

for (const relative of canonicalTestFiles) {
  if (!await exists(relative)) continue;
  const [canonical, learnerCopy] = await Promise.all([
    readFile(path.join(exerciseRoot, "skeleton", relative)),
    readFile(path.join(workRoot, relative))
  ]);
  if (!canonical.equals(learnerCopy)) {
    errors.push(`기준 검사는 수정하지 않고 학습자 검사를 별도 추가해야 함: ${relative}`);
  }
}

const disabledTests = await findDisabledTests(workRoot);
for (const entry of disabledTests) errors.push(`비활성 검사 표식이 남아 있음: ${entry}`);

const unfinished = await findUnfinishedMarkers(workRoot);
for (const entry of unfinished) errors.push(`미완성 표식이 남아 있음: ${entry}`);

if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}

console.log(`단계 ${stage}의 구조와 검증 진입점을 확인했습니다: ${relativeWork}`);
if (structureOnly) process.exit(0);

let activeChild;
let signalExitCode;
let signalPromise;
for (const [signal, code] of [["SIGHUP", 129], ["SIGINT", 130], ["SIGTERM", 143]]) {
  process.once(signal, () => {
    signalExitCode ??= code;
    signalPromise ??= stopChildGroup(activeChild);
  });
}
try {
  await runTrustedPlan();
} catch (error) {
  if (!signalExitCode) throw error;
}
if (signalExitCode) {
  await signalPromise;
  process.exit(signalExitCode);
}
console.log(`단계 ${stage}의 저장소 소유 누적 검증을 통과했습니다: ${stageScript}`);

async function exists(relative) {
  try {
    await access(path.join(workRoot, relative));
    return true;
  } catch {
    return false;
  }
}

async function findUnfinishedMarkers(directory) {
  const matches = [];
  const ignored = new Set([".git", ".next", "node_modules", "coverage", "test-results", "playwright-report"]);
  async function walk(current) {
    for (const entry of await readdir(current, { withFileTypes: true })) {
      if (ignored.has(entry.name)) continue;
      const target = path.join(current, entry.name);
      if (entry.isDirectory()) {
        await walk(target);
        continue;
      }
      if (!entry.isFile() || !/\.(?:[cm]?[jt]sx?)$/.test(entry.name)) continue;
      const text = await readFile(target, "utf8");
      if (/TODO_STAGE|FIXME_STAGE|not implemented/i.test(text)) {
        matches.push(path.relative(workRoot, target));
      }
    }
  }
  await walk(directory);
  return matches;
}

async function findDisabledTests(directory) {
  const matches = [];
  const ignored = new Set([".git", ".next", "node_modules", "coverage", "test-results", "playwright-report"]);
  async function walk(current) {
    for (const entry of await readdir(current, { withFileTypes: true })) {
      if (ignored.has(entry.name)) continue;
      const target = path.join(current, entry.name);
      if (entry.isDirectory()) {
        await walk(target);
        continue;
      }
      if (!entry.isFile() || !/\.(?:test|spec)\.[cm]?[jt]sx?$/.test(entry.name)) continue;
      const text = await readFile(target, "utf8");
      if (containsDisabledTestApi(target, text)) {
        matches.push(path.relative(workRoot, target));
      }
    }
  }
  await walk(directory);
  return matches;
}

function containsDisabledTestApi(file, text) {
  const disabledMembers = new Set(["only", "skip", "todo", "skipIf", "runIf", "fails", "fixme", "fail"]);
  const canonicalTestApis = new Set(["describe", "suite", "it", "test"]);
  const testApiRoots = new Set(canonicalTestApis);
  const testNamespaces = new Set();
  const nodeTestRoots = new Set();
  const nodeTestNamespaces = new Set();
  const source = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, scriptKind(file));
  const constInitializers = collectConstInitializers(source);
  collectTestApiAliases(
    source,
    testApiRoots,
    testNamespaces,
    nodeTestRoots,
    nodeTestNamespaces,
    canonicalTestApis
  );
  let disabled = false;
  const visit = (node) => {
    if (disabled) return;
    if (ts.isPropertyAccessExpression(node) || ts.isElementAccessExpression(node)) {
      const chain = callChain(node);
      const members = testApiMembers(chain, testApiRoots, testNamespaces, canonicalTestApis);
      if (members?.some((name) => disabledMembers.has(name))) {
        disabled = true;
        return;
      }
    }
    if (ts.isCallExpression(node)) {
      const chain = callChain(node.expression);
      const members = testApiMembers(chain, testApiRoots, testNamespaces, canonicalTestApis);
      const nodeMembers = testApiMembers(chain, nodeTestRoots, nodeTestNamespaces, canonicalTestApis);
      if (
        chain.length > 0 &&
        (members?.some((name) => disabledMembers.has(name)) ||
          ["xdescribe", "xit", "xtest"].includes(chain[0]))
      ) {
        disabled = true;
        return;
      }
      if (members?.length === 0 && containsDisabledNodeOptions(
        node.arguments,
        constInitializers,
        nodeMembers?.length === 0
      )) {
        disabled = true;
        return;
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(source);
  return disabled;
}

function collectConstInitializers(source) {
  const values = new Map();
  const ambiguous = new Set();
  const visit = (node) => {
    if (
      ts.isVariableDeclaration(node) &&
      ts.isIdentifier(node.name) &&
      node.initializer &&
      ts.isVariableDeclarationList(node.parent) &&
      (node.parent.flags & ts.NodeFlags.Const) !== 0
    ) {
      const name = node.name.text;
      if (values.has(name) || ambiguous.has(name)) {
        values.delete(name);
        ambiguous.add(name);
      } else {
        values.set(name, node.initializer);
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(source);
  return { values, ambiguous };
}

function collectTestApiAliases(
  source,
  testApiRoots,
  testNamespaces,
  nodeTestRoots,
  nodeTestNamespaces,
  canonicalTestApis
) {
  const modules = new Set(["vitest", "@playwright/test", "node:test"]);
  const aliasEdges = [];
  const visit = (node) => {
    if (ts.isImportDeclaration(node) && ts.isStringLiteralLike(node.moduleSpecifier) && modules.has(node.moduleSpecifier.text)) {
      const nodeTestModule = node.moduleSpecifier.text === "node:test";
      const clause = node.importClause;
      if (clause?.name) {
        testApiRoots.add(clause.name.text);
        if (nodeTestModule) nodeTestRoots.add(clause.name.text);
      }
      if (clause?.namedBindings && ts.isNamespaceImport(clause.namedBindings)) {
        testNamespaces.add(clause.namedBindings.name.text);
        if (nodeTestModule) nodeTestNamespaces.add(clause.namedBindings.name.text);
      }
      if (clause?.namedBindings && ts.isNamedImports(clause.namedBindings)) {
        for (const element of clause.namedBindings.elements) {
          const imported = (element.propertyName ?? element.name).text;
          if (canonicalTestApis.has(imported)) {
            testApiRoots.add(element.name.text);
            if (nodeTestModule) nodeTestRoots.add(element.name.text);
          }
        }
      }
    }
    if (ts.isVariableDeclaration(node) && node.initializer) {
      const requiredModule = testModuleRequire(node.initializer, modules);
      if (requiredModule) {
        const nodeTestModule = requiredModule === "node:test";
        if (ts.isIdentifier(node.name)) {
          testApiRoots.add(node.name.text);
          testNamespaces.add(node.name.text);
          if (nodeTestModule) {
            nodeTestRoots.add(node.name.text);
            nodeTestNamespaces.add(node.name.text);
          }
        } else if (ts.isObjectBindingPattern(node.name)) {
          for (const element of node.name.elements) {
            const imported = propertyName(element.propertyName ?? element.name);
            if (canonicalTestApis.has(imported) && ts.isIdentifier(element.name)) {
              testApiRoots.add(element.name.text);
              if (nodeTestModule) nodeTestRoots.add(element.name.text);
            }
          }
        }
      } else if (ts.isIdentifier(node.name)) {
        aliasEdges.push([node.name.text, node.initializer]);
      }
    }
    if (
      ts.isBinaryExpression(node) &&
      node.operatorToken.kind === ts.SyntaxKind.EqualsToken &&
      ts.isIdentifier(node.left)
    ) aliasEdges.push([node.left.text, node.right]);
    ts.forEachChild(node, visit);
  };
  visit(source);

  let changed = true;
  while (changed) {
    changed = false;
    for (const [alias, expression] of aliasEdges) {
      if (!testApiRoots.has(alias) && isTestApiReference(expression, testApiRoots, testNamespaces, canonicalTestApis)) {
        testApiRoots.add(alias);
        changed = true;
      }
      if (!nodeTestRoots.has(alias) && isTestApiReference(expression, nodeTestRoots, nodeTestNamespaces, canonicalTestApis)) {
        nodeTestRoots.add(alias);
        changed = true;
      }
      if (!testNamespaces.has(alias) && isTestNamespaceReference(expression, testNamespaces)) {
        testNamespaces.add(alias);
        changed = true;
      }
      if (!nodeTestNamespaces.has(alias) && isTestNamespaceReference(expression, nodeTestNamespaces)) {
        nodeTestNamespaces.add(alias);
        changed = true;
      }
    }
  }
}

function testModuleRequire(expression, modules) {
  const target = unwrapExpression(expression);
  if (ts.isCallExpression(target) &&
    ts.isIdentifier(target.expression) &&
    target.expression.text === "require" &&
    target.arguments.length === 1 &&
    ts.isStringLiteralLike(target.arguments[0]) &&
    modules.has(target.arguments[0].text)) return target.arguments[0].text;
  return null;
}

function isTestApiReference(expression, testApiRoots, testNamespaces, canonicalTestApis) {
  const target = unwrapExpression(expression);
  if (ts.isIdentifier(target)) return testApiRoots.has(target.text);
  const chain = callChain(target);
  return chain.length === 2 && testNamespaces.has(chain[0]) && canonicalTestApis.has(chain[1]);
}

function isTestNamespaceReference(expression, testNamespaces) {
  const target = unwrapExpression(expression);
  return ts.isIdentifier(target) && testNamespaces.has(target.text);
}

function testApiMembers(chain, testApiRoots, testNamespaces, canonicalTestApis) {
  if (testApiRoots.has(chain[0])) return chain.slice(1);
  if (testNamespaces.has(chain[0]) && canonicalTestApis.has(chain[1])) return chain.slice(2);
  return null;
}

function callChain(expression) {
  expression = unwrapExpression(expression);
  if (ts.isIdentifier(expression)) return [expression.text];
  if (ts.isCallExpression(expression)) return callChain(expression.expression);
  if (ts.isPropertyAccessExpression(expression)) return [...callChain(expression.expression), expression.name.text];
  if (ts.isElementAccessExpression(expression) && ts.isStringLiteralLike(expression.argumentExpression)) {
    return [...callChain(expression.expression), expression.argumentExpression.text];
  }
  return [];
}

function unwrapExpression(expression) {
  while (
    ts.isParenthesizedExpression(expression) ||
    ts.isAsExpression(expression) ||
    ts.isTypeAssertionExpression(expression) ||
    ts.isNonNullExpression(expression) ||
    ts.isSatisfiesExpression(expression)
  ) expression = expression.expression;
  return expression;
}

function containsDisabledNodeOptions(args, constInitializers, conservativeUnknownPosition) {
  for (let index = 0; index < args.length; index += 1) {
    const argument = unwrapExpression(args[index]);
    const directObject = ts.isObjectLiteralExpression(argument);
    const constObjectAlias = ts.isIdentifier(argument) &&
      (constInitializers.values.has(argument.text) || constInitializers.ambiguous.has(argument.text));
    const resolvedConstObject = constObjectAlias && resolvesToObjectLiteral(argument, constInitializers, new Set());
    const thirdArgumentIsCallback = args.length >= 3 && isInlineFunction(args[2]);
    const namedOptionsPosition = index === 1 && args.length >= 3 &&
      (conservativeUnknownPosition || resolvedConstObject || thirdArgumentIsCallback);
    const firstConstObject = index === 0 && resolvedConstObject;
    if (!directObject && !namedOptionsPosition && !firstConstObject) continue;
    const options = resolveNodeOptions(argument, constInitializers, new Set());
    if (options.skip === "disabled" || options.skip === "unknown" ||
        options.todo === "disabled" || options.todo === "unknown") return true;
  }
  return false;
}

function isInlineFunction(expression) {
  const target = unwrapExpression(expression);
  return ts.isArrowFunction(target) || ts.isFunctionExpression(target);
}

function resolvesToObjectLiteral(expression, constInitializers, seen) {
  expression = unwrapExpression(expression);
  if (ts.isObjectLiteralExpression(expression)) return true;
  if (!ts.isIdentifier(expression) || seen.has(expression.text) || constInitializers.ambiguous.has(expression.text)) return false;
  const initializer = constInitializers.values.get(expression.text);
  if (!initializer) return false;
  const nextSeen = new Set(seen);
  nextSeen.add(expression.text);
  return resolvesToObjectLiteral(initializer, constInitializers, nextSeen);
}

function resolveNodeOptions(expression, constInitializers, seen) {
  expression = unwrapExpression(expression);
  if (ts.isIdentifier(expression)) {
    if (seen.has(expression.text) || constInitializers.ambiguous.has(expression.text)) return unknownNodeOptions();
    const initializer = constInitializers.values.get(expression.text);
    if (!initializer) return unknownNodeOptions();
    const nextSeen = new Set(seen);
    nextSeen.add(expression.text);
    return resolveNodeOptions(initializer, constInitializers, nextSeen);
  }
  if (!ts.isObjectLiteralExpression(expression)) return unknownNodeOptions();

  const result = { skip: "absent", todo: "absent" };
  for (const property of expression.properties) {
    if (ts.isSpreadAssignment(property)) {
      const spread = resolveNodeOptions(property.expression, constInitializers, new Set(seen));
      for (const option of ["skip", "todo"]) {
        if (spread[option] !== "absent") result[option] = spread[option];
      }
      continue;
    }
    const name = propertyName(property.name);
    if (name !== "skip" && name !== "todo") {
      if (ts.isComputedPropertyName(property.name)) {
        result.skip = "unknown";
        result.todo = "unknown";
      }
      continue;
    }
    if (ts.isPropertyAssignment(property)) {
      result[name] = isStaticallyFalse(property.initializer) ? "enabled" : "disabled";
    } else {
      result[name] = "disabled";
    }
  }
  return result;
}

function unknownNodeOptions() {
  return { skip: "unknown", todo: "unknown" };
}

function propertyName(name) {
  if (!name) return null;
  if (ts.isIdentifier(name) || ts.isStringLiteralLike(name) || ts.isNumericLiteral(name)) return name.text;
  if (ts.isComputedPropertyName(name) && ts.isStringLiteralLike(name.expression)) return name.expression.text;
  return null;
}

function isStaticallyFalse(expression) {
  expression = unwrapExpression(expression);
  if (expression.kind === ts.SyntaxKind.FalseKeyword || expression.kind === ts.SyntaxKind.NullKeyword) return true;
  if (ts.isIdentifier(expression) && expression.text === "undefined") return true;
  if (ts.isNumericLiteral(expression)) return Number(expression.text) === 0;
  if (ts.isStringLiteralLike(expression)) return expression.text.length === 0;
  return false;
}

function scriptKind(file) {
  if (/\.tsx$/i.test(file)) return ts.ScriptKind.TSX;
  if (/\.jsx$/i.test(file)) return ts.ScriptKind.JSX;
  if (/\.[cm]?js$/i.test(file)) return ts.ScriptKind.JS;
  return ts.ScriptKind.TS;
}

async function runTrustedPlan() {
  const direct = [
    ["--filter", "@capstone/contracts", "exec", "tsc", "--noEmit"],
    ["--filter", "@capstone/db", "exec", "tsc", "--noEmit"],
    ["--filter", "@capstone/api", "exec", "tsc", "--noEmit"],
    ["--filter", "@capstone/web", "exec", "next", "typegen"],
    ["--filter", "@capstone/web", "exec", "tsc", "--noEmit"],
    ["--filter", "@capstone/api", "exec", "tsx", "--test", "src/app.test.ts", "src/config.test.ts"]
  ];
  for (const args of direct) await run("pnpm", args, workRoot);

  if (stage >= 5) {
    await run(process.execPath, [postgresVerifier, "--learner-work", workRoot], workRoot);
  }

  const packageChecks = [
    [2, "@capstone/web", "build"],
    [2, "@capstone/web", "test:e2e"],
    [3, "@capstone/web", "test"],
    [3, "@capstone/contracts", "test"],
    [4, "@capstone/api", "test"],
    [6, "@capstone/api", "test:security"],
    [7, "@capstone/api", "test:websocket"]
  ];
  for (const [minimumStage, packageName, script] of packageChecks) {
    if (stage >= minimumStage) await run("pnpm", ["--filter", packageName, "run", script], workRoot);
  }
  if (stage >= 8) {
    await run("pnpm", ["exec", "playwright", "test"], workRoot);
    await run(process.execPath, [path.join(workRoot, "tests", "smoke.mjs")], workRoot);
  }
}

function isAllowedPackageScript(relative, script, command) {
  return packageScriptContract(relative, script).pattern.test(command);
}

function packageScriptContract(relative, script) {
  const vitestFlags = String.raw`(?:\s+--reporter=(?:default|verbose|dot))*`;
  const nodeTestFlags = String.raw`(?:(?:\s+--test-reporter=(?:spec|dot|tap))|(?:\s+--test-concurrency=\d+))*`;
  const playwrightFlags = String.raw`(?:(?:\s+--reporter=(?:line|list|dot))|(?:\s+--workers=\d+))*`;
  if (script === "typecheck") {
    return relative === "apps/web/package.json"
      ? {
          pattern: /^next typegen && tsc --noEmit$/,
          description: "next typegen && tsc --noEmit"
        }
      : {
          pattern: /^tsc --noEmit(?: --pretty(?:=(?:true|false))?)?$/,
          description: "tsc --noEmit [--pretty[=true|false]]"
        };
  }
  if (script === "build") {
    return {
      pattern: /^next build$/,
      description: "next build"
    };
  }
  if (script === "test:e2e") {
    return {
      pattern: new RegExp(`^playwright test${playwrightFlags}$`),
      description: "playwright test [--reporter=line|list|dot] [--workers=N]"
    };
  }
  if (script === "test:postgres") {
    return {
      pattern: new RegExp(`^vitest run${vitestFlags}$`),
      description: "vitest run [--reporter=default|verbose|dot]"
    };
  }
  if (["test", "test:security", "test:websocket"].includes(script)) {
    const canonicalGlob = script === "test" && relative === "apps/api/package.json"
      ? String.raw`src/\*\.test\.ts`
      : script === "test:security"
        ? String.raw`tests/security/\*\.test\.ts`
        : script === "test:websocket"
          ? String.raw`tests/websocket/\*\.test\.ts`
          : null;
    const tsxCommand = canonicalGlob ? `|tsx --test ${canonicalGlob}${nodeTestFlags}` : "";
    return {
      pattern: new RegExp(`^(?:vitest run${vitestFlags}${tsxCommand})$`),
      description: canonicalGlob
        ? `vitest run [안전한 reporter] 또는 tsx --test ${canonicalGlob.replaceAll("\\", "")} [안전한 test runner 인자]`
        : "vitest run [--reporter=default|verbose|dot]"
    };
  }
  return { pattern: /$a/, description: "지원하는 저장소 소유 runner" };
}

function run(command, args, cwd) {
  return new Promise((resolve, reject) => {
    if (signalExitCode) {
      reject(new Error("검증이 signal로 중단됐습니다."));
      return;
    }
    const child = spawn(command, args, {
      cwd,
      detached: process.platform !== "win32",
      stdio: "inherit",
      shell: false
    });
    activeChild = child;
    child.once("error", (error) => {
      if (activeChild === child) activeChild = undefined;
      reject(error);
    });
    child.once("exit", (code, signal) => {
      if (activeChild === child) activeChild = undefined;
      if (code === 0) resolve();
      else reject(new Error(`${command} ${args.join(" ")} 실패: ${signal ?? code}`));
    });
  });
}

async function stopChildGroup(child) {
  if (!child || child.exitCode !== null || child.signalCode !== null) return;
  signalChildGroup(child, "SIGTERM");
  if (!await waitForExit(child, 10_000)) {
    signalChildGroup(child, "SIGKILL");
    await waitForExit(child, 1_000);
  }
}

function signalChildGroup(child, signal) {
  if (!child?.pid || child.exitCode !== null || child.signalCode !== null) return;
  try {
    if (process.platform === "win32") child.kill(signal);
    else process.kill(-child.pid, signal);
  } catch (error) {
    if (error.code !== "ESRCH") throw error;
  }
}

function waitForExit(child, timeoutMs) {
  if (child.exitCode !== null || child.signalCode !== null) return Promise.resolve(true);
  return new Promise((resolve) => {
    const finish = (exited) => {
      clearTimeout(timer);
      child.off("exit", onExit);
      resolve(exited);
    };
    const onExit = () => finish(true);
    const timer = setTimeout(() => finish(false), timeoutMs);
    child.once("exit", onExit);
  });
}

function fail(message) {
  console.error(message);
  process.exit(2);
}
