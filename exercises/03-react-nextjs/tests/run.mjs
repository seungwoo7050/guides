import { spawn } from "node:child_process";
import net from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";

const exercise = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const target = path.resolve(exercise, process.argv[2] ?? "work");
const port = await freePort();
const command = process.platform === "win32" ? "pnpm.cmd" : "pnpm";
const child = spawn(command, ["exec", "next", "dev", "-H", "127.0.0.1", "-p", String(port)], {
  cwd: target,
  stdio: ["ignore", "pipe", "pipe"]
});
let output = "";
let spawnError;
child.once("error", (error) => { spawnError = error; });
child.stdout.on("data", (chunk) => { output += chunk.toString(); });
child.stderr.on("data", (chunk) => { output += chunk.toString(); });
try {
  await waitForUrl(`http://127.0.0.1:${port}`, child, () => output, () => spawnError);
  const verifier = path.join(exercise, "tests", "verify-browser.mjs");
  await run(process.execPath, [verifier, `http://127.0.0.1:${port}`], exercise);
} finally {
  child.kill("SIGTERM");
  await new Promise((resolve) => {
    const timer = setTimeout(() => { child.kill("SIGKILL"); resolve(); }, 2_000);
    child.once("exit", () => { clearTimeout(timer); resolve(); });
  });
}

async function waitForUrl(url, processHandle, getOutput, getSpawnError) {
  for (let attempt = 0; attempt < 200; attempt += 1) {
    if (getSpawnError()) throw new Error(`pnpm 또는 Next.js를 시작하지 못했습니다: ${getSpawnError().message}`);
    if (processHandle.exitCode !== null) throw new Error(`Next.js가 일찍 종료되었습니다.\n${getOutput()}`);
    try { const response = await fetch(url); if (response.ok) return; } catch {}
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error(`Next.js 시작을 확인하지 못했습니다.\n${getOutput()}`);
}
function run(command, args, cwd) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { cwd, stdio: "inherit" });
    child.once("error", reject);
    child.once("exit", (code) => code === 0 ? resolve() : reject(new Error(`검증 종료 코드: ${code}`)));
  });
}
function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      if (!address || typeof address === "string") return reject(new Error("빈 포트를 찾지 못했습니다."));
      server.close(() => resolve(address.port));
    });
  });
}
