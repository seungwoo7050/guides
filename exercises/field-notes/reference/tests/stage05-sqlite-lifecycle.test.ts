import { NotificationIntentCoordinator } from "@field-notes/lifecycle-engine";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { NotificationResponseController } from "../src/lifecycle/NotificationResponseController";
import {
  LOCAL_DEMO_ACCOUNT_ID,
  SQLiteNotificationRepository,
} from "../src/lifecycle/SQLiteNotificationRepository";
import { SQLiteFieldNotesRepository } from "../src/storage/SQLiteFieldNotesRepository";
import {
  CREATE_V1_SCHEMA_SQL,
  MIGRATE_V1_TO_V2_SQL,
  MIGRATE_V2_TO_V3_SQL,
  MIGRATE_V3_TO_V4_SQL,
  MIGRATE_V4_TO_V5_SQL,
} from "../src/storage/migrations";
import { sequentialIds } from "../src/storage/testing/DeterministicLocalStore";
import { NodeSQLiteDatabase } from "./support/NodeSQLiteDatabase";

function repositoryFor(database: NodeSQLiteDatabase) {
  return new SQLiteFieldNotesRepository({
    ids: sequentialIds(),
    clock: { now: () => "2026-08-09T18:00:00.000Z" },
    openDatabase: async () => database.asExpoDatabase(),
  });
}

async function v5Database(): Promise<NodeSQLiteDatabase> {
  const database = new NodeSQLiteDatabase();
  await database.execAsync(CREATE_V1_SCHEMA_SQL);
  await database.execAsync(MIGRATE_V1_TO_V2_SQL);
  await database.execAsync(MIGRATE_V2_TO_V3_SQL);
  await database.execAsync(MIGRATE_V3_TO_V4_SQL);
  await database.execAsync(MIGRATE_V4_TO_V5_SQL);
  await database.runAsync(
    "INSERT INTO processed_intents (intent_key, processed_at) VALUES (?, ?)",
    ["legacy-message", "2026-08-09T17:59:00.000Z"],
  );
  await database.execAsync("PRAGMA user_version = 5");
  return database;
}

describe("Stage 05 SQLite notification lifecycle", () => {
  it("migrates v5 markers to v6 terminal-safe ledger without storing content", async () => {
    const database = await v5Database();
    const repository = repositoryFor(database);
    await repository.ready();
    const notifications = new SQLiteNotificationRepository({ repository });

    expect((await repository.snapshot()).schemaVersion).toBe(6);
    expect(await notifications.inspectLedger()).toEqual([
      {
        messageId: "legacy-message",
        state: "completed",
        completedAt: Date.parse("2026-08-09T17:59:00.000Z"),
      },
    ]);
    expect(await notifications.claim({
      messageId: "legacy-message",
      ownerId: "owner-legacy",
      now: 1,
      leaseDurationMs: 100,
    })).toEqual({ kind: "duplicate" });
    const columns = await database.getAllAsync<{ name: string }>(
      "PRAGMA table_info(processed_intents)",
    );
    expect(columns.map((row) => row.name)).not.toContain("payload");
    database.close();
  });

  it("survives restart, protects a live lease, reclaims expiry and rejects stale completion", async () => {
    const database = new NodeSQLiteDatabase();
    const repository = repositoryFor(database);
    await repository.ready();
    const tokens = ["claim-one", "claim-two"];
    const firstProcess = new SQLiteNotificationRepository({
      repository,
      claimToken: () => tokens.shift() ?? "claim-extra",
      completionNow: () => 250,
    });
    const first = await firstProcess.claim({
      messageId: "message-restart",
      ownerId: "owner-one",
      now: 100,
      leaseDurationMs: 100,
    });
    expect(first.kind).toBe("claimed");
    if (first.kind !== "claimed") throw new Error("claim missing");

    const restarted = new SQLiteNotificationRepository({
      repository,
      claimToken: () => tokens.shift() ?? "claim-extra",
      completionNow: () => 250,
    });
    expect(await restarted.claim({
      messageId: "message-restart",
      ownerId: "owner-two",
      now: 199,
      leaseDurationMs: 100,
    })).toEqual({ kind: "busy" });
    const recovered = await restarted.claim({
      messageId: "message-restart",
      ownerId: "owner-two",
      now: 200,
      leaseDurationMs: 100,
    });
    expect(recovered.kind).toBe("claimed");
    if (recovered.kind !== "claimed") throw new Error("reclaim missing");
    expect(recovered.claim.token).toBe("claim-two");
    await expect(firstProcess.complete(first.claim)).rejects.toThrow("no longer owned");
    await restarted.complete(recovered.claim, {
      kind: "terminal",
      code: "record-deleted",
    });
    expect(await restarted.claim({
      messageId: "message-restart",
      ownerId: "owner-three",
      now: 400,
      leaseDurationMs: 100,
    })).toEqual({ kind: "duplicate" });
    expect(await restarted.inspectLedger()).toEqual([
      {
        messageId: "message-restart",
        state: "terminal",
        completedAt: 250,
        terminalCode: "record-deleted",
      },
    ]);
    expect(await restarted.automaticSyncEnabled()).toBe(false);
    database.close();
  });

  it("reads current record/account state and terminalizes valid account mismatch only", async () => {
    const database = new NodeSQLiteDatabase();
    const repository = repositoryFor(database);
    await repository.ready();
    const notifications = new SQLiteNotificationRepository({
      repository,
      claimToken: () => "claim-state",
      completionNow: () => 500,
    });
    expect(await notifications.currentAccount()).toEqual({
      kind: "active",
      accountId: LOCAL_DEMO_ACCOUNT_ID,
    });
    expect(await notifications.recordState("forest-edge")).toBe("active");
    expect(await notifications.recordState("missing-record")).toBe("missing");

    const record = await repository.get("forest-edge");
    if (record === null) throw new Error("fixture missing");
    await repository.deleteWithCommand({
      id: record.id,
      expectedLocalRevision: record.localRevision,
    });
    expect(await notifications.recordState("forest-edge")).toBe("deleted");

    const coordinator = new NotificationIntentCoordinator({
      repository: notifications,
      claims: notifications,
      clock: { now: () => 400 },
      owners: { next: () => "notification-owner" },
      claimLeaseMs: 100,
    });
    const navigation = jest.fn(async () => undefined);
    const controller = new NotificationResponseController({
      coordinator,
      ledger: notifications,
      draftActive: () => false,
      navigate: navigation,
      now: () => 500,
    });
    const mismatched = {
      notification: { request: { content: { data: {
        schemaVersion: 1,
        messageId: "previous-account-message",
        accountId: "previous-account",
        intent: { kind: "sync-blocked" },
      } } } },
    };
    await expect(controller.handle(mismatched)).resolves.toEqual({
      kind: "terminal",
      code: "account-mismatch",
    });
    await expect(controller.handle({
      notification: { request: { content: { data: { secret: "not-an-envelope" } } } },
    })).resolves.toEqual({ kind: "terminal", code: "malformed" });
    expect(navigation).not.toHaveBeenCalled();
    expect(await notifications.inspectLedger()).toEqual([
      {
        messageId: "previous-account-message",
        state: "terminal",
        completedAt: 500,
        terminalCode: "account-mismatch",
      },
    ]);
    database.close();
  });

  it("rechecks user_version under one migration owner across concurrent connections", async () => {
    const directory = mkdtempSync(join(tmpdir(), "field-notes-v6-race-"));
    const filename = join(directory, "field-notes.db");
    const seed = new NodeSQLiteDatabase(filename);
    await seed.execAsync(CREATE_V1_SCHEMA_SQL);
    await seed.execAsync(MIGRATE_V1_TO_V2_SQL);
    await seed.execAsync(MIGRATE_V2_TO_V3_SQL);
    await seed.execAsync(MIGRATE_V3_TO_V4_SQL);
    await seed.execAsync(MIGRATE_V4_TO_V5_SQL);
    await seed.execAsync("PRAGMA user_version = 5");
    seed.close();

    const firstDb = new NodeSQLiteDatabase(filename);
    const secondDb = new NodeSQLiteDatabase(filename);
    let entered!: () => void;
    let release!: () => void;
    const enteredGate = new Promise<void>((resolve) => { entered = resolve; });
    const releaseGate = new Promise<void>((resolve) => { release = resolve; });
    const first = new SQLiteFieldNotesRepository({
      openDatabase: async () => firstDb.asExpoDatabase(),
      migration: {
        beforeVersionCommit: async (from) => {
          if (from === 5) {
            entered();
            await releaseGate;
          }
        },
      },
    });
    const second = new SQLiteFieldNotesRepository({
      openDatabase: async () => secondDb.asExpoDatabase(),
    });
    const firstReady = first.ready();
    await enteredGate;
    const secondReady = second.ready();
    release();
    await expect(Promise.all([firstReady, secondReady])).resolves.toEqual([
      undefined,
      undefined,
    ]);
    expect((await first.snapshot()).schemaVersion).toBe(6);
    expect((await second.snapshot()).migrationHistory.filter(
      (entry) => entry.fromVersion === 5 && entry.toVersion === 6,
    )).toHaveLength(1);
    firstDb.close();
    secondDb.close();
    rmSync(directory, { recursive: true, force: true });
  });
});
