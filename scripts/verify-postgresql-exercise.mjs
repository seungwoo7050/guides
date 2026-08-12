import { spawn } from "node:child_process";
import net from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const exercise = path.join(root, "exercises", "05-postgresql-kysely");
const port = await freePort();
const composeProject = `guide-webapp-05-${process.pid}-${Math.random().toString(36).slice(2, 8)}`;
const environment = {
  ...process.env,
  POSTGRES_PORT: String(port),
  DATABASE_URL: `postgres://postgres:postgres@127.0.0.1:${port}/board_dev`
};
const pnpm = process.platform === "win32" ? "pnpm.cmd" : "pnpm";
let primaryError;
let activeChild;
let interrupted;

for (const [signal, code] of [["SIGHUP", 129], ["SIGINT", 130], ["SIGTERM", 143]]) {
  process.once(signal, () => {
    interrupted ??= code;
    terminate(activeChild, signal);
  });
}

try {
  await run("docker", ["compose", "-p", composeProject, "-f", "compose.test.yml", "config", "--quiet"], exercise, environment);
  await run("docker", ["compose", "-p", composeProject, "-f", "compose.test.yml", "up", "-d", "--wait", "--wait-timeout", "60"], exercise, environment);
  await run(pnpm, ["--dir", "reference", "typecheck"], exercise, environment);
  await run(pnpm, ["--dir", "reference", "migrate"], exercise, environment);
  await run(pnpm, ["--dir", "reference", "test"], exercise, environment);
  console.log(`PostgreSQL 실습을 임시 port ${port}에서 확인했습니다.`);
} catch (error) {
  primaryError = error;
} finally {
  try {
    await run("docker", ["compose", "-p", composeProject, "-f", "compose.test.yml", "down", "-v", "--remove-orphans"], exercise, environment);
  } catch (cleanupError) {
    if (!primaryError) primaryError = cleanupError;
    else console.error(`PostgreSQL 정리 실패: ${cleanupError.message}`);
  }
}

if (interrupted) process.exit(interrupted);
if (primaryError) throw primaryError;

function run(command, args, cwd, env) {
  return new Promise((resolve, reject) => {
    const detached = process.platform !== "win32";
    const child = spawn(command, args, { cwd, env, detached, stdio: "inherit" });
    activeChild = child;
    child.once("error", (error) => reject(new Error(`${command} 실행 실패: ${error.message}`)));
    child.once("exit", (code, signal) => {
      if (activeChild === child) activeChild = undefined;
      if (code === 0) resolve();
      else reject(new Error(`${command} ${args.join(" ")} 종료: ${signal ?? code}`));
    });
  });
}

function terminate(child, signal = "SIGTERM") {
  if (!child?.pid) return;
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
