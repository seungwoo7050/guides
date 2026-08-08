import { spawnSync } from "node:child_process";
import { createServer } from "node:net";

const host = "127.0.0.1";
const port = await findAvailablePort();
const forwarded = process.argv.slice(2);
const env = {
  ...process.env,
  CATALOG_E2E_PORT: String(port)
};

const npmExecPath = process.env.npm_execpath;
let command;
let args;

if (npmExecPath) {
  command = process.execPath;
  args = [npmExecPath, "exec", "playwright", "test", ...forwarded];
} else {
  command = "pnpm";
  args = ["exec", "playwright", "test", ...forwarded];
}

const result = spawnSync(command, args, {
  stdio: "inherit",
  env
});

if (result.error) {
  console.error(`Playwright 실행 실패: ${result.error.message}`);
  process.exit(1);
}
if (result.signal) {
  console.error(`Playwright가 signal로 종료되었습니다: ${result.signal}`);
  process.exit(1);
}
process.exit(result.status ?? 1);

async function findAvailablePort() {
  const server = createServer();
  server.unref();
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, host, resolve);
  });
  const address = server.address();
  if (typeof address !== "object" || address === null) {
    server.close();
    throw new Error("사용 가능한 Playwright port를 확인하지 못했습니다.");
  }
  const selected = address.port;
  await new Promise((resolve, reject) =>
    server.close((error) => (error ? reject(error) : resolve()))
  );
  return selected;
}
