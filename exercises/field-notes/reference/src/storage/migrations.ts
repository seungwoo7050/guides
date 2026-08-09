import { FIELD_RECORD_FIXTURES } from "@field-notes/shared";
import type { SQLiteDatabase } from "expo-sqlite";
import { CorruptLocalDataError } from "./localMutation";

export const CURRENT_SCHEMA_VERSION = 5;

export const CREATE_V1_SCHEMA_SQL = `
CREATE TABLE records (
  id TEXT PRIMARY KEY NOT NULL,
  title TEXT NOT NULL,
  notes TEXT,
  observed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS schema_migrations (
  from_version INTEGER NOT NULL,
  to_version INTEGER PRIMARY KEY NOT NULL,
  applied_at TEXT NOT NULL
);
`;

export const MIGRATE_V1_TO_V2_SQL = `
CREATE TABLE IF NOT EXISTS schema_migrations (
  from_version INTEGER NOT NULL,
  to_version INTEGER PRIMARY KEY NOT NULL,
  applied_at TEXT NOT NULL
);
ALTER TABLE records ADD COLUMN status TEXT NOT NULL DEFAULT 'open';
ALTER TABLE records ADD COLUMN local_revision INTEGER NOT NULL DEFAULT 1;
ALTER TABLE records ADD COLUMN remote_version INTEGER;
ALTER TABLE records ADD COLUMN sync_state TEXT NOT NULL DEFAULT 'local-only';
ALTER TABLE records ADD COLUMN location_json TEXT;
ALTER TABLE records ADD COLUMN deleted_at_local TEXT;

CREATE TABLE attachments (
  id TEXT PRIMARY KEY NOT NULL,
  record_id TEXT NOT NULL REFERENCES records(id),
  local_uri TEXT NOT NULL UNIQUE,
  checksum TEXT NOT NULL,
  byte_size INTEGER NOT NULL CHECK (byte_size > 0),
  mime_type TEXT NOT NULL,
  state TEXT NOT NULL,
  remote_id TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE outbox (
  command_id TEXT PRIMARY KEY NOT NULL,
  record_id TEXT NOT NULL REFERENCES records(id),
  operation TEXT NOT NULL CHECK (operation IN ('upsert', 'delete')),
  base_version INTEGER,
  local_revision INTEGER NOT NULL,
  payload_json TEXT,
  payload_version INTEGER NOT NULL DEFAULT 1,
  state TEXT NOT NULL DEFAULT 'pending',
  attempt_count INTEGER NOT NULL DEFAULT 0,
  claimed_at TEXT,
  last_error TEXT,
  created_at TEXT NOT NULL,
  UNIQUE(record_id, local_revision, operation)
);

CREATE INDEX attachments_record_idx ON attachments(record_id);
CREATE INDEX outbox_state_created_idx ON outbox(state, created_at, command_id);
`;

export const MIGRATE_V2_TO_V3_SQL = `
CREATE TABLE conflicts (
  command_id TEXT PRIMARY KEY NOT NULL REFERENCES outbox(command_id),
  record_id TEXT NOT NULL REFERENCES records(id),
  base_version INTEGER,
  local_payload_json TEXT NOT NULL,
  remote_payload_json TEXT NOT NULL,
  remote_version INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE processed_intents (
  intent_key TEXT PRIMARY KEY NOT NULL,
  processed_at TEXT NOT NULL
);

CREATE INDEX conflicts_record_idx ON conflicts(record_id);
`;

export const MIGRATE_V3_TO_V4_SQL = `
CREATE TABLE external_media_operations (
  operation_id TEXT PRIMARY KEY NOT NULL,
  active_slot INTEGER UNIQUE CHECK (active_slot IS NULL OR active_slot = 1),
  record_id TEXT NOT NULL REFERENCES records(id),
  source TEXT NOT NULL CHECK (source IN ('camera', 'photo-picker')),
  state TEXT NOT NULL CHECK (
    state IN ('launched', 'copying', 'completed', 'cancelled', 'failed', 'interrupted')
  ),
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  completed_at TEXT,
  attachment_id TEXT UNIQUE REFERENCES attachments(id),
  failure_reason TEXT
);

CREATE INDEX external_media_record_created_idx
  ON external_media_operations(record_id, created_at, operation_id);
`;

export const MIGRATE_V4_TO_V5_SQL = `
ALTER TABLE outbox ADD COLUMN attempted_json TEXT;
ALTER TABLE outbox ADD COLUMN sequence INTEGER;
ALTER TABLE outbox ADD COLUMN lease_token TEXT;
ALTER TABLE outbox ADD COLUMN lease_owner TEXT;
ALTER TABLE outbox ADD COLUMN lease_expires_at INTEGER;
ALTER TABLE outbox ADD COLUMN next_attempt_at INTEGER;
ALTER TABLE outbox ADD COLUMN completed_at INTEGER;
ALTER TABLE outbox ADD COLUMN completed_remote_version INTEGER;
ALTER TABLE outbox ADD COLUMN conflict_id TEXT;

UPDATE outbox SET sequence = rowid WHERE sequence IS NULL;
UPDATE outbox
SET attempted_json = json_object(
  'commandId', command_id,
  'recordId', record_id,
  'operation', operation,
  'baseVersion', base_version,
  'localRevision', local_revision,
  'payload', CASE
    WHEN payload_json IS NULL THEN NULL
    ELSE json(payload_json)
  END,
  'createdAt', created_at
)
WHERE state != 'pending' AND attempted_json IS NULL;
CREATE INDEX outbox_sequence_idx ON outbox(sequence, command_id);
CREATE INDEX outbox_lease_expiry_idx ON outbox(state, lease_expires_at);
CREATE TRIGGER outbox_attempted_snapshot_immutable
BEFORE UPDATE OF attempted_json ON outbox
WHEN OLD.attempted_json IS NOT NULL AND NEW.attempted_json IS NOT OLD.attempted_json
BEGIN
  SELECT RAISE(ABORT, 'attempted command snapshot is immutable');
END;

DROP INDEX IF EXISTS conflicts_record_idx;
ALTER TABLE conflicts RENAME TO conflicts_v4;
CREATE TABLE conflicts (
  conflict_id TEXT PRIMARY KEY NOT NULL,
  command_id TEXT NOT NULL UNIQUE REFERENCES outbox(command_id),
  record_id TEXT NOT NULL REFERENCES records(id),
  attempted_json TEXT,
  local_payload_json TEXT,
  local_revision INTEGER NOT NULL,
  remote_payload_json TEXT,
  remote_version INTEGER,
  remote_deleted INTEGER,
  created_at INTEGER NOT NULL,
  resolution_kind TEXT CHECK (
    resolution_kind IS NULL OR resolution_kind IN ('remote', 'local', 'merge')
  ),
  resolved_at INTEGER,
  resolution_command_id TEXT
);
INSERT INTO conflicts (
  conflict_id, command_id, record_id, attempted_json,
  local_payload_json, local_revision,
  remote_payload_json, remote_version, remote_deleted,
  created_at
)
SELECT
  'conflict:' || legacy.command_id,
  legacy.command_id,
  legacy.record_id,
  COALESCE(
    outbox.attempted_json,
    json_object(
      'commandId', outbox.command_id,
      'recordId', outbox.record_id,
      'operation', outbox.operation,
      'baseVersion', outbox.base_version,
      'localRevision', outbox.local_revision,
      'payload', CASE
        WHEN outbox.payload_json IS NULL THEN NULL
        ELSE json(outbox.payload_json)
      END,
      'createdAt', outbox.created_at
    )
  ),
  legacy.local_payload_json,
  COALESCE(outbox.local_revision, 1),
  legacy.remote_payload_json,
  legacy.remote_version,
  0,
  COALESCE(CAST(strftime('%s', legacy.created_at) AS INTEGER) * 1000, 0)
FROM conflicts_v4 AS legacy
LEFT JOIN outbox ON outbox.command_id = legacy.command_id;
UPDATE outbox
SET conflict_id = 'conflict:' || command_id
WHERE state = 'conflict'
  AND EXISTS (
    SELECT 1 FROM conflicts
    WHERE conflicts.command_id = outbox.command_id
  );
DROP TABLE conflicts_v4;
CREATE INDEX conflicts_record_idx ON conflicts(record_id, created_at, conflict_id);

CREATE TABLE sync_checkpoints (
  sequence INTEGER PRIMARY KEY AUTOINCREMENT,
  command_id TEXT NOT NULL REFERENCES outbox(command_id),
  lease_token TEXT NOT NULL,
  outcome TEXT NOT NULL CHECK (
    outcome IN ('success', 'conflict', 'retry_wait', 'blocked_auth', 'permanent')
  ),
  created_at INTEGER NOT NULL
);
CREATE INDEX sync_checkpoints_command_idx
  ON sync_checkpoints(command_id, sequence);
`;

export type LegacyV1FixtureRecord = {
  id: string;
  title: string;
  notes: string | null;
  observedAt: string;
};

export const V1_FIXTURE_RECORDS: readonly LegacyV1FixtureRecord[] = [
  ...FIELD_RECORD_FIXTURES.map((record) => ({
    id: record.id,
    title: record.title,
    notes: record.notes,
    observedAt: record.observedAt,
  })),
  {
    id: "legacy-null-notes",
    title: "이전 버전 nullable 메모",
    notes: null,
    observedAt: "2026-07-31T23:59:00.000Z",
  },
  {
    id: "legacy-long-unicode",
    title: "긴 유니코드 관찰",
    notes: "해안선 변화 기록 · ".repeat(80),
    observedAt: "2026-07-30T10:00:00.000Z",
  },
] as const;

type MigrationTxn = Pick<SQLiteDatabase, "execAsync" | "runAsync">;

async function applyStep(txn: MigrationTxn, fromVersion: number): Promise<void> {
  if (fromVersion === 0) {
    await txn.execAsync(CREATE_V1_SCHEMA_SQL);
    for (const record of V1_FIXTURE_RECORDS) {
      await txn.runAsync(
        "INSERT INTO records (id, title, notes, observed_at) VALUES (?, ?, ?, ?)",
        [record.id, record.title, record.notes, record.observedAt],
      );
    }
    return;
  }
  if (fromVersion === 1) {
    await txn.execAsync(MIGRATE_V1_TO_V2_SQL);
    return;
  }
  if (fromVersion === 2) {
    await txn.execAsync(MIGRATE_V2_TO_V3_SQL);
    return;
  }
  if (fromVersion === 3) {
    await txn.execAsync(MIGRATE_V3_TO_V4_SQL);
    return;
  }
  if (fromVersion === 4) {
    await txn.execAsync(MIGRATE_V4_TO_V5_SQL);
    return;
  }
  throw new CorruptLocalDataError(
    "schema",
    `no forward migration from version ${fromVersion}`,
  );
}
export type MigrationOptions = {
  now(): string;
  beforeVersionCommit?(fromVersion: number, toVersion: number): Promise<void>;
};

export async function migrateSQLiteDatabase(
  db: SQLiteDatabase,
  options: MigrationOptions,
): Promise<void> {
  await db.execAsync("PRAGMA journal_mode = WAL; PRAGMA foreign_keys = ON;");
  const row = await db.getFirstAsync<{ user_version: number }>("PRAGMA user_version");
  let version = row?.user_version ?? 0;
  if (version > CURRENT_SCHEMA_VERSION) {
    throw new CorruptLocalDataError(
      "schema",
      `database version ${version} is newer than supported ${CURRENT_SCHEMA_VERSION}`,
    );
  }

  while (version < CURRENT_SCHEMA_VERSION) {
    const fromVersion = version;
    const toVersion = version + 1;
    await db.withExclusiveTransactionAsync(async (txn) => {
      await applyStep(txn, fromVersion);
      await options.beforeVersionCommit?.(fromVersion, toVersion);
      await txn.runAsync(
        `INSERT INTO schema_migrations (from_version, to_version, applied_at)
         VALUES (?, ?, ?)`,
        [fromVersion, toVersion, options.now()],
      );
      await txn.execAsync(`PRAGMA user_version = ${toVersion}`);
    });
    version = toVersion;
  }
}
