import assert from "node:assert/strict";
import test from "node:test";
import {
  DeterministicFaultServer,
  ManualClock,
  ResponseLostError,
  type ConflictBody,
  type PermanentFailureBody,
  type RecordCommand,
  type RecordPayload,
  type SuccessBody,
} from "../src/index.ts";

const BASE_PAYLOAD: RecordPayload = {
  title: "능선 표지판",
  notes: "고정 볼트를 교체했다.",
  status: "resolved",
  observedAt: "2026-08-09T03:05:00.000Z",
};

function command(
  commandId: string,
  recordId: string,
  overrides: Partial<RecordCommand> = {},
): RecordCommand {
  return {
    commandId,
    recordId,
    operation: "upsert",
    baseVersion: null,
    localRevision: 1,
    payload: { ...BASE_PAYLOAD },
    createdAt: "2026-08-09T04:00:00.000Z",
    ...overrides,
  };
}

test("stable commandId memoizes one apply and rejects identity reuse", async () => {
  const server = new DeterministicFaultServer();
  const attempted = command("cmd-stable", "ridge-marker");

  const first = await server.execute(attempted);
  assert.equal(first.status, 200);
  assert.equal((first.body as SuccessBody).replayed, false);

  const duplicate = await server.execute(structuredClone(attempted));
  assert.equal(duplicate.status, 200);
  assert.equal((duplicate.body as SuccessBody).replayed, true);
  assert.equal((duplicate.body as SuccessBody).record.version, 1);
  assert.equal(server.getApplyCount(attempted.commandId), 1);

  const reused = await server.execute({
    ...attempted,
    payload: { ...BASE_PAYLOAD, notes: "같은 ID로 바뀐 payload" },
  });
  assert.equal(reused.status, 409);
  assert.deepEqual(reused.body, {
    kind: "command-identity-reuse",
    commandId: attempted.commandId,
    reason: "same-command-id-different-attempted-command",
  });
  assert.equal(server.getApplyCount(attempted.commandId), 1);
});

test("baseVersion conflict is durable and replayable without apply", async () => {
  const server = new DeterministicFaultServer();
  server.seedRecord("ridge-marker", BASE_PAYLOAD, 3);
  const stale = command("cmd-conflict", "ridge-marker", { baseVersion: 2 });

  const first = await server.execute(stale);
  assert.equal(first.status, 409);
  const conflict = first.body as ConflictBody;
  assert.equal(conflict.kind, "conflict");
  assert.equal(conflict.current?.version, 3);
  assert.equal(conflict.replayed, false);

  const replay = await server.execute(stale);
  assert.equal(replay.status, 409);
  assert.equal((replay.body as ConflictBody).replayed, true);
  assert.equal(server.getApplyCount(stale.commandId), 0);
  assert.equal(server.getRecord("ridge-marker")?.version, 3);
});

test("response loss happens after apply and duplicate retry returns memo", async () => {
  const server = new DeterministicFaultServer();
  const attempted = command("cmd-lost", "forest-edge");
  server.inject({ kind: "response-loss" }, { commandId: attempted.commandId });

  await assert.rejects(
    () => server.execute(attempted),
    (error: unknown) =>
      error instanceof ResponseLostError && error.commandId === attempted.commandId,
  );
  assert.equal(server.getRecord(attempted.recordId)?.version, 1);
  assert.equal(server.getApplyCount(attempted.commandId), 1);

  const retry = await server.execute(attempted);
  assert.equal(retry.status, 200);
  assert.equal((retry.body as SuccessBody).replayed, true);
  assert.equal(server.getApplyCount(attempted.commandId), 1);
});

test("manual clock delays A so B completes first without wall-clock sleep", async () => {
  const clock = new ManualClock(1_000);
  const server = new DeterministicFaultServer(clock);
  const commandA = command("cmd-a", "record-a");
  const commandB = command("cmd-b", "record-b");
  server.inject({ kind: "delay", milliseconds: 50 }, { commandId: commandA.commandId });

  const pendingA = server.execute(commandA);
  assert.equal(clock.pendingCount(), 1);

  const resultB = await server.execute(commandB);
  assert.equal(resultB.status, 200);
  assert.equal(server.getRecord("record-a"), null);
  assert.equal(server.getRecord("record-b")?.version, 1);

  clock.advanceBy(49);
  assert.equal(server.getRecord("record-a"), null);
  clock.advanceBy(1);
  const resultA = await pendingA;
  assert.equal(resultA.status, 200);

  const appliedOrder = server
    .snapshot()
    .history.filter((event) => event.kind === "applied")
    .map((event) => event.commandId);
  assert.deepEqual(appliedOrder, ["cmd-b", "cmd-a"]);
});

test("401 is pre-apply and a later retry can recover", async () => {
  const server = new DeterministicFaultServer();
  const attempted = command("cmd-auth", "harbor-light");
  server.inject({ kind: "unauthorized" }, { commandId: attempted.commandId });

  const unauthorized = await server.execute(attempted);
  assert.equal(unauthorized.status, 401);
  assert.equal(server.getApplyCount(attempted.commandId), 0);
  assert.equal(server.snapshot().memoizedCommandIds.length, 0);

  const recovered = await server.execute(attempted);
  assert.equal(recovered.status, 200);
  assert.equal(server.getApplyCount(attempted.commandId), 1);
});

test("malformed success distorts one delivery after a real apply", async () => {
  const server = new DeterministicFaultServer();
  const attempted = command("cmd-malformed", "marsh-edge");
  server.inject({ kind: "malformed-success" }, { commandId: attempted.commandId });

  const malformed = await server.execute(attempted);
  assert.equal(malformed.status, 200);
  assert.deepEqual(malformed.body, {
    kind: "success",
    commandId: attempted.commandId,
    record: "malformed-record",
  });
  assert.equal(server.getRecord(attempted.recordId)?.version, 1);

  const retry = await server.execute(attempted);
  assert.equal(retry.status, 200);
  assert.equal((retry.body as SuccessBody).record.version, 1);
  assert.equal((retry.body as SuccessBody).replayed, true);
  assert.equal(server.getApplyCount(attempted.commandId), 1);
});

test("version regression changes only the delivered response", async () => {
  const server = new DeterministicFaultServer();
  server.seedRecord("ridge-marker", BASE_PAYLOAD, 5);
  const attempted = command("cmd-regression", "ridge-marker", {
    baseVersion: 5,
    localRevision: 2,
  });
  server.inject({ kind: "version-regression", by: 2 }, { commandId: attempted.commandId });

  const regressed = await server.execute(attempted);
  assert.equal(regressed.status, 200);
  assert.equal((regressed.body as SuccessBody).record.version, 4);
  assert.equal(server.getRecord(attempted.recordId)?.version, 6);

  const retry = await server.execute(attempted);
  assert.equal((retry.body as SuccessBody).record.version, 6);
  assert.equal((retry.body as SuccessBody).replayed, true);
  assert.equal(server.getApplyCount(attempted.commandId), 1);
});

test("permanent validation result is memoized and requires a new ID", async () => {
  const server = new DeterministicFaultServer();
  const attempted = command("cmd-permanent", "cliff-path");
  server.inject(
    { kind: "permanent-validation", reason: "payload-policy-rejected" },
    { commandId: attempted.commandId },
  );

  const failed = await server.execute(attempted);
  assert.equal(failed.status, 422);
  assert.deepEqual(failed.body, {
    kind: "permanent-failure",
    commandId: attempted.commandId,
    reason: "payload-policy-rejected",
    replayed: false,
  } satisfies PermanentFailureBody);
  assert.equal(server.getApplyCount(attempted.commandId), 0);

  const retry = await server.execute(attempted);
  assert.equal(retry.status, 422);
  assert.equal((retry.body as PermanentFailureBody).replayed, true);

  const changedUnderSameId = await server.execute({
    ...attempted,
    payload: { ...BASE_PAYLOAD, title: "수정한 제목" },
  });
  assert.equal(changedUnderSameId.status, 409);

  const corrected = await server.execute(command("cmd-corrected", attempted.recordId));
  assert.equal(corrected.status, 200);
});

test("invalid business payload is a permanent result, not an apply", async () => {
  const server = new DeterministicFaultServer();
  const invalid = command("cmd-empty-title", "empty-title", {
    payload: { ...BASE_PAYLOAD, title: "   " },
  });

  const response = await server.execute(invalid);
  assert.equal(response.status, 422);
  assert.equal((response.body as PermanentFailureBody).reason, "title-required");
  assert.equal(server.getApplyCount(invalid.commandId), 0);
  assert.equal(server.getRecord(invalid.recordId), null);
});

test("wire validation rejects non-canonical instants and out-of-range coordinates", async () => {
  const server = new DeterministicFaultServer();
  const invalidPayloads: RecordPayload[] = [
    { ...BASE_PAYLOAD, observedAt: "2026-02-30T00:00:00.000Z" },
    { ...BASE_PAYLOAD, observedAt: "2026-08-09" },
    {
      ...BASE_PAYLOAD,
      location: {
        latitude: 37,
        longitude: -999,
        accuracyMeters: 1,
        measuredAt: "2026-08-09T03:05:00.000Z",
      },
    },
  ];
  for (const [index, payload] of invalidPayloads.entries()) {
    const attempted = command(`cmd-invalid-wire-${index}`, `invalid-wire-${index}`, {
      payload,
    });
    const response = await server.execute(attempted);
    assert.equal(response.status, 400);
    assert.equal(server.getApplyCount(attempted.commandId), 0);
    assert.equal(server.getRecord(attempted.recordId), null);
  }
});
