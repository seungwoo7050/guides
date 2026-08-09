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

type RawPathResult =
  | { kind: "segments"; segments: string[] }
  | { kind: "malformed" }
  | { kind: "unexpected-scheme" };

function rawPathSegments(input: string, expectedScheme: string): RawPathResult {
  try {
    if (input.startsWith("/")) {
      const url = new URL(input, "https://field-notes.invalid");
      return {
        kind: "segments",
        segments: url.pathname
          .split("/")
          .filter(Boolean)
          .map((segment) => decodeURIComponent(segment)),
      };
    }

    const url = new URL(input);
    const actualScheme = url.protocol.slice(0, -1).toLocaleLowerCase("en-US");
    const normalizedExpectedScheme = expectedScheme.toLocaleLowerCase("en-US");
    const isExpoDevelopmentLink = actualScheme === "exp" || actualScheme === "exps";
    if (actualScheme !== normalizedExpectedScheme && !isExpoDevelopmentLink) {
      return { kind: "unexpected-scheme" };
    }
    const customSchemeHost =
      actualScheme === normalizedExpectedScheme && url.hostname ? [url.hostname] : [];
    const encodedSegments = url.pathname.split("/").filter(Boolean);
    const segments = [...customSchemeHost, ...encodedSegments].map((segment) =>
      decodeURIComponent(segment),
    );
    const expoSeparator = segments.indexOf("--");
    if (isExpoDevelopmentLink && expoSeparator < 0) {
      return { kind: "unexpected-scheme" };
    }
    return {
      kind: "segments",
      segments: expoSeparator >= 0 ? segments.slice(expoSeparator + 1) : segments,
    };
  } catch {
    return { kind: "malformed" };
  }
}

export function parseNavigationIntent(
  input: string,
  source: NavigationIntentSource = "link",
  expectedScheme = "fieldnotes",
): NavigationIntent {
  const result = rawPathSegments(input, expectedScheme);
  if (result.kind === "malformed") {
    return { kind: "invalid", reason: "malformed-encoding", source };
  }
  if (result.kind === "unexpected-scheme") {
    return { kind: "invalid", reason: "unexpected-scheme", source };
  }
  const { segments } = result;
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
