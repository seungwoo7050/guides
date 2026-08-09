import type {
  FieldRecord,
  OutboxEntry,
  RecordCommand,
  RecordPayload,
} from "@field-notes/shared";

export class LocalRevisionMismatchError extends Error {
  public constructor(
    public readonly recordId: string,
    public readonly expected: number | null,
    public readonly actual: number | null,
  ) {
    super(
      `Local revision mismatch for ${recordId}: expected ${String(expected)}, actual ${String(actual)}`,
    );
    this.name = "LocalRevisionMismatchError";
  }
}

export class InvalidRecordPayloadError extends Error {
  public constructor(message: string) {
    super(message);
    this.name = "InvalidRecordPayloadError";
  }
}

export class CorruptLocalDataError extends Error {
  public constructor(public readonly resource: string, message: string) {
    super(`${resource}: ${message}`);
    this.name = "CorruptLocalDataError";
  }
}

export type MutationIdentity = {
  commandId: string;
  createdAt: string;
};

export function validateRecordPayload(payload: RecordPayload): void {
  if (payload.title.trim().length === 0 || [...payload.title].length > 120) {
    throw new InvalidRecordPayloadError("title must contain 1..120 code points");
  }
  if (!Number.isFinite(Date.parse(payload.observedAt))) {
    throw new InvalidRecordPayloadError("observedAt must be an ISO-compatible date");
  }
  if (!(["draft", "open", "resolved"] as const).includes(payload.status)) {
    throw new InvalidRecordPayloadError("unsupported record status");
  }
}

export function snapshotRecordPayload(payload: RecordPayload): RecordPayload {
  return {
    ...payload,
    location: payload.location === undefined ? undefined : { ...payload.location },
  };
}

export function planRecordSave(input: {
  current: FieldRecord | null;
  id: string;
  expectedLocalRevision: number | null;
  payload: RecordPayload;
  identity: MutationIdentity;
}): { record: FieldRecord; command: RecordCommand; outbox: OutboxEntry } {
  validateRecordPayload(input.payload);
  const actualRevision = input.current?.localRevision ?? null;
  if (
    actualRevision !== input.expectedLocalRevision ||
    input.current?.deletedAtLocal !== undefined
  ) {
    throw new LocalRevisionMismatchError(
      input.id,
      input.expectedLocalRevision,
      actualRevision,
    );
  }
  const payload = snapshotRecordPayload(input.payload);
  const record: FieldRecord = {
    id: input.id,
    ...payload,
    localRevision: (input.current?.localRevision ?? 0) + 1,
    remoteVersion: input.current?.remoteVersion ?? null,
    syncState: "pending",
  };
  const command: RecordCommand = {
    commandId: input.identity.commandId,
    recordId: record.id,
    operation: "upsert",
    baseVersion: record.remoteVersion,
    localRevision: record.localRevision,
    payload: snapshotRecordPayload(payload),
    createdAt: input.identity.createdAt,
  };
  return {
    record,
    command,
    outbox: {
      ...command,
      payload: snapshotRecordPayload(payload),
      state: "pending",
      attemptCount: 0,
      payloadVersion: 1,
    },
  };
}

export function planRecordDelete(input: {
  current: FieldRecord | null;
  id: string;
  expectedLocalRevision: number;
  identity: MutationIdentity;
}): { record: FieldRecord; command: RecordCommand; outbox: OutboxEntry } {
  const actualRevision = input.current?.localRevision ?? null;
  if (
    input.current === null ||
    input.current.deletedAtLocal !== undefined ||
    actualRevision !== input.expectedLocalRevision
  ) {
    throw new LocalRevisionMismatchError(
      input.id,
      input.expectedLocalRevision,
      actualRevision,
    );
  }
  const record: FieldRecord = {
    ...input.current,
    localRevision: input.current.localRevision + 1,
    syncState: "pending",
    deletedAtLocal: input.identity.createdAt,
  };
  const command: RecordCommand = {
    commandId: input.identity.commandId,
    recordId: record.id,
    operation: "delete",
    baseVersion: record.remoteVersion,
    localRevision: record.localRevision,
    payload: null,
    createdAt: input.identity.createdAt,
  };
  return {
    record,
    command,
    outbox: {
      ...command,
      state: "pending",
      attemptCount: 0,
      payloadVersion: 1,
    },
  };
}
