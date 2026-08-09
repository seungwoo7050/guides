import type {
  NotificationEnvelope,
  NotificationEnvelopeIntent,
  NotificationParseResult,
} from "./types.ts";

type JsonObject = Record<string, unknown>;

function isObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasOnlyKeys(value: JsonObject, allowed: readonly string[]): boolean {
  const accepted = new Set(allowed);
  return Object.keys(value).every((key) => accepted.has(key));
}

function validOpaqueId(value: unknown): value is string {
  return (
    typeof value === "string" &&
    /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(value)
  );
}

function parseIntent(value: unknown):
  | { kind: "valid"; intent: NotificationEnvelopeIntent }
  | { kind: "invalid"; reason: "invalid-intent" | "invalid-record-id" } {
  if (!isObject(value) || typeof value.kind !== "string") {
    return { kind: "invalid", reason: "invalid-intent" };
  }
  if (value.kind === "sync-blocked") {
    return hasOnlyKeys(value, ["kind"])
      ? { kind: "valid", intent: { kind: "sync-blocked" } }
      : { kind: "invalid", reason: "invalid-intent" };
  }
  if (value.kind === "record-conflict" || value.kind === "record-updated") {
    if (!hasOnlyKeys(value, ["kind", "recordId"])) {
      return { kind: "invalid", reason: "invalid-intent" };
    }
    if (!validOpaqueId(value.recordId)) {
      return { kind: "invalid", reason: "invalid-record-id" };
    }
    return {
      kind: "valid",
      intent: { kind: value.kind, recordId: value.recordId },
    };
  }
  return { kind: "invalid", reason: "invalid-intent" };
}

export function parseNotificationEnvelope(raw: unknown): NotificationParseResult {
  if (!isObject(raw)) {
    return { kind: "invalid", reason: "not-an-object" };
  }
  if (!hasOnlyKeys(raw, ["schemaVersion", "messageId", "accountId", "intent"])) {
    return { kind: "invalid", reason: "unexpected-field" };
  }
  if (raw.schemaVersion !== 1) {
    return { kind: "invalid", reason: "unsupported-schema" };
  }
  if (!validOpaqueId(raw.messageId)) {
    return { kind: "invalid", reason: "invalid-message-id" };
  }
  if (!validOpaqueId(raw.accountId)) {
    return { kind: "invalid", reason: "invalid-account-id" };
  }
  const parsedIntent = parseIntent(raw.intent);
  if (parsedIntent.kind === "invalid") {
    return parsedIntent;
  }
  const envelope: NotificationEnvelope = {
    schemaVersion: 1,
    messageId: raw.messageId,
    accountId: raw.accountId,
    intent: parsedIntent.intent,
  };
  return { kind: "valid", envelope };
}
