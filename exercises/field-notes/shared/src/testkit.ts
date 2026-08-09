import type {
  NavigationIntent,
  NavigationIntentSource,
  RecordIdResult,
  Stage01NavigationImplementation,
} from "./contracts";

type IntentCase = {
  name: string;
  input: string;
  source?: NavigationIntentSource;
  expected: NavigationIntent;
};

type RecordIdCase = {
  name: string;
  input: string;
  expected: RecordIdResult;
};

export const RECORD_ID_CASES: readonly RecordIdCase[] = [
  {
    name: "canonical id",
    input: "forest-edge",
    expected: { kind: "valid", recordId: "forest-edge" },
  },
  {
    name: "trim and lowercase",
    input: "  RIDGE-Marker  ",
    expected: { kind: "valid", recordId: "ridge-marker" },
  },
  {
    name: "empty id",
    input: "   ",
    expected: { kind: "invalid", reason: "empty" },
  },
  {
    name: "id over 64 code points",
    input: "a".repeat(65),
    expected: { kind: "invalid", reason: "too-long" },
  },
  {
    name: "encoded path separator",
    input: "record/child",
    expected: { kind: "invalid", reason: "unsupported-characters" },
  },
] as const;

export const NAVIGATION_INTENT_CASES: readonly IntentCase[] = [
  {
    name: "records path",
    input: "/records",
    expected: { kind: "records", source: "link" },
  },
  {
    name: "custom-scheme host path",
    input: "fieldnotes://records/forest-edge",
    expected: {
      kind: "open-record",
      recordId: "forest-edge",
      destination: "detail",
      source: "link",
    },
  },
  {
    name: "edit deep link",
    input: "fieldnotes:///records/RIDGE-Marker/edit",
    expected: {
      kind: "open-record",
      recordId: "ridge-marker",
      destination: "edit",
      source: "link",
    },
  },
  {
    name: "Expo development link",
    input: "exp://127.0.0.1:8081/--/sync",
    expected: { kind: "open-sync", source: "link" },
  },
  {
    name: "restored settings path",
    input: "/settings",
    source: "restoration",
    expected: { kind: "open-settings", source: "restoration" },
  },
  {
    name: "malformed encoding",
    input: "fieldnotes:///records/%E0%A4%A",
    expected: {
      kind: "invalid",
      reason: "malformed-encoding",
      source: "link",
    },
  },
  {
    name: "record id too long",
    input: `/records/${"a".repeat(65)}`,
    expected: { kind: "invalid", reason: "too-long", source: "link" },
  },
  {
    name: "unknown route",
    input: "/records/forest-edge/history",
    expected: { kind: "invalid", reason: "unknown-route", source: "link" },
  },
] as const;

export type ContractFailure = {
  caseName: string;
  expected: unknown;
  actual: unknown;
};

function sameValue(left: unknown, right: unknown): boolean {
  return JSON.stringify(left) === JSON.stringify(right);
}

/**
 * Framework-neutral contract runner. The reference must return no failures;
 * the learner skeleton is intentionally rejected until Stage 01 is complete.
 */
export function evaluateStage01Contract(
  implementation: Stage01NavigationImplementation,
): ContractFailure[] {
  const failures: ContractFailure[] = [];

  for (const testCase of RECORD_ID_CASES) {
    const actual = implementation.normalizeRecordId(testCase.input);
    if (!sameValue(actual, testCase.expected)) {
      failures.push({
        caseName: `record id: ${testCase.name}`,
        expected: testCase.expected,
        actual,
      });
    }
  }

  for (const testCase of NAVIGATION_INTENT_CASES) {
    const actual = implementation.parseNavigationIntent(
      testCase.input,
      testCase.source,
    );
    if (!sameValue(actual, testCase.expected)) {
      failures.push({
        caseName: `intent: ${testCase.name}`,
        expected: testCase.expected,
        actual,
      });
    }
  }

  const detail: NavigationIntent = {
    kind: "open-record",
    recordId: "forest-edge",
    destination: "detail",
    source: "link",
  };
  const detailAgain: NavigationIntent = { ...detail, source: "notification" };
  const edit: NavigationIntent = { ...detail, destination: "edit" };

  const key = implementation.intentKey(detail);
  const repeatedSourceKey = implementation.intentKey(detailAgain);
  const editKey = implementation.intentKey(edit);
  if (key !== repeatedSourceKey) {
    failures.push({
      caseName: "duplicate intent ignores delivery source",
      expected: key,
      actual: repeatedSourceKey,
    });
  }
  if (key === editKey) {
    failures.push({
      caseName: "detail and edit are different intents",
      expected: "different keys",
      actual: editKey,
    });
  }

  if (implementation.decideDraftBack(false) !== "leave") {
    failures.push({
      caseName: "clean draft can leave",
      expected: "leave",
      actual: implementation.decideDraftBack(false),
    });
  }
  if (implementation.decideDraftBack(true) !== "confirm-discard") {
    failures.push({
      caseName: "dirty draft requires confirmation",
      expected: "confirm-discard",
      actual: implementation.decideDraftBack(true),
    });
  }

  return failures;
}

