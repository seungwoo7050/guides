import type {
  AccountReadinessState,
  BoundedWorkerObservation,
  ConflictReadinessState,
  LifecycleSyncTrigger,
  NotificationPermissionState,
  ProcessedIntentClaim,
  RecordReadinessState,
} from "./types.ts";

export interface BoundedWorkerPort {
  run(input: {
    trigger: LifecycleSyncTrigger;
    workerId: string;
    signal?: AbortSignal;
  }): Promise<BoundedWorkerObservation>;
}

export interface LifecycleClock {
  now(): number;
}

export interface DeadlineScheduler {
  schedule(at: number, callback: () => void): () => void;
}

export interface WorkerIdGenerator {
  next(trigger: LifecycleSyncTrigger): string;
}

/** Repository reads are invalid until ready() has completed. */
export interface NotificationStateRepository {
  ready(): Promise<void>;
  currentAccount(): Promise<AccountReadinessState>;
  recordState(recordId: string): Promise<RecordReadinessState>;
  conflictState(recordId: string): Promise<ConflictReadinessState>;
  isSyncBlocked(): Promise<boolean>;
}

export type ProcessedIntentClaimResult =
  | { kind: "claimed"; claim: ProcessedIntentClaim }
  | { kind: "duplicate" }
  | { kind: "busy" };

/**
 * Production implementations must persist claim/complete state. A live lease
 * prevents concurrent navigation; an expired incomplete claim is recoverable.
 */
export interface ProcessedIntentClaimPort {
  claim(input: {
    messageId: string;
    ownerId: string;
    now: number;
    leaseDurationMs: number;
  }): Promise<ProcessedIntentClaimResult>;
  complete(claim: ProcessedIntentClaim): Promise<void>;
  release(claim: ProcessedIntentClaim): Promise<void>;
}

export interface NotificationOwnerIdGenerator {
  next(messageId: string): string;
}

export interface AndroidNotificationChannelPort {
  ensureChannel(): Promise<
    | { kind: "ready" }
    | { kind: "failed"; reason: string }
  >;
}

export interface NotificationPermissionPort {
  current(): Promise<NotificationPermissionState>;
  request(): Promise<NotificationPermissionState>;
}

export interface PushTokenPort {
  getToken(): Promise<
    | { kind: "token"; token: string }
    | { kind: "failed"; reason: string }
  >;
}
