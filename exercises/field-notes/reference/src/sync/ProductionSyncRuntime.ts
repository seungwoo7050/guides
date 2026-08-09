import {
  LifecycleSyncCoordinator,
  type LifecycleSyncTrigger,
  type SyncOpportunityResult,
} from "@field-notes/lifecycle-engine";
import {
  BoundedSyncWorker,
  FixedSyncBudget,
  type SyncTransport,
  type WorkerRunResult,
} from "@field-notes/sync-engine";
import { createSystemWallClockDeadlineScheduler } from "../lifecycle/WallClockDeadlineScheduler";
import { productionIds } from "../storage/productionIdentity";
import {
  SQLiteFieldNotesRepository,
  type SQLiteRepositoryOptions,
} from "../storage/SQLiteFieldNotesRepository";
import { configuredSyncEndpoint, FetchSyncTransport } from "./FetchSyncTransport";
import { SQLiteSyncRepositoryAdapter } from "./SQLiteSyncRepositoryAdapter";

export type ProductionSyncRuntime = {
  repository: SQLiteFieldNotesRepository;
  syncRepository: SQLiteSyncRepositoryAdapter;
  worker: BoundedSyncWorker;
  coordinator: LifecycleSyncCoordinator;
  endpoint: string;
  run(
    trigger: LifecycleSyncTrigger,
    options?: { deadlineAt?: number; signal?: AbortSignal },
  ): Promise<SyncOpportunityResult>;
  dispose(): void;
};

let workerSequence = 0;

function nextWorkerId(trigger: LifecycleSyncTrigger): string {
  workerSequence += 1;
  return `${trigger}-${Date.now().toString(36)}-${workerSequence.toString(36)}`;
}

/** React-independent composition used by mounted UI and headless tasks alike. */
export function createProductionSyncRuntime(options: {
  repository?: SQLiteFieldNotesRepository;
  repositoryOptions?: SQLiteRepositoryOptions;
  transport?: SyncTransport;
  endpoint?: string;
  now?: () => number;
  workerId?: (trigger: LifecycleSyncTrigger) => string;
} = {}): ProductionSyncRuntime {
  const now = options.now ?? Date.now;
  const repository = options.repository ?? new SQLiteFieldNotesRepository(
    options.repositoryOptions,
  );
  const syncRepository = new SQLiteSyncRepositoryAdapter(repository);
  const endpoint = configuredSyncEndpoint(options.endpoint);
  const worker = new BoundedSyncWorker({
    repository: syncRepository,
    transport: options.transport ?? new FetchSyncTransport({ endpoint }),
    clock: { now },
    budget: new FixedSyncBudget({
      maxCommands: 10,
      leaseDurationMs: 30_000,
      retryDelayMs: 5_000,
      maxAttempts: 5,
    }),
  });
  const deadlines = createSystemWallClockDeadlineScheduler();
  const coordinator = new LifecycleSyncCoordinator({
    worker,
    clock: { now },
    deadlines,
    workerIds: { next: options.workerId ?? nextWorkerId },
  });
  return {
    repository,
    syncRepository,
    worker,
    coordinator,
    endpoint,
    run: (trigger, runOptions) => coordinator.runOpportunity(trigger, runOptions),
    dispose: () => deadlines.dispose(),
  };
}

export function observedWorkerRun(
  opportunity: SyncOpportunityResult,
): WorkerRunResult | null {
  const execution = opportunity.kind === "coalesced"
    ? opportunity.execution
    : opportunity;
  return execution.kind === "ran"
    ? (execution.worker as WorkerRunResult)
    : null;
}

/** Claim tokens are process-independent enough for foreground/headless overlap. */
export function nextProductionNotificationClaimToken(): string {
  return productionIds.commandId().replace(/^command-/, "notification-claim-");
}
