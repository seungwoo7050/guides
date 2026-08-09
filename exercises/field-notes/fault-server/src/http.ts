import { createServer, type IncomingMessage, type Server, type ServerResponse } from "node:http";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";
import { DeterministicFaultServer, ResponseLostError } from "./fault-server.ts";
import type { Fault } from "./types.ts";

const MAX_BODY_BYTES = 1_048_576;

async function readJson(request: IncomingMessage): Promise<unknown> {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of request) {
    const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    size += buffer.byteLength;
    if (size > MAX_BODY_BYTES) {
      throw new RangeError("request body exceeds 1 MiB test-server limit");
    }
    chunks.push(buffer);
  }
  const source = Buffer.concat(chunks).toString("utf8");
  return source.length === 0 ? null : JSON.parse(source);
}

function sendJson(response: ServerResponse, status: number, body: unknown): void {
  const serialized = JSON.stringify(body);
  response.writeHead(status, {
    "content-type": "application/json; charset=utf-8",
    "content-length": Buffer.byteLength(serialized),
    "cache-control": "no-store",
  });
  response.end(serialized);
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseFault(value: unknown): { fault: Fault; commandId?: string } {
  if (!isObject(value) || !isObject(value.fault) || typeof value.fault.kind !== "string") {
    throw new TypeError("body must contain a fault object");
  }
  if (value.commandId !== undefined && typeof value.commandId !== "string") {
    throw new TypeError("commandId filter must be a string");
  }

  const raw = value.fault;
  let fault: Fault;
  switch (raw.kind) {
    case "delay":
      if (typeof raw.milliseconds !== "number") {
        throw new TypeError("delay fault requires milliseconds");
      }
      fault = { kind: "delay", milliseconds: raw.milliseconds };
      break;
    case "response-loss":
    case "unauthorized":
      fault = { kind: raw.kind };
      break;
    case "malformed-success":
      fault = Object.hasOwn(raw, "body")
        ? { kind: "malformed-success", body: raw.body }
        : { kind: "malformed-success" };
      break;
    case "version-regression":
      if (raw.by !== undefined && typeof raw.by !== "number") {
        throw new TypeError("version-regression by must be a number");
      }
      fault = raw.by === undefined
        ? { kind: "version-regression" }
        : { kind: "version-regression", by: raw.by };
      break;
    case "permanent-validation":
      if (typeof raw.reason !== "string") {
        throw new TypeError("permanent-validation fault requires reason");
      }
      fault = { kind: "permanent-validation", reason: raw.reason };
      break;
    default:
      throw new TypeError(`unsupported fault kind: ${raw.kind}`);
  }

  return value.commandId === undefined
    ? { fault }
    : { fault, commandId: value.commandId as string };
}

async function handle(
  request: IncomingMessage,
  response: ServerResponse,
  faultServer: DeterministicFaultServer,
): Promise<void> {
  const url = new URL(request.url ?? "/", "http://127.0.0.1");

  if (request.method === "GET" && url.pathname === "/health") {
    sendJson(response, 200, { ok: true, purpose: "local-test-double" });
    return;
  }
  if (request.method === "GET" && url.pathname === "/__test/state") {
    sendJson(response, 200, faultServer.snapshot());
    return;
  }
  if (request.method === "POST" && url.pathname === "/commands") {
    const result = await faultServer.execute(await readJson(request));
    sendJson(response, result.status, result.body);
    return;
  }
  if (request.method === "POST" && url.pathname === "/__test/faults") {
    const plan = parseFault(await readJson(request));
    faultServer.inject(
      plan.fault,
      plan.commandId === undefined ? {} : { commandId: plan.commandId },
    );
    sendJson(response, 202, { accepted: true });
    return;
  }
  if (request.method === "POST" && url.pathname === "/__test/clock/advance") {
    const body = await readJson(request);
    if (!isObject(body) || typeof body.milliseconds !== "number") {
      throw new TypeError("clock advance requires numeric milliseconds");
    }
    faultServer.clock.advanceBy(body.milliseconds);
    sendJson(response, 200, { now: faultServer.clock.now() });
    return;
  }
  if (request.method === "POST" && url.pathname === "/__test/reset") {
    faultServer.reset();
    sendJson(response, 200, { reset: true });
    return;
  }

  sendJson(response, 404, { error: "not-found" });
}

export function createFaultHttpServer(
  faultServer = new DeterministicFaultServer(),
): Server {
  return createServer((request, response) => {
    void handle(request, response, faultServer).catch((error: unknown) => {
      if (error instanceof ResponseLostError) {
        response.destroy(error);
        return;
      }
      const message = error instanceof Error ? error.message : "unknown request error";
      if (!response.headersSent) {
        sendJson(response, 400, { error: "invalid-test-request", message });
      } else {
        response.destroy(error instanceof Error ? error : undefined);
      }
    });
  });
}

export async function listenOnLoopback(
  server: Server,
  port = 0,
): Promise<{ host: "127.0.0.1"; port: number }> {
  if (!Number.isInteger(port) || port < 0 || port > 65_535) {
    throw new RangeError("port must be an integer from 0 through 65535");
  }
  await new Promise<void>((resolveListen, rejectListen) => {
    const onError = (error: Error): void => rejectListen(error);
    server.once("error", onError);
    server.listen(port, "127.0.0.1", () => {
      server.off("error", onError);
      resolveListen();
    });
  });
  const address = server.address();
  if (address === null || typeof address === "string") {
    throw new Error("fault server did not expose an IPv4 loopback address");
  }
  return { host: "127.0.0.1", port: address.port };
}

function isDirectExecution(): boolean {
  const entry = process.argv[1];
  return entry !== undefined && resolve(entry) === fileURLToPath(import.meta.url);
}

if (isDirectExecution()) {
  const requestedPort = process.env.FIELD_NOTES_FAULT_PORT;
  const port = requestedPort === undefined ? 3104 : Number(requestedPort);
  const server = createFaultHttpServer();
  const address = await listenOnLoopback(server, port);
  process.stdout.write(
    `Field Notes local fault server listening on http://${address.host}:${address.port}\n`,
  );
}
