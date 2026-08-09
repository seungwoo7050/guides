import assert from "node:assert/strict";
import test from "node:test";
import {
  DeterministicFaultServer,
  ManualClock,
} from "../../fault-server/src/index.ts";
import {
  BoundedSyncWorker,
  FaultServerTransport,
  FixedSyncBudget,
  InMemorySyncRepository,
  SequentialCommandIdGenerator,
  type DurableCommand,
  type LocalRecord,
  type RecordCommand,
  type RecordPayload,
} from "../src/index.ts";

const PAYLOAD_A: RecordPayload = {
  title: "숲 가장자리",
  notes: "첫 번째 local 의도",
  status: "open",
  observedAt: "2026-08-09T01:00:00.000Z",
};

const PAYLOAD_B: RecordPayload = {
  title: "숲 가장자리 수정",
  notes: "전송 중 만든 더 최신 local 의도",
  status: "resolved",
  observedAt: "2026-08-09T01:05:00.000Z",
};

const REMOTE_PAYLOAD: RecordPayload = {
  title: "서버의 표지",
  notes: "다른 기기에서 먼저 반영됨",
  status: "open",
  observedAt: "2026-08-09T00:55:00.000Z",
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
    payload: structuredClone(PAYLOAD_A),
    createdAt: "2026-08-09T01:00:01.000Z",
    ...overrides,
  };
}

function harness(options: {
  maxCommands?: number;
  maxAttempts?: number;
  idGenerator?: SequentialCommandIdGenerator;
} = {}): {
  clock: ManualClock;
  server: DeterministicFaultServer;
  repository: InMemorySyncRepository;
  worker: (workerId: string) => BoundedSyncWorker;
} {
  const clock = new ManualClock(0);
  const server = new DeterministicFaultServer(clock);
  const repository = new InMemorySyncRepository({
    idGenerator: options.idGenerator ?? new SequentialCommandIdGenerator(),
  });
  const transport = new FaultServerTransport(server);
  const budget = new FixedSyncBudget({
    maxCommands: options.maxCommands ?? 1,
    leaseDurationMs: 100,
    retryDelayMs: 10,
    ...(options.maxAttempts === undefined
      ? {}
      : { maxAttempts: options.maxAttempts }),
  });
  return {
    clock,
    server,
    repository,
    worker: () =>
      new BoundedSyncWorker({ repository, transport, clock, budget }),
  };
}

async function requireCommand(
  repository: InMemorySyncRepository,
  commandId: string,
): Promise<DurableCommand> {
  const entry = await repository.getCommand(commandId);
  assert.notEqual(entry, null, `missing command ${commandId}`);
  return entry as DurableCommand;
}

async function requireRecord(
  repository: InMemorySyncRepository,
  recordId: string,
): Promise<LocalRecord> {
  const record = await repository.getRecord(recordId);
  assert.notEqual(record, null, `missing record ${recordId}`);
  return record as LocalRecord;
}

async function settleUntilClockWaiter(clock: ManualClock): Promise<void> {
  for (let turn = 0; turn < 8 && clock.pendingCount() === 0; turn += 1) {
    await Promise.resolve();
  }
  assert.equal(clock.pendingCount(), 1, "expected a controlled delay waiter");
}

test("response loss retries the immutable attempted command and applies once", async () => {
  const { clock, server, repository, worker } = harness();
  const attempted = command("cmd-loss", "forest-edge");
  repository.enqueueLocalCommand(attempted);
  server.inject({ kind: "response-loss" }, { commandId: attempted.commandId });

  const firstRun = await worker("foreground-1").run({
    trigger: "foreground",
    workerId: "foreground-1",
  });
  assert.equal(firstRun.claimed, 1);
  assert.equal(firstRun.checkpoints.length, 1);
  const waiting = await requireCommand(repository, attempted.commandId);
  assert.equal(waiting.state.kind, "retry_wait");
  if (waiting.state.kind !== "retry_wait") {
    throw new Error("expected retry_wait");
  }
  assert.deepEqual(waiting.state.attempted, attempted);
  assert.match(waiting.state.reason, /RESPONSE_LOST/);
  assert.equal(server.getApplyCount(attempted.commandId), 1);

  clock.advanceBy(10);
  const retryRun = await worker("foreground-2").run({
    trigger: "foreground",
    workerId: "foreground-2",
  });
  assert.equal(retryRun.checkpoints[0]?.state, "completed");
  const completed = await requireCommand(repository, attempted.commandId);
  assert.equal(completed.state.kind, "completed");
  if (completed.state.kind !== "completed") {
    throw new Error("expected completed");
  }
  assert.deepEqual(completed.state.attempted, attempted);
  assert.equal(completed.state.attempt, 2);
  assert.equal(server.getApplyCount(attempted.commandId), 1);
});

test("lost local checkpoint causes duplicate delivery but not duplicate apply", async () => {
  const { clock, server, repository, worker } = harness();
  const attempted = command("cmd-checkpoint-loss", "ridge-marker");
  repository.enqueueLocalCommand(attempted);
  repository.failNextCheckpoint(attempted.commandId);

  const firstRun = await worker("foreground-crash").run({
    trigger: "foreground",
    workerId: "foreground-crash",
  });
  assert.equal(firstRun.stopped, "checkpoint-failed");
  assert.equal(firstRun.checkpoints.length, 0);
  assert.equal(server.getApplyCount(attempted.commandId), 1);
  const stranded = await requireCommand(repository, attempted.commandId);
  assert.equal(stranded.state.kind, "in_flight");

  clock.advanceBy(100);
  const recovered = await worker("background-recovery").run({
    trigger: "background",
    workerId: "background-recovery",
  });
  assert.equal(recovered.checkpoints[0]?.state, "completed");
  const completed = await requireCommand(repository, attempted.commandId);
  assert.equal(completed.state.kind, "completed");
  if (completed.state.kind !== "completed") {
    throw new Error("expected completed");
  }
  assert.equal(completed.state.attempt, 2);
  assert.deepEqual(completed.state.attempted, attempted);
  assert.equal(server.getApplyCount(attempted.commandId), 1);
  assert.equal(
    server.snapshot().history.filter((event) => event.kind === "replayed").length,
    1,
  );
});

test("controlled delay makes B finish before A without changing queue correctness", async () => {
  const { clock, server, repository, worker } = harness();
  const commandA = command("cmd-delay-a", "record-a");
  const commandB = command("cmd-delay-b", "record-b");
  repository.enqueueLocalCommand(commandA);
  repository.enqueueLocalCommand(commandB);
  server.inject({ kind: "delay", milliseconds: 50 }, { commandId: commandA.commandId });

  const pendingA = worker("foreground-a").run({
    trigger: "foreground",
    workerId: "foreground-a",
  });
  await settleUntilClockWaiter(clock);

  const runB = await worker("background-b").run({
    trigger: "background",
    workerId: "background-b",
  });
  assert.equal(runB.checkpoints[0]?.commandId, commandB.commandId);
  assert.equal((await requireCommand(repository, commandA.commandId)).state.kind, "in_flight");
  assert.equal((await requireCommand(repository, commandB.commandId)).state.kind, "completed");

  clock.advanceBy(50);
  await pendingA;
  const order = server
    .snapshot()
    .history.filter((event) => event.kind === "applied")
    .map((event) => event.commandId);
  assert.deepEqual(order, [commandB.commandId, commandA.commandId]);
});

test("foreground/background overlap cannot claim one live command twice", async () => {
  const { clock, server, repository, worker } = harness();
  const attempted = command("cmd-overlap", "overlap-record");
  repository.enqueueLocalCommand(attempted);
  server.inject({ kind: "delay", milliseconds: 20 }, { commandId: attempted.commandId });

  const foreground = worker("foreground-owner").run({
    trigger: "foreground",
    workerId: "foreground-owner",
  });
  await settleUntilClockWaiter(clock);
  const background = await worker("background-contender").run({
    trigger: "background",
    workerId: "background-contender",
  });
  assert.equal(background.claimed, 0);
  assert.equal(background.stopped, "idle");

  clock.advanceBy(20);
  await foreground;
  assert.equal(server.getApplyCount(attempted.commandId), 1);
});

test("401 blocks durably and explicit auth resume retries the same snapshot", async () => {
  const { clock, server, repository, worker } = harness();
  const attempted = command("cmd-auth", "auth-record");
  repository.enqueueLocalCommand(attempted);
  server.inject({ kind: "unauthorized" }, { commandId: attempted.commandId });

  await worker("foreground-auth").run({
    trigger: "foreground",
    workerId: "foreground-auth",
  });
  const blocked = await requireCommand(repository, attempted.commandId);
  assert.equal(blocked.state.kind, "blocked_auth");
  if (blocked.state.kind !== "blocked_auth") {
    throw new Error("expected blocked_auth");
  }
  assert.deepEqual(blocked.state.attempted, attempted);
  assert.equal((await requireRecord(repository, attempted.recordId)).syncState, "blocked_auth");
  assert.equal(server.getApplyCount(attempted.commandId), 0);

  assert.equal(await repository.resumeBlockedAuth(clock.now()), 1);
  await worker("foreground-auth-resumed").run({
    trigger: "app-active",
    workerId: "foreground-auth-resumed",
  });
  const completed = await requireCommand(repository, attempted.commandId);
  assert.equal(completed.state.kind, "completed");
  if (completed.state.kind !== "completed") {
    throw new Error("expected completed");
  }
  assert.deepEqual(completed.state.attempted, attempted);
  assert.equal(server.getApplyCount(attempted.commandId), 1);
});

test("malformed success never checkpoints success and same-ID retry reconciles", async () => {
  const { clock, server, repository, worker } = harness();
  const attempted = command("cmd-malformed", "malformed-record");
  repository.enqueueLocalCommand(attempted);
  server.inject({ kind: "malformed-success" }, { commandId: attempted.commandId });

  await worker("foreground-malformed").run({
    trigger: "foreground",
    workerId: "foreground-malformed",
  });
  const waiting = await requireCommand(repository, attempted.commandId);
  assert.equal(waiting.state.kind, "retry_wait");
  if (waiting.state.kind !== "retry_wait") {
    throw new Error("expected retry_wait");
  }
  assert.match(waiting.state.reason, /required-fields-invalid/);
  assert.equal((await requireRecord(repository, attempted.recordId)).knownRemoteVersion, null);
  assert.equal(server.getApplyCount(attempted.commandId), 1);

  clock.advanceBy(10);
  await worker("foreground-malformed-retry").run({
    trigger: "foreground",
    workerId: "foreground-malformed-retry",
  });
  assert.equal((await requireCommand(repository, attempted.commandId)).state.kind, "completed");
  assert.equal((await requireRecord(repository, attempted.recordId)).knownRemoteVersion, 1);
  assert.equal(server.getApplyCount(attempted.commandId), 1);
});

test("version regression is rejected until a same-ID replay returns monotonic version", async () => {
  const { clock, server, repository, worker } = harness();
  server.seedRecord("versioned-record", REMOTE_PAYLOAD, 5);
  repository.seedLocalRecord({
    recordId: "versioned-record",
    payload: structuredClone(PAYLOAD_A),
    deleted: false,
    localRevision: 2,
    knownRemoteVersion: 5,
    syncState: "pending",
  });
  const attempted = command("cmd-version", "versioned-record", {
    baseVersion: 5,
    localRevision: 2,
  });
  repository.enqueueLocalCommand(attempted);
  server.inject({ kind: "version-regression", by: 2 }, { commandId: attempted.commandId });

  await worker("foreground-version").run({
    trigger: "foreground",
    workerId: "foreground-version",
  });
  const waiting = await requireCommand(repository, attempted.commandId);
  assert.equal(waiting.state.kind, "retry_wait");
  if (waiting.state.kind !== "retry_wait") {
    throw new Error("expected retry_wait");
  }
  assert.match(waiting.state.reason, /remote-version-regression|did-not-advance/);
  assert.equal((await requireRecord(repository, attempted.recordId)).knownRemoteVersion, 5);
  assert.equal(server.getRecord(attempted.recordId)?.version, 6);

  clock.advanceBy(10);
  await worker("foreground-version-retry").run({
    trigger: "foreground",
    workerId: "foreground-version-retry",
  });
  assert.equal((await requireCommand(repository, attempted.commandId)).state.kind, "completed");
  assert.equal((await requireRecord(repository, attempted.recordId)).knownRemoteVersion, 6);
  assert.equal(server.getApplyCount(attempted.commandId), 1);
});

test("permanent result is terminal and is not automatically reclaimed", async () => {
  const { server, repository, worker } = harness();
  const attempted = command("cmd-permanent", "permanent-record");
  repository.enqueueLocalCommand(attempted);
  server.inject(
    { kind: "permanent-validation", reason: "record-policy-rejected" },
    { commandId: attempted.commandId },
  );

  await worker("foreground-permanent").run({
    trigger: "foreground",
    workerId: "foreground-permanent",
  });
  const permanent = await requireCommand(repository, attempted.commandId);
  assert.equal(permanent.state.kind, "permanent");
  if (permanent.state.kind !== "permanent") {
    throw new Error("expected permanent");
  }
  assert.equal(permanent.state.reason, "record-policy-rejected");
  assert.equal(server.getApplyCount(attempted.commandId), 0);

  const later = await worker("background-later").run({
    trigger: "background",
    workerId: "background-later",
  });
  assert.equal(later.claimed, 0);
});

test("conflict preserves both sides and local resolution creates a new command", async () => {
  const { server, repository, worker } = harness();
  server.seedRecord("conflicted-record", REMOTE_PAYLOAD, 2);
  repository.seedLocalRecord({
    recordId: "conflicted-record",
    payload: structuredClone(PAYLOAD_A),
    deleted: false,
    localRevision: 1,
    knownRemoteVersion: 1,
    syncState: "pending",
  });
  const attempted = command("cmd-conflict", "conflicted-record", { baseVersion: 1 });
  repository.enqueueLocalCommand(attempted);

  await worker("foreground-conflict").run({
    trigger: "foreground",
    workerId: "foreground-conflict",
  });
  const conflicted = await requireCommand(repository, attempted.commandId);
  assert.equal(conflicted.state.kind, "conflict");
  if (conflicted.state.kind !== "conflict") {
    throw new Error("expected conflict");
  }
  const conflict = await repository.getConflict(conflicted.state.conflictId);
  assert.notEqual(conflict, null);
  assert.deepEqual(conflict?.local.payload, PAYLOAD_A);
  assert.deepEqual(conflict?.remote?.payload, REMOTE_PAYLOAD);
  assert.equal(conflict?.remote?.version, 2);
  assert.deepEqual(conflict?.attempted, attempted);

  const resolved = await repository.resolveConflict(conflicted.state.conflictId, {
    kind: "local",
    commandId: "cmd-conflict-resolution",
    createdAt: "2026-08-09T01:10:00.000Z",
    resolvedAt: 10,
  });
  assert.equal(resolved.command?.command.commandId, "cmd-conflict-resolution");
  assert.equal(resolved.command?.command.baseVersion, 2);
  assert.deepEqual(resolved.command?.command.payload, PAYLOAD_A);
  assert.equal(resolved.conflict.resolution?.kind, "local");
  assert.equal((await requireCommand(repository, attempted.commandId)).state.kind, "completed");

  await worker("foreground-resolution").run({
    trigger: "foreground",
    workerId: "foreground-resolution",
  });
  assert.equal(
    (await requireCommand(repository, "cmd-conflict-resolution")).state.kind,
    "completed",
  );
  assert.equal(server.getRecord(attempted.recordId)?.version, 3);
  assert.deepEqual(server.getRecord(attempted.recordId)?.payload, PAYLOAD_A);
  const preservedEvidence = await repository.getConflict(conflicted.state.conflictId);
  assert.deepEqual(preservedEvidence?.local.payload, PAYLOAD_A);
  assert.deepEqual(preservedEvidence?.remote?.payload, REMOTE_PAYLOAD);
  assert.equal(preservedEvidence?.resolution?.kind, "local");
});

test("expired lease survives snapshot restore and keeps the attempted command", async () => {
  const { clock, server, repository } = harness();
  const attempted = command("cmd-expired", "expired-record");
  repository.enqueueLocalCommand(attempted);

  const abandoned = await repository.claimNext({
    workerId: "crashed-worker",
    now: clock.now(),
    leaseDurationMs: 100,
  });
  assert.notEqual(abandoned, null);
  assert.deepEqual(abandoned?.attempted, attempted);

  const restored = new InMemorySyncRepository({
    snapshot: await repository.snapshot(),
  });
  const restoredWorker = (workerId: string): BoundedSyncWorker =>
    new BoundedSyncWorker({
      repository: restored,
      transport: new FaultServerTransport(server),
      clock,
      budget: new FixedSyncBudget({
        maxCommands: 1,
        leaseDurationMs: 100,
        retryDelayMs: 10,
      }),
    });

  const beforeExpiry = await restoredWorker("early-worker").run({
    trigger: "background",
    workerId: "early-worker",
  });
  assert.equal(beforeExpiry.claimed, 0);

  clock.advanceBy(100);
  await restoredWorker("recovery-worker").run({
    trigger: "background",
    workerId: "recovery-worker",
  });
  const completed = await requireCommand(restored, attempted.commandId);
  assert.equal(completed.state.kind, "completed");
  if (completed.state.kind !== "completed") {
    throw new Error("expected completed");
  }
  assert.equal(completed.state.attempt, 2);
  assert.deepEqual(completed.state.attempted, attempted);
  assert.equal(server.getApplyCount(attempted.commandId), 1);
});

test("success preserves newer local edit and rebases only its unattempted command", async () => {
  const { clock, server, repository, worker } = harness({
    idGenerator: new SequentialCommandIdGenerator(7),
  });
  const commandA = command("cmd-active", "editing-record");
  repository.enqueueLocalCommand(commandA);
  server.inject({ kind: "delay", milliseconds: 30 }, { commandId: commandA.commandId });

  const activeRun = worker("foreground-active").run({
    trigger: "foreground",
    workerId: "foreground-active",
  });
  await settleUntilClockWaiter(clock);
  const commandB = command("cmd-newer", "editing-record", {
    localRevision: 2,
    payload: structuredClone(PAYLOAD_B),
    createdAt: "2026-08-09T01:05:01.000Z",
  });
  repository.enqueueLocalCommand(commandB);

  const activeState = await requireCommand(repository, commandA.commandId);
  assert.equal(activeState.state.kind, "in_flight");
  if (activeState.state.kind !== "in_flight") {
    throw new Error("expected in_flight");
  }
  assert.deepEqual(activeState.state.attempted, commandA);

  clock.advanceBy(30);
  const firstResult = await activeRun;
  assert.deepEqual(firstResult.checkpoints[0]?.rebased, [
    {
      previousCommandId: "cmd-newer",
      commandId: "cmd-newer:rebase:7",
      baseVersion: 1,
    },
  ]);
  assert.equal(await repository.getCommand("cmd-newer"), null);
  const rebased = await requireCommand(repository, "cmd-newer:rebase:7");
  assert.equal(rebased.state.kind, "pending");
  assert.equal(rebased.command.baseVersion, 1);
  assert.deepEqual(rebased.command.payload, PAYLOAD_B);
  const localAfterA = await requireRecord(repository, commandA.recordId);
  assert.equal(localAfterA.localRevision, 2);
  assert.equal(localAfterA.knownRemoteVersion, 1);
  assert.deepEqual(localAfterA.payload, PAYLOAD_B);
  assert.equal(localAfterA.syncState, "pending");

  await worker("foreground-newer").run({
    trigger: "foreground",
    workerId: "foreground-newer",
  });
  const localAfterB = await requireRecord(repository, commandA.recordId);
  assert.equal(localAfterB.knownRemoteVersion, 2);
  assert.deepEqual(localAfterB.payload, PAYLOAD_B);
  assert.equal(localAfterB.syncState, "synced");
  assert.deepEqual((await requireCommand(repository, commandA.commandId)).state.kind, "completed");
  assert.equal(server.getApplyCount(commandA.commandId), 1);
  assert.equal(server.getApplyCount("cmd-newer:rebase:7"), 1);
});

test("repeated malformed UNKNOWN responses exhaust a finite attempt ceiling", async () => {
  const { clock, server, repository, worker } = harness({ maxAttempts: 3 });
  const attempted = command("cmd-attempt-ceiling", "ceiling-record");
  repository.enqueueLocalCommand(attempted);
  for (let attempt = 0; attempt < 3; attempt += 1) {
    server.inject({ kind: "malformed-success" }, { commandId: attempted.commandId });
  }

  await worker("ceiling-1").run({ trigger: "manual", workerId: "ceiling-1" });
  assert.equal((await requireCommand(repository, attempted.commandId)).state.kind, "retry_wait");
  clock.advanceBy(10);
  await worker("ceiling-2").run({ trigger: "manual", workerId: "ceiling-2" });
  assert.equal((await requireCommand(repository, attempted.commandId)).state.kind, "retry_wait");
  clock.advanceBy(10);
  await worker("ceiling-3").run({ trigger: "manual", workerId: "ceiling-3" });

  const exhausted = await requireCommand(repository, attempted.commandId);
  assert.equal(exhausted.state.kind, "permanent");
  if (exhausted.state.kind !== "permanent") throw new Error("attempt ceiling missing");
  assert.equal(exhausted.state.attempt, 3);
  assert.match(exhausted.state.reason, /^attempt-exhausted:invalid-response:/);
  assert.equal(server.getApplyCount(attempted.commandId), 1);
  assert.equal(
    await repository.claimNext({
      workerId: "must-not-reclaim-exhausted",
      now: 999_999,
      leaseDurationMs: 100,
    }),
    null,
  );
});
