import type {
  AttemptedCommand,
  CheckpointOutcome,
  CheckpointResult,
  ClaimedCommand,
  CommandIdGenerator,
  ConflictResolution,
  ConflictResolutionResult,
  DurableCommand,
  DurableCommandState,
  DurableConflict,
  LocalRecord,
  RecordCommand,
  RecordPayload,
  RemoteRecord,
  RepositorySnapshot,
  SyncRepository,
} from "@field-notes/sync-engine";
import type { SQLiteDatabase } from "expo-sqlite";
import { productionIds } from "../storage/productionIdentity";
import type { SQLiteFieldNotesRepository } from "../storage/SQLiteFieldNotesRepository";

type OutboxRow = {
  command_id: string;
  record_id: string;
  operation: string;
  base_version: number | null;
  local_revision: number;
  payload_json: string | null;
  state: string;
  attempt_count: number;
  created_at: string;
  attempted_json: string | null;
  sequence: number | null;
  lease_token: string | null;
  lease_owner: string | null;
  lease_expires_at: number | null;
  next_attempt_at: number | null;
  completed_at: number | null;
  completed_remote_version: number | null;
  conflict_id: string | null;
  last_error: string | null;
};

type RecordRow = {
  id: string;
  title: string;
  notes: string | null;
  status: string;
  observed_at: string;
  location_json: string | null;
  local_revision: number;
  remote_version: number | null;
  sync_state: string;
  deleted_at_local: string | null;
};

type ConflictRow = {
  conflict_id: string;
  command_id: string;
  record_id: string;
  attempted_json: string | null;
  local_payload_json: string | null;
  local_revision: number;
  remote_payload_json: string | null;
  remote_version: number | null;
  remote_deleted: number | null;
  created_at: number;
  resolution_kind: string | null;
  resolved_at: number | null;
  resolution_command_id: string | null;
};

type CheckpointRow = {
  sequence: number;
  command_id: string;
  lease_token: string;
  outcome: string;
};

type AdapterOptions = {
  commandIds?: CommandIdGenerator;
  nextLeaseToken?: () => string;
  now?: () => number;
  /** Test-only crash seam; a throw rolls the entire checkpoint transaction back. */
  beforeCheckpointCommit?: (commandId: string) => Promise<void>;
};

function clone<T>(value: T): T {
  return structuredClone(value);
}

function canonicalize(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (typeof value === "object" && value !== null) {
    const source = value as Record<string, unknown>;
    const result: Record<string, unknown> = {};
    for (const key of Object.keys(source).sort()) {
      result[key] = canonicalize(source[key]);
    }
    return result;
  }
  return value;
}

function sameCommand(left: RecordCommand, right: RecordCommand): boolean {
  return JSON.stringify(canonicalize(left)) === JSON.stringify(canonicalize(right));
}

function requireFiniteInteger(value: unknown, label: string, minimum = 0): number {
  if (!Number.isInteger(value) || (value as number) < minimum) {
    throw new Error(`${label} must be an integer >= ${minimum}`);
  }
  return value as number;
}

function parsePayload(source: string | null, label: string): RecordPayload | null {
  if (source === null) return null;
  const value = JSON.parse(source) as RecordPayload;
  if (
    typeof value !== "object" ||
    value === null ||
    typeof value.title !== "string" ||
    typeof value.notes !== "string" ||
    !(value.status === "draft" || value.status === "open" || value.status === "resolved") ||
    !Number.isFinite(Date.parse(value.observedAt))
  ) {
    throw new Error(`${label} has an invalid payload`);
  }
  if (
    value.location !== undefined &&
    (!Number.isFinite(value.location.latitude) ||
      value.location.latitude < -90 ||
      value.location.latitude > 90 ||
      !Number.isFinite(value.location.longitude) ||
      value.location.longitude < -180 ||
      value.location.longitude > 180 ||
      !Number.isFinite(value.location.accuracyMeters) ||
      value.location.accuracyMeters < 0 ||
      !Number.isFinite(Date.parse(value.location.measuredAt)))
  ) {
    throw new Error(`${label} has an invalid location`);
  }
  return value;
}

function commandFromRow(row: OutboxRow): RecordCommand {
  if (!(row.operation === "upsert" || row.operation === "delete")) {
    throw new Error(`outbox ${row.command_id} has an invalid operation`);
  }
  const payload = parsePayload(row.payload_json, `outbox ${row.command_id}`);
  if ((row.operation === "upsert") !== (payload !== null)) {
    throw new Error(`outbox ${row.command_id} operation and payload disagree`);
  }
  return {
    commandId: row.command_id,
    recordId: row.record_id,
    operation: row.operation,
    baseVersion: row.base_version,
    localRevision: requireFiniteInteger(
      row.local_revision,
      `outbox ${row.command_id} local revision`,
      1,
    ),
    payload,
    createdAt: row.created_at,
  };
}

function attemptedFromRow(row: OutboxRow): AttemptedCommand | null {
  if (row.attempted_json === null) return null;
  const attempted = JSON.parse(row.attempted_json) as RecordCommand;
  const reparsed = commandFromRow({
    ...row,
    command_id: attempted.commandId,
    record_id: attempted.recordId,
    operation: attempted.operation,
    base_version: attempted.baseVersion,
    local_revision: attempted.localRevision,
    payload_json: attempted.payload === null ? null : JSON.stringify(attempted.payload),
    created_at: attempted.createdAt,
  });
  if (attempted.commandId !== row.command_id || attempted.recordId !== row.record_id) {
    throw new Error(`outbox ${row.command_id} attempted identity changed`);
  }
  return reparsed;
}

function durableState(row: OutboxRow): DurableCommandState {
  const attempted = attemptedFromRow(row);
  if (row.state === "pending") {
    if (attempted !== null || row.attempt_count !== 0) {
      throw new Error(`pending outbox ${row.command_id} already has attempted evidence`);
    }
    return { kind: "pending" };
  }
  if (attempted === null) {
    throw new Error(`outbox ${row.command_id} state ${row.state} lacks attempted evidence`);
  }
  const attempt = requireFiniteInteger(
    row.attempt_count,
    `outbox ${row.command_id} attempt count`,
    1,
  );
  if (row.state === "claimed") {
    if (
      row.lease_token === null ||
      row.lease_owner === null ||
      row.lease_expires_at === null
    ) {
      throw new Error(`claimed outbox ${row.command_id} lacks a complete lease`);
    }
    return {
      kind: "in_flight",
      attempted,
      attempt,
      lease: {
        token: row.lease_token,
        owner: row.lease_owner,
        expiresAt: row.lease_expires_at,
      },
    };
  }
  if (row.state === "retry-wait") {
    if (row.next_attempt_at === null || row.last_error === null) {
      throw new Error(`retry outbox ${row.command_id} lacks retry evidence`);
    }
    return {
      kind: "retry_wait",
      attempted,
      attempt,
      nextAttemptAt: row.next_attempt_at,
      reason: row.last_error,
    };
  }
  if (row.state === "blocked-auth") {
    return {
      kind: "blocked_auth",
      attempted,
      attempt,
      reason: row.last_error ?? "unauthorized",
    };
  }
  if (row.state === "conflict") {
    if (row.conflict_id === null) {
      throw new Error(`conflict outbox ${row.command_id} lacks a conflict ID`);
    }
    return { kind: "conflict", attempted, attempt, conflictId: row.conflict_id };
  }
  if (row.state === "permanent-failure") {
    return {
      kind: "permanent",
      attempted,
      attempt,
      reason: row.last_error ?? "permanent-failure",
    };
  }
  if (row.state === "applied") {
    if (row.completed_at === null) {
      throw new Error(`applied outbox ${row.command_id} lacks completion time`);
    }
    return {
      kind: "completed",
      attempted,
      attempt,
      remoteVersion: row.completed_remote_version,
      completedAt: row.completed_at,
    };
  }
  throw new Error(`outbox ${row.command_id} has unknown state ${row.state}`);
}

function durableCommand(row: OutboxRow): DurableCommand {
  return {
    command: commandFromRow(row),
    state: durableState(row),
    sequence: requireFiniteInteger(row.sequence, `outbox ${row.command_id} sequence`),
  };
}

function payloadFromRecord(row: RecordRow): RecordPayload | null {
  if (row.deleted_at_local !== null) return null;
  const payload: RecordPayload = {
    title: row.title,
    notes: row.notes ?? "",
    status:
      row.status === "draft" || row.status === "open" || row.status === "resolved"
        ? row.status
        : (() => {
            throw new Error(`record ${row.id} has invalid status ${row.status}`);
          })(),
    observedAt: row.observed_at,
  };
  if (row.location_json !== null) {
    payload.location = parsePayload(
      JSON.stringify({ ...payload, location: JSON.parse(row.location_json) }),
      `record ${row.id}`,
    )?.location;
  }
  return payload;
}

function syncState(value: string): LocalRecord["syncState"] {
  switch (value) {
    case "pending":
      return "pending";
    case "syncing":
      return "in_flight";
    case "retry-wait":
      return "retry_wait";
    case "blocked-auth":
      return "blocked_auth";
    case "conflict":
      return "conflict";
    case "failed":
      return "permanent";
    case "local-only":
    case "synced":
      return "synced";
    default:
      throw new Error(`record has unknown sync state ${value}`);
  }
}

function localRecord(row: RecordRow): LocalRecord {
  return {
    recordId: row.id,
    payload: payloadFromRecord(row),
    deleted: row.deleted_at_local !== null,
    localRevision: row.local_revision,
    knownRemoteVersion: row.remote_version,
    syncState: syncState(row.sync_state),
  };
}

function conflictFromRow(row: ConflictRow, fallback: OutboxRow | null): DurableConflict {
  const attempted = row.attempted_json === null
    ? fallback === null
      ? null
      : attemptedFromRow(fallback) ?? commandFromRow(fallback)
    : (JSON.parse(row.attempted_json) as RecordCommand);
  if (attempted === null) {
    throw new Error(`conflict ${row.conflict_id} lacks attempted evidence`);
  }
  const localPayload = parsePayload(row.local_payload_json, `conflict ${row.conflict_id} local`);
  const remote: RemoteRecord | null = row.remote_version === null
    ? null
    : {
        recordId: row.record_id,
        payload: parsePayload(
          row.remote_payload_json,
          `conflict ${row.conflict_id} remote`,
        ),
        version: row.remote_version,
        deleted: row.remote_deleted === 1,
      };
  let resolution: DurableConflict["resolution"];
  if (row.resolution_kind === "remote" && row.resolved_at !== null) {
    resolution = { kind: "remote", resolvedAt: row.resolved_at };
  } else if (
    (row.resolution_kind === "local" || row.resolution_kind === "merge") &&
    row.resolved_at !== null &&
    row.resolution_command_id !== null
  ) {
    resolution = {
      kind: row.resolution_kind,
      resolvedAt: row.resolved_at,
      resolutionCommandId: row.resolution_command_id,
    };
  } else if (
    row.resolution_kind !== null ||
    row.resolved_at !== null ||
    row.resolution_command_id !== null
  ) {
    throw new Error(`conflict ${row.conflict_id} has partial resolution evidence`);
  }
  const result: DurableConflict = {
    conflictId: row.conflict_id,
    commandId: row.command_id,
    recordId: row.record_id,
    attempted,
    local: { payload: localPayload, localRevision: row.local_revision },
    remote,
    createdAt: row.created_at,
  };
  if (resolution !== undefined) result.resolution = resolution;
  return result;
}

function checkpointOutcomeTime(outcome: CheckpointOutcome, fallback: number): number {
  if (outcome.kind === "success") return outcome.completedAt;
  if (outcome.kind === "conflict") return outcome.createdAt;
  return fallback;
}

function isoFromMilliseconds(value: number): string {
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) throw new Error("timestamp is outside Date range");
  return date.toISOString();
}

export class SQLiteSyncRepositoryAdapter implements SyncRepository {
  readonly #source: Pick<SQLiteFieldNotesRepository, "databaseForSyncAdapter">;
  readonly #commandIds: CommandIdGenerator;
  readonly #nextLeaseToken: () => string;
  readonly #now: () => number;
  readonly #beforeCheckpointCommit?: (commandId: string) => Promise<void>;

  public constructor(
    source: Pick<SQLiteFieldNotesRepository, "databaseForSyncAdapter">,
    options: AdapterOptions = {},
  ) {
    this.#source = source;
    this.#commandIds = options.commandIds ?? {
      next: () => productionIds.commandId(),
    };
    this.#nextLeaseToken = options.nextLeaseToken ?? (() => productionIds.externalOperationId());
    this.#now = options.now ?? Date.now;
    this.#beforeCheckpointCommit = options.beforeCheckpointCommit;
  }

  async #db(): Promise<SQLiteDatabase> {
    return this.#source.databaseForSyncAdapter();
  }

  public async claimNext(input: {
    workerId: string;
    now: number;
    leaseDurationMs: number;
  }): Promise<ClaimedCommand | null> {
    if (!Number.isFinite(input.now)) throw new TypeError("claim time must be finite");
    if (!Number.isFinite(input.leaseDurationMs) || input.leaseDurationMs <= 0) {
      throw new RangeError("lease duration must be positive");
    }
    const db = await this.#db();
    let result: ClaimedCommand | null = null;
    await db.withExclusiveTransactionAsync(async (txn) => {
      const row = await txn.getFirstAsync<OutboxRow>(
        `SELECT candidate.* FROM outbox AS candidate
         WHERE (
           (candidate.state = 'claimed' AND candidate.lease_expires_at <= ?)
           OR (
             (
               candidate.state = 'pending' OR
               (candidate.state = 'retry-wait' AND candidate.next_attempt_at <= ?)
             ) AND NOT EXISTS (
               SELECT 1 FROM outbox AS live
               WHERE live.record_id = candidate.record_id
                 AND live.state = 'claimed'
                 AND live.lease_expires_at > ?
             )
           )
         ) AND NOT EXISTS (
           SELECT 1 FROM conflicts AS unresolved
           WHERE unresolved.record_id = candidate.record_id
             AND unresolved.resolution_kind IS NULL
         ) AND NOT EXISTS (
           SELECT 1 FROM outbox AS auth_block
           WHERE auth_block.state = 'blocked-auth'
         )
         ORDER BY candidate.sequence, candidate.command_id
         LIMIT 1`,
        [input.now, input.now, input.now],
      );
      if (row === null) return;
      const priorAttempted = attemptedFromRow(row);
      const attempted = priorAttempted ?? commandFromRow(row);
      if (row.state !== "pending" && priorAttempted === null) {
        throw new Error(`retryable command ${row.command_id} lost attempted evidence`);
      }
      const attempt = row.attempt_count + 1;
      const lease = {
        token: this.#nextLeaseToken(),
        owner: input.workerId,
        expiresAt: input.now + input.leaseDurationMs,
      };
      const update = await txn.runAsync(
        `UPDATE outbox
         SET state = 'claimed', attempted_json = COALESCE(attempted_json, ?),
             attempt_count = ?, claimed_at = ?, last_error = NULL,
             lease_token = ?, lease_owner = ?, lease_expires_at = ?,
             next_attempt_at = NULL
         WHERE command_id = ?`,
        [
          JSON.stringify(attempted),
          attempt,
          isoFromMilliseconds(input.now),
          lease.token,
          lease.owner,
          lease.expiresAt,
          row.command_id,
        ],
      );
      if (update.changes !== 1) throw new Error("atomic sync claim lost its candidate");
      await this.#refreshRecordState(txn, row.record_id);
      const record = await txn.getFirstAsync<{ remote_version: number | null }>(
        "SELECT remote_version FROM records WHERE id = ?",
        [row.record_id],
      );
      if (record === null) throw new Error("sync claim record is missing");
      result = {
        commandId: row.command_id,
        attempted: clone(attempted),
        attempt,
        lease,
        knownRemoteVersion: record.remote_version,
      };
    });
    return result;
  }

  public async checkpoint(input: {
    claim: ClaimedCommand;
    outcome: CheckpointOutcome;
  }): Promise<CheckpointResult> {
    const db = await this.#db();
    let result: CheckpointResult | null = null;
    await db.withExclusiveTransactionAsync(async (txn) => {
      const row = await txn.getFirstAsync<OutboxRow>(
        "SELECT * FROM outbox WHERE command_id = ?",
        [input.claim.commandId],
      );
      if (row === null || row.state !== "claimed") {
        throw new Error("checkpoint requires a currently in-flight command");
      }
      if (row.lease_token !== input.claim.lease.token) {
        throw new Error("checkpoint lease token is stale");
      }
      const attempted = attemptedFromRow(row);
      if (attempted === null || !sameCommand(attempted, input.claim.attempted)) {
        throw new Error("attempted command snapshot changed before checkpoint");
      }
      const rebased: CheckpointResult["rebased"] = [];
      if (input.outcome.kind === "success") {
        await this.#checkpointSuccess(txn, row, attempted, input.outcome, rebased);
      } else if (input.outcome.kind === "conflict") {
        await this.#checkpointConflict(txn, row, attempted, input.outcome);
      } else if (input.outcome.kind === "retry_wait") {
        await txn.runAsync(
          `UPDATE outbox SET state = 'retry-wait', next_attempt_at = ?, last_error = ?,
             lease_token = NULL, lease_owner = NULL, lease_expires_at = NULL
           WHERE command_id = ?`,
          [input.outcome.nextAttemptAt, input.outcome.reason, row.command_id],
        );
      } else if (input.outcome.kind === "blocked_auth") {
        await txn.runAsync(
          `UPDATE outbox SET state = 'blocked-auth', last_error = ?,
             lease_token = NULL, lease_owner = NULL, lease_expires_at = NULL
           WHERE command_id = ?`,
          [input.outcome.reason, row.command_id],
        );
      } else {
        await txn.runAsync(
          `UPDATE outbox SET state = 'permanent-failure', last_error = ?,
             lease_token = NULL, lease_owner = NULL, lease_expires_at = NULL
           WHERE command_id = ?`,
          [input.outcome.reason, row.command_id],
        );
      }
      await txn.runAsync(
        `INSERT INTO sync_checkpoints
           (command_id, lease_token, outcome, created_at)
         VALUES (?, ?, ?, ?)`,
        [
          row.command_id,
          input.claim.lease.token,
          input.outcome.kind,
          checkpointOutcomeTime(input.outcome, this.#now()),
        ],
      );
      await this.#refreshRecordState(txn, row.record_id);
      await this.#beforeCheckpointCommit?.(row.command_id);
      const updated = await txn.getFirstAsync<{ state: string }>(
        "SELECT state FROM outbox WHERE command_id = ?",
        [row.command_id],
      );
      if (updated === null) throw new Error("checkpoint command disappeared");
      result = {
        commandId: row.command_id,
        state:
          updated.state === "retry-wait"
            ? "retry_wait"
            : updated.state === "blocked-auth"
              ? "blocked_auth"
              : updated.state === "permanent-failure"
                ? "permanent"
                : updated.state === "applied"
                  ? "completed"
                  : updated.state as DurableCommandState["kind"],
        rebased,
      };
    });
    if (result === null) throw new Error("checkpoint transaction produced no result");
    return result;
  }

  async #checkpointSuccess(
    txn: SQLiteDatabase,
    row: OutboxRow,
    attempted: AttemptedCommand,
    outcome: Extract<CheckpointOutcome, { kind: "success" }>,
    rebased: CheckpointResult["rebased"],
  ): Promise<void> {
    const remote = outcome.remote;
    if (remote.recordId !== attempted.recordId) {
      throw new Error("success remote record does not match attempted command");
    }
    const local = await txn.getFirstAsync<RecordRow>(
      "SELECT * FROM records WHERE id = ?",
      [attempted.recordId],
    );
    if (local === null) throw new Error("local record is missing during success checkpoint");
    if (local.remote_version !== null && remote.version < local.remote_version) {
      throw new Error("repository refused remote version regression");
    }
    if (local.local_revision === attempted.localRevision) {
      if (remote.deleted) {
        await txn.runAsync(
          `UPDATE records SET remote_version = ?, deleted_at_local = COALESCE(deleted_at_local, ?)
           WHERE id = ?`,
          [remote.version, isoFromMilliseconds(outcome.completedAt), local.id],
        );
      } else {
        if (remote.payload === null) throw new Error("live remote success lacks payload");
        await this.#writeRemotePayload(txn, local.id, remote.payload, remote.version, null);
      }
    } else {
      await txn.runAsync("UPDATE records SET remote_version = ? WHERE id = ?", [
        remote.version,
        local.id,
      ]);
    }
    await txn.runAsync(
      `UPDATE outbox SET state = 'applied', completed_at = ?,
         completed_remote_version = ?, last_error = NULL,
         lease_token = NULL, lease_owner = NULL, lease_expires_at = NULL,
         conflict_id = NULL
       WHERE command_id = ?`,
      [outcome.completedAt, remote.version, row.command_id],
    );

    const pending = await txn.getAllAsync<OutboxRow>(
      `SELECT * FROM outbox
       WHERE record_id = ? AND state = 'pending'
       ORDER BY sequence, command_id`,
      [attempted.recordId],
    );
    for (const candidate of pending) {
      if (candidate.base_version === remote.version) continue;
      const commandId = this.#commandIds.next(candidate.command_id);
      if (commandId === candidate.command_id) {
        throw new Error("rebase requires a new command ID");
      }
      const update = await txn.runAsync(
        `UPDATE outbox SET command_id = ?, base_version = ?
         WHERE command_id = ? AND state = 'pending' AND attempted_json IS NULL`,
        [commandId, remote.version, candidate.command_id],
      );
      if (update.changes !== 1) throw new Error("pending rebase lost its guard");
      rebased.push({
        previousCommandId: candidate.command_id,
        commandId,
        baseVersion: remote.version,
      });
    }
  }

  async #checkpointConflict(
    txn: SQLiteDatabase,
    row: OutboxRow,
    attempted: AttemptedCommand,
    outcome: Extract<CheckpointOutcome, { kind: "conflict" }>,
  ): Promise<void> {
    const local = await txn.getFirstAsync<RecordRow>(
      "SELECT * FROM records WHERE id = ?",
      [attempted.recordId],
    );
    if (local === null) throw new Error("local record is missing during conflict checkpoint");
    if (
      outcome.remote !== null &&
      local.remote_version !== null &&
      outcome.remote.version < local.remote_version
    ) {
      throw new Error("repository refused conflict version regression");
    }
    if (outcome.remote !== null) {
      await txn.runAsync("UPDATE records SET remote_version = ? WHERE id = ?", [
        outcome.remote.version,
        local.id,
      ]);
    }
    const conflictId = `conflict:${attempted.commandId}`;
    await txn.runAsync(
      `INSERT INTO conflicts (
         conflict_id, command_id, record_id, attempted_json,
         local_payload_json, local_revision,
         remote_payload_json, remote_version, remote_deleted, created_at
       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        conflictId,
        row.command_id,
        attempted.recordId,
        JSON.stringify(attempted),
        local.deleted_at_local === null
          ? JSON.stringify(payloadFromRecord(local))
          : null,
        local.local_revision,
        outcome.remote?.payload === null || outcome.remote === null
          ? null
          : JSON.stringify(outcome.remote.payload),
        outcome.remote?.version ?? null,
        outcome.remote?.deleted === true ? 1 : outcome.remote === null ? null : 0,
        outcome.createdAt,
      ],
    );
    await txn.runAsync(
      `UPDATE outbox SET state = 'conflict', conflict_id = ?,
         lease_token = NULL, lease_owner = NULL, lease_expires_at = NULL
       WHERE command_id = ?`,
      [conflictId, row.command_id],
    );
  }

  async #writeRemotePayload(
    txn: SQLiteDatabase,
    recordId: string,
    payload: RecordPayload,
    remoteVersion: number | null,
    deletedAt: string | null,
  ): Promise<void> {
    await txn.runAsync(
      `UPDATE records SET title = ?, notes = ?, status = ?, observed_at = ?,
         location_json = ?, remote_version = ?, deleted_at_local = ?
       WHERE id = ?`,
      [
        payload.title,
        payload.notes,
        payload.status,
        payload.observedAt,
        payload.location === undefined ? null : JSON.stringify(payload.location),
        remoteVersion,
        deletedAt,
        recordId,
      ],
    );
  }

  async #refreshRecordState(
    txn: Pick<SQLiteDatabase, "getAllAsync" | "runAsync">,
    recordId: string,
  ): Promise<void> {
    const rows = await txn.getAllAsync<{ state: string; local_revision: number }>(
      `SELECT state, local_revision FROM outbox
       WHERE record_id = ? AND state != 'applied'`,
      [recordId],
    );
    const record = await txn.getAllAsync<{ local_revision: number }>(
      "SELECT local_revision FROM records WHERE id = ?",
      [recordId],
    );
    const currentRevision = record[0]?.local_revision;
    if (currentRevision === undefined || !Number.isInteger(currentRevision)) {
      throw new Error("record revision is missing");
    }
    const states = rows.map((row) => row.state);
    const currentPermanentFailure = rows.some(
      (row) =>
        row.state === "permanent-failure" &&
        row.local_revision >= currentRevision,
    );
    const state = states.includes("conflict")
      ? "conflict"
      : states.includes("blocked-auth")
        ? "blocked-auth"
        : currentPermanentFailure
          ? "failed"
          : states.includes("claimed")
            ? "syncing"
            : states.includes("retry-wait")
              ? "retry-wait"
              : states.includes("pending")
                ? "pending"
                : "synced";
    await txn.runAsync("UPDATE records SET sync_state = ? WHERE id = ?", [state, recordId]);
  }

  public async resumeBlockedAuth(now: number): Promise<number> {
    if (!Number.isFinite(now)) throw new TypeError("resume time must be finite");
    const db = await this.#db();
    let resumed = 0;
    await db.withExclusiveTransactionAsync(async (txn) => {
      const records = await txn.getAllAsync<{ record_id: string }>(
        "SELECT DISTINCT record_id FROM outbox WHERE state = 'blocked-auth'",
      );
      const update = await txn.runAsync(
        `UPDATE outbox SET state = 'retry-wait', next_attempt_at = ?,
           last_error = 'auth-resumed'
         WHERE state = 'blocked-auth'`,
        [now],
      );
      resumed = update.changes;
      for (const row of records) await this.#refreshRecordState(txn, row.record_id);
    });
    return resumed;
  }

  public async resolveConflict(
    conflictId: string,
    resolution: ConflictResolution,
  ): Promise<ConflictResolutionResult> {
    const validatedMergePayload = resolution.kind === "merge"
      ? parsePayload(JSON.stringify(resolution.payload), "merge resolution")
      : null;
    if (resolution.kind === "merge" && validatedMergePayload === null) {
      throw new Error("merge resolution requires a payload");
    }
    const db = await this.#db();
    let result: ConflictResolutionResult | null = null;
    await db.withExclusiveTransactionAsync(async (txn) => {
      const row = await txn.getFirstAsync<ConflictRow>(
        "SELECT * FROM conflicts WHERE conflict_id = ?",
        [conflictId],
      );
      if (row === null) throw new Error(`unknown conflict: ${conflictId}`);
      if (row.resolution_kind !== null) {
        throw new Error(`conflict already resolved: ${conflictId}`);
      }
      const original = await txn.getFirstAsync<OutboxRow>(
        "SELECT * FROM outbox WHERE command_id = ?",
        [row.command_id],
      );
      if (original === null || original.state !== "conflict") {
        throw new Error("conflict command is not in conflict state");
      }
      const conflict = conflictFromRow(row, original);
      const record = await txn.getFirstAsync<RecordRow>(
        "SELECT * FROM records WHERE id = ?",
        [row.record_id],
      );
      if (record === null) throw new Error("conflict local record is missing");
      let resolutionCommand: DurableCommand | null = null;
      const remoteVersion = conflict.remote?.version ?? null;

      if (resolution.kind === "remote") {
        await txn.runAsync(
          `DELETE FROM outbox
           WHERE record_id = ? AND state = 'pending' AND attempted_json IS NULL`,
          [row.record_id],
        );
        if (conflict.remote === null || conflict.remote.deleted) {
          await txn.runAsync(
            `UPDATE records SET remote_version = ?, deleted_at_local = ? WHERE id = ?`,
            [remoteVersion, isoFromMilliseconds(resolution.resolvedAt), row.record_id],
          );
        } else {
          if (conflict.remote.payload === null) throw new Error("remote resolution lacks payload");
          await this.#writeRemotePayload(
            txn,
            row.record_id,
            conflict.remote.payload,
            remoteVersion,
            null,
          );
        }
        await txn.runAsync(
          `UPDATE conflicts SET resolution_kind = 'remote', resolved_at = ?
           WHERE conflict_id = ?`,
          [resolution.resolvedAt, conflictId],
        );
      } else {
        if (resolution.commandId === original.command_id) {
          throw new Error("conflict resolution requires a new command ID");
        }
        const existing = await txn.getFirstAsync<{ command_id: string }>(
          "SELECT command_id FROM outbox WHERE command_id = ?",
          [resolution.commandId],
        );
        if (existing !== null) {
          throw new Error(`resolution command already exists: ${resolution.commandId}`);
        }
        const payload = resolution.kind === "merge"
          ? clone(validatedMergePayload)
          : clone(payloadFromRecord(record));
        const localRevision = resolution.kind === "merge"
          ? record.local_revision + 1
          : record.local_revision;
        const command: RecordCommand = {
          commandId: resolution.commandId,
          recordId: row.record_id,
          operation: payload === null ? "delete" : "upsert",
          baseVersion: remoteVersion,
          localRevision,
          payload,
          createdAt: resolution.createdAt,
        };
        await txn.runAsync(
          `DELETE FROM outbox
           WHERE record_id = ? AND state = 'pending' AND attempted_json IS NULL`,
          [row.record_id],
        );
        await txn.runAsync(
          `INSERT INTO outbox (
             command_id, record_id, operation, base_version, local_revision,
             payload_json, payload_version, state, attempt_count, created_at, sequence
           ) VALUES (?, ?, ?, ?, ?, ?, 1, 'pending', 0, ?,
             (SELECT COALESCE(MAX(sequence), 0) + 1 FROM outbox)
           )`,
          [
            command.commandId,
            command.recordId,
            command.operation,
            command.baseVersion,
            command.localRevision,
            command.payload === null ? null : JSON.stringify(command.payload),
            command.createdAt,
          ],
        );
        if (payload === null) {
          await txn.runAsync(
            `UPDATE records SET local_revision = ?, remote_version = ?, deleted_at_local = ?
             WHERE id = ?`,
            [
              localRevision,
              remoteVersion,
              isoFromMilliseconds(resolution.resolvedAt),
              row.record_id,
            ],
          );
        } else {
          await this.#writeRemotePayload(txn, row.record_id, payload, remoteVersion, null);
          await txn.runAsync("UPDATE records SET local_revision = ? WHERE id = ?", [
            localRevision,
            row.record_id,
          ]);
        }
        await txn.runAsync(
          `UPDATE conflicts SET resolution_kind = ?, resolved_at = ?,
             resolution_command_id = ? WHERE conflict_id = ?`,
          [resolution.kind, resolution.resolvedAt, resolution.commandId, conflictId],
        );
        resolutionCommand = {
          command,
          state: { kind: "pending" },
          sequence: requireFiniteInteger(
            (await txn.getFirstAsync<{ sequence: number }>(
              "SELECT sequence FROM outbox WHERE command_id = ?",
              [command.commandId],
            ))?.sequence,
            "resolution command sequence",
          ),
        };
      }
      await txn.runAsync(
        `UPDATE outbox SET state = 'applied', completed_at = ?,
           completed_remote_version = ?, conflict_id = NULL
         WHERE command_id = ?`,
        [resolution.resolvedAt, remoteVersion, original.command_id],
      );
      await this.#refreshRecordState(txn, row.record_id);
      const resolvedRow = await txn.getFirstAsync<ConflictRow>(
        "SELECT * FROM conflicts WHERE conflict_id = ?",
        [conflictId],
      );
      if (resolvedRow === null) throw new Error("resolved conflict disappeared");
      result = {
        conflict: conflictFromRow(resolvedRow, original),
        command: resolutionCommand,
      };
    });
    if (result === null) throw new Error("resolution transaction produced no result");
    return result;
  }

  public async getCommand(commandId: string): Promise<DurableCommand | null> {
    const row = await (await this.#db()).getFirstAsync<OutboxRow>(
      "SELECT * FROM outbox WHERE command_id = ?",
      [commandId],
    );
    return row === null ? null : durableCommand(row);
  }

  public async getRecord(recordId: string): Promise<LocalRecord | null> {
    const row = await (await this.#db()).getFirstAsync<RecordRow>(
      "SELECT * FROM records WHERE id = ?",
      [recordId],
    );
    return row === null ? null : localRecord(row);
  }

  public async getConflict(conflictId: string): Promise<DurableConflict | null> {
    const db = await this.#db();
    const row = await db.getFirstAsync<ConflictRow>(
      "SELECT * FROM conflicts WHERE conflict_id = ?",
      [conflictId],
    );
    if (row === null) return null;
    const command = await db.getFirstAsync<OutboxRow>(
      "SELECT * FROM outbox WHERE command_id = ?",
      [row.command_id],
    );
    return conflictFromRow(row, command);
  }

  public async snapshot(): Promise<RepositorySnapshot> {
    const db = await this.#db();
    const [recordRows, commandRows, conflictRows, checkpointRows] = await Promise.all([
      db.getAllAsync<RecordRow>("SELECT * FROM records ORDER BY id"),
      db.getAllAsync<OutboxRow>("SELECT * FROM outbox ORDER BY sequence, command_id"),
      db.getAllAsync<ConflictRow>("SELECT * FROM conflicts ORDER BY conflict_id"),
      db.getAllAsync<CheckpointRow>(
        `SELECT sequence, command_id, lease_token, outcome
         FROM sync_checkpoints ORDER BY sequence`,
      ),
    ]);
    const commandRowsById = new Map(commandRows.map((row) => [row.command_id, row]));
    return {
      records: recordRows.map(localRecord),
      commands: commandRows.map(durableCommand),
      conflicts: conflictRows.map((row) =>
        conflictFromRow(row, commandRowsById.get(row.command_id) ?? null),
      ),
      checkpoints: checkpointRows.map((row) => {
        if (
          !(row.outcome === "success" ||
            row.outcome === "conflict" ||
            row.outcome === "retry_wait" ||
            row.outcome === "blocked_auth" ||
            row.outcome === "permanent")
        ) {
          throw new Error(`checkpoint ${row.sequence} has invalid outcome`);
        }
        return {
          sequence: row.sequence,
          commandId: row.command_id,
          leaseToken: row.lease_token,
          outcome: row.outcome,
        };
      }),
    };
  }
}
