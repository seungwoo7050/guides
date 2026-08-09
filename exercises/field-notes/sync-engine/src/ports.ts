import type {
  CheckpointOutcome,
  CheckpointResult,
  ClaimedCommand,
  ConflictResolution,
  ConflictResolutionResult,
  DurableConflict,
  DurableCommand,
  LocalRecord,
  RecordCommand,
  RepositorySnapshot,
  WireResponse,
} from "./types.ts";

export interface SyncRepository {
  claimNext(input: {
    workerId: string;
    now: number;
    leaseDurationMs: number;
  }): Promise<ClaimedCommand | null>;

  checkpoint(input: {
    claim: ClaimedCommand;
    outcome: CheckpointOutcome;
  }): Promise<CheckpointResult>;

  resumeBlockedAuth(now: number): Promise<number>;

  resolveConflict(
    conflictId: string,
    resolution: ConflictResolution,
  ): Promise<ConflictResolutionResult>;

  getCommand(commandId: string): Promise<DurableCommand | null>;
  getRecord(recordId: string): Promise<LocalRecord | null>;
  getConflict(conflictId: string): Promise<DurableConflict | null>;
  snapshot(): Promise<RepositorySnapshot>;
}

export interface SyncTransport {
  send(command: RecordCommand, signal: AbortSignal): Promise<WireResponse>;
}

export interface SyncClock {
  now(): number;
}

export interface SyncBudget {
  canStartNext(input: { claimed: number; now: number }): boolean;
  leaseDurationMs(): number;
  retryDelayMs(input: { attempt: number; reason: string }): number;
}

export interface CommandIdGenerator {
  next(previousCommandId: string): string;
}
