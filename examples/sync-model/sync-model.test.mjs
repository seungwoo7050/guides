import test from "node:test";
import assert from "node:assert/strict";

import {
  assertValid,
  createLocalRecord,
  createSyncedRecord,
  editRecord,
  replacePermanentFailure,
  resolveWithLocal,
  resolveWithMerged,
  resolveWithRemote,
  resumeAfterAuthentication,
  startNext,
  statusOf,
  syncConflicted,
  syncFailed,
  syncSucceeded,
} from "./sync-model.mjs";

const base = { title: "현장 A", notes: "초기", status: "open" };

test("local record is pending and becomes synced after success", () => {
  let state = createLocalRecord({ id: "rec-1", payload: base, commandId: "cmd-1" });
  assert.equal(statusOf(state), "pending");
  state = startNext(state);
  assert.equal(statusOf(state), "syncing");
  state = syncSucceeded(state, {
    commandId: "cmd-1",
    server: { version: 1, payload: { ...base, title: "현장 A 정규화" } },
  });
  assert.equal(statusOf(state), "synced");
  assert.equal(state.local.payload.title, "현장 A 정규화");
});

test("stale success cannot modify current state", () => {
  let state = startNext(
    createLocalRecord({ id: "rec-1", payload: base, commandId: "cmd-1" }),
  );
  const before = structuredClone(state);
  state = syncSucceeded(state, {
    commandId: "another-command",
    server: { version: 99, payload: { ...base, title: "오래된 결과" } },
  });
  assert.deepEqual(state, before);
});

test("newer edit survives success and attempted command stays immutable", () => {
  let state = createSyncedRecord({ id: "rec-1", payload: base, version: 4 });
  state = startNext(editRecord(state, { commandId: "cmd-5", patch: { notes: "r1" } }));
  const attempted = structuredClone(state.active);
  state = editRecord(state, { commandId: "cmd-6", patch: { notes: "r2" } });
  assert.deepEqual(state.active, attempted);
  state = syncSucceeded(state, {
    commandId: "cmd-5",
    server: { version: 5, payload: { ...base, notes: "r1" } },
  });
  assert.equal(state.local.payload.notes, "r2");
  assert.equal(state.queued.commandId, "cmd-6");
  assert.equal(state.queued.baseVersion, 5);
  assert.deepEqual(attempted, {
    commandId: "cmd-5",
    localRevision: 1,
    baseVersion: 4,
    payload: { ...base, notes: "r1" },
  });
});

test("retryable response loss keeps the same command snapshot", () => {
  let state = createSyncedRecord({ id: "rec-1", payload: base, version: 2 });
  state = startNext(editRecord(state, { commandId: "cmd-3", patch: { title: "수정" } }));
  const attempted = structuredClone(state.active);
  state = syncFailed(state, {
    commandId: "cmd-3",
    reason: "response-lost",
    classification: "retryable",
  });
  assert.equal(statusOf(state), "retry-wait");
  assert.deepEqual(state.retry, attempted);
  state = startNext(state);
  assert.deepEqual(state.active, attempted);
});

test("retry of older command stays ahead of a newer edit", () => {
  let state = createSyncedRecord({ id: "rec-1", payload: base, version: 2 });
  state = startNext(editRecord(state, { commandId: "cmd-old", patch: { notes: "old" } }));
  state = editRecord(state, { commandId: "cmd-new", patch: { notes: "new" } });
  state = syncFailed(state, {
    commandId: "cmd-old",
    reason: "timeout-unknown",
  });
  state = startNext(state);
  assert.equal(state.active.commandId, "cmd-old");
  assert.equal(state.queued.commandId, "cmd-new");
});

test("authentication block is durable and resumes the same command", () => {
  let state = createSyncedRecord({ id: "rec-1", payload: base, version: 2 });
  state = startNext(editRecord(state, { commandId: "cmd-auth", patch: { notes: "auth" } }));
  const attempted = structuredClone(state.active);
  state = syncFailed(state, {
    commandId: "cmd-auth",
    reason: "refresh-required",
    classification: "blocked-auth",
  });
  assert.equal(statusOf(state), "blocked-auth");
  assert.deepEqual(startNext(state), state);
  state = resumeAfterAuthentication(state);
  state = startNext(state);
  assert.deepEqual(state.active, attempted);
});

test("permanent failure is not reported as synced or retried automatically", () => {
  let state = createSyncedRecord({ id: "rec-1", payload: base, version: 2 });
  state = startNext(editRecord(state, { commandId: "cmd-bad", patch: { notes: "bad" } }));
  state = syncFailed(state, {
    commandId: "cmd-bad",
    reason: "validation-rejected",
    classification: "permanent",
  });
  assert.equal(statusOf(state), "permanent-failure");
  assert.deepEqual(startNext(state), state);
  state = replacePermanentFailure(state, { commandId: "cmd-fixed" });
  assert.equal(statusOf(state), "pending");
  assert.equal(state.queued.commandId, "cmd-fixed");
});

test("malformed success is rejected without partial state change", () => {
  const state = startNext(
    createLocalRecord({ id: "rec-1", payload: base, commandId: "cmd-1" }),
  );
  assert.throws(
    () =>
      syncSucceeded(state, {
        commandId: "cmd-1",
        server: { version: 1, payload: { title: "누락", status: "open" } },
      }),
    /notes is required/,
  );
  assert.equal(state.active.commandId, "cmd-1");
  assert.equal(state.remote, null);
});

test("server version regression is rejected", () => {
  let state = createSyncedRecord({ id: "rec-1", payload: base, version: 7 });
  state = startNext(editRecord(state, { commandId: "cmd-8", patch: { title: "수정" } }));
  assert.throws(
    () =>
      syncSucceeded(state, {
        commandId: "cmd-8",
        server: { version: 3, payload: { ...base, title: "회귀" } },
      }),
    /version regression/,
  );
  assert.equal(state.remote.version, 7);
  assert.equal(state.active.commandId, "cmd-8");
});

test("conflict preserves local and remote values", () => {
  let state = createSyncedRecord({ id: "rec-1", payload: base, version: 7 });
  state = startNext(editRecord(state, { commandId: "cmd-8", patch: { title: "내 제목" } }));
  state = syncConflicted(state, {
    commandId: "cmd-8",
    server: { version: 8, payload: { ...base, title: "서버 제목" } },
  });
  assert.equal(statusOf(state), "conflict");
  assert.equal(state.conflict.local.title, "내 제목");
  assert.equal(state.conflict.remote.payload.title, "서버 제목");
});

test("local conflict resolution creates a new command on the new base", () => {
  let state = createConflict();
  state = resolveWithLocal(state, { commandId: "cmd-9" });
  assert.equal(state.queued.commandId, "cmd-9");
  assert.equal(state.queued.baseVersion, 8);
  assert.equal(state.queued.payload.title, "내 제목");
});

test("remote conflict resolution explicitly discards local intent", () => {
  const state = resolveWithRemote(createConflict());
  assert.equal(statusOf(state), "synced");
  assert.equal(state.local.payload.title, "서버 제목");
});

test("merged conflict resolution validates payload and creates a command", () => {
  const state = resolveWithMerged(createConflict(), {
    commandId: "cmd-9",
    payload: { ...base, title: "병합", notes: "병합 메모" },
  });
  assert.equal(state.local.payload.title, "병합");
  assert.equal(state.queued.baseVersion, 8);
});

test("duplicate command identities across durable slots are rejected", () => {
  const state = createSyncedRecord({ id: "rec-1", payload: base, version: 1 });
  const duplicate = {
    commandId: "same",
    localRevision: 0,
    baseVersion: 1,
    payload: base,
  };
  state.blocked = { command: duplicate, reason: "auth" };
  state.queued = duplicate;
  assert.throws(() => assertValid(state), /unique/);
});

function createConflict() {
  let state = createSyncedRecord({ id: "rec-1", payload: base, version: 7 });
  state = startNext(editRecord(state, { commandId: "cmd-8", patch: { title: "내 제목" } }));
  return syncConflicted(state, {
    commandId: "cmd-8",
    server: { version: 8, payload: { ...base, title: "서버 제목" } },
  });
}
