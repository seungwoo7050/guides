import { spawn } from "node:child_process";
import net from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const exercise = path.join(root, "exercises", "05-postgresql-kysely");
const port = await freePort();
const environment = {
  ...process.env,
  POSTGRES_PORT: String(port),
  DATABASE_URL: `postgres://postgres:postgres@127.0.0.1:${port}/board_dev`
};
const pnpm = process.platform === "win32" ? "pnpm.cmd" : "pnpm";
let primaryError;

try {
  await run("docker", ["compose", "-f", "compose.test.yml", "config", "--quiet"], exercise, environment);
  await run("docker", ["compose", "-f", "compose.test.yml", "up", "-d", "--wait"], exercise, environment);
  await run(pnpm, ["--dir", "reference", "typecheck"], exercise, environment);
  await run(pnpm, ["--dir", "reference", "migrate"], exercise, environment);
  await run(pnpm, ["--dir", "reference", "test"], exercise, environment);
  console.log(`PostgreSQL 실습을 임시 port ${port}에서 확인했습니다.`);
} catch (error) {
  primaryError = error;
} finally {
  try {
    await run("docker", ["compose", "-f", "compose.test.yml", "down", "-v", "--remove-orphans"], exercise, environment);
  } catch (cleanupError) {
    if (!primaryError) primaryError = cleanupError;
    else console.error(`PostgreSQL 정리 실패: ${cleanupError.message}`);
  }
}

if (primaryError) throw primaryError;

function run(command, args, cwd, env) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { cwd, env, stdio: "inherit" });
    child.once("error", (error) => reject(new Error(`${command} 실행 실패: ${error.message}`)));
    child.once("exit", (code, signal) => {
      if (code === 0) resolve();
      else reject(new Error(`${command} ${args.join(" ")} 종료: ${signal ?? code}`));
    });
  });
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
