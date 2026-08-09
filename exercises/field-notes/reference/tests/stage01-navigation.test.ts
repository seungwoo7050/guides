import { FIELD_RECORD_FIXTURES } from "@field-notes/shared";
import { evaluateStage01Contract } from "@field-notes/shared/testkit";
import {
  RecentIntentSet,
  resolveNavigationIntent,
  StartupIntentCoordinator,
} from "../src/navigation/decision";
import {
  parseNavigationIntent,
  stage01Navigation,
} from "../src/navigation/stage01";

describe("Stage 01 navigation behavior", () => {
  it("satisfies the shared parser, id, duplicate-key, and back contract", () => {
    expect(evaluateStage01Contract(stage01Navigation)).toEqual([]);
  });

  it("distinguishes an invalid id from a valid but missing target", async () => {
    const exists = async (recordId: string) =>
      FIELD_RECORD_FIXTURES.some((record) => record.id === recordId);

    await expect(
      resolveNavigationIntent(
        parseNavigationIntent("/records/contains%2Fslash"),
        exists,
      ),
    ).resolves.toEqual({
      kind: "invalid",
      reason: "unsupported-characters",
      fallbackHref: "/records",
    });

    await expect(
      resolveNavigationIntent(parseNavigationIntent("/records/missing-record"), exists),
    ).resolves.toEqual({
      kind: "missing-record",
      recordId: "missing-record",
      fallbackHref: "/records",
    });
  });

  it("waits for target existence before choosing an edit route", async () => {
    const checked: string[] = [];
    const decision = await resolveNavigationIntent(
      parseNavigationIntent("fieldnotes:///records/forest-edge/edit"),
      async (recordId) => {
        checked.push(recordId);
        return true;
      },
    );
    expect(checked).toEqual(["forest-edge"]);
    expect(decision).toEqual({
      kind: "navigate",
      href: "/records/forest-edge/edit",
    });
  });

  it("rejects the same delivered intent and bounds retained keys", () => {
    const recent = new RecentIntentSet(2);
    expect(recent.accept("record:a:detail")).toBe(true);
    expect(recent.accept("record:a:detail")).toBe(false);
    expect(recent.accept("record:b:detail")).toBe(true);
    expect(recent.accept("record:c:detail")).toBe(true);
    expect(recent.accept("record:a:detail")).toBe(true);
  });

  it("does not resolve or navigate before startup state is ready", async () => {
    const events: string[] = [];
    let releaseReady: (() => void) | undefined;
    const ready = new Promise<void>((resolve) => {
      releaseReady = resolve;
    });
    const coordinator = new StartupIntentCoordinator({
      ready: async () => {
        events.push("ready:start");
        await ready;
        events.push("ready:done");
      },
      recordExists: async () => {
        events.push("target:checked");
        return true;
      },
    });
    const intent = parseNavigationIntent("/records/forest-edge");
    const decisionPromise = coordinator.handle(intent, "record:forest-edge:detail");
    await Promise.resolve();
    expect(events).toEqual(["ready:start"]);
    releaseReady?.();
    await expect(decisionPromise).resolves.toEqual({
      kind: "navigate",
      href: "/records/forest-edge",
    });
    expect(events).toEqual(["ready:start", "ready:done", "target:checked"]);
    await expect(
      coordinator.handle(intent, "record:forest-edge:detail"),
    ).resolves.toEqual({ kind: "duplicate" });
  });
});
