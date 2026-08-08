import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import path from "node:path";

const directory = path.resolve(process.argv[2] ?? ".");
const port = parsePort(process.argv[3] ?? "8080");
const MIME = new Map([
  [".html", "text/html; charset=utf-8"],
  [".css", "text/css; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".mjs", "text/javascript; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".svg", "image/svg+xml"],
  [".png", "image/png"]
]);

const rootInfo = await stat(directory).catch(() => null);
if (!rootInfo?.isDirectory()) {
  console.error(`정적 파일 디렉터리를 찾지 못했습니다: ${directory}`);
  process.exit(1);
}

const server = createServer(async (request, response) => {
  try {
    const requestUrl = new URL(request.url ?? "/", "http://127.0.0.1");
    const decoded = decodeURIComponent(requestUrl.pathname);
    const candidate = path.resolve(directory, `.${decoded}`);
    if (candidate !== directory && !candidate.startsWith(`${directory}${path.sep}`)) {
      response.writeHead(403, { "content-type": "text/plain; charset=utf-8" }).end("forbidden");
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
    response.writeHead(404, { "content-type": "text/plain; charset=utf-8" }).end("not found");
  }
});

await new Promise((resolve, reject) => {
  server.once("error", reject);
  server.listen(port, "127.0.0.1", resolve);
});
console.log(`${directory} 를 http://127.0.0.1:${port} 에서 제공합니다.`);
console.log("종료하려면 Ctrl+C를 누르세요.");

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.once(signal, () => {
    server.close((error) => {
      if (error) {
        console.error(error);
        process.exitCode = 1;
      }
    });
  });
}

function parsePort(raw) {
  const value = Number(raw);
  if (!Number.isInteger(value) || value < 1 || value > 65535) {
    console.error(`올바르지 않은 port입니다: ${raw}`);
    process.exit(1);
  }
  return value;
}
