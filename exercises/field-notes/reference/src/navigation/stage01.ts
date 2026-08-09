import type {
  DraftBackDecision,
  NavigationIntent,
  NavigationIntentSource,
  RecordIdResult,
  Stage01NavigationImplementation,
} from "@field-notes/shared";

export const MAX_RECORD_ID_LENGTH = 64;

export function normalizeRecordId(input: string): RecordIdResult {
  const recordId = input.trim().toLocaleLowerCase("en-US");
  if (recordId.length === 0) {
    return { kind: "invalid", reason: "empty" };
  }
  if ([...recordId].length > MAX_RECORD_ID_LENGTH) {
    return { kind: "invalid", reason: "too-long" };
  }
  if (!/^[a-z0-9][a-z0-9_-]*$/.test(recordId)) {
    return { kind: "invalid", reason: "unsupported-characters" };
  }
  return { kind: "valid", recordId };
}

function rawPathSegments(input: string): string[] | null {
  try {
    const url = input.startsWith("/")
      ? new URL(input, "https://field-notes.invalid")
      : new URL(input);
    const customSchemeHost =
      url.protocol === "fieldnotes:" && url.hostname ? [url.hostname] : [];
    const encodedSegments = url.pathname.split("/").filter(Boolean);
    const segments = [...customSchemeHost, ...encodedSegments].map((segment) =>
      decodeURIComponent(segment),
    );
    const expoSeparator = segments.indexOf("--");
    return expoSeparator >= 0 ? segments.slice(expoSeparator + 1) : segments;
  } catch {
    return null;
  }
}

export function parseNavigationIntent(
  input: string,
  source: NavigationIntentSource = "link",
): NavigationIntent {
  const segments = rawPathSegments(input);
  if (segments === null) {
    return { kind: "invalid", reason: "malformed-encoding", source };
  }
  if (segments.length === 0 || (segments.length === 1 && segments[0] === "records")) {
    return { kind: "records", source };
  }
  if (segments.length === 1 && segments[0] === "sync") {
    return { kind: "open-sync", source };
  }
  if (segments.length === 1 && segments[0] === "settings") {
    return { kind: "open-settings", source };
  }
  if (
    segments[0] === "records" &&
    (segments.length === 2 || (segments.length === 3 && segments[2] === "edit"))
  ) {
    const id = normalizeRecordId(segments[1] ?? "");
    if (id.kind === "invalid") {
      return { kind: "invalid", reason: id.reason, source };
    }
    return {
      kind: "open-record",
      recordId: id.recordId,
      destination: segments[2] === "edit" ? "edit" : "detail",
      source,
    };
  }
  return { kind: "invalid", reason: "unknown-route", source };
}

export function intentKey(intent: NavigationIntent): string {
  switch (intent.kind) {
    case "records":
      return "records";
    case "open-record":
      return `record:${intent.recordId}:${intent.destination}`;
    case "open-sync":
      return "sync";
    case "open-settings":
      return "settings";
    case "invalid":
      return `invalid:${intent.reason}`;
  }
}

export function decideDraftBack(dirty: boolean): DraftBackDecision {
  return dirty ? "confirm-discard" : "leave";
}

export const stage01Navigation: Stage01NavigationImplementation = {
  normalizeRecordId,
  parseNavigationIntent,
  intentKey,
  decideDraftBack,
};

