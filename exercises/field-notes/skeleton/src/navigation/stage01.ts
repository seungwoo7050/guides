import type {
  DraftBackDecision,
  NavigationIntent,
  NavigationIntentSource,
  RecordIdResult,
  Stage01NavigationImplementation,
} from "@field-notes/shared";

/** TODO(Stage 01): enforce length and allowed-character invariants. */
export function normalizeRecordId(input: string): RecordIdResult {
  const recordId = input.trim().toLowerCase();
  return recordId.length === 0
    ? { kind: "invalid", reason: "empty" }
    : { kind: "valid", recordId };
}

/**
 * TODO(Stage 01): parse custom-scheme, universal, Expo development, malformed,
 * detail/edit, sync, and settings URLs without throwing.
 */
export function parseNavigationIntent(
  input: string,
  source: NavigationIntentSource = "link",
): NavigationIntent {
  return input === "/records"
    ? { kind: "records", source }
    : { kind: "invalid", reason: "TODO-stage-01-parser", source };
}

/** TODO(Stage 01): distinguish targets while ignoring delivery source. */
export function intentKey(intent: NavigationIntent): string {
  return intent.kind;
}

/** TODO(Stage 01): dirty drafts need a discard decision on every back path. */
export function decideDraftBack(_dirty: boolean): DraftBackDecision {
  return "leave";
}

export const stage01Navigation: Stage01NavigationImplementation = {
  normalizeRecordId,
  parseNavigationIntent,
  intentKey,
  decideDraftBack,
};

