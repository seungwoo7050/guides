export type RecordStatus = "draft" | "open" | "resolved";

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

/** Structurally compatible with @field-notes/shared RecordCommand. */
export type RecordCommand = {
  commandId: string;
  recordId: string;
  operation: "upsert" | "delete";
  baseVersion: number | null;
  localRevision: number;
  payload: RecordPayload | null;
  createdAt: string;
};

export type RemoteRecord = {
  recordId: string;
  payload: RecordPayload | null;
  version: number;
  deleted: boolean;
};

export type SuccessBody = {
  kind: "success";
  commandId: string;
  record: RemoteRecord;
  replayed: boolean;
};

export type ConflictBody = {
  kind: "conflict";
  commandId: string;
  recordId: string;
  expectedBaseVersion: number | null;
  current: RemoteRecord | null;
  replayed: boolean;
};

export type UnauthorizedBody = {
  kind: "unauthorized";
  commandId: string;
};

export type PermanentFailureBody = {
  kind: "permanent-failure";
  commandId: string;
  reason: string;
  replayed: boolean;
};

export type IdentityReuseBody = {
  kind: "command-identity-reuse";
  commandId: string;
  reason: "same-command-id-different-attempted-command";
};

export type ValidationFailureBody = {
  kind: "validation-failure";
  commandId: string | null;
  reason: string;
};

export type WireResponse = {
  status: 200 | 400 | 401 | 409 | 422;
  body: unknown;
};

export type MemoizedResponse =
  | { status: 200; body: SuccessBody }
  | { status: 409; body: ConflictBody }
  | { status: 422; body: PermanentFailureBody };

export type Fault =
  | { kind: "delay"; milliseconds: number }
  | { kind: "response-loss" }
  | { kind: "unauthorized" }
  | { kind: "malformed-success"; body?: unknown }
  | { kind: "version-regression"; by?: number }
  | { kind: "permanent-validation"; reason: string };

export type FaultPlan = {
  commandId?: string;
  fault: Fault;
};

export type HistoryEvent =
  | { sequence: number; kind: "fault-consumed"; commandId: string; fault: Fault["kind"] }
  | { sequence: number; kind: "delayed"; commandId: string; until: number }
  | { sequence: number; kind: "applied"; commandId: string; recordId: string; version: number }
  | { sequence: number; kind: "memoized"; commandId: string; result: "success" | "conflict" | "permanent-failure" }
  | { sequence: number; kind: "replayed"; commandId: string }
  | { sequence: number; kind: "identity-reuse-rejected"; commandId: string }
  | { sequence: number; kind: "unauthorized"; commandId: string }
  | { sequence: number; kind: "response-lost"; commandId: string }
  | { sequence: number; kind: "malformed-sent"; commandId: string }
  | { sequence: number; kind: "version-regression-sent"; commandId: string; version: number };

export type ServerSnapshot = {
  now: number;
  records: RemoteRecord[];
  memoizedCommandIds: string[];
  applyCountByCommand: Record<string, number>;
  pendingFaults: FaultPlan[];
  history: HistoryEvent[];
};
