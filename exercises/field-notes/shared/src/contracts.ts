export type RecordStatus = "draft" | "open" | "resolved";

export type RecordSyncState =
  | "local-only"
  | "pending"
  | "syncing"
  | "synced"
  | "retry-wait"
  | "blocked-auth"
  | "conflict"
  | "failed";

export type RecordPayload = {
  title: string;
  notes: string;
  status: RecordStatus;
  observedAt: string;
  location?: {
    latitude: number;
    longitude: number;
    accuracyMeters: number;
    measuredAt: string;
  };
};

export type FieldRecord = RecordPayload & {
  id: string;
  localRevision: number;
  remoteVersion: number | null;
  syncState: RecordSyncState;
  deletedAtLocal?: string;
};

export type AttachmentState =
  | "staging"
  | "local-ready"
  | "upload-pending"
  | "uploading"
  | "uploaded"
  | "missing-local-file"
  | "cleanup-pending"
  | "removed"
  | "failed";

export type Attachment = {
  id: string;
  recordId: string;
  localUri: string;
  checksum: string;
  byteSize: number;
  mimeType: string;
  state: AttachmentState;
  remoteId?: string;
};

export type RecordCommand = {
  commandId: string;
  recordId: string;
  operation: "upsert" | "delete";
  baseVersion: number | null;
  localRevision: number;
  payload: RecordPayload | null;
  createdAt: string;
};

export type OutboxState =
  | "pending"
  | "claimed"
  | "retry-wait"
  | "blocked-auth"
  | "conflict"
  | "permanent-failure"
  | "applied";

export type OutboxEntry = RecordCommand & {
  state: OutboxState;
  attemptCount: number;
  payloadVersion: 1;
  claimedAt?: string;
  lastError?: string;
};

export type StorageReconciliationReport = {
  removedOrphanUris: string[];
  missingAttachmentIds: string[];
  removedAttachmentIds: string[];
  stagingFilesRemoved: number;
  failures: { resource: string; reason: string }[];
};

export type LocalDatabaseSnapshot = {
  schemaVersion: number;
  records: FieldRecord[];
  attachments: Attachment[];
  outbox: OutboxEntry[];
  conflicts: RecordConflict[];
  processedIntentKeys: string[];
  migrationHistory: { fromVersion: number; toVersion: number }[];
  externalMediaOperations: ExternalMediaOperation[];
};

export type RecordConflict = {
  commandId: string;
  recordId: string;
  baseVersion: number | null;
  local: RecordPayload;
  remote: RecordPayload & { version: number };
};

export type CapabilityAvailability =
  | { kind: "available" }
  | { kind: "limited"; description: string }
  | { kind: "unavailable"; reason: string };

export type PermissionState =
  | { kind: "not-required" }
  | { kind: "not-determined" }
  | { kind: "granted" }
  | { kind: "limited"; description: string }
  | { kind: "denied"; canAskAgain: boolean }
  | { kind: "restricted"; reason: string };

export type MediaSource = "camera" | "photo-picker";

export type MediaFailureCode =
  | "launch-failed"
  | "permission-revoked"
  | "interrupted"
  | "invalid-result";

export type MediaAcquisitionResult =
  | { kind: "acquired"; temporaryUri: string; mimeType?: string }
  | { kind: "cancelled" }
  | { kind: "failed"; code: MediaFailureCode; reason: string };

export type LocationMeasurementResult =
  | {
      kind: "measured";
      latitude: number;
      longitude: number;
      accuracyMeters: number;
      measuredAt: string;
    }
  | { kind: "permission-revoked"; permission: PermissionState }
  | { kind: "unavailable"; reason: string }
  | { kind: "failed"; reason: string };

export type ExternalMediaOperationState =
  | "launched"
  | "copying"
  | "completed"
  | "cancelled"
  | "failed"
  | "interrupted";

export type ExternalMediaOperation = {
  operationId: string;
  recordId: string;
  source: MediaSource;
  state: ExternalMediaOperationState;
  createdAt: string;
  expiresAt: string;
  completedAt?: string;
  attachmentId?: string;
  failureReason?: string;
};

export type NavigationIntentSource =
  | "internal"
  | "link"
  | "notification"
  | "restoration";

export type NavigationIntent =
  | { kind: "records"; source: NavigationIntentSource }
  | {
      kind: "open-record";
      recordId: string;
      destination: "detail" | "edit";
      source: NavigationIntentSource;
    }
  | { kind: "open-sync"; source: NavigationIntentSource }
  | { kind: "open-settings"; source: NavigationIntentSource }
  | { kind: "invalid"; reason: string; source: NavigationIntentSource };

export type RecordIdResult =
  | { kind: "valid"; recordId: string }
  | { kind: "invalid"; reason: "empty" | "too-long" | "unsupported-characters" };

export type NavigationDecision =
  | { kind: "navigate"; href: string }
  | { kind: "invalid"; reason: string; fallbackHref: "/records" }
  | { kind: "missing-record"; recordId: string; fallbackHref: "/records" }
  | { kind: "duplicate" };

export type DraftBackDecision = "leave" | "confirm-discard";

export interface Stage01NavigationImplementation {
  normalizeRecordId(input: string): RecordIdResult;
  parseNavigationIntent(
    input: string,
    source?: NavigationIntentSource,
  ): NavigationIntent;
  intentKey(intent: NavigationIntent): string;
  decideDraftBack(dirty: boolean): DraftBackDecision;
}
