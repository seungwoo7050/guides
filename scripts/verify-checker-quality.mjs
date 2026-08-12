import { spawn, spawnSync } from "node:child_process";
import { cp, mkdir, mkdtemp, readFile, rm, rmdir, symlink, writeFile } from "node:fs/promises";
import net from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const packageManager = detectPnpm();
const temporaryRoots = [];
const temporaryParent = path.join(root, ".guide-tmp");
await mkdir(temporaryParent, { recursive: true });
const temporaryBase = await mkdtemp(path.join(temporaryParent, "checker-quality-"));
let cleanupPromise;
let handlingSignal = false;
const activeChildren = new Set();
const activeComposeProjects = new Map();

for (const [signal, code] of [["SIGINT", 130], ["SIGTERM", 143], ["SIGHUP", 129]]) {
  process.once(signal, () => {
    if (handlingSignal) return;
    handlingSignal = true;
    for (const child of activeChildren) terminate(child, signal);
    cleanupActiveComposeProjects();
    cleanupTemporary().finally(() => process.exit(code));
  });
}

try {
  await expectReactMutantFailure();

  await expectPackageMutantFailure(
    "04-fastify-zod-api",
    "src/app.ts",
    'if (!memo) return reply.code(404).send({ code: "not_found", message: "메모를 찾을 수 없습니다." });',
    'if (false && !memo) return reply.code(404).send({ code: "not_found", message: "메모를 찾을 수 없습니다." });'
  );

  await expectPackageMutantFailure(
    "04-fastify-zod-api",
    "src/app.ts",
    'code: "internal_error",',
    'code: "unexpected_failure",'
  );

  await expectPackageMutantFailure(
    "04-fastify-zod-api",
    "src/app.ts",
    'return reply.code(400).send({ code: "invalid_request", message: "요청이 올바르지 않습니다." });',
    'return reply.code(400).send({ code: "invalid_request", message: "요청이 올바르지 않습니다.", issues: parsed.error.issues });'
  );

  await expectPackageMutantFailure(
    "04-fastify-zod-api",
    "src/app.ts",
    'return reply.code(409).send({ code: error.message, message: "title already exists" });',
    'return reply.code(409).send({ code: error.message, message: "title already exists", internal: "duplicate-title" });'
  );

  await expectPackageMutantFailure(
    "06-security",
    "src/app.ts",
    'if (actor.id !== id && actor.role !== "admin") return forbidden(reply);',
    'if (false) return forbidden(reply);'
  );

  await expectPackageMutantFailure(
    "06-security",
    "src/app.ts",
    'if (!origin || !allowedOrigins.includes(origin)) {',
    'if (false) {'
  );

  await expectPackageMutantFailure(
    "06-security",
    "src/app.ts",
    'if (!origin || !allowedOrigins.includes(origin)) {',
    'if (!origin || !origin.endsWith("localhost:3000")) {'
  );

  await expectPackageMutantFailure(
    "07-websocket",
    "src/app.ts",
    'if (client.role === "viewer" && event.type !== "cursor.move") {',
    'if (false) {'
  );

  await expectPackageMutantFailure(
    "07-websocket",
    "src/app.ts",
    'if (client.role === "viewer" && event.type !== "cursor.move") {',
    'if (client.role === "viewer" && event.type === "item.create") {'
  );

  await expectPackageMutantFailure(
    "07-websocket",
    "src/app.ts",
    'if (client.role === "viewer" && event.type !== "cursor.move") {',
    'if (client.role === "viewer" && event.type !== "cursor.move" && event.type !== "item.move") {'
  );

  await expectPackageMutantFailure(
    "07-websocket",
    "src/app.ts",
    'if (!item || item.version !== event.baseVersion) {',
    'if (!item) {'
  );

  await expectPackageMutantFailure(
    "07-websocket",
    "src/app.ts",
    'if (!item || item.version !== event.baseVersion) {',
    'if (!item || event.baseVersion > item.version) {'
  );

  await expectPackageMutantFailure(
    "07-websocket",
    "src/app.ts",
    'if (!item || item.version !== event.baseVersion) {',
    'if (!item || (event.type === "item.update" && item.version !== event.baseVersion)) {'
  );

  await expectPackageMutantFailure(
    "07-websocket",
    "src/app.ts",
    'if (event.type === "item.update" || event.type === "item.move") {',
    'if (event.type === "item.move") return;\n      if (event.type === "item.update") {'
  );

  await expectPackageMutantFailure(
    "07-websocket",
    "src/app.ts",
    '          if (!event.final) {',
    '          if (!event.final) {\n            item.x = event.x;\n            item.y = event.y;'
  );

  await expectPackageMutantFailure(
    "07-websocket",
    "src/app.ts",
    '                x: event.x,\n                y: event.y,',
    '                x: 0,\n                y: 0,'
  );

  await expectPackageMutantFailure(
    "07-websocket",
    "src/app.ts",
    'if (event.type === "snapshot.request") {',
    'if (false && event.type === "snapshot.request") {'
  );

  await expectPackageMutantFailure(
    "07-websocket",
    "src/app.ts",
    'if (event.type === "snapshot.request") {',
    'if (event.type === "snapshot.request" && (event.afterSequence === undefined || event.afterSequence === 0)) {'
  );

  await expectPackageMutantFailure(
    "08-testing",
    "src/counter.ts",
    'if (action.type === "decrement") return Math.max(0, value - 1);',
    'if (action.type === "decrement") return value - 1;'
  );

  await expectTestingBrowserMutantFailure();
  await expectDatabaseMutantFailures();
  console.log("알려진 잘못된 React·API·DB·보안·WebSocket·단위·브라우저 구현을 각 검사기가 거부함을 확인했습니다.");
} finally {
  await cleanupTemporary();
}

function cleanupTemporary() {
  cleanupPromise ??= (async () => {
    await Promise.allSettled(temporaryRoots.map((directory) => rm(directory, { recursive: true, force: true })));
    await rm(temporaryBase, { recursive: true, force: true });
    await rmdir(temporaryParent).catch((error) => {
      if (error?.code !== "ENOENT" && error?.code !== "ENOTEMPTY") throw error;
    });
  })();
  return cleanupPromise;
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
    '<button id="increment">증가</button>',
    '<div id="increment">증가</div>'
  );
  const result = await runPackage(["--dir", temporary, "test:e2e"], root, process.env, 180_000);
  expectFailure(result, `${exerciseName}: 접근 가능한 증가 버튼을 제거한 구현이 browser 검사를 통과했습니다.`);
  console.log(`${exerciseName}: browser-accessibility mutation을 정상적으로 검출했습니다.`);
}

async function expectDatabaseMutantFailures() {
  const exerciseName = "05-postgresql-kysely";
  const composePrefix = process.env.GUIDE_WEBAPP_MUTANT_COMPOSE_PROJECT ?? `guide-webapp-quality-${process.pid}`;
  const baseline = await copyReference(exerciseName);
  await runDatabaseSuite(baseline, `${composePrefix}-baseline`, true, "baseline");

  const mutations = [
    {
      label: "고유 제약",
      file: "migrations/001_initial.sql",
      original: "  created_at timestamptz not null default now(),\n  unique (event_id, seat_no)\n);",
      replacement: "  created_at timestamptz not null default now()\n);"
    },
    {
      label: "감사 기록",
      file: "src/repository.ts",
      original: '  await trx.insertInto("reservation_audit").values({\n    reservation_id: reservation.id,\n    action: "reserved"\n  }).executeTakeFirstOrThrow();',
      replacement: "  // mutation: reservation audit omitted"
    },
    {
      label: "rollback 주입",
      file: "src/repository.ts",
      original: "  await options.afterReservation?.();",
      replacement: "  // mutation: injected failure ignored"
    },
    {
      label: "autocommit 보상 삭제",
      replacements: [
        {
          file: "src/repository.ts",
          original: "    return await db.transaction().execute(async (trx) => reserveInTransaction(trx, input, options));",
          replacement: "    return await reserveInTransaction(db as unknown as Transaction<Database>, input, options);"
        },
        {
          file: "src/repository.ts",
          original: "    throw error;",
          replacement: "    await db.deleteFrom(\"reservation_audit\").where(\"reservation_id\", \"in\", db.selectFrom(\"reservations\").select(\"id\").where(\"event_id\", \"=\", input.eventId).where(\"seat_no\", \"=\", input.seatNo)).execute();\n    await db.deleteFrom(\"reservations\").where(\"event_id\", \"=\", input.eventId).where(\"seat_no\", \"=\", input.seatNo).execute();\n    throw error;"
        }
      ]
    },
    {
      label: "SQL raw 보간",
      replacements: [
        {
          file: "src/repository.ts",
          original: 'import type { Kysely, Transaction } from "kysely";',
          replacement: 'import { sql, type Kysely, type Transaction } from "kysely";'
        },
        {
          file: "src/repository.ts",
          original: '  return db.insertInto("events").values({ name }).returningAll().executeTakeFirstOrThrow();',
          replacement: "  return db.insertInto(\"events\").values({ name: sql.raw<string>(`'${name}'`) }).returningAll().executeTakeFirstOrThrow();"
        }
      ]
    },
    {
      label: "부분 수동 escape 뒤 SQL raw 보간",
      replacements: [
        {
          file: "src/repository.ts",
          original: 'import type { Kysely, Transaction } from "kysely";',
          replacement: 'import { sql, type Kysely, type Transaction } from "kysely";'
        },
        {
          file: "src/repository.ts",
          original: '  return db.insertInto("events").values({ name }).returningAll().executeTakeFirstOrThrow();',
          replacement: "  const escaped = name.replace(\"'\", \"''\");\n  return db.insertInto(\"events\").values({ name: sql.raw<string>(`'${escaped}'`) }).returningAll().executeTakeFirstOrThrow();"
        }
      ]
    }
  ];

  for (const [index, mutation] of mutations.entries()) {
    const temporary = await copyReference(exerciseName);
    const replacements = mutation.replacements ?? [mutation];
    for (const replacement of replacements) {
      await replaceExactly(
        path.join(temporary, replacement.file),
        replacement.original,
        replacement.replacement
      );
    }
    await runDatabaseSuite(
      temporary,
      `${composePrefix}-${index}`,
      false,
      mutation.label
    );
    console.log(`${exerciseName}: ${mutation.label} mutation을 정상적으로 검출했습니다.`);
  }
}

async function runDatabaseSuite(temporary, composeProject, expectSuccess, label) {
  const exerciseRoot = path.join(root, "exercises", "05-postgresql-kysely");
  const port = await freePort();
  const environment = {
    ...process.env,
    POSTGRES_PORT: String(port),
    DATABASE_URL: `postgres://postgres:postgres@127.0.0.1:${port}/board_dev`
  };
  activeComposeProjects.set(composeProject, { exerciseRoot, environment });
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
      expectFailure(result, `05-postgresql-kysely: ${label} 결함이 test를 통과했습니다.`);
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
    activeComposeProjects.delete(composeProject);
    if (cleanup.code !== 0 && !primaryError) primaryError = new Error(`PostgreSQL quality 정리 실패\n${cleanup.output}`);
  }
  if (primaryError) throw primaryError;
}

function cleanupActiveComposeProjects() {
  for (const [composeProject, { exerciseRoot, environment }] of activeComposeProjects) {
    const cleanup = spawnSync(
      "docker",
      ["compose", "-p", composeProject, "-f", "compose.test.yml", "down", "-v", "--remove-orphans"],
      { cwd: exerciseRoot, env: environment, encoding: "utf8", timeout: 120_000 }
    );
    if (cleanup.status !== 0) {
      console.error(`signal cleanup 실패 (${composeProject})\n${cleanup.stdout ?? ""}\n${cleanup.stderr ?? ""}`);
    }
    activeComposeProjects.delete(composeProject);
  }
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
  // Next.js 16 Turbopack은 filesystem root 밖의 node_modules symlink를 거절한다.
  // 저장소 안의 ignore된 run 전용 경로를 사용해 reference 의존성을 공유하되 finally에서 제거한다.
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
    activeChildren.add(child);
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
      activeChildren.delete(child);
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
