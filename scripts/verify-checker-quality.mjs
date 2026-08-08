import { spawn, spawnSync } from "node:child_process";
import { cp, mkdtemp, readFile, rm, symlink, writeFile } from "node:fs/promises";
import net from "node:net";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const packageManager = detectPnpm();
const temporaryRoots = [];
const temporaryBase = process.env.GUIDE_VERIFY_TEMP_ROOT ?? tmpdir();

try {
  await expectReactMutantFailure();

  await expectPackageMutantFailure(
    "04-fastify-zod-api",
    "src/app.ts",
    'if (!memo) return reply.code(404).send({ code: "not_found", message: "메모를 찾을 수 없습니다." });',
    'if (false && !memo) return reply.code(404).send({ code: "not_found", message: "메모를 찾을 수 없습니다." });'
  );

  await expectPackageMutantFailure(
    "06-security",
    "src/app.ts",
    'if (actor.id !== id && actor.role !== "admin") return forbidden(reply);',
    'if (false) return forbidden(reply);'
  );

  await expectPackageMutantFailure(
    "07-websocket",
    "src/app.ts",
    'if (client.role !== "editor") return client.socket.close(1008, "write permission required");',
    'if (false) return client.socket.close(1008, "write permission required");'
  );

  await expectPackageMutantFailure(
    "08-testing",
    "src/counter.ts",
    'if (action.type === "decrement") return Math.max(0, value - 1);',
    'if (action.type === "decrement") return value - 1;'
  );

  await expectTestingBrowserMutantFailure();
  await expectDatabaseMutantFailure();
  console.log("알려진 잘못된 React·API·DB·보안·WebSocket·단위·브라우저 구현을 각 검사기가 거부함을 확인했습니다.");
} finally {
  await Promise.allSettled(temporaryRoots.map((directory) => rm(directory, { recursive: true, force: true })));
}

async function expectReactMutantFailure() {
  const exerciseName = "03-react-nextjs";
  const temporary = await copyReference(exerciseName);
  await runReactBrowserRequired(temporary, "baseline");
  await replaceExactly(
    path.join(temporary, "app", "page.tsx"),
    "return () => controller.abort();",
    "return () => {};"
  );
  const result = await runReactBrowser(temporary);
  expectFailure(result, `${exerciseName}: 취소되지 않은 이전 요청이 browser 검사를 통과했습니다.`);
  console.log(`${exerciseName}: stale-response mutation을 정상적으로 검출했습니다.`);
}

async function expectPackageMutantFailure(exerciseName, relativeFile, original, replacement) {
  const temporary = await copyReference(exerciseName);
  await runPackageRequired(["--dir", temporary, "test"], root, process.env, `${exerciseName} baseline`);
  await replaceExactly(path.join(temporary, relativeFile), original, replacement);
  const result = await runPackage(["--dir", temporary, "test"], root, process.env);
  expectFailure(result, `${exerciseName}: 알려진 잘못된 구현이 test를 통과했습니다.`);
  console.log(`${exerciseName}: mutation을 정상적으로 검출했습니다.`);
}

async function expectTestingBrowserMutantFailure() {
  const exerciseName = "08-testing";
  const temporary = await copyReference(exerciseName);
  await runPackageRequired(["--dir", temporary, "test:e2e"], root, process.env, `${exerciseName} browser baseline`, 180_000);
  await replaceExactly(
    path.join(temporary, "src", "app.ts"),
    '<button id="increment" type="button">증가</button>',
    '<div id="increment">증가</div>'
  );
  const result = await runPackage(["--dir", temporary, "test:e2e"], root, process.env, 180_000);
  expectFailure(result, `${exerciseName}: 접근 가능한 증가 버튼을 제거한 구현이 browser 검사를 통과했습니다.`);
  console.log(`${exerciseName}: browser-accessibility mutation을 정상적으로 검출했습니다.`);
}

async function expectDatabaseMutantFailure() {
  const exerciseName = "05-postgresql-kysely";
  const temporary = await copyReference(exerciseName);
  const composeProject = process.env.GUIDE_WEBAPP_MUTANT_COMPOSE_PROJECT ?? `guide-webapp-quality-${process.pid}`;

  await runDatabaseSuite(temporary, composeProject, true);
  await replaceExactly(
    path.join(temporary, "migrations", "001_initial.sql"),
    "  created_at timestamptz not null default now(),\n  unique (event_id, seat_no)\n);",
    "  created_at timestamptz not null default now()\n);"
  );
  await runDatabaseSuite(temporary, composeProject, false);
  console.log(`${exerciseName}: 고유 제약 mutation을 정상적으로 검출했습니다.`);
}

async function runDatabaseSuite(temporary, composeProject, expectSuccess) {
  const exerciseRoot = path.join(root, "exercises", "05-postgresql-kysely");
  const port = await freePort();
  const environment = {
    ...process.env,
    POSTGRES_PORT: String(port),
    DATABASE_URL: `postgres://postgres:postgres@127.0.0.1:${port}/board_dev`
  };
  let primaryError;
  try {
    await runRequired(
      "docker",
      ["compose", "-p", composeProject, "-f", "compose.test.yml", "up", "-d", "--wait", "--wait-timeout", "60"],
      exerciseRoot,
      environment,
      "PostgreSQL quality container",
      120_000
    );
    await runPackageRequired(["--dir", temporary, "typecheck"], root, environment, "PostgreSQL quality typecheck");
    await runPackageRequired(["--dir", temporary, "migrate"], root, environment, "PostgreSQL quality migration");
    const result = await runPackage(["--dir", temporary, "test"], root, environment, 120_000);
    if (expectSuccess) {
      if (result.code !== 0) throw new Error(`PostgreSQL baseline 검사가 실패했습니다.\n${result.output}`);
    } else {
      expectFailure(result, "05-postgresql-kysely: 고유 제약이 없는 migration이 test를 통과했습니다.");
    }
  } catch (error) {
    primaryError = error;
  } finally {
    const cleanup = await run(
      "docker",
      ["compose", "-p", composeProject, "-f", "compose.test.yml", "down", "-v", "--remove-orphans"],
      exerciseRoot,
      environment,
      120_000
    );
    if (cleanup.code !== 0 && !primaryError) primaryError = new Error(`PostgreSQL quality 정리 실패\n${cleanup.output}`);
  }
  if (primaryError) throw primaryError;
}

async function runReactBrowser(temporary) {
  return run(
    process.execPath,
    [path.join(root, "exercises", "03-react-nextjs", "tests", "run.mjs"), temporary],
    root,
    process.env,
    180_000
  );
}

async function runReactBrowserRequired(temporary, label) {
  const result = await runReactBrowser(temporary);
  if (result.code !== 0) throw new Error(`03-react-nextjs ${label} 실패\n${result.output}`);
}

async function copyReference(exerciseName) {
  const source = path.join(root, "exercises", exerciseName, "reference");
  const temporary = await mkdtemp(path.join(temporaryBase, `${exerciseName}-mutant-`));
  temporaryRoots.push(temporary);
  await cp(source, temporary, {
    recursive: true,
    filter(sourcePath) {
      return !["node_modules", ".next", ".turbo", "coverage", "playwright-report", "test-results"].includes(path.basename(sourcePath));
    }
  });
  await symlink(path.join(source, "node_modules"), path.join(temporary, "node_modules"), "dir");
  return temporary;
}

async function replaceExactly(file, original, replacement) {
  const source = await readFile(file, "utf8");
  const occurrences = source.split(original).length - 1;
  if (occurrences !== 1) throw new Error(`${path.relative(root, file)} mutation 기준 문자열 개수: ${occurrences}`);
  await writeFile(file, source.replace(original, replacement));
}

function expectFailure(result, message) {
  if (result.timedOut) throw new Error(`${message}\n검사가 제한 시간 안에 종료되지 않았습니다.\n${result.output}`);
  if (result.code === 0) throw new Error(`${message}\n${result.output}`);
}

function detectPnpm() {
  const direct = process.platform === "win32" ? "pnpm.cmd" : "pnpm";
  if (spawnSync(direct, ["--version"], { stdio: "ignore" }).status === 0) return { command: direct, prefix: [] };
  if (spawnSync("corepack", ["pnpm", "--version"], { stdio: "ignore" }).status === 0) {
    return { command: "corepack", prefix: ["pnpm"] };
  }
  throw new Error("pnpm 또는 corepack pnpm을 실행할 수 없습니다.");
}

function runPackage(args, cwd, env, timeoutMs = 120_000) {
  return run(packageManager.command, [...packageManager.prefix, ...args], cwd, env, timeoutMs);
}

async function runPackageRequired(args, cwd, env, label, timeoutMs = 120_000) {
  const result = await runPackage(args, cwd, env, timeoutMs);
  if (result.code !== 0) throw new Error(`${label} 실패${result.timedOut ? " (timeout)" : ""}\n${result.output}`);
}

async function runRequired(command, args, cwd, env, label, timeoutMs = 120_000) {
  const result = await run(command, args, cwd, env, timeoutMs);
  if (result.code !== 0) throw new Error(`${label} 실패${result.timedOut ? " (timeout)" : ""}\n${result.output}`);
}

function run(command, args, cwd, env, timeoutMs = 120_000) {
  return new Promise((resolve) => {
    const detached = process.platform !== "win32";
    const child = spawn(command, args, {
      cwd,
      env,
      detached,
      stdio: ["ignore", "pipe", "pipe"]
    });
    let output = "";
    let completed = false;
    let timedOut = false;
    let forceTimer;

    const timer = setTimeout(() => {
      timedOut = true;
      terminate(child, "SIGTERM");
      forceTimer = setTimeout(() => terminate(child, "SIGKILL"), 5_000);
      forceTimer.unref();
    }, timeoutMs);
    timer.unref();

    child.stdout?.on("data", (chunk) => { output += chunk; });
    child.stderr?.on("data", (chunk) => { output += chunk; });
    child.once("error", (error) => finish(127, null, `${output}\n${error.message}`));
    child.once("exit", (code, signal) => finish(code ?? 1, signal, output));

    function finish(code, signal, captured) {
      if (completed) return;
      completed = true;
      clearTimeout(timer);
      if (forceTimer) clearTimeout(forceTimer);
      resolve({ code: timedOut ? 124 : code, signal, output: captured, timedOut });
    }
  });
}

function terminate(child, signal) {
  if (!child.pid) return;
  try {
    if (process.platform === "win32") child.kill(signal);
    else process.kill(-child.pid, signal);
  } catch {
    try { child.kill(signal); } catch {}
  }
}

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      if (!address || typeof address === "string") {
        server.close();
        reject(new Error("빈 PostgreSQL port를 찾지 못했습니다."));
        return;
      }
      server.close((error) => error ? reject(error) : resolve(address.port));
    });
  });
}
