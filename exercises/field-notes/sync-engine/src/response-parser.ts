import type {
  AttemptedCommand,
  ParsedTransportResult,
  RecordPayload,
  RemoteRecord,
  WireResponse,
} from "./types.ts";

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isIsoDate(value: unknown): value is string {
  return typeof value === "string" && value.length > 0 && Number.isFinite(Date.parse(value));
}

function parsePayload(value: unknown): RecordPayload | null {
  if (!isObject(value)) {
    return null;
  }
  if (
    typeof value.title !== "string" ||
    typeof value.notes !== "string" ||
    (value.status !== "draft" && value.status !== "open" && value.status !== "resolved") ||
    !isIsoDate(value.observedAt)
  ) {
    return null;
  }

  const payload: RecordPayload = {
    title: value.title,
    notes: value.notes,
    status: value.status,
    observedAt: value.observedAt,
  };

  if (value.location !== undefined) {
    if (!isObject(value.location)) {
      return null;
    }
    const { latitude, longitude, accuracyMeters, measuredAt } = value.location;
    if (
      !isFiniteNumber(latitude) ||
      !isFiniteNumber(longitude) ||
      !isFiniteNumber(accuracyMeters) ||
      accuracyMeters < 0 ||
      !isIsoDate(measuredAt)
    ) {
      return null;
    }
    payload.location = { latitude, longitude, accuracyMeters, measuredAt };
  }

  return payload;
}

function parseRemoteRecord(value: unknown): RemoteRecord | null {
  if (
    !isObject(value) ||
    typeof value.recordId !== "string" ||
    !Number.isInteger(value.version) ||
    (value.version as number) < 1 ||
    typeof value.deleted !== "boolean"
  ) {
    return null;
  }

  if (value.deleted) {
    if (value.payload !== null) {
      return null;
    }
    return {
      recordId: value.recordId,
      payload: null,
      version: value.version as number,
      deleted: true,
    };
  }

  const payload = parsePayload(value.payload);
  if (payload === null) {
    return null;
  }
  return {
    recordId: value.recordId,
    payload,
    version: value.version as number,
    deleted: false,
  };
}

function invalid(reason: string): ParsedTransportResult {
  return { kind: "invalid_response", reason };
}

function validateCommandId(body: Record<string, unknown>, attempted: AttemptedCommand): string | null {
  if (typeof body.commandId !== "string") {
    return "response-command-id-missing";
  }
  if (body.commandId !== attempted.commandId) {
    return "response-command-id-mismatch";
  }
  return null;
}

function validateRemoteVersion(
  remote: RemoteRecord,
  attempted: AttemptedCommand,
  knownRemoteVersion: number | null,
  requireAdvanceFromBase: boolean,
): string | null {
  if (remote.recordId !== attempted.recordId) {
    return "response-record-id-mismatch";
  }
  if (knownRemoteVersion !== null && remote.version < knownRemoteVersion) {
    return "remote-version-regression";
  }
  if (
    requireAdvanceFromBase &&
    attempted.baseVersion !== null &&
    remote.version <= attempted.baseVersion
  ) {
    return "remote-version-did-not-advance";
  }
  return null;
}

export function parseTransportResponse(
  response: WireResponse,
  context: {
    attempted: AttemptedCommand;
    knownRemoteVersion: number | null;
  },
): ParsedTransportResult {
  const { attempted, knownRemoteVersion } = context;
  if (!isObject(response.body) || typeof response.body.kind !== "string") {
    return invalid("response-body-malformed");
  }
  const commandIdError = validateCommandId(response.body, attempted);
  if (commandIdError !== null) {
    return invalid(commandIdError);
  }

  if (response.status === 200) {
    if (response.body.kind !== "success") {
      return invalid("success-kind-mismatch");
    }
    const remote = parseRemoteRecord(response.body.record);
    if (remote === null) {
      return invalid("success-record-required-fields-invalid");
    }
    const versionError = validateRemoteVersion(remote, attempted, knownRemoteVersion, true);
    if (versionError !== null) {
      return invalid(versionError);
    }
    if (attempted.operation === "delete" && !remote.deleted) {
      return invalid("delete-success-not-deleted");
    }
    if (attempted.operation === "upsert" && remote.deleted) {
      return invalid("upsert-success-deleted");
    }
    return { kind: "success", remote };
  }

  if (response.status === 401) {
    return response.body.kind === "unauthorized"
      ? { kind: "blocked_auth", reason: "unauthorized" }
      : invalid("unauthorized-kind-mismatch");
  }

  if (response.status === 409) {
    if (response.body.kind === "command-identity-reuse") {
      return { kind: "permanent", reason: "command-identity-reuse" };
    }
    if (response.body.kind !== "conflict") {
      return invalid("conflict-kind-mismatch");
    }
    if (response.body.recordId !== attempted.recordId) {
      return invalid("conflict-record-id-mismatch");
    }
    if (response.body.expectedBaseVersion !== attempted.baseVersion) {
      return invalid("conflict-base-version-mismatch");
    }
    if (response.body.current === null) {
      if (knownRemoteVersion !== null) {
        return invalid("conflict-current-regressed-to-null");
      }
      return { kind: "conflict", remote: null };
    }
    const remote = parseRemoteRecord(response.body.current);
    if (remote === null) {
      return invalid("conflict-current-required-fields-invalid");
    }
    const versionError = validateRemoteVersion(remote, attempted, knownRemoteVersion, false);
    if (versionError !== null) {
      return invalid(versionError);
    }
    if (remote.version === attempted.baseVersion) {
      return invalid("conflict-current-equals-base-version");
    }
    return { kind: "conflict", remote };
  }

  if (response.status === 422) {
    if (response.body.kind !== "permanent-failure" || typeof response.body.reason !== "string") {
      return invalid("permanent-response-malformed");
    }
    if (response.body.reason.trim().length === 0) {
      return invalid("permanent-reason-empty");
    }
    return { kind: "permanent", reason: response.body.reason };
  }

  if (response.status === 400) {
    if (response.body.kind !== "validation-failure" || typeof response.body.reason !== "string") {
      return invalid("validation-response-malformed");
    }
    return { kind: "permanent", reason: `transport-validation:${response.body.reason}` };
  }

  return invalid(`unsupported-status:${String(response.status)}`);
}
