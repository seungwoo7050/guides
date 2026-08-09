import { cp, mkdir, mkdtemp, readFile, rm, rmdir, symlink, writeFile } from "node:fs/promises";
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const exerciseRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = path.resolve(exerciseRoot, "..", "..");
const skeletonRoot = path.join(exerciseRoot, "skeleton");
const verifier = path.join(exerciseRoot, "checks", "verify-work.mjs");
const postgresVerifier = path.join(repositoryRoot, "scripts", "verify-collaboration-postgresql.mjs");
const temporaryRoots = [];
const temporaryParent = path.join(exerciseRoot, ".guide-tmp");
const databasePolicy = process.argv.includes("--database");
await mkdir(temporaryParent, { recursive: true });

try {
  await expectPostgresPolicy();
  if (databasePolicy) {
    await expectPostgresFixtureAccepted();
    await expectPostgresFixtureRejected();
    await expectPostgresSemanticNoopRejected();
  }
  await expectAccepted("기준 starter", async () => {});
  await expectAccepted("허용된 test runner 추가 인자", async (workRoot) => {
    const manifestPath = path.join(workRoot, "apps", "api", "package.json");
    const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
    manifest.scripts.test = "tsx --test src/*.test.ts --test-reporter=spec";
    await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  });
  await expectAccepted("주석·문자열·template의 비활성 표식", async (workRoot) => {
    await writeFile(path.join(workRoot, "apps", "api", "src", "disabled-marker.test.ts"), `
// test.skip("주석은 실행 코드가 아닙니다.");
const quotedMarker = "test.skip(";
const templateMarker = \`describe.skipIf(true)(\`;
export { quotedMarker, templateMarker };
`.trimStart());
  });
  await expectAccepted("명시적으로 활성화된 Node test option", async (workRoot) => {
    await writePolicyTest(workRoot, "test(\"case\", { skip: (false), todo: false as boolean }, () => {});\n");
  });
  await expectAccepted("const로 활성화된 Node test option", async (workRoot) => {
    await writePolicyTest(workRoot, "const options = { skip: false, todo: false }; test(\"case\", options, () => {});\n");
  });
  await expectAccepted("const test 이름은 options로 오인하지 않음", async (workRoot) => {
    await writePolicyTest(workRoot, "const title = \"case\"; test(title, () => {});\n");
  });
  await expectAccepted("Vitest 3-인자 timeout은 Node options로 오인하지 않음", async (workRoot) => {
    await writePolicyTest(workRoot, "import { test as spec } from \"vitest\"; spec(\"slow\", async () => {}, 10_000);\n");
  });
  await expectAccepted("나중 property가 spread 비활성 값을 해제", async (workRoot) => {
    await writePolicyTest(workRoot, "test(\"case\", { ...{ skip: true }, skip: false }, () => {});\n");
  });
  for (const [label, source] of [
    ["focused suite", "describe.only(\"suite\", () => {});"],
    ["skipped test", "test.skip(\"case\", () => {});"],
    ["todo test", "it.todo(\"case\");"],
    ["conditional suite", "describe.skipIf(true)(\"suite\", () => {});"],
    ["conditional test", "test.runIf(true)(\"case\", () => {});"],
    ["expected failure", "test.fails(\"case\", () => {});"],
    ["Playwright fixme", "test.fixme(\"case\", () => {});"],
    ["Playwright fail", "test.fail(\"case\", () => {});"],
    ["nested Playwright suite", "test.describe.skip(\"suite\", () => {});"],
    ["parameterized skipped test", "test.each([1]).skip(\"case\", () => {});"],
    ["aliased disabled suite", "const disabled = describe.skip; disabled(\"suite\", () => {});"],
    ["Vitest named import alias", "import { test as check } from \"vitest\"; check.skip(\"case\", () => {});"],
    ["simple identifier alias", "const check = test; check.todo(\"case\");"],
    ["Playwright namespace alias", "import * as runner from \"@playwright/test\"; runner.test.fixme(\"case\", () => {});"],
    ["Node default import alias", "import check from \"node:test\"; check(\"case\", { skip: true }, () => {});"],
    ["Node const option alias", "const check = test; const options = { skip: true }; check(\"case\", options, () => {});"],
    ["Node let option alias", "import { test as nodeTest } from \"node:test\"; const check = nodeTest; let options = { skip: true }; check(\"case\", options, () => {});"],
    ["Node namespace provenance alias", "import * as nodeTests from \"node:test\"; const runner = nodeTests; let options = { todo: true }; runner.test(\"case\", options, () => {});"],
    ["Vitest let option alias", "import { test as spec } from \"vitest\"; let options = { skip: true }; spec(\"case\", options, () => {});"],
    ["later spread disables Node test", "test(\"case\", { skip: false, ...{ skip: true } }, () => {});"],
    ["cyclic Node option aliases", "import { test as nodeTest } from \"node:test\"; const first = second; const second = first; nodeTest(\"case\", first, () => {});"],
    ["unknown Node option spread", "test(\"case\", { ...externalOptions, skip: false }, () => {});"],
    ["Node test skip option", "test(\"case\", { [\"skip\"]: true }, () => {});"],
    ["Node suite todo option", "suite(\"case\", { todo: \"later\" }, () => {});"]
  ]) {
    await expectRejected(label, async (workRoot) => {
      await writePolicyTest(workRoot, `${source}\n`);
    }, "비활성 검사 표식");
  }
  await expectRejected("학습자 root 검증 script 무력화", async (workRoot) => {
    const manifestPath = path.join(workRoot, "package.json");
    const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
    manifest.scripts["verify:01"] = "node -e 'console.log(\"passed\")'";
    await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  }, "누적 단계 script 계약 불일치");
  await expectRejected("임의 이름의 학습자 verifier 무력화", async (workRoot) => {
    const manifestPath = path.join(workRoot, "package.json");
    const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
    manifest.scripts["verify:01"] = "node tests/verify-everything.mjs";
    await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
    await mkdir(path.join(workRoot, "tests"), { recursive: true });
    await writeFile(path.join(workRoot, "tests", "verify-everything.mjs"), "process.exit(0);\n");
  }, "누적 단계 script 계약 불일치");
  await expectRejected("package test script 무력화", async (workRoot) => {
    const manifestPath = path.join(workRoot, "apps", "api", "package.json");
    const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
    manifest.scripts.test = "exit 0";
    await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  }, "test script 계약 불일치");
  await expectRejected("임의 test 파일 선택으로 package 검사 무력화", async (workRoot) => {
    const manifestPath = path.join(workRoot, "apps", "api", "package.json");
    const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
    manifest.scripts.test = "tsx --test src/noop.test.ts";
    await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
    await writeFile(path.join(workRoot, "apps", "api", "src", "noop.test.ts"), "process.exit(0);\n");
  }, "test script 계약 불일치");
  await expectRejected("저장소 소유 기준 test 수정", async (workRoot) => {
    const testPath = path.join(workRoot, "apps", "api", "src", "app.test.ts");
    await writeFile(testPath, `${await readFile(testPath, "utf8")}\n// learner mutation\n`);
  }, "기준 검사는 수정하지 않고");
  console.log(databasePolicy
    ? "협업 보드 검사기가 PostgreSQL runtime skip·semantic no-op과 기존 검증 우회를 거부함을 확인했습니다."
    : "협업 보드 검사기가 PostgreSQL skip report policy와 기존 검증 우회를 거부함을 확인했습니다.");
} finally {
  await Promise.allSettled(temporaryRoots.map((directory) => rm(directory, { recursive: true, force: true })));
  await rmdir(temporaryParent).catch((error) => {
    if (error?.code !== "ENOENT" && error?.code !== "ENOTEMPTY") throw error;
  });
}

async function expectPostgresPolicy() {
  const source = await readFile(verifier, "utf8");
  const route = 'await run(process.execPath, [postgresVerifier, "--learner-work", workRoot], workRoot);';
  if (!source.includes(route)) throw new Error("Stage 5 trusted plan에서 저장소 소유 PostgreSQL runner 호출이 누락됐습니다.");
  const result = await run(process.execPath, [postgresVerifier, "--self-test"]);
  if (result.code !== 0 || !result.output.includes("skip·빈 test report를 거부")) {
    throw new Error(`PostgreSQL skip report meta 검사가 실패했습니다.\n${result.output}`);
  }
}

async function expectPostgresFixtureAccepted() {
  const workRoot = await postgresFixture(`
import { Client } from "pg";
import { describe, expect, it } from "vitest";
describe("learner PostgreSQL", () => {
  it("uses the repository-owned database", async () => {
    const client = new Client({ connectionString: process.env.DATABASE_URL });
    await client.connect();
    try { expect((await client.query("select 1 as value")).rows[0].value).toBe(1); }
    finally { await client.end(); }
  });
});
`);
  const result = await run(process.execPath, [postgresVerifier, "--learner-work", workRoot]);
  if (result.code !== 0 || !result.output.includes("test 1개를") || !result.output.includes("skip 없이")) {
    throw new Error(`정상 학습자 PostgreSQL fixture를 거부했습니다.\n${result.output}`);
  }
}

async function expectPostgresFixtureRejected() {
  const workRoot = await postgresFixture(`
import { describe, it } from "vitest";
const suite = process.env.DATABASE_URL ? describe.skip : describe;
suite("learner PostgreSQL", () => { it("is silently skipped", () => {}); });
`);
  const result = await run(process.execPath, [postgresVerifier, "--learner-work", workRoot]);
  if (result.code === 0 || !result.output.includes("skip/todo")) {
    throw new Error(`runtime skip 학습자 PostgreSQL fixture를 허용했습니다.\n${result.output}`);
  }
}

async function expectPostgresSemanticNoopRejected() {
  const workRoot = await postgresFixture(`
import { describe, it } from "vitest";
describe("learner PostgreSQL", () => { it("only proves that one is one", () => {}); });
`);
  await writeFile(path.join(workRoot, "packages", "db", "migrations", "001_initial.sql"), "select 1;\n");
  await writeFile(
    path.join(workRoot, "packages", "db", "src", "postgres.ts"),
    "export function createPostgresRepository() { return {}; }\n"
  );
  const result = await run(process.execPath, [postgresVerifier, "--learner-work", workRoot]);
  if (result.code === 0 || !result.output.includes("stage5-postgresql.test.ts")) {
    throw new Error(`의미 없는 Stage 5 PostgreSQL fixture를 허용했습니다.\n${result.output}`);
  }
}

async function postgresFixture(testSource) {
  const workRoot = await mkdtemp(path.join(temporaryParent, "verify-work-postgres-"));
  temporaryRoots.push(workRoot);
  const packageRoot = path.join(workRoot, "packages", "db");
  await mkdir(path.join(packageRoot, "tests", "postgres"), { recursive: true });
  await mkdir(path.join(packageRoot, "migrations"), { recursive: true });
  await mkdir(path.join(packageRoot, "src"), { recursive: true });
  await writeFile(path.join(workRoot, "package.json"), '{"name":"postgres-policy-fixture","private":true}\n');
  await writeFile(path.join(workRoot, "pnpm-workspace.yaml"), "packages:\n  - packages/*\n");
  await writeFile(path.join(packageRoot, "package.json"), `${JSON.stringify({
    name: "@capstone/db",
    private: true,
    type: "module",
    scripts: { "test:postgres": "vitest run" }
  }, null, 2)}\n`);
  await writeFile(path.join(packageRoot, "tests", "postgres", "database.test.ts"), testSource.trimStart());
  await cp(
    path.join(repositoryRoot, "projects", "collaboration-board", "packages", "db", "migrations", "001_initial.sql"),
    path.join(packageRoot, "migrations", "001_initial.sql")
  );
  for (const sourceFile of ["postgres.ts", "index.ts", "db-types.ts"]) {
    await cp(
      path.join(repositoryRoot, "projects", "collaboration-board", "packages", "db", "src", sourceFile),
      path.join(packageRoot, "src", sourceFile)
    );
  }
  await symlink(path.join(repositoryRoot, "projects", "collaboration-board", "packages", "db", "node_modules"), path.join(packageRoot, "node_modules"), "dir");
  return workRoot;
}

async function expectAccepted(label, mutate) {
  const result = await exerciseCopy(mutate);
  if (result.code !== 0) throw new Error(`${label}을 거부했습니다.\n${result.output}`);
}

async function expectRejected(label, mutate, expectedMessage) {
  const result = await exerciseCopy(mutate);
  if (result.code === 0) throw new Error(`${label}을 허용했습니다.`);
  if (!result.output.includes(expectedMessage)) {
    throw new Error(`${label}이 예상한 이유로 거부되지 않았습니다.\n${result.output}`);
  }
}

async function exerciseCopy(mutate) {
  const workRoot = await mkdtemp(path.join(temporaryParent, "verify-work-policy-"));
  temporaryRoots.push(workRoot);
  await cp(skeletonRoot, workRoot, { recursive: true });
  await mutate(workRoot);
  return run(process.execPath, [verifier, path.relative(exerciseRoot, workRoot), "1", "--structure-only"]);
}

async function writePolicyTest(workRoot, source) {
  await writeFile(path.join(workRoot, "apps", "api", "src", "disabled-policy.test.ts"), source);
}

function run(command, args) {
  return new Promise((resolve) => {
    const child = spawn(command, args, {
      cwd: exerciseRoot,
      stdio: ["ignore", "pipe", "pipe"],
      shell: false
    });
    let output = "";
    child.stdout.on("data", (chunk) => { output += chunk; });
    child.stderr.on("data", (chunk) => { output += chunk; });
    child.once("error", (error) => resolve({ code: 127, output: `${output}\n${error.message}` }));
    child.once("exit", (code) => resolve({ code: code ?? 1, output }));
  });
}
