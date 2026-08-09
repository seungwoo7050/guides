import { spawn } from "node:child_process";
import { randomBytes } from "node:crypto";
import { mkdtemp, readFile, readdir, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const projectRoot = path.join(root, "projects", "collaboration-board");
const composeFile = path.join(root, "exercises", "collaboration-board", "checks", "postgresql.compose.yml");
const postgresTest = path.join(projectRoot, "packages", "db", "src", "postgres.test.ts");
const learnerOracle = path.join(root, "exercises", "collaboration-board", "checks", "stage5-postgresql.test.ts");
const pnpm = process.platform === "win32" ? "pnpm.cmd" : "pnpm";
const expectedPostgresTests = 1;
const expectedLearnerOracleTests = 6;
const learnerFlagIndex = process.argv.indexOf("--learner-work");

if (process.argv.includes("--self-test")) {
  verifyReportValidator();
  console.log("capstone PostgreSQL 결과 검사기가 Vitest skip·빈 test report를 거부함을 확인했습니다.");
} else {
  const learnerWork = learnerFlagIndex === -1 ? undefined : process.argv[learnerFlagIndex + 1];
  if (learnerFlagIndex !== -1 && !learnerWork) throw new Error("--learner-work 뒤에 work directory가 필요합니다.");
  await verifyPostgresIntegration({
    databaseOnly: process.argv.includes("--database-only"),
    learnerWork: learnerWork ? validateLearnerWork(learnerWork) : undefined
  });
}

async function verifyPostgresIntegration({ databaseOnly, learnerWork }) {
  const composeProject = `guide-webapp-capstone-db-${process.pid}-${randomBytes(3).toString("hex")}`;
  const temporary = await mkdtemp(path.join(tmpdir(), "guide-webapp-capstone-db-"));
  const reportFile = path.join(temporary, "vitest-report.json");
  const oracleReportFile = path.join(temporary, "stage5-oracle-report.json");
  const composeArgs = ["compose", "--project-name", composeProject, "--file", composeFile];
  let activeChild;
  let cleanupPromise;
  let primaryError;
  let signalExitCode;
  let signalPromise;

  const cleanup = () => {
    cleanupPromise ??= (async () => {
      let cleanupError;
      try {
        await run("docker", [...composeArgs, "down", "--volumes", "--remove-orphans"], {
          cwd: root,
          timeoutMs: 60_000,
          track: false
        });
      } catch (error) {
        cleanupError = error;
      } finally {
        await rm(temporary, { recursive: true, force: true });
      }
      if (cleanupError) throw cleanupError;
    })();
    return cleanupPromise;
  };

  for (const [signal, code] of [["SIGHUP", 129], ["SIGINT", 130], ["SIGTERM", 143]]) {
    process.once(signal, () => {
      signalExitCode ??= code;
      const child = activeChild;
      signalPromise ??= (async () => {
        await stopChildGroup(child);
        await cleanup();
      })();
    });
  }

  try {
    await run("docker", [...composeArgs, "config", "--quiet"], { cwd: root });
    await run("docker", [...composeArgs, "up", "--detach", "--wait", "--wait-timeout", "60", "db"], {
      cwd: root,
      timeoutMs: 120_000
    });

    const endpoint = (await run("docker", [...composeArgs, "port", "db", "5432"], {
      capture: true,
      cwd: root
    })).trim();
    const match = endpoint.match(/^127\.0\.0\.1:(\d+)$/);
    if (!match) throw new Error(`동적 PostgreSQL port를 확인할 수 없습니다: ${endpoint || "<empty>"}`);
    const port = Number(match[1]);
    if (!Number.isSafeInteger(port) || port < 1 || port > 65535) {
      throw new Error(`잘못된 PostgreSQL port입니다: ${match[1]}`);
    }

    const environment = {
      ...process.env,
      DATABASE_URL: `postgresql://board:board@127.0.0.1:${port}/board`
    };
    if (learnerWork) {
      await run(pnpm, [
        "--dir", projectRoot,
        "exec", "vitest", "run",
        "--root", root,
        learnerOracle,
        "--reporter=json",
        `--outputFile=${oracleReportFile}`
      ], {
        cwd: root,
        env: { ...environment, LEARNER_WORK_ROOT: learnerWork },
        timeoutMs: 120_000
      });
      const oracleReport = JSON.parse(await readFile(oracleReportFile, "utf8"));
      validateVitestReport(oracleReport, [learnerOracle], expectedLearnerOracleTests);
      console.log(`저장소 소유 Stage 5 PostgreSQL oracle ${expectedLearnerOracleTests}개를 통과했습니다.`);
      const testCount = await runLearnerPostgresTests(learnerWork, environment, reportFile, run);
      console.log(`학습자 Stage 5 PostgreSQL test ${testCount}개를 동적 port ${port}에서 skip 없이 확인했습니다.`);
    } else {
      await run(pnpm, ["--dir", projectRoot, "--filter", "@board/db", "migrate"], {
        cwd: root,
        env: environment
      });
      await run(pnpm, ["--dir", projectRoot, "--filter", "@board/db", "seed"], {
        cwd: root,
        env: environment
      });
      if (!databaseOnly) {
        await run(pnpm, ["--dir", projectRoot, "typecheck"], {
          cwd: root,
          env: environment
        });
      }
      await run(pnpm, [
        "--dir", projectRoot,
        "--filter", "@board/db",
        "exec", "vitest", "run", "src/postgres.test.ts",
        "--reporter=json",
        `--outputFile=${reportFile}`
      ], {
        cwd: root,
        env: environment,
        timeoutMs: 120_000
      });

      const report = JSON.parse(await readFile(reportFile, "utf8"));
      const testCount = validateVitestReport(report, [postgresTest], expectedPostgresTests);
      console.log(`capstone PostgreSQL 통합 test ${testCount}개를 동적 port ${port}에서 skip 없이 확인했습니다.`);
      if (!databaseOnly) {
        await run(pnpm, ["--dir", projectRoot, "test"], {
          cwd: root,
          env: environment
        });
        await run(pnpm, ["--dir", projectRoot, "build"], {
          cwd: root,
          env: environment,
          timeoutMs: 180_000
        });
        await run(pnpm, ["--dir", projectRoot, "test:e2e"], {
          cwd: root,
          env: environment,
          timeoutMs: 180_000
        });
      }
    }
  } catch (error) {
    primaryError = error;
  } finally {
    try {
      await cleanup();
    } catch (cleanupError) {
      if (!primaryError) primaryError = cleanupError;
      else console.error(`capstone PostgreSQL 정리 실패: ${cleanupError.message}`);
    }
  }

  if (signalExitCode) {
    try {
      await signalPromise;
    } catch (error) {
      console.error(`capstone PostgreSQL 정리 실패: ${error.message}`);
    }
    process.exit(signalExitCode);
  }
  if (primaryError) throw primaryError;

  function run(command, args, options = {}) {
    const {
      capture = false,
      cwd = root,
      env = process.env,
      timeoutMs = 120_000,
      track = true
    } = options;
    if (signalExitCode && track) {
      return Promise.reject(new Error("검증이 signal로 중단됐습니다."));
    }
    return new Promise((resolve, reject) => {
      const child = spawn(command, args, {
        cwd,
        detached: process.platform !== "win32",
        env,
        stdio: capture ? ["ignore", "pipe", "pipe"] : "inherit"
      });
      if (track) activeChild = child;
      let output = "";
      let settled = false;
      let timedOut = false;
      let killTimer;
      if (capture) {
        child.stdout.setEncoding("utf8");
        child.stderr.setEncoding("utf8");
        child.stdout.on("data", (chunk) => { output += chunk; });
        child.stderr.on("data", (chunk) => { output += chunk; });
      }
      const timer = setTimeout(() => {
        timedOut = true;
        terminateChild(child);
        killTimer = setTimeout(() => terminateChild(child, "SIGKILL"), 5_000);
      }, timeoutMs);
      const finish = (error, value) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        clearTimeout(killTimer);
        if (track && activeChild === child) activeChild = undefined;
        if (error) reject(error);
        else resolve(value);
      };
      child.once("error", (error) => {
        finish(new Error(`${command} 실행 실패: ${error.message}`));
      });
      child.once("exit", (code, signal) => {
        if (code === 0) finish(undefined, output);
        else {
          const reason = timedOut ? `timeout ${timeoutMs}ms` : (signal ?? code);
          finish(new Error(`${command} ${args.join(" ")} 종료: ${reason}${output ? `\n${output}` : ""}`));
        }
      });
    });
  }
}

async function runLearnerPostgresTests(learnerWork, environment, reportFile, run) {
  const packageRoot = path.join(learnerWork, "packages", "db");
  const manifest = JSON.parse(await readFile(path.join(packageRoot, "package.json"), "utf8"));
  const command = manifest.scripts?.["test:postgres"];
  if (!/^vitest run(?:\s+--reporter=(?:default|verbose|dot))*$/.test(command ?? "")) {
    throw new Error(`학습자 test:postgres는 허용된 Vitest 명령이어야 합니다: ${command ?? "<missing>"}`);
  }
  const testsRoot = path.join(packageRoot, "tests", "postgres");
  const testFiles = (await readdir(testsRoot, { withFileTypes: true }))
    .filter((entry) => entry.isFile() && entry.name.endsWith(".test.ts"))
    .map((entry) => path.join(testsRoot, entry.name))
    .sort();
  if (testFiles.length === 0) throw new Error("학습자 PostgreSQL 기준 test 파일이 없습니다: packages/db/tests/postgres/*.test.ts");

  await run(pnpm, [
    "--dir", projectRoot,
    "exec", "vitest", "run",
    "--root", packageRoot,
    ...testFiles.map((file) => path.relative(packageRoot, file)),
    "--reporter=json",
    `--outputFile=${reportFile}`
  ], {
    cwd: root,
    env: environment,
    timeoutMs: 120_000
  });
  const report = JSON.parse(await readFile(reportFile, "utf8"));
  return validateVitestReport(report, testFiles);
}

function validateVitestReport(report, expectedTestFiles, exactTestCount) {
  const total = Number(report?.numTotalTests);
  const passed = Number(report?.numPassedTests);
  const failed = Number(report?.numFailedTests);
  const pending = Number(report?.numPendingTests);
  const todo = Number(report?.numTodoTests);
  if (!Number.isSafeInteger(total) || total < 1) {
    throw new Error(`PostgreSQL 통합 test가 실행되지 않았습니다: ${total}`);
  }
  if (exactTestCount !== undefined && total !== exactTestCount) {
    throw new Error(`PostgreSQL 통합 test 수가 ${exactTestCount}이 아닙니다: ${total}`);
  }
  if (pending !== 0 || todo !== 0) {
    throw new Error(`PostgreSQL 통합 test에 skip/todo가 있습니다: pending=${pending}, todo=${todo}`);
  }
  if (report.success !== true || failed !== 0 || passed !== total) {
    throw new Error(`PostgreSQL 통합 test 결과가 완전 통과가 아닙니다: passed=${passed}/${total}, failed=${failed}`);
  }
  const results = Array.isArray(report.testResults) ? report.testResults : [];
  const expected = new Set(expectedTestFiles.map((file) => path.resolve(file)));
  const observed = results.map((result) => path.resolve(result.name ?? ""));
  const observedSet = new Set(observed);
  if (
    results.length !== expected.size ||
    observedSet.size !== expected.size ||
    observed.some((file) => !expected.has(file)) ||
    [...expected].some((file) => !observedSet.has(file))
  ) {
    throw new Error(`PostgreSQL 기준 test 파일 실행 집합이 다릅니다: expected=${expected.size}, observed=${results.length}`);
  }
  const assertions = results.flatMap((result) => Array.isArray(result.assertionResults) ? result.assertionResults : []);
  if (assertions.length !== total || assertions.some((assertion) => assertion.status !== "passed")) {
    throw new Error("PostgreSQL 기준 test assertion 수 또는 상태가 report 합계와 다릅니다.");
  }
  return total;
}

function verifyReportValidator() {
  const expected = "/tmp/capstone-postgres.test.ts";
  const passing = {
    success: true,
    numTotalTests: 1,
    numPassedTests: 1,
    numFailedTests: 0,
    numPendingTests: 0,
    numTodoTests: 0,
    testResults: [{
      name: expected,
      assertionResults: [{ status: "passed" }]
    }]
  };
  if (validateVitestReport(passing, [expected], 1) !== 1) throw new Error("정상 report의 test 수를 확인하지 못했습니다.");
  expectReportFailure({ ...passing, numTotalTests: 0, numPassedTests: 0, testResults: [] }, [expected]);
  expectReportFailure({
    ...passing,
    numPassedTests: 0,
    numPendingTests: 1,
    testResults: [{ name: expected, assertionResults: [{ status: "pending" }] }]
  }, [expected]);
  const second = "/tmp/second-postgres.test.ts";
  expectReportFailure({
    ...passing,
    numTotalTests: 2,
    numPassedTests: 2,
    testResults: [
      { name: expected, assertionResults: [{ status: "passed" }] },
      { name: expected, assertionResults: [{ status: "passed" }] }
    ]
  }, [expected, second]);
}

function expectReportFailure(report, expected) {
  try {
    validateVitestReport(report, expected);
  } catch {
    return;
  }
  throw new Error("잘못된 PostgreSQL Vitest report가 허용되었습니다.");
}

function validateLearnerWork(argument) {
  const exercise = path.join(root, "exercises", "collaboration-board");
  const resolved = path.resolve(argument);
  const relative = path.relative(exercise, resolved);
  if (!relative || relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error("학습자 work directory는 exercises/collaboration-board 아래에 있어야 합니다.");
  }
  const blocked = new Set(["checks", "fixtures", "patches", "skeleton", "specs", "walkthrough-base"]);
  if (blocked.has(relative.split(path.sep)[0])) throw new Error(`검증할 수 없는 학습자 work directory입니다: ${relative}`);
  return resolved;
}

function terminateChild(child, signal = "SIGTERM") {
  if (!child?.pid || child.exitCode !== null || child.signalCode !== null) return;
  try {
    if (process.platform === "win32") child.kill(signal);
    else process.kill(-child.pid, signal);
  } catch (error) {
    if (error.code !== "ESRCH") throw error;
  }
}

async function stopChildGroup(child) {
  if (!child || child.exitCode !== null || child.signalCode !== null) return;
  terminateChild(child, "SIGTERM");
  if (!await waitForExit(child, 3_000)) {
    terminateChild(child, "SIGKILL");
    await waitForExit(child, 1_000);
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
