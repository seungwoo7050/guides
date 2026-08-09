import type {
  Attachment,
  AttachmentRepository,
  Clock,
  ExternalMediaOperation,
  ExternalMediaOperationRepository,
  FieldRecord,
  IdGenerator,
  LocalDatabaseSnapshot,
  LocalStoreInspection,
  OutboxEntry,
  OutboxRepository,
  RecordCommand,
  RecordConflict,
  RecordPayload,
  RecordRepository,
  SyncCheckpoint,
} from "@field-notes/shared";
import {
  openDatabaseAsync,
  type SQLiteDatabase,
} from "expo-sqlite";
import {
  CorruptLocalDataError,
  planRecordDelete,
  planRecordSave,
  snapshotRecordPayload,
  validateRecordPayload,
} from "./localMutation";
import {
  CURRENT_SCHEMA_VERSION,
  migrateSQLiteDatabase,
  type MigrationOptions,
} from "./migrations";
import { productionClock, productionIds } from "./productionIdentity";

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

type OutboxRow = {
  command_id: string;
  record_id: string;
  operation: string;
  base_version: number | null;
  local_revision: number;
  payload_json: string | null;
  payload_version: number;
  state: string;
  attempt_count: number;
  claimed_at: string | null;
  last_error: string | null;
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

type SyncCheckpointRow = {
  sequence: number;
  command_id: string;
  lease_token: string;
  outcome: string;
};

type AttachmentRow = {
  id: string;
  record_id: string;
  local_uri: string;
  checksum: string;
  byte_size: number;
  mime_type: string;
  state: string;
  remote_id: string | null;
};

type ExternalMediaOperationRow = {
  operation_id: string;
  active_slot: number | null;
  record_id: string;
  source: string;
  state: string;
  created_at: string;
  expires_at: string;
  completed_at: string | null;
  attachment_id: string | null;
  failure_reason: string | null;
};

const RECORD_COLUMNS = `
  id, title, notes, status, observed_at, location_json,
  local_revision, remote_version, sync_state, deleted_at_local
`;

const ATTACHMENT_STATES: readonly Attachment["state"][] = [
  "staging",
  "local-ready",
  "upload-pending",
  "uploading",
  "uploaded",
  "missing-local-file",
  "cleanup-pending",
  "removed",
  "failed",
];

const OUTBOX_STATES: readonly OutboxEntry["state"][] = [
  "pending",
  "claimed",
  "retry-wait",
  "blocked-auth",
  "conflict",
  "permanent-failure",
  "applied",
];

function parseLocation(value: string | null): RecordPayload["location"] {
  if (value === null) return undefined;
  try {
    const parsed = JSON.parse(value) as RecordPayload["location"];
    if (
      parsed === undefined ||
      !Number.isFinite(parsed.latitude) ||
      parsed.latitude < -90 ||
      parsed.latitude > 90 ||
      !Number.isFinite(parsed.longitude) ||
      parsed.longitude < -180 ||
      parsed.longitude > 180 ||
      !Number.isFinite(parsed.accuracyMeters) ||
      parsed.accuracyMeters < 0 ||
      !Number.isFinite(Date.parse(parsed.measuredAt))
    ) {
      throw new Error("invalid location values");
    }
    return parsed;
  } catch (error) {
    throw new CorruptLocalDataError("record.location", String(error));
  }
}

function rowToRecord(row: RecordRow): FieldRecord {
  if (!(row.status === "draft" || row.status === "open" || row.status === "resolved")) {
    throw new CorruptLocalDataError(`record:${row.id}`, `unknown status ${row.status}`);
  }
  if (
    !(
      row.sync_state === "local-only" ||
      row.sync_state === "pending" ||
      row.sync_state === "syncing" ||
      row.sync_state === "synced" ||
      row.sync_state === "retry-wait" ||
      row.sync_state === "blocked-auth" ||
      row.sync_state === "conflict" ||
      row.sync_state === "failed"
    )
  ) {
    throw new CorruptLocalDataError(
      `record:${row.id}`,
      `unknown sync state ${row.sync_state}`,
    );
  }
  if (!Number.isInteger(row.local_revision) || row.local_revision < 1) {
    throw new CorruptLocalDataError(`record:${row.id}`, "invalid local revision");
  }
  return {
    id: row.id,
    title: row.title,
    notes: row.notes ?? "",
    status: row.status,
    observedAt: row.observed_at,
    location: parseLocation(row.location_json),
    localRevision: row.local_revision,
    remoteVersion: row.remote_version,
    syncState: row.sync_state,
    deletedAtLocal: row.deleted_at_local ?? undefined,
  };
}

function rowToAttachment(row: AttachmentRow): Attachment {
  if (!ATTACHMENT_STATES.includes(row.state as Attachment["state"])) {
    throw new CorruptLocalDataError(
      `attachment:${row.id}`,
      `unknown state ${row.state}`,
    );
  }
  if (!Number.isInteger(row.byte_size) || row.byte_size <= 0) {
    throw new CorruptLocalDataError(`attachment:${row.id}`, "invalid byte size");
  }
  return {
    id: row.id,
    recordId: row.record_id,
    localUri: row.local_uri,
    checksum: row.checksum,
    byteSize: row.byte_size,
    mimeType: row.mime_type,
    state: row.state as Attachment["state"],
    remoteId: row.remote_id ?? undefined,
  };
}

function rowToExternalMediaOperation(
  row: ExternalMediaOperationRow,
): ExternalMediaOperation {
  if (!(row.source === "camera" || row.source === "photo-picker")) {
    throw new CorruptLocalDataError(
      `external-media:${row.operation_id}`,
      `unknown source ${row.source}`,
    );
  }
  if (
    !(
      row.state === "launched" ||
      row.state === "copying" ||
      row.state === "completed" ||
      row.state === "cancelled" ||
      row.state === "failed" ||
      row.state === "interrupted"
    )
  ) {
    throw new CorruptLocalDataError(
      `external-media:${row.operation_id}`,
      `unknown state ${row.state}`,
    );
  }
  return {
    operationId: row.operation_id,
    recordId: row.record_id,
    source: row.source,
    state: row.state,
    createdAt: row.created_at,
    expiresAt: row.expires_at,
    completedAt: row.completed_at ?? undefined,
    attachmentId: row.attachment_id ?? undefined,
    failureReason: row.failure_reason ?? undefined,
  };
}

function parsePayload(row: OutboxRow): RecordPayload | null {
  if (row.payload_json === null) return null;
  try {
    const payload = JSON.parse(row.payload_json) as RecordPayload;
    validateRecordPayload(payload);
    return payload;
  } catch (error) {
    throw new CorruptLocalDataError(`outbox:${row.command_id}`, String(error));
  }
}

function rowToOutbox(row: OutboxRow): OutboxEntry {
  if (!(row.operation === "upsert" || row.operation === "delete")) {
    throw new CorruptLocalDataError(
      `outbox:${row.command_id}`,
      `unknown operation ${row.operation}`,
    );
  }
  if (!OUTBOX_STATES.includes(row.state as OutboxEntry["state"])) {
    throw new CorruptLocalDataError(
      `outbox:${row.command_id}`,
      `unknown state ${row.state}`,
    );
  }
  if (row.payload_version !== 1) {
    throw new CorruptLocalDataError(
      `outbox:${row.command_id}`,
      `unknown payload version ${row.payload_version}`,
    );
  }
  const payload = parsePayload(row);
  if ((row.operation === "upsert") !== (payload !== null)) {
    throw new CorruptLocalDataError(
      `outbox:${row.command_id}`,
      "operation and payload disagree",
    );
  }
  let attempted: RecordCommand | undefined;
  if (row.attempted_json !== null) {
    try {
      const parsed = JSON.parse(row.attempted_json) as RecordCommand;
      if (
        parsed.commandId !== row.command_id ||
        parsed.recordId !== row.record_id ||
        !(parsed.operation === "upsert" || parsed.operation === "delete") ||
        !Number.isInteger(parsed.localRevision) ||
        !Number.isFinite(Date.parse(parsed.createdAt)) ||
        (parsed.operation === "upsert") !== (parsed.payload !== null)
      ) {
        throw new Error("attempted command does not match outbox identity");
      }
      if (parsed.payload !== null) validateRecordPayload(parsed.payload);
      attempted = parsed;
    } catch (error) {
      throw new CorruptLocalDataError(
        `outbox:${row.command_id}:attempted`,
        String(error),
      );
    }
  }
  const leaseParts = [row.lease_token, row.lease_owner, row.lease_expires_at];
  if (
    leaseParts.some((value) => value !== null) &&
    leaseParts.some((value) => value === null)
  ) {
    throw new CorruptLocalDataError(
      `outbox:${row.command_id}:lease`,
      "partial lease fields",
    );
  }
  return {
    commandId: row.command_id,
    recordId: row.record_id,
    operation: row.operation,
    baseVersion: row.base_version,
    localRevision: row.local_revision,
    payload,
    createdAt: row.created_at,
    payloadVersion: 1,
    state: row.state as OutboxEntry["state"],
    attemptCount: row.attempt_count,
    claimedAt: row.claimed_at ?? undefined,
    lastError: row.last_error ?? undefined,
    attempted,
    lease:
      row.lease_token === null ||
      row.lease_owner === null ||
      row.lease_expires_at === null
        ? undefined
        : {
            token: row.lease_token,
            owner: row.lease_owner,
            expiresAt: row.lease_expires_at,
          },
    nextAttemptAt: row.next_attempt_at ?? undefined,
    completedAt: row.completed_at ?? undefined,
    completedRemoteVersion:
      row.completed_at === null ? undefined : row.completed_remote_version,
    conflictId: row.conflict_id ?? undefined,
    sequence: row.sequence ?? undefined,
  };
}

function rowToConflict(
  row: ConflictRow,
  command: OutboxEntry | undefined,
): RecordConflict {
  const attemptedSource = row.attempted_json ??
    (command?.attempted === undefined ? null : JSON.stringify(command.attempted));
  if (attemptedSource === null) {
    throw new CorruptLocalDataError(
      `conflict:${row.conflict_id}`,
      "attempted command evidence is missing",
    );
  }
  let attempted: RecordCommand;
  let local: RecordPayload | null;
  let remotePayload: RecordPayload | null;
  try {
    attempted = JSON.parse(attemptedSource) as RecordCommand;
    local = row.local_payload_json === null
      ? null
      : (JSON.parse(row.local_payload_json) as RecordPayload);
    remotePayload = row.remote_payload_json === null
      ? null
      : (JSON.parse(row.remote_payload_json) as RecordPayload);
    if (attempted.payload !== null) validateRecordPayload(attempted.payload);
    if (local !== null) validateRecordPayload(local);
    if (remotePayload !== null) validateRecordPayload(remotePayload);
  } catch (error) {
    throw new CorruptLocalDataError(`conflict:${row.conflict_id}`, String(error));
  }
  const remote = row.remote_version === null
    ? null
    : {
        recordId: row.record_id,
        payload: remotePayload,
        version: row.remote_version,
        deleted: row.remote_deleted === 1,
      };
  let resolution: RecordConflict["resolution"];
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
    throw new CorruptLocalDataError(
      `conflict:${row.conflict_id}`,
      "partial resolution evidence",
    );
  }
  return {
    conflictId: row.conflict_id,
    commandId: row.command_id,
    recordId: row.record_id,
    attempted,
    local: { payload: local, localRevision: row.local_revision },
    remote,
    createdAt: row.created_at,
    resolution,
  };
}

function rowToSyncCheckpoint(row: SyncCheckpointRow): SyncCheckpoint {
  if (
    !(row.outcome === "success" ||
      row.outcome === "conflict" ||
      row.outcome === "retry_wait" ||
      row.outcome === "blocked_auth" ||
      row.outcome === "permanent")
  ) {
    throw new CorruptLocalDataError(
      `sync-checkpoint:${row.sequence}`,
      `unknown outcome ${row.outcome}`,
    );
  }
  return {
    sequence: row.sequence,
    commandId: row.command_id,
    leaseToken: row.lease_token,
    outcome: row.outcome,
  };
}

export type SQLiteRepositoryOptions = {
  databaseName?: string;
  clock?: Clock;
  ids?: IdGenerator;
  openDatabase?: (databaseName: string) => Promise<SQLiteDatabase>;
  migration?: Omit<MigrationOptions, "now">;
};

export class SQLiteFieldNotesRepository
  implements
    RecordRepository,
    AttachmentRepository,
    OutboxRepository,
    LocalStoreInspection,
    ExternalMediaOperationRepository
{
  private readonly clock: Clock;
  private readonly ids: IdGenerator;
  private readonly databasePromise: Promise<SQLiteDatabase>;
  private readyPromise: Promise<void> | null = null;

  public constructor(options: SQLiteRepositoryOptions = {}) {
    this.clock = options.clock ?? productionClock;
    this.ids = options.ids ?? productionIds;
    const open = options.openDatabase ?? openDatabaseAsync;
    this.databasePromise = open(options.databaseName ?? "field-notes.db");
    this.migration = options.migration;
  }

  private readonly migration: SQLiteRepositoryOptions["migration"];

  public ready(): Promise<void> {
    this.readyPromise ??= (async () => {
      const db = await this.databasePromise;
      await migrateSQLiteDatabase(db, {
        now: () => this.clock.now(),
        beforeVersionCommit: this.migration?.beforeVersionCommit,
      });
    })();
    return this.readyPromise;
  }

  private async db(): Promise<SQLiteDatabase> {
    await this.ready();
    return this.databasePromise;
  }

  /** Narrow hand-off used by the Stage 04 SQLite SyncRepository adapter. */
  public async databaseForSyncAdapter(): Promise<SQLiteDatabase> {
    return this.db();
  }

  private async currentRecord(
    db: Pick<SQLiteDatabase, "getFirstAsync">,
    id: string,
  ): Promise<FieldRecord | null> {
    const row = await db.getFirstAsync<RecordRow>(
      `SELECT ${RECORD_COLUMNS} FROM records WHERE id = ?`,
      [id],
    );
    return row === null ? null : rowToRecord(row);
  }

  public async list(): Promise<FieldRecord[]> {
    const db = await this.db();
    const rows = await db.getAllAsync<RecordRow>(
      `SELECT ${RECORD_COLUMNS} FROM records
       WHERE deleted_at_local IS NULL
       ORDER BY observed_at DESC, id ASC`,
    );
    return rows.map(rowToRecord);
  }

  public async get(id: string): Promise<FieldRecord | null> {
    const record = await this.currentRecord(await this.db(), id);
    return record?.deletedAtLocal === undefined ? record : null;
  }

  public async saveWithCommand(input: {
    id: string;
    expectedLocalRevision: number | null;
    payload: RecordPayload;
  }): Promise<{ record: FieldRecord; command: RecordCommand }> {
    const stableInput = {
      ...input,
      payload: snapshotRecordPayload(input.payload),
    };
    const db = await this.db();
    const identity = {
      commandId: this.ids.commandId(),
      createdAt: this.clock.now(),
    };
    let result: ReturnType<typeof planRecordSave> | undefined;
    await db.withExclusiveTransactionAsync(async (txn) => {
      const current = await this.currentRecord(txn, stableInput.id);
      result = planRecordSave({ ...stableInput, current, identity });
      const locationJson =
        result.record.location === undefined
          ? null
          : JSON.stringify(result.record.location);
      if (current === null) {
        await txn.runAsync(
          `INSERT INTO records (
             id, title, notes, status, observed_at, location_json,
             local_revision, remote_version, sync_state, deleted_at_local
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)`,
          [
            result.record.id,
            result.record.title,
            result.record.notes,
            result.record.status,
            result.record.observedAt,
            locationJson,
            result.record.localRevision,
            result.record.remoteVersion,
            result.record.syncState,
          ],
        );
      } else {
        const update = await txn.runAsync(
          `UPDATE records
           SET title = ?, notes = ?, status = ?, observed_at = ?, location_json = ?,
               local_revision = ?, sync_state = ?, deleted_at_local = NULL
           WHERE id = ? AND local_revision = ? AND deleted_at_local IS NULL`,
          [
            result.record.title,
            result.record.notes,
            result.record.status,
            result.record.observedAt,
            locationJson,
            result.record.localRevision,
            result.record.syncState,
            result.record.id,
            stableInput.expectedLocalRevision,
          ],
        );
        if (update.changes !== 1) {
          throw new Error("record update lost its revision guard");
        }
      }
      await txn.runAsync(
        `DELETE FROM outbox
         WHERE record_id = ? AND operation = 'upsert' AND state = 'pending'`,
        [stableInput.id],
      );
      await this.insertOutbox(txn, result.outbox);
      const unresolvedConflict = await txn.getFirstAsync<{ conflict_id: string }>(
        `SELECT conflict_id FROM conflicts
         WHERE record_id = ? AND resolution_kind IS NULL LIMIT 1`,
        [stableInput.id],
      );
      if (unresolvedConflict !== null) {
        await txn.runAsync(
          "UPDATE records SET sync_state = 'conflict' WHERE id = ?",
          [stableInput.id],
        );
        result = {
          ...result,
          record: { ...result.record, syncState: "conflict" },
        };
      }
    });
    if (result === undefined) throw new Error("save transaction produced no result");
    return { record: result.record, command: result.command };
  }

  public async deleteWithCommand(input: {
    id: string;
    expectedLocalRevision: number;
  }): Promise<{ record: FieldRecord; command: RecordCommand }> {
    const db = await this.db();
    const identity = {
      commandId: this.ids.commandId(),
      createdAt: this.clock.now(),
    };
    let result: ReturnType<typeof planRecordDelete> | undefined;
    await db.withExclusiveTransactionAsync(async (txn) => {
      const current = await this.currentRecord(txn, input.id);
      result = planRecordDelete({ ...input, current, identity });
      const update = await txn.runAsync(
        `UPDATE records
         SET local_revision = ?, sync_state = 'pending', deleted_at_local = ?
         WHERE id = ? AND local_revision = ? AND deleted_at_local IS NULL`,
        [
          result.record.localRevision,
          result.record.deletedAtLocal ?? null,
          result.record.id,
          input.expectedLocalRevision,
        ],
      );
      if (update.changes !== 1) {
        throw new Error("record delete lost its revision guard");
      }
      await txn.runAsync(
        `UPDATE attachments SET state = 'cleanup-pending'
         WHERE record_id = ? AND state NOT IN ('removed', 'cleanup-pending')`,
        [input.id],
      );
      await this.insertOutbox(txn, result.outbox);
      const unresolvedConflict = await txn.getFirstAsync<{ conflict_id: string }>(
        `SELECT conflict_id FROM conflicts
         WHERE record_id = ? AND resolution_kind IS NULL LIMIT 1`,
        [input.id],
      );
      if (unresolvedConflict !== null) {
        await txn.runAsync(
          "UPDATE records SET sync_state = 'conflict' WHERE id = ?",
          [input.id],
        );
        result = {
          ...result,
          record: { ...result.record, syncState: "conflict" },
        };
      }
    });
    if (result === undefined) throw new Error("delete transaction produced no result");
    return { record: result.record, command: result.command };
  }

  private async insertOutbox(
    db: Pick<SQLiteDatabase, "runAsync">,
    entry: OutboxEntry,
  ): Promise<void> {
    await db.runAsync(
      `INSERT INTO outbox (
         command_id, record_id, operation, base_version, local_revision,
         payload_json, payload_version, state, attempt_count, created_at, sequence
       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
         (SELECT COALESCE(MAX(sequence), 0) + 1 FROM outbox)
       )`,
      [
        entry.commandId,
        entry.recordId,
        entry.operation,
        entry.baseVersion,
        entry.localRevision,
        entry.payload === null ? null : JSON.stringify(entry.payload),
        entry.payloadVersion,
        entry.state,
        entry.attemptCount,
        entry.createdAt,
      ],
    );
  }

  public async attachOwnedFile(
    input: Omit<Attachment, "state">,
  ): Promise<Attachment> {
    if (!input.localUri.startsWith("file://") || input.byteSize <= 0 || input.checksum === "") {
      throw new Error("attachment must be a verified app-owned file");
    }
    const db = await this.db();
    let attachment: Attachment | undefined;
    await db.withExclusiveTransactionAsync(async (txn) => {
      const record = await this.currentRecord(txn, input.recordId);
      if (record === null || record.deletedAtLocal !== undefined) {
        throw new Error("cannot attach a file to a missing or deleted record");
      }
      const existing = await txn.getFirstAsync<AttachmentRow>(
        "SELECT * FROM attachments WHERE id = ? OR local_uri = ?",
        [input.id, input.localUri],
      );
      if (existing !== null) {
        const decoded = rowToAttachment(existing);
        if (
          decoded.id === input.id &&
          decoded.localUri === input.localUri &&
          decoded.checksum === input.checksum &&
          decoded.recordId === input.recordId
        ) {
          attachment = decoded;
          return;
        }
        throw new Error("attachment identity collision");
      }
      attachment = { ...input, state: "local-ready" };
      await txn.runAsync(
        `INSERT INTO attachments (
          id, record_id, local_uri, checksum, byte_size, mime_type, state, remote_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [
          attachment.id,
          attachment.recordId,
          attachment.localUri,
          attachment.checksum,
          attachment.byteSize,
          attachment.mimeType,
          attachment.state,
          attachment.remoteId ?? null,
          this.clock.now(),
        ],
      );
    });
    if (attachment === undefined) throw new Error("attachment transaction produced no result");
    return attachment;
  }

  public async markMissing(id: string): Promise<void> {
    const db = await this.db();
    await db.runAsync(
      `UPDATE attachments SET state = 'missing-local-file'
       WHERE id = ? AND state NOT IN ('removed', 'cleanup-pending')`,
      [id],
    );
  }

  public async markRemoved(id: string): Promise<void> {
    const db = await this.db();
    await db.runAsync("UPDATE attachments SET state = 'removed' WHERE id = ?", [id]);
  }

  public async listAttachments(recordId?: string): Promise<Attachment[]> {
    const db = await this.db();
    const rows =
      recordId === undefined
        ? await db.getAllAsync<AttachmentRow>("SELECT * FROM attachments ORDER BY id")
        : await db.getAllAsync<AttachmentRow>(
            "SELECT * FROM attachments WHERE record_id = ? ORDER BY id",
            [recordId],
          );
    return rows.map(rowToAttachment);
  }

  public async listOutbox(state?: OutboxEntry["state"]): Promise<OutboxEntry[]> {
    const db = await this.db();
    const rows =
      state === undefined
        ? await db.getAllAsync<OutboxRow>(
            "SELECT * FROM outbox ORDER BY created_at, command_id",
          )
        : await db.getAllAsync<OutboxRow>(
            "SELECT * FROM outbox WHERE state = ? ORDER BY created_at, command_id",
            [state],
          );
    return rows.map(rowToOutbox);
  }

  public async beginExternalMediaOperation(input: {
    operationId: string;
    recordId: string;
    source: ExternalMediaOperation["source"];
    createdAt: string;
    expiresAt: string;
  }): Promise<ExternalMediaOperation> {
    if (
      !Number.isFinite(Date.parse(input.createdAt)) ||
      !Number.isFinite(Date.parse(input.expiresAt)) ||
      Date.parse(input.expiresAt) <= Date.parse(input.createdAt)
    ) {
      throw new Error("external media operation has invalid lifetime");
    }
    const db = await this.db();
    await db.withExclusiveTransactionAsync(async (txn) => {
      const record = await this.currentRecord(txn, input.recordId);
      if (record === null || record.deletedAtLocal !== undefined) {
        throw new Error("cannot launch media for a missing or deleted record");
      }
      const active = await txn.getFirstAsync<ExternalMediaOperationRow>(
        "SELECT * FROM external_media_operations WHERE active_slot = 1",
      );
      if (active !== null) {
        throw new Error("another external media operation is active");
      }
      await txn.runAsync(
        `INSERT INTO external_media_operations (
           operation_id, active_slot, record_id, source, state, created_at, expires_at
         ) VALUES (?, 1, ?, ?, 'launched', ?, ?)`,
        [
          input.operationId,
          input.recordId,
          input.source,
          input.createdAt,
          input.expiresAt,
        ],
      );
    });
    return { ...input, state: "launched" };
  }

  public async activeExternalMediaOperation(): Promise<ExternalMediaOperation | null> {
    const db = await this.db();
    const row = await db.getFirstAsync<ExternalMediaOperationRow>(
      "SELECT * FROM external_media_operations WHERE active_slot = 1",
    );
    return row === null ? null : rowToExternalMediaOperation(row);
  }

  public async claimExternalMediaResult(operationId: string): Promise<boolean> {
    const db = await this.db();
    const update = await db.runAsync(
      `UPDATE external_media_operations SET state = 'copying'
       WHERE operation_id = ? AND active_slot = 1 AND state = 'launched'`,
      [operationId],
    );
    return update.changes === 1;
  }

  public async completeExternalMediaWithAttachment(input: {
    operationId: string;
    completedAt: string;
    attachment: Omit<Attachment, "state">;
  }): Promise<
    | { kind: "completed"; attachment: Attachment }
    | { kind: "stale" }
  > {
    if (
      !input.attachment.localUri.startsWith("file://") ||
      input.attachment.byteSize <= 0 ||
      input.attachment.checksum === "" ||
      !Number.isFinite(Date.parse(input.completedAt))
    ) {
      throw new Error("media completion requires a verified app-owned file");
    }
    const db = await this.db();
    let result:
      | { kind: "completed"; attachment: Attachment }
      | { kind: "stale" } = { kind: "stale" };
    await db.withExclusiveTransactionAsync(async (txn) => {
      const row = await txn.getFirstAsync<ExternalMediaOperationRow>(
        "SELECT * FROM external_media_operations WHERE operation_id = ?",
        [input.operationId],
      );
      if (row === null || row.state !== "copying" || row.active_slot !== 1) return;
      const operation = rowToExternalMediaOperation(row);
      if (operation.recordId !== input.attachment.recordId) {
        throw new Error("media completion does not match its operation");
      }
      const record = await this.currentRecord(txn, operation.recordId);
      if (record === null || record.deletedAtLocal !== undefined) {
        throw new Error("cannot attach media to a missing or deleted record");
      }
      const existing = await txn.getFirstAsync<AttachmentRow>(
        "SELECT * FROM attachments WHERE id = ? OR local_uri = ?",
        [input.attachment.id, input.attachment.localUri],
      );
      if (existing !== null) throw new Error("attachment identity collision");
      const attachment: Attachment = {
        ...input.attachment,
        state: "local-ready",
      };
      await txn.runAsync(
        `INSERT INTO attachments (
           id, record_id, local_uri, checksum, byte_size, mime_type, state,
           remote_id, created_at
         ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [
          attachment.id,
          attachment.recordId,
          attachment.localUri,
          attachment.checksum,
          attachment.byteSize,
          attachment.mimeType,
          attachment.state,
          attachment.remoteId ?? null,
          input.completedAt,
        ],
      );
      const update = await txn.runAsync(
        `UPDATE external_media_operations
         SET active_slot = NULL, state = 'completed', completed_at = ?, attachment_id = ?
         WHERE operation_id = ? AND active_slot = 1 AND state = 'copying'`,
        [input.completedAt, attachment.id, input.operationId],
      );
      if (update.changes !== 1) {
        throw new Error("external media operation lost its completion guard");
      }
      result = { kind: "completed", attachment };
    });
    return result;
  }

  public async finishExternalMediaOperation(input: {
    operationId: string;
    state: "cancelled" | "failed" | "interrupted";
    completedAt: string;
    failureReason?: string;
  }): Promise<boolean> {
    const db = await this.db();
    const update = await db.runAsync(
      `UPDATE external_media_operations
       SET active_slot = NULL, state = ?, completed_at = ?, failure_reason = ?
       WHERE operation_id = ? AND active_slot = 1
         AND state IN ('launched', 'copying')`,
      [
        input.state,
        input.completedAt,
        input.failureReason ?? null,
        input.operationId,
      ],
    );
    return update.changes === 1;
  }

  public async snapshot(): Promise<LocalDatabaseSnapshot> {
    const db = await this.db();
    const [
      records,
      attachments,
      outbox,
      conflictRows,
      checkpoints,
      processed,
      history,
      operations,
      version,
    ] = await Promise.all([
      db.getAllAsync<RecordRow>(`SELECT ${RECORD_COLUMNS} FROM records ORDER BY id`),
      db.getAllAsync<AttachmentRow>("SELECT * FROM attachments ORDER BY id"),
      db.getAllAsync<OutboxRow>("SELECT * FROM outbox ORDER BY created_at, command_id"),
      db.getAllAsync<ConflictRow>(
        "SELECT * FROM conflicts ORDER BY created_at, conflict_id",
      ),
      db.getAllAsync<SyncCheckpointRow>(
        "SELECT sequence, command_id, lease_token, outcome FROM sync_checkpoints ORDER BY sequence",
      ),
      db.getAllAsync<{ message_id: string }>(
        `SELECT message_id FROM processed_intents
         WHERE state IN ('completed', 'terminal') ORDER BY message_id`,
      ),
      db.getAllAsync<{ from_version: number; to_version: number }>(
        "SELECT from_version, to_version FROM schema_migrations ORDER BY to_version",
      ),
      db.getAllAsync<ExternalMediaOperationRow>(
        "SELECT * FROM external_media_operations ORDER BY created_at, operation_id",
      ),
      db.getFirstAsync<{ user_version: number }>("PRAGMA user_version"),
    ]);
    const decodedOutbox = outbox.map(rowToOutbox);
    const outboxById = new Map(decodedOutbox.map((entry) => [entry.commandId, entry]));
    const conflicts = conflictRows.map((row) =>
      rowToConflict(row, outboxById.get(row.command_id)),
    );
    return {
      schemaVersion: version?.user_version ?? CURRENT_SCHEMA_VERSION,
      records: records.map(rowToRecord),
      attachments: attachments.map(rowToAttachment),
      outbox: decodedOutbox,
      conflicts,
      processedIntentKeys: processed.map((row) => row.message_id),
      migrationHistory: history.map((row) => ({
        fromVersion: row.from_version,
        toVersion: row.to_version,
      })),
      externalMediaOperations: operations.map(rowToExternalMediaOperation),
      syncCheckpoints: checkpoints.map(rowToSyncCheckpoint),
    };
  }
}
