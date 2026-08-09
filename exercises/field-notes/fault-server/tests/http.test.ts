import assert from "node:assert/strict";
import type { Server } from "node:http";
import test from "node:test";
import { createFaultHttpServer, listenOnLoopback } from "../src/http.ts";
import type { RecordCommand, SuccessBody } from "../src/index.ts";

function close(server: Server): Promise<void> {
  return new Promise((resolveClose, rejectClose) => {
    server.close((error) => (error === undefined ? resolveClose() : rejectClose(error)));
  });
}

const command: RecordCommand = {
  commandId: "cmd-http",
  recordId: "http-record",
  operation: "upsert",
  baseVersion: null,
  localRevision: 1,
  payload: {
    title: "HTTP 경계",
    notes: "core와 같은 결정적 상태를 사용한다.",
    status: "open",
    observedAt: "2026-08-09T05:00:00.000Z",
  },
  createdAt: "2026-08-09T05:01:00.000Z",
};

test("loopback HTTP entry exposes health, fault control, commands and state", async (context) => {
  const server = createFaultHttpServer();
  const address = await listenOnLoopback(server, 0);
  context.after(() => close(server));
  const baseUrl = `http://${address.host}:${address.port}`;

  const health = await fetch(`${baseUrl}/health`);
  assert.equal(health.status, 200);
  assert.deepEqual(await health.json(), { ok: true, purpose: "local-test-double" });

  const injected = await fetch(`${baseUrl}/__test/faults`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ commandId: command.commandId, fault: { kind: "unauthorized" } }),
  });
  assert.equal(injected.status, 202);

  const unauthorized = await fetch(`${baseUrl}/commands`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(command),
  });
  assert.equal(unauthorized.status, 401);

  const success = await fetch(`${baseUrl}/commands`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(command),
  });
  assert.equal(success.status, 200);
  const successBody = (await success.json()) as SuccessBody;
  assert.equal(successBody.kind, "success");
  assert.equal(successBody.record.version, 1);

  const state = await fetch(`${baseUrl}/__test/state`);
  assert.equal(state.status, 200);
  const snapshot = (await state.json()) as { applyCountByCommand: Record<string, number> };
  assert.equal(snapshot.applyCountByCommand[command.commandId], 1);
});
