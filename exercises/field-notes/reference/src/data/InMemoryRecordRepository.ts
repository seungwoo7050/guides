import {
  cloneFixtureRecords,
  type FieldRecord,
  type RecordPayload,
  type Stage01RecordRepository,
} from "@field-notes/shared";

export class RevisionMismatchError extends Error {
  public constructor() {
    super("The in-memory record changed after this draft was opened.");
    this.name = "RevisionMismatchError";
  }
}

export class InMemoryRecordRepository implements Stage01RecordRepository {
  private readonly records = new Map<string, FieldRecord>(
    cloneFixtureRecords().map((record) => [record.id, record]),
  );

  public async ready(): Promise<void> {
    // Stage 02 replaces this immediate fixture readiness with database migration.
  }

  public async list(): Promise<FieldRecord[]> {
    return [...this.records.values()]
      .filter((record) => record.deletedAtLocal === undefined)
      .sort((left, right) => right.observedAt.localeCompare(left.observedAt))
      .map((record) => ({ ...record }));
  }

  public async get(id: string): Promise<FieldRecord | null> {
    const record = this.records.get(id);
    return record === undefined || record.deletedAtLocal !== undefined
      ? null
      : { ...record };
  }

  public async saveInMemory(input: {
    id: string;
    expectedLocalRevision: number | null;
    payload: RecordPayload;
  }): Promise<FieldRecord> {
    const current = this.records.get(input.id);
    if (
      (current?.localRevision ?? null) !== input.expectedLocalRevision
    ) {
      throw new RevisionMismatchError();
    }
    const record: FieldRecord = {
      id: input.id,
      ...input.payload,
      localRevision: (current?.localRevision ?? 0) + 1,
      remoteVersion: current?.remoteVersion ?? null,
      syncState: "local-only",
    };
    this.records.set(record.id, record);
    return { ...record };
  }
}

