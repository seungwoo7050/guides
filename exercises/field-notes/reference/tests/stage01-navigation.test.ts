import { FIELD_RECORD_FIXTURES } from "@field-notes/shared";
import { evaluateStage01Contract } from "@field-notes/shared/testkit";
import {
  ExpoLinkIntentAdapter,
  resolvedAppScheme,
} from "../src/adapters/ExpoLinkIntentAdapter";
import {
  LatestStartupIntentBuffer,
  RecentIntentSet,
  resolveNavigationIntent,
  StartupIntentCoordinator,
} from "../src/navigation/decision";
import {
  applyReservedRoute,
  CrossSourceRouteArbiter,
} from "../src/navigation/CrossSourceRouteArbiter";
import {
  handlePreventedDraftNavigation,
  OneShotNavigationPermit,
  requestDraftLeave,
} from "../src/navigation/draftLeavePolicy";
import {
  intentKey,
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

  it("accepts only the resolved profile scheme (plus bounded Expo development links)", () => {
    expect(
      parseNavigationIntent(
        "fieldnotes-development:///records/forest-edge",
        "link",
        "fieldnotes-development",
      ),
    ).toMatchObject({ kind: "open-record", recordId: "forest-edge" });
    expect(
      parseNavigationIntent(
        "fieldnotes-preview://records/forest-edge/edit",
        "link",
        "fieldnotes-preview",
      ),
    ).toMatchObject({ kind: "open-record", destination: "edit" });
    expect(
      parseNavigationIntent(
        "fieldnotes:///records/forest-edge",
        "link",
        "fieldnotes-preview",
      ),
    ).toEqual({
      kind: "invalid",
      reason: "unexpected-scheme",
      source: "link",
    });
    expect(
      parseNavigationIntent(
        "https://attacker.invalid/records/forest-edge",
        "link",
        "fieldnotes",
      ),
    ).toEqual({
      kind: "invalid",
      reason: "unexpected-scheme",
      source: "link",
    });
    expect(
      parseNavigationIntent(
        "exp://127.0.0.1:8081/records/forest-edge",
        "link",
        "fieldnotes-development",
      ),
    ).toEqual({
      kind: "invalid",
      reason: "unexpected-scheme",
      source: "link",
    });
  });

  it("binds initial and warm links to the adapter's resolved scheme", async () => {
    let warmListener: ((event: { url: string }) => void) | undefined;
    const source = {
      getInitialURL: async () => "fieldnotes-preview:///sync",
      addEventListener: (
        _eventName: "url",
        listener: (event: { url: string }) => void,
      ) => {
        warmListener = listener;
        return { remove: jest.fn() };
      },
    };
    const adapter = new ExpoLinkIntentAdapter("fieldnotes-preview", source);
    await expect(adapter.initial()).resolves.toEqual({
      kind: "open-sync",
      source: "link",
    });
    const received: unknown[] = [];
    adapter.subscribe((intent) => received.push(intent));
    warmListener?.({ url: "fieldnotes:///settings" });
    expect(received).toEqual([
      { kind: "invalid", reason: "unexpected-scheme", source: "link" },
    ]);
  });

  it("requires one concrete scheme from resolved Expo config", () => {
    expect(resolvedAppScheme("fieldnotes-preview")).toBe("fieldnotes-preview");
    expect(() => resolvedAppScheme(["fieldnotes", "fieldnotes-preview"])).toThrow(
      "exactly one",
    );
    expect(() => resolvedAppScheme(undefined)).toThrow("exactly one");
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

  it("keeps the latest bounded warm link until bootstrap can consume it", () => {
    const buffer = new LatestStartupIntentBuffer();
    buffer.offer(parseNavigationIntent("/records/forest-edge"));
    buffer.offer(parseNavigationIntent("/settings"));
    expect(buffer.take()).toEqual({ kind: "open-settings", source: "link" });
    expect(buffer.take()).toBeNull();
  });

  it("releases a failed startup reservation so the same route can retry", async () => {
    let attempts = 0;
    const coordinator = new StartupIntentCoordinator({
      ready: async () => {
        attempts += 1;
        if (attempts === 1) throw new Error("opening database failed once");
      },
      recordExists: async () => true,
    });
    const intent = parseNavigationIntent("/records/forest-edge");
    await expect(coordinator.handle(intent, intentKey(intent))).rejects.toThrow("failed once");
    await expect(coordinator.handle(intent, intentKey(intent))).resolves.toEqual({
      kind: "navigate",
      href: "/records/forest-edge",
    });
  });

  it("deduplicates committed link/notification routes but releases failed routing", () => {
    const arbiter = new CrossSourceRouteArbiter(4);
    const link = parseNavigationIntent("/records/forest-edge");
    const first = arbiter.reserveLink(link);
    expect(first).not.toBeNull();
    expect(() => applyReservedRoute(first!, () => {
      throw new Error("router was not ready");
    })).toThrow("router was not ready");
    const retry = arbiter.reserveNotification({
      kind: "open-record",
      recordId: "forest-edge",
    });
    expect(retry).not.toBeNull();
    retry?.commit();
    expect(arbiter.reserveLink(link)).toBeNull();
  });

  it("leaves clean drafts directly and dispatches dirty leave only after approval", () => {
    const events: string[] = [];
    expect(requestDraftLeave(false, () => events.push("unexpected"), () => events.push("left")))
      .toBe("left");
    let approve: (() => void) | undefined;
    expect(requestDraftLeave(true, (discard) => {
      events.push("confirm");
      approve = discard;
    }, () => events.push("discarded"))).toBe("confirmation-requested");
    expect(events).toEqual(["left", "confirm"]);
    approve?.();
    expect(events).toEqual(["left", "confirm", "discarded"]);
  });

  it("grants exactly one committed navigation without bypassing a later dirty leave", () => {
    const permit = new OneShotNavigationPermit();
    expect(permit.consume()).toBe(false);
    permit.grant();
    expect(permit.consume()).toBe(true);
    expect(permit.consume()).toBe(false);
    permit.grant();
    permit.revoke();
    expect(permit.consume()).toBe(false);
  });

  it("uses one confirmation for cancel and no confirmation for committed navigation", () => {
    const permit = new OneShotNavigationPermit();
    let approve: (() => void) | undefined;
    const confirms: string[] = [];
    const dispatched: string[] = [];
    expect(handlePreventedDraftNavigation(
      permit,
      (discard) => {
        confirms.push("confirm");
        approve = discard;
      },
      () => dispatched.push("cancel-action"),
    )).toBe("confirmation-requested");
    approve?.();
    expect(confirms).toEqual(["confirm"]);
    expect(dispatched).toEqual(["cancel-action"]);

    permit.grant();
    expect(handlePreventedDraftNavigation(
      permit,
      () => confirms.push("unexpected"),
      () => dispatched.push("saved-replace"),
    )).toBe("bypassed");
    expect(confirms).toEqual(["confirm"]);
    expect(dispatched).toEqual(["cancel-action", "saved-replace"]);
  });
});
