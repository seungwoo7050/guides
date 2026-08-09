import type {
  Attachment,
  CapabilityAvailability,
  FieldRecord,
  ExternalMediaOperation,
  LocationMeasurementResult,
  MediaAcquisitionResult,
  MediaSource,
  NavigationIntent,
  LocalDatabaseSnapshot,
  OutboxEntry,
  PermissionState,
  RecordCommand,
  RecordConflict,
  RecordPayload,
  StorageReconciliationReport,
} from "./contracts";

export interface Clock {
  now(): string;
}

export interface IdGenerator {
  recordId(): string;
  attachmentId(): string;
  commandId(): string;
  externalOperationId(): string;
}

export interface RecordRepository {
  ready(): Promise<void>;
  list(): Promise<FieldRecord[]>;
  get(id: string): Promise<FieldRecord | null>;
  saveWithCommand(input: {
    id: string;
    expectedLocalRevision: number | null;
    payload: RecordPayload;
  }): Promise<{ record: FieldRecord; command: RecordCommand }>;
  deleteWithCommand(input: {
    id: string;
    expectedLocalRevision: number;
  }): Promise<{ record: FieldRecord; command: RecordCommand }>;
}

/** Stage 01 deliberately has no durable storage or outbox. */
export interface Stage01RecordRepository {
  ready(): Promise<void>;
  list(): Promise<FieldRecord[]>;
  get(id: string): Promise<FieldRecord | null>;
  saveInMemory(input: {
    id: string;
    expectedLocalRevision: number | null;
    payload: RecordPayload;
  }): Promise<FieldRecord>;
}

export interface AttachmentFileStore {
  takeOwnership(temporaryUri: string): Promise<{
    ownedUri: string;
    checksum: string;
    byteSize: number;
  }>;
  remove(ownedUri: string): Promise<void>;
  listOrphans(): Promise<string[]>;
  exists(ownedUri: string): Promise<boolean>;
  cleanupStaging(): Promise<number>;
}

export interface AttachmentRepository {
  attachOwnedFile(input: Omit<Attachment, "state">): Promise<Attachment>;
  markMissing(id: string): Promise<void>;
  markRemoved(id: string): Promise<void>;
  listAttachments(recordId?: string): Promise<Attachment[]>;
}

export interface OutboxRepository {
  listOutbox(state?: OutboxEntry["state"]): Promise<OutboxEntry[]>;
}

export interface LocalStoreInspection {
  snapshot(): Promise<LocalDatabaseSnapshot>;
}

export interface StorageMaintenance {
  reconcile(): Promise<StorageReconciliationReport>;
}

export interface ExternalMediaOperationRepository {
  beginExternalMediaOperation(input: {
    operationId: string;
    recordId: string;
    source: MediaSource;
    createdAt: string;
    expiresAt: string;
  }): Promise<ExternalMediaOperation>;
  activeExternalMediaOperation(): Promise<ExternalMediaOperation | null>;
  claimExternalMediaResult(operationId: string): Promise<boolean>;
  completeExternalMediaWithAttachment(input: {
    operationId: string;
    completedAt: string;
    attachment: Omit<Attachment, "state">;
  }): Promise<
    | { kind: "completed"; attachment: Attachment }
    | { kind: "stale" }
  >;
  finishExternalMediaOperation(input: {
    operationId: string;
    state: "cancelled" | "failed" | "interrupted";
    completedAt: string;
    failureReason?: string;
  }): Promise<boolean>;
}

export type SyncResult =
  | {
      kind: "success";
      commandId: string;
      record: FieldRecord & { remoteVersion: number };
    }
  | { kind: "conflict"; conflict: RecordConflict }
  | { kind: "unauthorized" }
  | { kind: "retryable"; reason: string }
  | { kind: "permanent-failure"; reason: string };

export interface SyncTransport {
  execute(command: RecordCommand, signal: AbortSignal): Promise<SyncResult>;
}

export interface SessionStore {
  readCredential(): Promise<string | null>;
  writeCredential(credential: string): Promise<void>;
  clearCredential(): Promise<void>;
}

export interface CameraPort {
  availability(): Promise<CapabilityAvailability>;
  permission(): Promise<PermissionState>;
  requestPermission(): Promise<PermissionState>;
  capture(): Promise<MediaAcquisitionResult>;
}

export interface PhotoPickerPort {
  availability(): Promise<CapabilityAvailability>;
  permission(): Promise<PermissionState>;
  requestPermission(): Promise<PermissionState>;
  choose(): Promise<MediaAcquisitionResult>;
}

export interface PendingMediaResultPort {
  recoverPending(): Promise<MediaAcquisitionResult | null>;
}

export interface LocationPort {
  availability(): Promise<CapabilityAvailability>;
  permission(): Promise<PermissionState>;
  requestPermission(): Promise<PermissionState>;
  current(): Promise<LocationMeasurementResult>;
}

export interface BackgroundScheduler {
  scheduleSyncOpportunity(): Promise<
    | { kind: "scheduled" }
    | { kind: "unavailable"; reason: string }
  >;
}

export interface NotificationPort {
  initialIntent(): Promise<NavigationIntent | null>;
  subscribe(listener: (intent: NavigationIntent) => void): () => void;
}

export interface NavigationIntentPort {
  initial(): Promise<NavigationIntent | null>;
  subscribe(listener: (intent: NavigationIntent) => void): () => void;
}
