import { spawn } from "node:child_process";
import { randomUUID } from "node:crypto";
import { once } from "node:events";
import { createServer } from "node:net";
import path from "node:path";
import { setTimeout as delay } from "node:timers/promises";
import { fileURLToPath } from "node:url";

const projectRoot = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const host = "127.0.0.1";
const maximumOutput = 64 * 1024;

await main().catch((error) => {
  console.error(formatError(error));
  process.exitCode = 1;
});

async function main() {
  const port = await findAvailablePort();
  const baseURL = `http://${host}:${port}`;
  const release = `smoke-${randomUUID()}`;
  const secretCanary = `server-only-${randomUUID()}`;
  let child;
  let primaryFailure;
  let cleanupFailure;
  let output = "";
  let launchFailure;

  try {
    child = spawn("pnpm", ["start", "--hostname", host, "--port", String(port)], {
      cwd: projectRoot,
      detached: process.platform !== "win32",
      env: {
        ...process.env,
        APP_RELEASE: release,
        CATALOG_SERVER_ONLY_CANARY: secretCanary
      },
      stdio: ["ignore", "pipe", "pipe"]
    });
    child.once("error", (error) => {
      launchFailure = error;
    });
    child.stdout?.on("data", (chunk) => {
      output = appendBounded(output, String(chunk));
    });
    child.stderr?.on("data", (chunk) => {
      output = appendBounded(output, String(chunk));
    });

    await waitForHealth({ baseURL, child, getLaunchFailure: () => launchFailure, getOutput: () => output });
    await verifyHealth(baseURL, release, secretCanary);
    const html = await fetchText(`${baseURL}/`, 3_000);
    if (!/<h1[^>]*>프로젝트 목록<\/h1>/.test(html)) {
      throw new Error("루트 HTML에서 프로젝트 목록 제목을 찾지 못했습니다.");
    }
    assertSecretAbsent(html, secretCanary, "루트 HTML");

    const search = await fetchJson(`${baseURL}/api/projects?page=1`, 3_000);
    if (
      typeof search !== "object" ||
      search === null ||
      !("projects" in search) ||
      !Array.isArray(search.projects)
    ) {
      throw new Error("프로젝트 API의 최소 검색 계약이 올바르지 않습니다.");
    }
    assertSecretAbsent(JSON.stringify(search), secretCanary, "프로젝트 API");

    const scripts = extractScriptSources(html);
    if (scripts.length === 0) throw new Error("초기 HTML에서 JavaScript 산출물을 찾지 못했습니다.");
    for (const source of scripts) {
      const script = await fetchText(new URL(source, baseURL).toString(), 3_000);
      assertSecretAbsent(script, secretCanary, `JavaScript 산출물 ${source}`);
    }

    console.log(`production smoke 통과: ${baseURL} (${release})`);
  } catch (error) {
    primaryFailure = withServerOutput(error, output);
  } finally {
    try {
      if (child) await stopChildTree(child);
    } catch (error) {
      cleanupFailure = withServerOutput(error, output);
    }
  }

  if (primaryFailure && cleanupFailure) {
    throw new AggregateError(
      [primaryFailure, cleanupFailure],
      "smoke 검증과 server process 정리가 모두 실패했습니다."
    );
  }
  if (primaryFailure) throw primaryFailure;
  if (cleanupFailure) throw cleanupFailure;
}

async function waitForHealth({ baseURL, child, getLaunchFailure, getOutput }) {
  const deadline = Date.now() + 20_000;
  while (Date.now() < deadline) {
    const launchFailure = getLaunchFailure();
    if (launchFailure) throw new Error(`pnpm start 실행 실패: ${launchFailure.message}`);
    if (hasExited(child)) {
      throw new Error(
        `production server가 준비되기 전에 종료되었습니다. code=${child.exitCode} signal=${child.signalCode}\n${getOutput()}`
      );
    }
    try {
      const response = await fetchWithTimeout(`${baseURL}/api/health`, {}, 1_000);
      if (response.ok) return;
    } catch {
      // 준비 중에는 연결 거부와 timeout을 다시 확인합니다.
    }
    await delay(100);
  }
  throw new Error(`production server가 제한 시간 안에 준비되지 않았습니다.\n${getOutput()}`);
}

async function verifyHealth(baseURL, release, secretCanary) {
  const response = await fetchWithTimeout(`${baseURL}/api/health`, {}, 3_000);
  if (!response.ok) throw new Error(`health 응답 실패: ${response.status}`);
  const body = await response.json();
  const keys = Object.keys(body).sort();
  if (keys.join(",") !== "release,status") {
    throw new Error(`health 공개 필드가 정확하지 않습니다: ${keys.join(",")}`);
  }
  if (body.status !== "ok" || body.release !== release) {
    throw new Error("health status 또는 release가 실행 환경과 일치하지 않습니다.");
  }
  const cacheControl = response.headers.get("cache-control") ?? "";
  if (!cacheControl.toLocaleLowerCase().includes("no-store")) {
    throw new Error("health 응답에 Cache-Control: no-store가 없습니다.");
  }
  assertSecretAbsent(JSON.stringify(body), secretCanary, "health 응답");
}

async function fetchText(url, timeout) {
  const response = await fetchWithTimeout(url, {}, timeout);
  if (!response.ok) throw new Error(`${url} 응답 실패: ${response.status}`);
  return response.text();
}

async function fetchJson(url, timeout) {
  const response = await fetchWithTimeout(url, {}, timeout);
  if (!response.ok) throw new Error(`${url} 응답 실패: ${response.status}`);
  return response.json();
}

function fetchWithTimeout(url, init, timeout) {
  return fetch(url, { ...init, signal: AbortSignal.timeout(timeout) });
}

function extractScriptSources(html) {
  const sources = [];
  for (const match of html.matchAll(/<script[^>]+src=["']([^"']+\.js(?:\?[^"']*)?)["'][^>]*>/g)) {
    sources.push(match[1].replaceAll("&amp;", "&"));
  }
  return [...new Set(sources)];
}

function assertSecretAbsent(content, secret, label) {
  if (content.includes(secret)) throw new Error(`${label}에 server-only secret이 노출되었습니다.`);
}

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
    throw new Error("사용 가능한 TCP port를 확인하지 못했습니다.");
  }
  const port = address.port;
  await new Promise((resolve, reject) => server.close((error) => (error ? reject(error) : resolve())));
  return port;
}

async function stopChildTree(child) {
  if (!child.pid || hasExited(child)) return;
  sendSignal(child, "SIGTERM");
  if (await waitForExit(child, 2_000)) return;
  sendSignal(child, "SIGKILL");
  if (await waitForExit(child, 2_000)) return;
  throw new Error(`production server process가 종료되지 않았습니다: pid=${child.pid}`);
}

function sendSignal(child, signal) {
  if (!child.pid || hasExited(child)) return;
  try {
    if (process.platform !== "win32") process.kill(-child.pid, signal);
    else child.kill(signal);
  } catch (error) {
    if (error?.code !== "ESRCH") throw error;
  }
}

async function waitForExit(child, timeout) {
  if (hasExited(child)) return true;
  await Promise.race([once(child, "exit"), delay(timeout)]);
  return hasExited(child);
}

function hasExited(child) {
  return child.exitCode !== null || child.signalCode !== null;
}

function appendBounded(current, addition) {
  const next = current + addition;
  return next.length <= maximumOutput ? next : next.slice(next.length - maximumOutput);
}

function withServerOutput(error, output) {
  const message = error instanceof Error ? error.message : String(error);
  const wrapped = new Error(output ? `${message}\n--- production server output ---\n${output}` : message);
  if (error instanceof Error && error.stack) wrapped.stack = `${wrapped.stack}\nCaused by:\n${error.stack}`;
  return wrapped;
}

function formatError(error) {
  if (error instanceof AggregateError) {
    return [error.message, ...error.errors.map((entry) => formatError(entry))].join("\n\n");
  }
  return error instanceof Error ? error.stack ?? error.message : String(error);
}
