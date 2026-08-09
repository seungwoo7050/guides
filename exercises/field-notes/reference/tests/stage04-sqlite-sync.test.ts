import {
  DeterministicFaultServer,
  ManualClock,
} from "../../fault-server/src/index.ts";
import { FaultServerTransport } from "../../sync-engine/src/fault-server-transport.ts";
import {
  BoundedSyncWorker,
  FixedSyncBudget,
  type CheckpointOutcome,
  type RecordCommand,
  type RecordPayload,
  type SyncTransport,
} from "@field-notes/sync-engine";
import { SQLiteFieldNotesRepository } from "../src/storage/SQLiteFieldNotesRepository";
import {
  CREATE_V1_SCHEMA_SQL,
  MIGRATE_V1_TO_V2_SQL,
  MIGRATE_V2_TO_V3_SQL,
  MIGRATE_V3_TO_V4_SQL,
} from "../src/storage/migrations";
import { sequentialIds } from "../src/storage/testing/DeterministicLocalStore";
import { SQLiteSyncRepositoryAdapter } from "../src/sync/SQLiteSyncRepositoryAdapter";
import { NodeSQLiteDatabase } from "./support/NodeSQLiteDatabase";

const BASE_TIME = Date.parse("2026-08-09T16:00:00.000Z");

const REMOTE_PAYLOAD: RecordPayload = {
  title: "remote 관찰",
  notes: "다른 기기에서 먼저 저장",
  status: "open",
  observedAt: "2026-08-09T15:30:00.000Z",
};

type Harness = Awaited<ReturnType<typeof createHarness>>;

async function createHarness(options: {
  maxCommands?: number;
  maxAttempts?: number;
  beforeCheckpointCommit?: (commandId: string) => Promise<void>;
} = {}) {
  const database = new NodeSQLiteDatabase();
  const manualClock = new ManualClock(0);
  const ids = sequentialIds();
  let lease = 0;
  let rebase = 0;
  const repository = new SQLiteFieldNotesRepository({
    clock: { now: () => new Date(BASE_TIME + manualClock.now()).toISOString() },
    ids,
    openDatabase: async () => database.asExpoDatabase(),
  });
  await repository.ready();
  const makeSyncRepository = (
    beforeCheckpointCommit = options.beforeCheckpointCommit,
  ) => new SQLiteSyncRepositoryAdapter(repository, {
    commandIds: {
      next: (previousCommandId) => `${previousCommandId}:rebase:${++rebase}`,
    },
    nextLeaseToken: () => `lease:${++lease}`,
    now: () => manualClock.now(),
    beforeCheckpointCommit,
  });
  const syncRepository = makeSyncRepository();
  const server = new DeterministicFaultServer(manualClock);
  const budget = new FixedSyncBudget({
    maxCommands: options.maxCommands ?? 1,
    leaseDurationMs: 100,
    retryDelayMs: 10,
    maxAttempts: options.maxAttempts,
  });
  const worker = (
    workerId: string,
    adapter = syncRepository,
    transport: SyncTransport = new FaultServerTransport(server),
  ) => new BoundedSyncWorker({
    repository: adapter,
    transport,
    clock: manualClock,
    budget,
  }).run({ trigger: "manual", workerId });
  return {
    database,
    manualClock,
    repository,
    syncRepository,
    makeSyncRepository,
    server,
    worker,
  };
}

async function updateRecord(
  harness: Harness,
  recordId: string,
  title: string,
) {
  const current = await harness.repository.get(recordId);
  if (current === null) throw new Error(`missing fixture ${recordId}`);
  return harness.repository.saveWithCommand({
    id: recordId,
    expectedLocalRevision: current.localRevision,
    payload: {
      title,
      notes: current.notes,
      status: current.status,
      observedAt: current.observedAt,
      location: current.location,
    },
  });
}

async function waitForControlledDelay(clock: ManualClock): Promise<void> {
  for (let turn = 0; turn < 100 && clock.pendingCount() === 0; turn += 1) {
    await Promise.resolve();
  }
  expect(clock.pendingCount()).toBe(1);
}

describe("Stage 04 production SQLite SyncRepository", () => {
  it("retries response loss with the same immutable snapshot and rebases only a newer pending edit", async () => {
    const harness = await createHarness();
    const first = await updateRecord(harness, "forest-edge", "attempted A");
    harness.server.inject({ kind: "response-loss" }, {
      commandId: first.command.commandId,
    });

    await harness.worker("manual-loss");
    const waiting = await harness.syncRepository.getCommand(first.command.commandId);
    expect(waiting?.state.kind).toBe("retry_wait");
    if (waiting?.state.kind !== "retry_wait") throw new Error("retry state missing");
    expect(waiting.state.attempted).toEqual(first.command);
    expect(harness.server.getApplyCount(first.command.commandId)).toBe(1);

    const newer = await updateRecord(harness, "forest-edge", "newer B");
    harness.manualClock.advanceBy(10);
    const retried = await harness.worker("manual-retry");
    expect(retried.checkpoints[0]?.rebased).toEqual([
      {
        previousCommandId: newer.command.commandId,
        commandId: `${newer.command.commandId}:rebase:1`,
        baseVersion: 1,
      },
    ]);
    const completed = await harness.syncRepository.getCommand(first.command.commandId);
    expect(completed?.state.kind).toBe("completed");
    if (completed?.state.kind !== "completed") throw new Error("completion missing");
    expect(completed.state.attempted).toEqual(first.command);
    expect(completed.state.attempt).toBe(2);
    expect(harness.server.getApplyCount(first.command.commandId)).toBe(1);
    expect(await harness.repository.get("forest-edge")).toMatchObject({
      title: "newer B",
      remoteVersion: 1,
      syncState: "pending",
    });
    const rebased = await harness.syncRepository.getCommand(
      `${newer.command.commandId}:rebase:1`,
    );
    expect(rebased).toMatchObject({
      command: { baseVersion: 1, payload: { title: "newer B" } },
      state: { kind: "pending" },
    });
    harness.database.close();
  });

  it("allows different records to finish out of order without double-claiming one live lease", async () => {
    const harness = await createHarness();
    const first = await updateRecord(harness, "forest-edge", "delayed A");
    const second = await updateRecord(harness, "harbor-light", "fast B");
    harness.server.inject({ kind: "delay", milliseconds: 50 }, {
      commandId: first.command.commandId,
    });

    const delayed = harness.worker("worker-a");
    await waitForControlledDelay(harness.manualClock);
    const contenderSameRecord = await harness.syncRepository.claimNext({
      workerId: "same-record-contender",
      now: harness.manualClock.now(),
      leaseDurationMs: 100,
    });
    expect(contenderSameRecord?.attempted.recordId).toBe(second.command.recordId);
    if (contenderSameRecord === null) throw new Error("second record was not claimable");
    await harness.server.execute(contenderSameRecord.attempted);
    const fastRemote = harness.server.getRecord(second.command.recordId);
    if (fastRemote === null) throw new Error("fast remote record missing");
    await harness.syncRepository.checkpoint({
      claim: contenderSameRecord,
      outcome: {
        kind: "success",
        remote: fastRemote,
        completedAt: harness.manualClock.now(),
      },
    });
    expect((await harness.syncRepository.getCommand(second.command.commandId))?.state.kind)
      .toBe("completed");
    harness.manualClock.advanceBy(50);
    await delayed;
    expect(
      harness.server.snapshot().history
        .filter((event) => event.kind === "applied")
        .map((event) => event.commandId),
    ).toEqual([second.command.commandId, first.command.commandId]);
    harness.database.close();
  });

  it("rolls back a lost checkpoint, then a restarted adapter reclaims the expired lease", async () => {
    let fail = true;
    const harness = await createHarness({
      beforeCheckpointCommit: async () => {
        if (fail) {
          fail = false;
          throw new Error("simulated process loss before checkpoint commit");
        }
      },
    });
    const saved = await updateRecord(harness, "ridge-marker", "checkpoint crash");
    const crashed = await harness.worker("worker-before-crash");
    expect(crashed.stopped).toBe("checkpoint-failed");
    expect(harness.server.getApplyCount(saved.command.commandId)).toBe(1);
    expect((await harness.syncRepository.getCommand(saved.command.commandId))?.state.kind)
      .toBe("in_flight");
    expect((await harness.syncRepository.snapshot()).checkpoints).toEqual([]);

    harness.manualClock.advanceBy(100);
    const restarted = harness.makeSyncRepository(undefined);
    const recovered = await harness.worker("worker-after-restart", restarted);
    expect(recovered.checkpoints[0]?.state).toBe("completed");
    const completed = await restarted.getCommand(saved.command.commandId);
    expect(completed?.state.kind).toBe("completed");
    if (completed?.state.kind !== "completed") throw new Error("completion missing");
    expect(completed.state.attempt).toBe(2);
    expect(harness.server.getApplyCount(saved.command.commandId)).toBe(1);
    expect((await restarted.snapshot()).checkpoints).toHaveLength(1);
    harness.database.close();
  });

  it("persists 401 blocking and resumes the same attempted command only after explicit auth action", async () => {
    const harness = await createHarness({ maxCommands: 2 });
    const saved = await updateRecord(harness, "forest-edge", "auth guarded");
    const later = await updateRecord(harness, "harbor-light", "must remain pending");
    harness.server.inject({ kind: "unauthorized" }, {
      commandId: saved.command.commandId,
    });
    const blockedRun = await harness.worker("auth-block");
    expect(blockedRun.stopped).toBe("auth-blocked");
    const blocked = await harness.syncRepository.getCommand(saved.command.commandId);
    expect(blocked?.state.kind).toBe("blocked_auth");
    if (blocked?.state.kind !== "blocked_auth") throw new Error("auth state missing");
    expect(blocked.state.attempted).toEqual(saved.command);
    expect((await harness.syncRepository.getCommand(later.command.commandId))?.state.kind)
      .toBe("pending");
    expect(harness.server.getApplyCount(later.command.commandId)).toBe(0);
    expect((await harness.syncRepository.getCommand(saved.command.commandId))?.state.kind)
      .toBe("blocked_auth");
    const stillBlocked = await harness.worker("must-not-auto-resume");
    expect(stillBlocked).toMatchObject({ claimed: 0, stopped: "idle" });
    expect((await harness.syncRepository.getCommand(later.command.commandId))?.state.kind)
      .toBe("pending");
    expect(harness.server.getApplyCount(later.command.commandId)).toBe(0);

    expect(await harness.syncRepository.resumeBlockedAuth(harness.manualClock.now())).toBe(1);
    await harness.worker("auth-resumed");
    expect((await harness.syncRepository.getCommand(saved.command.commandId))?.state.kind)
      .toBe("completed");
    expect((await harness.syncRepository.getCommand(later.command.commandId))?.state.kind)
      .toBe("completed");
    expect(harness.server.getApplyCount(saved.command.commandId)).toBe(1);
    harness.database.close();
  });

  it("reconciles an expired lease beyond maxAttempts without another transport send", async () => {
    let failCheckpoint = true;
    const harness = await createHarness({
      maxAttempts: 1,
      beforeCheckpointCommit: async () => {
        if (failCheckpoint) {
          failCheckpoint = false;
          throw new Error("simulated process death");
        }
      },
    });
    const saved = await updateRecord(harness, "forest-edge", "attempt ceiling crash");
    expect((await harness.worker("attempt-one")).stopped).toBe("checkpoint-failed");
    expect(harness.server.getApplyCount(saved.command.commandId)).toBe(1);

    harness.manualClock.advanceBy(100);
    const recovered = await harness.worker("recovered-over-ceiling");
    expect(recovered.checkpoints[0]).toMatchObject({ state: "permanent" });
    expect(harness.server.getApplyCount(saved.command.commandId)).toBe(1);
    expect((await harness.syncRepository.getCommand(saved.command.commandId))?.state)
      .toMatchObject({
        kind: "permanent",
        reason: "attempt-exhausted:expired-lease-recovered-without-resend",
      });
    harness.database.close();
  });

  it("treats malformed and regressed responses as retryable, but preserves permanent terminal state", async () => {
    const harness = await createHarness();
    const malformed = await updateRecord(harness, "forest-edge", "malformed response");
    harness.server.inject({ kind: "malformed-success" }, {
      commandId: malformed.command.commandId,
    });
    await harness.worker("malformed");
    expect((await harness.syncRepository.getCommand(malformed.command.commandId))?.state.kind)
      .toBe("retry_wait");
    expect((await harness.repository.get("forest-edge"))?.remoteVersion).toBeNull();
    harness.manualClock.advanceBy(10);
    await harness.worker("malformed-reconcile");
    expect((await harness.repository.get("forest-edge"))?.remoteVersion).toBe(1);

    harness.server.seedRecord("harbor-light", REMOTE_PAYLOAD, 5);
    await harness.database.runAsync(
      "UPDATE records SET remote_version = 5 WHERE id = 'harbor-light'",
    );
    const versioned = await updateRecord(harness, "harbor-light", "version guarded");
    harness.server.inject({ kind: "version-regression", by: 2 }, {
      commandId: versioned.command.commandId,
    });
    await harness.worker("version-regression");
    expect((await harness.syncRepository.getCommand(versioned.command.commandId))?.state.kind)
      .toBe("retry_wait");
    expect((await harness.repository.get("harbor-light"))?.remoteVersion).toBe(5);
    harness.manualClock.advanceBy(10);
    await harness.worker("version-reconcile");
    expect((await harness.repository.get("harbor-light"))?.remoteVersion).toBe(6);

    const permanent = await updateRecord(harness, "ridge-marker", "terminal policy");
    harness.server.inject({ kind: "permanent-validation", reason: "policy-rejected" }, {
      commandId: permanent.command.commandId,
    });
    await harness.worker("permanent");
    const terminal = await harness.syncRepository.getCommand(permanent.command.commandId);
    expect(terminal?.state).toMatchObject({
      kind: "permanent",
      reason: "policy-rejected",
    });
    expect(await harness.syncRepository.claimNext({
      workerId: "terminal-must-not-retry",
      now: 99_999,
      leaseDurationMs: 100,
    })).toBeNull();
    expect((await harness.repository.get("ridge-marker"))?.title).toBe("terminal policy");
    harness.database.close();
  });

  it("keeps historical permanent evidence without letting it dominate a newer successful revision", async () => {
    const harness = await createHarness();
    const failed = await updateRecord(harness, "forest-edge", "old rejected edit");
    harness.server.inject({ kind: "permanent-validation", reason: "old-policy" }, {
      commandId: failed.command.commandId,
    });
    await harness.worker("old-permanent");
    expect((await harness.repository.get("forest-edge"))?.syncState).toBe("failed");

    const newer = await updateRecord(harness, "forest-edge", "new accepted edit");
    expect(newer.record.syncState).toBe("pending");
    await harness.worker("new-success");
    expect(await harness.repository.get("forest-edge")).toMatchObject({
      title: "new accepted edit",
      syncState: "synced",
      remoteVersion: 1,
    });
    expect((await harness.syncRepository.getCommand(failed.command.commandId))?.state.kind)
      .toBe("permanent");
    harness.database.close();
  });

  it("rejects an out-of-range remote location without a partial success checkpoint", async () => {
    const harness = await createHarness();
    const saved = await updateRecord(harness, "forest-edge", "invalid remote location");
    const transport: SyncTransport = {
      send: async (attempted) => ({
        status: 200,
        body: {
          kind: "success",
          commandId: attempted.commandId,
          record: {
            recordId: attempted.recordId,
            version: 1,
            deleted: false,
            payload: {
              ...attempted.payload,
              location: {
                latitude: 999,
                longitude: 127,
                accuracyMeters: 10,
                measuredAt: "2026-08-09T16:00:00.000Z",
              },
            },
          },
        },
      }),
    };
    const result = await harness.worker("invalid-location", harness.syncRepository, transport);
    expect(result.checkpoints[0]?.state).toBe("retry_wait");
    expect((await harness.repository.get("forest-edge"))?.remoteVersion).toBeNull();
    expect((await harness.repository.get("forest-edge"))?.title)
      .toBe("invalid remote location");
    const checkpoints = (await harness.syncRepository.snapshot()).checkpoints;
    expect(checkpoints).toEqual([
      expect.objectContaining({
        commandId: saved.command.commandId,
        outcome: "retry_wait",
      }),
    ]);
    harness.database.close();
  });

  it("makes repeated malformed UNKNOWN results terminal at the configured attempt ceiling", async () => {
    const harness = await createHarness({ maxAttempts: 2 });
    const saved = await updateRecord(harness, "forest-edge", "bounded malformed");
    const malformed: SyncTransport = {
      send: async (attempted) => ({
        status: 200,
        body: { kind: "success", commandId: attempted.commandId, record: "invalid" },
      }),
    };
    await harness.worker("bounded-1", harness.syncRepository, malformed);
    expect((await harness.syncRepository.getCommand(saved.command.commandId))?.state.kind)
      .toBe("retry_wait");
    harness.manualClock.advanceBy(10);
    await harness.worker("bounded-2", harness.syncRepository, malformed);
    const terminal = await harness.syncRepository.getCommand(saved.command.commandId);
    expect(terminal?.state).toMatchObject({
      kind: "permanent",
      attempt: 2,
      reason: expect.stringMatching(/^attempt-exhausted:/),
    });
    expect(await harness.syncRepository.claimNext({
      workerId: "must-not-reclaim",
      now: 999_999,
      leaseDurationMs: 100,
    })).toBeNull();
    expect(await harness.repository.get("forest-edge")).toMatchObject({
      title: "bounded malformed",
      syncState: "failed",
    });
    harness.database.close();
  });

  it("preserves both conflict sides and resolves latest post-conflict edit with a new ID", async () => {
    const harness = await createHarness();
    harness.server.seedRecord("forest-edge", REMOTE_PAYLOAD, 1);
    const attempted = await updateRecord(harness, "forest-edge", "conflicting local A");
    await harness.worker("conflict");
    const conflicted = await harness.syncRepository.snapshot();
    expect(conflicted.conflicts).toHaveLength(1);
    const conflict = conflicted.conflicts[0]!;
    expect(conflict).toMatchObject({
      commandId: attempted.command.commandId,
      attempted: { payload: { title: "conflicting local A" } },
      local: { payload: { title: "conflicting local A" }, localRevision: 2 },
      remote: { payload: { title: "remote 관찰" }, version: 1 },
    });

    const latest = await updateRecord(harness, "forest-edge", "latest local B");
    expect(latest.record).toMatchObject({ syncState: "conflict", localRevision: 3 });
    expect(await harness.syncRepository.claimNext({
      workerId: "blocked-by-unresolved-conflict",
      now: 0,
      leaseDurationMs: 100,
    })).toBeNull();

    const resolved = await harness.syncRepository.resolveConflict(conflict.conflictId, {
      kind: "local",
      commandId: "resolution-new-id",
      createdAt: "2026-08-09T16:00:10.000Z",
      resolvedAt: 10_000,
    });
    expect(resolved.command).toMatchObject({
      command: {
        commandId: "resolution-new-id",
        baseVersion: 1,
        localRevision: 3,
        payload: { title: "latest local B" },
      },
      state: { kind: "pending" },
    });
    expect(resolved.conflict.resolution).toEqual({
      kind: "local",
      resolvedAt: 10_000,
      resolutionCommandId: "resolution-new-id",
    });
    expect(await harness.syncRepository.getCommand(latest.command.commandId)).toBeNull();
    await harness.worker("resolution-send");
    expect((await harness.syncRepository.getCommand("resolution-new-id"))?.state.kind)
      .toBe("completed");
    expect(harness.server.getApplyCount("resolution-new-id")).toBe(1);
    harness.database.close();
  });
});

describe("Stage 04 v4 to v5 migration", () => {
  it("reconstructs legacy conflict attempted evidence while leaving pending commands unattempted", async () => {
    const database = new NodeSQLiteDatabase();
    await database.execAsync(CREATE_V1_SCHEMA_SQL);
    await database.execAsync(MIGRATE_V1_TO_V2_SQL);
    await database.execAsync(MIGRATE_V2_TO_V3_SQL);
    await database.execAsync(MIGRATE_V3_TO_V4_SQL);
    const localPayload = {
      title: "legacy local",
      notes: "preserve me",
      status: "open",
      observedAt: "2026-08-09T15:00:00.000Z",
    } satisfies RecordPayload;
    await database.runAsync(
      `INSERT INTO records (
         id, title, notes, observed_at, status, local_revision,
         remote_version, sync_state
       ) VALUES (?, ?, ?, ?, 'open', 2, 6, 'conflict')`,
      ["legacy-conflict", localPayload.title, localPayload.notes, localPayload.observedAt],
    );
    await database.runAsync(
      `INSERT INTO outbox (
         command_id, record_id, operation, base_version, local_revision,
         payload_json, state, attempt_count, created_at
       ) VALUES (?, ?, 'upsert', 6, 2, ?, 'conflict', 1, ?)`,
      [
        "legacy-command",
        "legacy-conflict",
        JSON.stringify(localPayload),
        "2026-08-09T15:01:00.000Z",
      ],
    );
    await database.runAsync(
      `INSERT INTO conflicts (
         command_id, record_id, base_version, local_payload_json,
         remote_payload_json, remote_version, created_at
       ) VALUES (?, ?, 6, ?, ?, 7, ?)`,
      [
        "legacy-command",
        "legacy-conflict",
        JSON.stringify(localPayload),
        JSON.stringify(REMOTE_PAYLOAD),
        "2026-08-09T15:02:00.000Z",
      ],
    );
    await database.runAsync(
      `INSERT INTO records (
         id, title, notes, observed_at, status, local_revision, sync_state
       ) VALUES ('legacy-pending', 'pending', '', ?, 'open', 1, 'pending')`,
      ["2026-08-09T15:03:00.000Z"],
    );
    await database.runAsync(
      `INSERT INTO outbox (
         command_id, record_id, operation, base_version, local_revision,
         payload_json, state, attempt_count, created_at
       ) VALUES ('legacy-pending-command', 'legacy-pending', 'upsert', NULL, 1,
         ?, 'pending', 0, ?)`,
      [
        JSON.stringify({ ...localPayload, title: "pending" }),
        "2026-08-09T15:03:01.000Z",
      ],
    );
    await database.execAsync("PRAGMA user_version = 4");

    const repository = new SQLiteFieldNotesRepository({
      openDatabase: async () => database.asExpoDatabase(),
    });
    await repository.ready();
    const sync = new SQLiteSyncRepositoryAdapter(repository);
    const snapshot = await sync.snapshot();
    expect(snapshot.conflicts).toEqual([
      expect.objectContaining({
        commandId: "legacy-command",
        attempted: expect.objectContaining({
          commandId: "legacy-command",
          recordId: "legacy-conflict",
          baseVersion: 6,
          localRevision: 2,
          payload: localPayload,
        }),
        local: { payload: localPayload, localRevision: 2 },
        remote: expect.objectContaining({ version: 7, payload: REMOTE_PAYLOAD }),
      }),
    ]);
    expect(await sync.getCommand("legacy-pending-command")).toMatchObject({
      state: { kind: "pending" },
    });
    expect((await repository.snapshot()).schemaVersion).toBe(6);
    database.close();
  });
});
