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
  planRecordDelete,
  planRecordSave,
  snapshotRecordPayload,
} from "../localMutation";
import {
  CURRENT_SCHEMA_VERSION,
  type LegacyV1FixtureRecord,
  V1_FIXTURE_RECORDS,
} from "../migrations";

type HarnessState = {
  schemaVersion: number;
  legacyRecords: LegacyV1FixtureRecord[];
  records: Map<string, FieldRecord>;
  attachments: Map<string, Attachment>;
  outbox: Map<string, OutboxEntry>;
  conflicts: Map<string, RecordConflict>;
  processedIntentKeys: Set<string>;
  migrationHistory: { fromVersion: number; toVersion: number }[];
};

function clonePayload(payload: RecordPayload): RecordPayload {
  return {
    ...payload,
    location: payload.location === undefined ? undefined : { ...payload.location },
  };
}

function cloneRecord(record: FieldRecord): FieldRecord {
  return { ...record, location: record.location === undefined ? undefined : { ...record.location } };
}

function cloneOutbox(entry: OutboxEntry): OutboxEntry {
  return {
    ...entry,
    payload: entry.payload === null ? null : clonePayload(entry.payload),
  };
}

function cloneState(state: HarnessState): HarnessState {
  return {
    schemaVersion: state.schemaVersion,
    legacyRecords: state.legacyRecords.map((record) => ({ ...record })),
    records: new Map(
      [...state.records].map(([id, record]) => [id, cloneRecord(record)]),
    ),
    attachments: new Map(
      [...state.attachments].map(([id, attachment]) => [id, { ...attachment }]),
    ),
    outbox: new Map(
      [...state.outbox].map(([id, entry]) => [id, cloneOutbox(entry)]),
    ),
    conflicts: new Map(
      [...state.conflicts].map(([id, conflict]) => [id, structuredClone(conflict)]),
    ),
    processedIntentKeys: new Set(state.processedIntentKeys),
    migrationHistory: state.migrationHistory.map((entry) => ({ ...entry })),
  };
}

function emptyState(schemaVersion = 0): HarnessState {
  return {
    schemaVersion,
    legacyRecords: [],
    records: new Map(),
    attachments: new Map(),
    outbox: new Map(),
    conflicts: new Map(),
    processedIntentKeys: new Set(),
    migrationHistory: [],
  };
}

export class DeterministicDatabaseBacking {
  public state: HarnessState;

  public constructor(state: HarnessState = emptyState()) {
    this.state = state;
  }

  public static v1(
    records: readonly LegacyV1FixtureRecord[] = V1_FIXTURE_RECORDS,
  ): DeterministicDatabaseBacking {
    const state = emptyState(1);
    state.legacyRecords = records.map((record) => ({ ...record }));
    state.migrationHistory.push({ fromVersion: 0, toVersion: 1 });
    return new DeterministicDatabaseBacking(state);
  }
}

export type DeterministicFault =
  | "after-record-write"
  | "after-attachment-write"
  | `migration-to-${number}`;

export class DeterministicLocalStore
  implements
    RecordRepository,
    AttachmentRepository,
    OutboxRepository,
    LocalStoreInspection
{
  private fault: DeterministicFault | null = null;
  private transactionTail: Promise<void> = Promise.resolve();

  public constructor(
    public readonly backing = new DeterministicDatabaseBacking(),
    private readonly clock: Clock = { now: () => "2026-08-09T12:00:00.000Z" },
    private readonly ids: IdGenerator = sequentialIds(),
  ) {}

  public failNextAt(fault: DeterministicFault): void {
    this.fault = fault;
  }

  private consumeFault(fault: DeterministicFault): void {
    if (this.fault === fault) {
      this.fault = null;
      throw new Error(`injected fault: ${fault}`);
    }
  }

  public async ready(): Promise<void> {
    while (this.backing.state.schemaVersion < CURRENT_SCHEMA_VERSION) {
      const draft = cloneState(this.backing.state);
      const fromVersion = draft.schemaVersion;
      const toVersion = fromVersion + 1;
      if (fromVersion === 0) {
        draft.legacyRecords = V1_FIXTURE_RECORDS.map((record) => ({ ...record }));
      } else if (fromVersion === 1) {
        for (const legacy of draft.legacyRecords) {
          draft.records.set(legacy.id, {
            id: legacy.id,
            title: legacy.title,
            notes: legacy.notes ?? "",
            status: "open",
            observedAt: legacy.observedAt,
            localRevision: 1,
            remoteVersion: null,
            syncState: "local-only",
          });
        }
        draft.legacyRecords = [];
      } else if (fromVersion !== 2) {
        throw new Error(`no migration from ${fromVersion}`);
      }
      this.consumeFault(`migration-to-${toVersion}`);
      draft.schemaVersion = toVersion;
      draft.migrationHistory.push({ fromVersion, toVersion });
      this.backing.state = draft;
    }
  }

  private async transaction(mutator: (draft: HarnessState) => void): Promise<void> {
    let release: (() => void) | undefined;
    const previous = this.transactionTail;
    this.transactionTail = new Promise<void>((resolve) => {
      release = resolve;
    });
    await previous;
    try {
      await this.ready();
      const draft = cloneState(this.backing.state);
      mutator(draft);
      this.backing.state = draft;
    } finally {
      release?.();
    }
  }

  public async list(): Promise<FieldRecord[]> {
    await this.ready();
    return [...this.backing.state.records.values()]
      .filter((record) => record.deletedAtLocal === undefined)
      .sort((left, right) =>
        right.observedAt.localeCompare(left.observedAt) || left.id.localeCompare(right.id),
      )
      .map(cloneRecord);
  }

  public async get(id: string): Promise<FieldRecord | null> {
    await this.ready();
    const record = this.backing.state.records.get(id);
    return record === undefined || record.deletedAtLocal !== undefined
      ? null
      : cloneRecord(record);
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
    let result: ReturnType<typeof planRecordSave> | undefined;
    await this.transaction((draft) => {
      const current = draft.records.get(stableInput.id) ?? null;
      result = planRecordSave({
        ...stableInput,
        current,
        identity: { commandId: this.ids.commandId(), createdAt: this.clock.now() },
      });
      draft.records.set(stableInput.id, result.record);
      this.consumeFault("after-record-write");
      if (draft.outbox.has(result.command.commandId)) {
        throw new Error("duplicate command id");
      }
      draft.outbox.set(result.command.commandId, result.outbox);
    });
    if (result === undefined) throw new Error("transaction produced no result");
    return { record: cloneRecord(result.record), command: structuredClone(result.command) };
  }

  public async deleteWithCommand(input: {
    id: string;
    expectedLocalRevision: number;
  }): Promise<{ record: FieldRecord; command: RecordCommand }> {
    let result: ReturnType<typeof planRecordDelete> | undefined;
    await this.transaction((draft) => {
      const current = draft.records.get(input.id) ?? null;
      result = planRecordDelete({
        ...input,
        current,
        identity: { commandId: this.ids.commandId(), createdAt: this.clock.now() },
      });
      draft.records.set(input.id, result.record);
      for (const [id, attachment] of draft.attachments) {
        if (attachment.recordId === input.id && attachment.state !== "removed") {
          draft.attachments.set(id, { ...attachment, state: "cleanup-pending" });
        }
      }
      this.consumeFault("after-record-write");
      draft.outbox.set(result.command.commandId, result.outbox);
    });
    if (result === undefined) throw new Error("transaction produced no result");
    return { record: cloneRecord(result.record), command: structuredClone(result.command) };
  }

  public async attachOwnedFile(
    input: Omit<Attachment, "state">,
  ): Promise<Attachment> {
    let result: Attachment | undefined;
    await this.transaction((draft) => {
      const record = draft.records.get(input.recordId);
      if (record === undefined || record.deletedAtLocal !== undefined) {
        throw new Error("missing record");
      }
      const existing = [...draft.attachments.values()].find(
        (attachment) =>
          attachment.id === input.id || attachment.localUri === input.localUri,
      );
      if (existing !== undefined) {
        if (
          existing.id === input.id &&
          existing.localUri === input.localUri &&
          existing.checksum === input.checksum &&
          existing.recordId === input.recordId
        ) {
          result = { ...existing };
          return;
        }
        throw new Error("attachment identity collision");
      }
      result = { ...input, state: "local-ready" };
      draft.attachments.set(result.id, result);
      this.consumeFault("after-attachment-write");
    });
    if (result === undefined) throw new Error("transaction produced no result");
    return { ...result };
  }

  public async markMissing(id: string): Promise<void> {
    await this.transaction((draft) => {
      const attachment = draft.attachments.get(id);
      if (
        attachment !== undefined &&
        attachment.state !== "removed" &&
        attachment.state !== "cleanup-pending"
      ) {
        draft.attachments.set(id, { ...attachment, state: "missing-local-file" });
      }
    });
  }

  public async markRemoved(id: string): Promise<void> {
    await this.transaction((draft) => {
      const attachment = draft.attachments.get(id);
      if (attachment !== undefined) {
        draft.attachments.set(id, { ...attachment, state: "removed" });
      }
    });
  }

  public async listAttachments(recordId?: string): Promise<Attachment[]> {
    await this.ready();
    return [...this.backing.state.attachments.values()]
      .filter((attachment) => recordId === undefined || attachment.recordId === recordId)
      .sort((left, right) => left.id.localeCompare(right.id))
      .map((attachment) => ({ ...attachment }));
  }

  public async listOutbox(state?: OutboxEntry["state"]): Promise<OutboxEntry[]> {
    await this.ready();
    return [...this.backing.state.outbox.values()]
      .filter((entry) => state === undefined || entry.state === state)
      .sort(
        (left, right) =>
          left.createdAt.localeCompare(right.createdAt) ||
          left.commandId.localeCompare(right.commandId),
      )
      .map(cloneOutbox);
  }

  public async snapshot(): Promise<LocalDatabaseSnapshot> {
    await this.ready();
    return {
      schemaVersion: this.backing.state.schemaVersion,
      records: [...this.backing.state.records.values()]
        .sort((left, right) => left.id.localeCompare(right.id))
        .map(cloneRecord),
      attachments: [...this.backing.state.attachments.values()]
        .sort((left, right) => left.id.localeCompare(right.id))
        .map((attachment) => ({ ...attachment })),
      outbox: await this.listOutbox(),
      conflicts: [...this.backing.state.conflicts.values()].map((value) =>
        structuredClone(value),
      ),
      processedIntentKeys: [...this.backing.state.processedIntentKeys].sort(),
      migrationHistory: this.backing.state.migrationHistory.map((entry) => ({ ...entry })),
    };
  }
}

export function sequentialIds(): IdGenerator {
  let record = 0;
  let attachment = 0;
  let command = 0;
  return {
    recordId: () => `record-${++record}`,
    attachmentId: () => `attachment-${++attachment}`,
    commandId: () => `command-${++command}`,
  };
}
