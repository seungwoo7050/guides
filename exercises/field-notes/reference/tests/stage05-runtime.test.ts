import { NotificationIntentCoordinator } from "@field-notes/lifecycle-engine";
import {
  DeterministicClock,
  DeterministicNotificationRepository,
  InMemoryProcessedIntentClaims,
  SequentialNotificationOwnerIds,
} from "@field-notes/lifecycle-engine/testkit";
import type { SyncTransport } from "@field-notes/sync-engine";
import {
  backgroundInvocationSucceeded,
  runBackgroundSync,
} from "../src/lifecycle/BackgroundSyncPolicy";
import { NotificationResponseController } from "../src/lifecycle/NotificationResponseController";
import { SQLiteFieldNotesRepository } from "../src/storage/SQLiteFieldNotesRepository";
import { sequentialIds } from "../src/storage/testing/DeterministicLocalStore";
import {
  createProductionSyncRuntime,
  observedWorkerRun,
} from "../src/sync/ProductionSyncRuntime";
import { NodeSQLiteDatabase } from "./support/NodeSQLiteDatabase";

describe("Stage 05 lifecycle composition", () => {
  it("uses durable checkpoints rather than registration as background success evidence", async () => {
    const controller = new AbortController();
    const durable = await runBackgroundSync({
      runtime: {
        repository: { ready: async () => undefined },
        run: async () => ({
          kind: "ran",
          trigger: "background",
          workerId: "background-1",
          worker: {
            trigger: "background",
            workerId: "background-1",
            claimed: 1,
            checkpoints: [{ outcome: "success" }],
            stopped: "idle",
          },
        }),
      },
      signal: controller.signal,
      deadlineAt: 1_000,
    });
    expect(durable).toEqual({ kind: "durable", claimed: 1, checkpoints: 1 });

    const incomplete = await runBackgroundSync({
      runtime: {
        repository: { ready: async () => undefined },
        run: async () => ({
          kind: "ran",
          trigger: "background",
          workerId: "background-2",
          worker: {
            trigger: "background",
            workerId: "background-2",
            claimed: 1,
            checkpoints: [],
            stopped: "checkpoint-failed",
          },
        }),
      },
      signal: controller.signal,
      deadlineAt: 1_000,
    });
    expect(incomplete).toEqual({ kind: "failed", claimed: 1, checkpoints: 0 });
  });

  it("production-default disabled background state starts no worker", async () => {
    const run = jest.fn();
    const result = await runBackgroundSync({
      runtime: {
        repository: { ready: async () => undefined },
        run,
      },
      signal: new AbortController().signal,
      deadlineAt: 1_000,
      automaticSyncEnabled: async () => false,
    });
    expect(result).toEqual({ kind: "disabled", claimed: 0, checkpoints: 0 });
    expect(run).not.toHaveBeenCalled();
    expect(backgroundInvocationSucceeded(result)).toBe(true);
    expect(backgroundInvocationSucceeded({ kind: "failed" })).toBe(false);
  });

  it("defers notification navigation while an edit draft is open, then acknowledges after routing", async () => {
    const repository = new DeterministicNotificationRepository({
      account: { kind: "active", accountId: "account-1" },
    });
    repository.setRecord("record-1", "active");
    const claims = new InMemoryProcessedIntentClaims();
    const coordinator = new NotificationIntentCoordinator({
      repository,
      claims,
      clock: new DeterministicClock(0),
      owners: new SequentialNotificationOwnerIds(),
      claimLeaseMs: 100,
    });
    let draftActive = true;
    const order: string[] = [];
    const controller = new NotificationResponseController({
      coordinator,
      ledger: { recordTerminalUnclaimed: async () => false },
      draftActive: () => draftActive,
      navigate: async () => {
        order.push(`navigate:${claims.state("notification-message")}`);
      },
      afterNavigation: async () => {
        order.push(`sync:${claims.state("notification-message")}`);
      },
    });
    const response = {
      notification: { request: { content: { data: {
        schemaVersion: 1,
        messageId: "notification-message",
        accountId: "account-1",
        intent: { kind: "record-updated", recordId: "record-1" },
      } } } },
    };
    await expect(controller.handle(response)).resolves.toEqual({
      kind: "retryable",
      code: "draft-active",
    });
    expect(claims.state("notification-message")).toBe("absent");
    expect(order).toEqual([]);

    draftActive = false;
    await expect(controller.handle(response)).resolves.toEqual({ kind: "acknowledged" });
    expect(order).toEqual(["navigate:claimed", "sync:processed"]);
    expect(claims.state("notification-message")).toBe("processed");
  });

  it("releases stale fallback claim when navigation fails, then terminalizes only after retry routes", async () => {
    const repository = new DeterministicNotificationRepository({
      account: { kind: "active", accountId: "account-1" },
    });
    repository.setRecord("record-1", "active");
    repository.setConflict("record-1", "resolved");
    const claims = new InMemoryProcessedIntentClaims();
    const coordinator = new NotificationIntentCoordinator({
      repository,
      claims,
      clock: new DeterministicClock(0),
      owners: new SequentialNotificationOwnerIds(),
      claimLeaseMs: 100,
    });
    let attempts = 0;
    let draftActive = true;
    const routes: string[] = [];
    const controller = new NotificationResponseController({
      coordinator,
      ledger: { recordTerminalUnclaimed: async () => false },
      draftActive: () => draftActive,
      navigate: async (intent) => {
        attempts += 1;
        if (attempts === 1) throw new Error("router unavailable");
        routes.push(intent.kind);
      },
    });
    const response = {
      notification: { request: { content: { data: {
        schemaVersion: 1,
        messageId: "stale-message",
        accountId: "account-1",
        intent: { kind: "record-conflict", recordId: "record-1" },
      } } } },
    };
    await expect(controller.handle(response)).resolves.toEqual({
      kind: "retryable",
      code: "draft-active",
    });
    expect(attempts).toBe(0);
    expect(claims.state("stale-message")).toBe("absent");
    draftActive = false;
    await expect(controller.handle(response)).resolves.toEqual({
      kind: "retryable",
      code: "navigation-failed",
    });
    expect(claims.state("stale-message")).toBe("absent");
    await expect(controller.handle(response)).resolves.toEqual({
      kind: "terminal",
      code: "stale",
    });
    expect(routes).toEqual(["open-record"]);
    expect(claims.state("stale-message")).toBe("processed");
  });

  it("app-active converges durable outbox even when no background invocation occurred", async () => {
    const database = new NodeSQLiteDatabase();
    const repository = new SQLiteFieldNotesRepository({
      ids: sequentialIds(),
      clock: { now: () => "2026-08-09T19:00:00.000Z" },
      openDatabase: async () => database.asExpoDatabase(),
    });
    await repository.ready();
    const current = await repository.get("forest-edge");
    if (current === null) throw new Error("fixture missing");
    const saved = await repository.saveWithCommand({
      id: current.id,
      expectedLocalRevision: current.localRevision,
      payload: {
        title: "foreground convergence",
        notes: current.notes,
        status: current.status,
        observedAt: current.observedAt,
      },
    });
    const transport: SyncTransport = {
      send: async (command) => ({
        status: 200,
        body: {
          kind: "success",
          commandId: command.commandId,
          record: {
            recordId: command.recordId,
            payload: command.payload,
            version: 1,
            deleted: false,
          },
        },
      }),
    };
    let worker = 0;
    const runtime = createProductionSyncRuntime({
      repository,
      transport,
      now: () => 100,
      workerId: () => `app-active-${++worker}`,
    });
    const opportunity = await runtime.run("app-active", { deadlineAt: 1_000 });
    expect(observedWorkerRun(opportunity)).toMatchObject({
      trigger: "app-active",
      claimed: 1,
      checkpoints: [expect.objectContaining({ commandId: saved.command.commandId })],
    });
    expect(await repository.get("forest-edge")).toMatchObject({
      title: "foreground convergence",
      remoteVersion: 1,
      syncState: "synced",
    });
    runtime.dispose();
    database.close();
  });
});
