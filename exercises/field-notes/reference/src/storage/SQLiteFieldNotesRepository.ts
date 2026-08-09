import type {
  Attachment,
  AttachmentRepository,
  Clock,
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
      !Number.isFinite(parsed.longitude) ||
      !Number.isFinite(parsed.accuracyMeters) ||
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
    LocalStoreInspection
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
      await this.insertOutbox(txn, result.outbox);
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
         payload_json, payload_version, state, attempt_count, created_at
       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
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

  public async snapshot(): Promise<LocalDatabaseSnapshot> {
    const db = await this.db();
    const [records, attachments, outbox, processed, history] = await Promise.all([
      db.getAllAsync<RecordRow>(`SELECT ${RECORD_COLUMNS} FROM records ORDER BY id`),
      db.getAllAsync<AttachmentRow>("SELECT * FROM attachments ORDER BY id"),
      db.getAllAsync<OutboxRow>("SELECT * FROM outbox ORDER BY created_at, command_id"),
      db.getAllAsync<{ intent_key: string }>(
        "SELECT intent_key FROM processed_intents ORDER BY intent_key",
      ),
      db.getAllAsync<{ from_version: number; to_version: number }>(
        "SELECT from_version, to_version FROM schema_migrations ORDER BY to_version",
      ),
    ]);
    const conflicts: RecordConflict[] = [];
    return {
      schemaVersion: CURRENT_SCHEMA_VERSION,
      records: records.map(rowToRecord),
      attachments: attachments.map(rowToAttachment),
      outbox: outbox.map(rowToOutbox),
      conflicts,
      processedIntentKeys: processed.map((row) => row.intent_key),
      migrationHistory: history.map((row) => ({
        fromVersion: row.from_version,
        toVersion: row.to_version,
      })),
    };
  }
}
