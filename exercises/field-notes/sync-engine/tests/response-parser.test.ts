import assert from "node:assert/strict";
import test from "node:test";
import { parseTransportResponse, type RecordCommand } from "../src/index.ts";

const attempted: RecordCommand = {
  commandId: "cmd-parser",
  recordId: "parser-record",
  operation: "upsert",
  baseVersion: 5,
  localRevision: 2,
  payload: {
    title: "parser",
    notes: "required fields",
    status: "open",
    observedAt: "2026-08-09T02:00:00.000Z",
  },
  createdAt: "2026-08-09T02:00:01.000Z",
};

function validBody(): Record<string, unknown> {
  return {
    kind: "success",
    commandId: attempted.commandId,
    record: {
      recordId: attempted.recordId,
      payload: structuredClone(attempted.payload),
      version: 6,
      deleted: false,
    },
    replayed: false,
  };
}

test("response parser requires matching commandId", () => {
  const body = validBody();
  body.commandId = "cmd-other";
  assert.deepEqual(
    parseTransportResponse(
      { status: 200, body },
      { attempted, knownRemoteVersion: 5 },
    ),
    { kind: "invalid_response", reason: "response-command-id-mismatch" },
  );
});

test("response parser rejects a success payload missing required fields", () => {
  const body = validBody();
  body.record = {
    recordId: attempted.recordId,
    payload: { title: "missing notes/status/time" },
    version: 6,
    deleted: false,
  };
  assert.deepEqual(
    parseTransportResponse(
      { status: 200, body },
      { attempted, knownRemoteVersion: 5 },
    ),
    {
      kind: "invalid_response",
      reason: "success-record-required-fields-invalid",
    },
  );
});

test("response parser rejects known remote version regression", () => {
  const body = validBody();
  body.record = {
    ...(body.record as Record<string, unknown>),
    version: 4,
  };
  assert.deepEqual(
    parseTransportResponse(
      { status: 200, body },
      { attempted, knownRemoteVersion: 5 },
    ),
    { kind: "invalid_response", reason: "remote-version-regression" },
  );
});

test("response parser accepts a complete monotonic success", () => {
  const result = parseTransportResponse(
    { status: 200, body: validBody() },
    { attempted, knownRemoteVersion: 5 },
  );
  assert.equal(result.kind, "success");
  if (result.kind !== "success") {
    throw new Error("expected success");
  }
  assert.equal(result.remote.version, 6);
  assert.deepEqual(result.remote.payload, attempted.payload);
});

test("response parser rejects normalized dates and out-of-range coordinates", () => {
  for (const payload of [
    { ...attempted.payload, observedAt: "2026-02-30T00:00:00.000Z" },
    { ...attempted.payload, observedAt: "2026-08-09" },
    {
      ...attempted.payload,
      location: {
        latitude: 999,
        longitude: 127,
        accuracyMeters: 1,
        measuredAt: "2026-08-09T02:00:00.000Z",
      },
    },
  ]) {
    const body = validBody();
    body.record = {
      ...(body.record as Record<string, unknown>),
      payload,
    };
    assert.deepEqual(
      parseTransportResponse(
        { status: 200, body },
        { attempted, knownRemoteVersion: 5 },
      ),
      {
        kind: "invalid_response",
        reason: "success-record-required-fields-invalid",
      },
    );
  }
});
