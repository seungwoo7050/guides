import type { CommandIdGenerator, SyncRepository } from "./ports.ts";
import type {
  AttemptedCommand,
  CheckpointOutcome,
  CheckpointResult,
  ClaimedCommand,
  ConflictResolution,
  ConflictResolutionResult,
  DurableConflict,
  DurableCommand,
  DurableCommandState,
  LocalRecord,
  RecordCommand,
  RepositorySnapshot,
} from "./types.ts";

function clone<T>(value: T): T {
  return structuredClone(value);
}

function deepFreeze<T>(value: T): T {
  if (typeof value === "object" && value !== null && !Object.isFrozen(value)) {
    Object.freeze(value);
    for (const child of Object.values(value)) {
      deepFreeze(child);
    }
  }
  return value;
}

function canonicalize(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(canonicalize);
  }
  if (typeof value === "object" && value !== null) {
    const source = value as Record<string, unknown>;
    const target: Record<string, unknown> = {};
    for (const key of Object.keys(source).sort()) {
      target[key] = canonicalize(source[key]);
    }
    return target;
  }
  return value;
}

function sameAttempt(left: AttemptedCommand, right: AttemptedCommand): boolean {
  return JSON.stringify(canonicalize(left)) === JSON.stringify(canonicalize(right));
}

function samePayload(left: LocalRecord["payload"], right: LocalRecord["payload"]): boolean {
  return JSON.stringify(canonicalize(left)) === JSON.stringify(canonicalize(right));
}

function attemptedFrom(state: DurableCommandState): AttemptedCommand | null {
  return state.kind === "pending" ? null : state.attempted;
}

function attemptFrom(state: DurableCommandState): number {
  return state.kind === "pending" ? 0 : state.attempt;
}

export class SequentialCommandIdGenerator implements CommandIdGenerator {
  #sequence: number;

  constructor(initialSequence = 1) {
    this.#sequence = initialSequence;
  }

  next(previousCommandId: string): string {
    return `${previousCommandId}:rebase:${this.#sequence++}`;
  }
}

export class InMemorySyncRepository implements SyncRepository {
  readonly #records = new Map<string, LocalRecord>();
  readonly #commands = new Map<string, DurableCommand>();
  readonly #conflicts = new Map<string, DurableConflict>();
  readonly #checkpoints: RepositorySnapshot["checkpoints"] = [];
  readonly #failCheckpoint = new Set<string>();
  readonly #idGenerator: CommandIdGenerator;
  #sequence = 0;
  #leaseSequence = 0;
  #checkpointSequence = 0;

  constructor(options: {
    idGenerator?: CommandIdGenerator;
    snapshot?: RepositorySnapshot;
  } = {}) {
    this.#idGenerator = options.idGenerator ?? new SequentialCommandIdGenerator();
    if (options.snapshot !== undefined) {
      this.#restore(options.snapshot);
    }
  }

  seedLocalRecord(record: LocalRecord): void {
    this.#records.set(record.recordId, clone(record));
  }

  enqueueLocalCommand(command: RecordCommand): void {
    if (this.#commands.has(command.commandId)) {
      throw new Error(`command already exists: ${command.commandId}`);
    }
    const current = this.#records.get(command.recordId);
    if (current !== undefined && command.localRevision < current.localRevision) {
      throw new Error("local revision cannot move backwards");
    }
    if (
      current !== undefined &&
      command.localRevision === current.localRevision &&
      (!samePayload(current.payload, command.payload) ||
        current.deleted !== (command.operation === "delete"))
    ) {
      throw new Error("same local revision cannot change payload or deletion meaning");
    }

    const record: LocalRecord = {
      recordId: command.recordId,
      payload: clone(command.payload),
      deleted: command.operation === "delete",
      localRevision: command.localRevision,
      knownRemoteVersion: current?.knownRemoteVersion ?? command.baseVersion,
      syncState: "pending",
    };
    this.#records.set(command.recordId, record);
    this.#commands.set(command.commandId, {
      command: clone(command),
      state: { kind: "pending" },
      sequence: this.#sequence++,
    });
    this.#refreshRecordSyncState(command.recordId);
  }

  failNextCheckpoint(commandId: string): void {
    this.#failCheckpoint.add(commandId);
  }

  async claimNext(input: {
    workerId: string;
    now: number;
    leaseDurationMs: number;
  }): Promise<ClaimedCommand | null> {
    if (!Number.isFinite(input.now)) {
      throw new TypeError("claim time must be finite");
    }
    if (!Number.isFinite(input.leaseDurationMs) || input.leaseDurationMs <= 0) {
      throw new RangeError("lease duration must be positive");
    }

    const liveRecordLeases = new Set<string>();
    for (const entry of this.#commands.values()) {
      if (entry.state.kind === "in_flight" && entry.state.lease.expiresAt > input.now) {
        liveRecordLeases.add(entry.command.recordId);
      }
    }

    const candidate = [...this.#commands.values()]
      .sort((left, right) => left.sequence - right.sequence)
      .find((entry) => {
        const { state } = entry;
        if (state.kind === "in_flight") {
          return state.lease.expiresAt <= input.now;
        }
        if (liveRecordLeases.has(entry.command.recordId)) {
          return false;
        }
        if (state.kind === "pending") {
          return true;
        }
        return state.kind === "retry_wait" && state.nextAttemptAt <= input.now;
      });

    if (candidate === undefined) {
      return null;
    }

    const previousAttempted = attemptedFrom(candidate.state);
    const attempted = previousAttempted === null
      ? deepFreeze(clone(candidate.command))
      : previousAttempted;
    const attempt = attemptFrom(candidate.state) + 1;
    const lease = {
      token: `lease:${this.#leaseSequence++}`,
      owner: input.workerId,
      expiresAt: input.now + input.leaseDurationMs,
    };
    candidate.state = { kind: "in_flight", attempted, attempt, lease };
    this.#refreshRecordSyncState(candidate.command.recordId);

    return {
      commandId: candidate.command.commandId,
      attempted: deepFreeze(clone(attempted)),
      attempt,
      lease: clone(lease),
      knownRemoteVersion: this.#records.get(candidate.command.recordId)?.knownRemoteVersion ?? null,
    };
  }

  async checkpoint(input: {
    claim: ClaimedCommand;
    outcome: CheckpointOutcome;
  }): Promise<CheckpointResult> {
    const entry = this.#commands.get(input.claim.commandId);
    if (entry === undefined || entry.state.kind !== "in_flight") {
      throw new Error("checkpoint requires a currently in-flight command");
    }
    if (entry.state.lease.token !== input.claim.lease.token) {
      throw new Error("checkpoint lease token is stale");
    }
    if (!sameAttempt(entry.state.attempted, input.claim.attempted)) {
      throw new Error("attempted command snapshot changed before checkpoint");
    }
    if (this.#failCheckpoint.delete(input.claim.commandId)) {
      throw new Error(`injected checkpoint failure for ${input.claim.commandId}`);
    }

    const attempted = entry.state.attempted;
    const attempt = entry.state.attempt;
    const rebased: CheckpointResult["rebased"] = [];

    switch (input.outcome.kind) {
      case "success": {
        const remote = input.outcome.remote;
        if (remote.recordId !== attempted.recordId) {
          throw new Error("success remote record does not match attempted command");
        }
        const local = this.#records.get(attempted.recordId);
        if (local === undefined) {
          throw new Error("local record is missing during success checkpoint");
        }
        if (
          local.knownRemoteVersion !== null &&
          remote.version < local.knownRemoteVersion
        ) {
          throw new Error("repository refused remote version regression");
        }
        local.knownRemoteVersion = remote.version;
        if (local.localRevision === attempted.localRevision) {
          local.payload = clone(remote.payload);
          local.deleted = remote.deleted;
        }
        entry.state = {
          kind: "completed",
          attempted,
          attempt,
          remoteVersion: remote.version,
          completedAt: input.outcome.completedAt,
        };
        rebased.push(...this.#rebasePending(attempted.recordId, remote.version));
        break;
      }
      case "conflict": {
        const local = this.#records.get(attempted.recordId);
        if (local === undefined) {
          throw new Error("local record is missing during conflict checkpoint");
        }
        if (
          input.outcome.remote !== null &&
          local.knownRemoteVersion !== null &&
          input.outcome.remote.version < local.knownRemoteVersion
        ) {
          throw new Error("repository refused conflict version regression");
        }
        if (input.outcome.remote !== null) {
          local.knownRemoteVersion = input.outcome.remote.version;
        }
        const conflictId = `conflict:${attempted.commandId}`;
        this.#conflicts.set(conflictId, {
          conflictId,
          commandId: attempted.commandId,
          recordId: attempted.recordId,
          attempted: clone(attempted),
          local: {
            payload: clone(local.payload),
            localRevision: local.localRevision,
          },
          remote: clone(input.outcome.remote),
          createdAt: input.outcome.createdAt,
        });
        entry.state = { kind: "conflict", attempted, attempt, conflictId };
        break;
      }
      case "retry_wait":
        entry.state = {
          kind: "retry_wait",
          attempted,
          attempt,
          nextAttemptAt: input.outcome.nextAttemptAt,
          reason: input.outcome.reason,
        };
        break;
      case "blocked_auth":
        entry.state = {
          kind: "blocked_auth",
          attempted,
          attempt,
          reason: input.outcome.reason,
        };
        break;
      case "permanent":
        entry.state = {
          kind: "permanent",
          attempted,
          attempt,
          reason: input.outcome.reason,
        };
        break;
    }

    this.#checkpoints.push({
      sequence: this.#checkpointSequence++,
      commandId: input.claim.commandId,
      leaseToken: input.claim.lease.token,
      outcome: input.outcome.kind,
    });
    this.#refreshRecordSyncState(attempted.recordId);

    return {
      commandId: input.claim.commandId,
      state: entry.state.kind,
      rebased,
    };
  }

  async resumeBlockedAuth(now: number): Promise<number> {
    let resumed = 0;
    const records = new Set<string>();
    for (const entry of this.#commands.values()) {
      if (entry.state.kind !== "blocked_auth") {
        continue;
      }
      entry.state = {
        kind: "retry_wait",
        attempted: entry.state.attempted,
        attempt: entry.state.attempt,
        nextAttemptAt: now,
        reason: "auth-resumed",
      };
      records.add(entry.command.recordId);
      resumed += 1;
    }
    for (const recordId of records) {
      this.#refreshRecordSyncState(recordId);
    }
    return resumed;
  }

  async resolveConflict(
    conflictId: string,
    resolution: ConflictResolution,
  ): Promise<ConflictResolutionResult> {
    const conflict = this.#conflicts.get(conflictId);
    if (conflict === undefined) {
      throw new Error(`unknown conflict: ${conflictId}`);
    }
    if (conflict.resolution !== undefined) {
      throw new Error(`conflict already resolved: ${conflictId}`);
    }
    const original = this.#commands.get(conflict.commandId);
    if (original === undefined || original.state.kind !== "conflict") {
      throw new Error("conflict command is not in conflict state");
    }
    const record = this.#records.get(conflict.recordId);
    if (record === undefined) {
      throw new Error("conflict local record is missing");
    }

    const attempt = original.state.attempt;
    const attempted = original.state.attempted;
    let resolutionCommand: DurableCommand | null = null;

    if (resolution.kind === "remote") {
      record.payload = clone(conflict.remote?.payload ?? null);
      record.deleted = conflict.remote?.deleted ?? true;
      record.knownRemoteVersion = conflict.remote?.version ?? null;
      original.state = {
        kind: "completed",
        attempted,
        attempt,
        remoteVersion: conflict.remote?.version ?? null,
        completedAt: resolution.resolvedAt,
      };
      conflict.resolution = { kind: "remote", resolvedAt: resolution.resolvedAt };
    } else {
      if (this.#commands.has(resolution.commandId)) {
        throw new Error(`resolution command already exists: ${resolution.commandId}`);
      }
      const payload = resolution.kind === "merge"
        ? clone(resolution.payload)
        : clone(conflict.local.payload);
      const localRevision = resolution.kind === "merge"
        ? record.localRevision + 1
        : record.localRevision;
      const command: RecordCommand = {
        commandId: resolution.commandId,
        recordId: conflict.recordId,
        operation: payload === null ? "delete" : "upsert",
        baseVersion: conflict.remote?.version ?? null,
        localRevision,
        payload,
        createdAt: resolution.createdAt,
      };
      resolutionCommand = {
        command,
        state: { kind: "pending" },
        sequence: this.#sequence++,
      };
      this.#commands.set(command.commandId, resolutionCommand);
      record.payload = clone(payload);
      record.deleted = payload === null;
      record.localRevision = localRevision;
      record.knownRemoteVersion = conflict.remote?.version ?? null;
      original.state = {
        kind: "completed",
        attempted,
        attempt,
        remoteVersion: conflict.remote?.version ?? null,
        completedAt: resolution.resolvedAt,
      };
      conflict.resolution = {
        kind: resolution.kind,
        resolvedAt: resolution.resolvedAt,
        resolutionCommandId: resolution.commandId,
      };
    }

    this.#refreshRecordSyncState(conflict.recordId);
    return {
      conflict: clone(conflict),
      command: resolutionCommand === null ? null : clone(resolutionCommand),
    };
  }

  async getCommand(commandId: string): Promise<DurableCommand | null> {
    const entry = this.#commands.get(commandId);
    return entry === undefined ? null : clone(entry);
  }

  async getRecord(recordId: string): Promise<LocalRecord | null> {
    const record = this.#records.get(recordId);
    return record === undefined ? null : clone(record);
  }

  async getConflict(conflictId: string): Promise<DurableConflict | null> {
    const conflict = this.#conflicts.get(conflictId);
    return conflict === undefined ? null : clone(conflict);
  }

  async snapshot(): Promise<RepositorySnapshot> {
    return {
      records: [...this.#records.values()]
        .map((record) => clone(record))
        .sort((left, right) => left.recordId.localeCompare(right.recordId)),
      commands: [...this.#commands.values()]
        .map((command) => clone(command))
        .sort((left, right) => left.sequence - right.sequence),
      conflicts: [...this.#conflicts.values()]
        .map((conflict) => clone(conflict))
        .sort((left, right) => left.conflictId.localeCompare(right.conflictId)),
      checkpoints: clone(this.#checkpoints),
    };
  }

  #rebasePending(
    recordId: string,
    baseVersion: number,
  ): CheckpointResult["rebased"] {
    const rebased: CheckpointResult["rebased"] = [];
    const pending = [...this.#commands.values()]
      .filter((entry) => entry.command.recordId === recordId && entry.state.kind === "pending")
      .sort((left, right) => left.sequence - right.sequence);

    for (const entry of pending) {
      const previousCommandId = entry.command.commandId;
      if (entry.command.baseVersion === baseVersion) {
        continue;
      }
      const commandId = this.#idGenerator.next(previousCommandId);
      if (this.#commands.has(commandId)) {
        throw new Error(`rebase command ID collision: ${commandId}`);
      }
      const replacement: DurableCommand = {
        command: {
          ...clone(entry.command),
          commandId,
          baseVersion,
        },
        state: { kind: "pending" },
        sequence: entry.sequence,
      };
      this.#commands.delete(previousCommandId);
      this.#commands.set(commandId, replacement);
      rebased.push({ previousCommandId, commandId, baseVersion });
    }
    return rebased;
  }

  #refreshRecordSyncState(recordId: string): void {
    const record = this.#records.get(recordId);
    if (record === undefined) {
      return;
    }
    const states = [...this.#commands.values()]
      .filter((entry) => entry.command.recordId === recordId)
      .map((entry) => entry.state.kind);

    if (states.includes("conflict")) {
      record.syncState = "conflict";
    } else if (states.includes("blocked_auth")) {
      record.syncState = "blocked_auth";
    } else if (states.includes("permanent")) {
      record.syncState = "permanent";
    } else if (states.includes("in_flight")) {
      record.syncState = "in_flight";
    } else if (states.includes("retry_wait")) {
      record.syncState = "retry_wait";
    } else if (states.includes("pending")) {
      record.syncState = "pending";
    } else {
      record.syncState = "synced";
    }
  }

  #restore(snapshot: RepositorySnapshot): void {
    for (const record of snapshot.records) {
      this.#records.set(record.recordId, clone(record));
    }
    for (const command of snapshot.commands) {
      const restored = clone(command);
      const attempted = attemptedFrom(restored.state);
      if (attempted !== null) {
        const frozen = deepFreeze(clone(attempted));
        restored.state = { ...restored.state, attempted: frozen } as DurableCommandState;
      }
      this.#commands.set(restored.command.commandId, restored);
      this.#sequence = Math.max(this.#sequence, restored.sequence + 1);
    }
    for (const conflict of snapshot.conflicts) {
      this.#conflicts.set(conflict.conflictId, clone(conflict));
    }
    this.#checkpoints.push(...clone(snapshot.checkpoints));
    this.#checkpointSequence =
      Math.max(0, ...snapshot.checkpoints.map((entry) => entry.sequence + 1));
    const leaseTokens = [
      ...snapshot.commands.flatMap((entry) =>
        entry.state.kind === "in_flight" ? [entry.state.lease.token] : [],
      ),
      ...snapshot.checkpoints.map((entry) => entry.leaseToken),
    ];
    for (const token of leaseTokens) {
      const match = /^lease:(\d+)$/.exec(token);
      if (match?.[1] !== undefined) {
        this.#leaseSequence = Math.max(this.#leaseSequence, Number(match[1]) + 1);
      }
    }
  }
}
