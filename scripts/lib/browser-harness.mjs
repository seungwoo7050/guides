import { spawn } from "node:child_process";
import { createServer } from "node:http";
import { access, mkdtemp, readFile, rm, stat } from "node:fs/promises";
import net from "node:net";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

const MIME = new Map([
  [".html", "text/html; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".mjs", "text/javascript; charset=utf-8"],
  [".css", "text/css; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".svg", "image/svg+xml"],
  [".png", "image/png"]
]);

export async function startStaticServer(directory) {
  const root = path.resolve(directory);
  const server = createServer(async (request, response) => {
    try {
      const url = new URL(request.url ?? "/", "http://localhost");
      const decoded = decodeURIComponent(url.pathname);
      const candidate = path.resolve(root, `.${decoded}`);
      if (candidate !== root && !candidate.startsWith(`${root}${path.sep}`)) {
        response.writeHead(403).end("forbidden");
        return;
      }

      let file = candidate;
      const info = await stat(file).catch(() => null);
      if (info?.isDirectory()) file = path.join(file, "index.html");
      const body = await readFile(file);
      response.writeHead(200, {
        "content-type": MIME.get(path.extname(file)) ?? "application/octet-stream",
        "cache-control": "no-store"
      });
      response.end(body);
    } catch {
      response.writeHead(404).end("not found");
    }
  });

  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  const address = server.address();
  if (!address || typeof address === "string") throw new Error("정적 서버 포트를 확인하지 못했습니다.");
  return {
    url: `http://127.0.0.1:${address.port}`,
    close: () => new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()))
  };
}

export async function launchBrowser(url, options = {}) {
  const executable = await findBrowser();
  const port = await freePort();
  const profile = await mkdtemp(path.join(os.tmpdir(), "guide-web-browser-"));
  const browserArgs = [
    "--headless=new",
    "--disable-background-networking",
    "--disable-component-update",
    "--disable-default-apps",
    "--disable-extensions",
    "--disable-features=Translate",
    "--disable-sync",
    "--metrics-recording-only",
    "--no-first-run",
    "--no-proxy-server",
    "--proxy-bypass-list=*",
    "--allow-insecure-localhost",
    "--allow-file-access-from-files",
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profile}`,
    "about:blank"
  ];
  if (process.getuid?.() === 0 || process.env.CHROMIUM_NO_SANDBOX === "1") {
    browserArgs.splice(-3, 0, "--no-sandbox");
  }
  const child = spawn(executable, browserArgs, { stdio: ["ignore", "ignore", "pipe"] });

  let stderr = "";
  child.stderr.on("data", (chunk) => { stderr += chunk.toString(); });
  const version = await pollJson(`http://127.0.0.1:${port}/json/version`, child, () => stderr);
  const target = await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: "PUT" }).then((response) => {
    if (!response.ok) throw new Error(`브라우저 탭을 열지 못했습니다: HTTP ${response.status}`);
    return response.json();
  });
  const session = new CdpSession(target.webSocketDebuggerUrl);
  await session.open();
  await Promise.all([
    session.call("Page.enable"),
    session.call("Runtime.enable"),
    session.call("DOM.enable")
  ]);
  await session.call("Emulation.setDeviceMetricsOverride", {
    width: options.width ?? 1280,
    height: options.height ?? 800,
    deviceScaleFactor: 1,
    mobile: false
  });
  let destination = url;
  if (options.serveDirectory) {
    const staticRoot = path.resolve(options.serveDirectory);
    destination = "http://guide.local/";
    await session.call("Fetch.enable", { patterns: [{ urlPattern: "http://guide.local/*" }] });
    session.on("Fetch.requestPaused", async ({ requestId, request }) => {
      try {
        const parsed = new URL(request.url);
        const decoded = decodeURIComponent(parsed.pathname);
        const candidate = path.resolve(staticRoot, `.${decoded}`);
        if (candidate !== staticRoot && !candidate.startsWith(`${staticRoot}${path.sep}`)) {
          await session.call("Fetch.fulfillRequest", { requestId, responseCode: 403, body: Buffer.from("forbidden").toString("base64") });
          return;
        }
        let file = candidate;
        const info = await stat(file).catch(() => null);
        if (info?.isDirectory()) file = path.join(file, "index.html");
        const body = await readFile(file);
        await session.call("Fetch.fulfillRequest", {
          requestId,
          responseCode: 200,
          responseHeaders: [
            { name: "Content-Type", value: MIME.get(path.extname(file)) ?? "application/octet-stream" },
            { name: "Cache-Control", value: "no-store" }
          ],
          body: body.toString("base64")
        });
      } catch {
        await session.call("Fetch.fulfillRequest", { requestId, responseCode: 404, body: Buffer.from("not found").toString("base64") });
      }
    });
  }
  await session.call("Page.navigate", { url: destination });
  await waitFor(async () => await session.evaluate("document.readyState") === "complete", 10_000, "페이지 로드");

  return {
    version: version.Browser,
    evaluate: (expression) => session.evaluate(expression),
    call: (method, params) => session.call(method, params),
    on: (method, handler) => session.on(method, handler),
    async resize(width, height) {
      await session.call("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false });
    },
    async press(key) {
      const code = key === "Tab" ? "Tab" : key === "Enter" ? "Enter" : key;
      const keyCode = key === "Tab" ? 9 : key === "Enter" ? 13 : 0;
      await session.call("Input.dispatchKeyEvent", { type: "keyDown", key, code, windowsVirtualKeyCode: keyCode });
      await session.call("Input.dispatchKeyEvent", { type: "keyUp", key, code, windowsVirtualKeyCode: keyCode });
    },
    waitFor: (predicate, timeout, label) => waitFor(predicate, timeout, label),
    async close() {
      session.close();
      child.kill("SIGTERM");
      await new Promise((resolve) => {
        const timer = setTimeout(() => { child.kill("SIGKILL"); resolve(); }, 2_000);
        child.once("exit", () => { clearTimeout(timer); resolve(); });
      });
      await rm(profile, { recursive: true, force: true });
    }
  };
}

export async function waitFor(predicate, timeout = 5_000, label = "조건") {
  const started = Date.now();
  let lastError;
  while (Date.now() - started < timeout) {
    try {
      if (await predicate()) return;
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, 40));
  }
  const suffix = lastError instanceof Error ? `: ${lastError.message}` : "";
  throw new Error(`${label}을 ${timeout}ms 안에 확인하지 못했습니다${suffix}`);
}

async function findBrowser() {
  const candidates = [
    process.env.CHROMIUM_PATH,
    process.env.CHROME_PATH,
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/google-chrome",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium"
  ].filter(Boolean);
  for (const candidate of candidates) {
    try { await access(candidate); return candidate; } catch {}
  }
  throw new Error("Chromium 또는 Chrome을 찾지 못했습니다. CHROMIUM_PATH를 설정해 주세요.");
}

async function freePort() {
  const server = net.createServer();
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  const address = server.address();
  if (!address || typeof address === "string") throw new Error("빈 포트를 찾지 못했습니다.");
  await new Promise((resolve) => server.close(resolve));
  return address.port;
}

async function pollJson(url, child, stderr) {
  for (let attempt = 0; attempt < 200; attempt += 1) {
    if (child.exitCode !== null) throw new Error(`브라우저가 일찍 종료되었습니다.\n${stderr()}`);
    try {
      const response = await fetch(url);
      if (response.ok) return await response.json();
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
  throw new Error(`브라우저 디버깅 포트가 열리지 않았습니다.\n${stderr()}`);
}

class CdpSession {
  constructor(url) {
    this.url = url;
    this.nextId = 1;
    this.pending = new Map();
    this.listeners = new Map();
  }

  async open() {
    this.socket = new WebSocket(this.url);
    await new Promise((resolve, reject) => {
      this.socket.addEventListener("open", resolve, { once: true });
      this.socket.addEventListener("error", reject, { once: true });
    });
    this.socket.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);
      if (!message.id) {
        for (const handler of this.listeners.get(message.method) ?? []) {
          Promise.resolve(handler(message.params ?? {})).catch((error) => console.error(error));
        }
        return;
      }
      const pending = this.pending.get(message.id);
      if (!pending) return;
      this.pending.delete(message.id);
      if (message.error) pending.reject(new Error(`${pending.method}: ${message.error.message}`));
      else pending.resolve(message.result ?? {});
    });
    this.socket.addEventListener("close", () => {
      for (const pending of this.pending.values()) pending.reject(new Error("브라우저 연결이 닫혔습니다."));
      this.pending.clear();
    });
  }

  on(method, handler) {
    const handlers = this.listeners.get(method) ?? [];
    handlers.push(handler);
    this.listeners.set(method, handlers);
    return () => this.listeners.set(method, handlers.filter((item) => item !== handler));
  }

  call(method, params = {}) {
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { method, resolve, reject });
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }

  async evaluate(expression) {
    const result = await this.call("Runtime.evaluate", {
      expression,
      awaitPromise: true,
      returnByValue: true,
      userGesture: true
    });
    if (result.exceptionDetails) {
      const text = result.exceptionDetails.exception?.description ?? result.exceptionDetails.text;
      throw new Error(`브라우저 평가 오류: ${text}`);
    }
    return result.result?.value;
  }

  close() {
    if (this.socket?.readyState === WebSocket.OPEN) this.socket.close();
  }
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? "").href) {
  console.error("이 파일은 검증 스크립트에서 불러오는 공용 모듈입니다.");
  process.exitCode = 1;
}
