import assert from "node:assert/strict";
import test from "node:test";
import { AndroidNotificationRegistrationCoordinator } from "../../lifecycle-engine/src/android-registration.ts";
import {
  ExpoAndroidNotificationChannelAdapter,
  ExpoAndroidNotificationPermissionAdapter,
  ExpoPushTokenAdapter,
  type ExpoAndroidNotificationsApi,
  type ExpoNotificationPermissionResponse,
} from "../src/lifecycle/AndroidNotificationAdapters.ts";
import {
  expoNotificationResponseKey,
  type ExpoNotificationResponseApi,
  type ExpoNotificationResponseShape,
  type NotificationResponseProcessingResult,
  SerializedExpoNotificationResponseSource,
} from "../src/lifecycle/ExpoNotificationResponseSource.ts";
import {
  type WallClockTimerApi,
  WallClockDeadlineScheduler,
} from "../src/lifecycle/WallClockDeadlineScheduler.ts";

const granted: ExpoNotificationPermissionResponse = {
  status: "granted",
  granted: true,
  canAskAgain: true,
};

class FakeNotificationsRegistrationApi implements ExpoAndroidNotificationsApi {
  readonly calls: string[] = [];
  currentPermission: ExpoNotificationPermissionResponse = granted;
  requestedPermission: ExpoNotificationPermissionResponse = granted;
  token = "SECRET_EXPO_PUSH_TOKEN";
  channelFailure = false;
  tokenFailure = false;

  async setNotificationChannelAsync(): Promise<unknown> {
    this.calls.push("channel");
    if (this.channelFailure) throw new Error("SECRET_EXPO_PUSH_TOKEN");
    return null;
  }

  async getPermissionsAsync(): Promise<ExpoNotificationPermissionResponse> {
    this.calls.push("permission:get");
    return this.currentPermission;
  }

  async requestPermissionsAsync(): Promise<ExpoNotificationPermissionResponse> {
    this.calls.push("permission:request");
    return this.requestedPermission;
  }

  async getExpoPushTokenAsync(): Promise<{ data: string }> {
    this.calls.push("token");
    if (this.tokenFailure) throw new Error(this.token);
    return { data: this.token };
  }
}

function registrationFixture(input: {
  api?: FakeNotificationsRegistrationApi;
  runtimePermissionRequired?: boolean;
} = {}) {
  const api = input.api ?? new FakeNotificationsRegistrationApi();
  const coordinator = new AndroidNotificationRegistrationCoordinator({
    channels: new ExpoAndroidNotificationChannelAdapter({
      api,
      channelId: "field-notes-sync",
      channel: { name: "Field Notes sync", importance: 4 },
    }),
    permissions: new ExpoAndroidNotificationPermissionAdapter({
      api,
      runtimePermissionRequired: input.runtimePermissionRequired ?? true,
    }),
    tokens: new ExpoPushTokenAdapter({ api, projectId: "project-id" }),
  });
  return { api, coordinator };
}

test("Android 13 maps channel then permission then token without logging token data", async () => {
  const { api, coordinator } = registrationFixture();
  assert.deepEqual(await coordinator.register({ requestPermission: true }), {
    kind: "token-ready",
    permission: "granted",
    token: "SECRET_EXPO_PUSH_TOKEN",
  });
  assert.deepEqual(api.calls, ["channel", "permission:get", "token"]);
  assert.equal(JSON.stringify(api.calls).includes(api.token), false);
});

test("denied and pre-Android-13 not-required remain distinct", async () => {
  const deniedApi = new FakeNotificationsRegistrationApi();
  deniedApi.currentPermission = {
    status: "denied",
    granted: false,
    canAskAgain: false,
  };
  const denied = registrationFixture({ api: deniedApi });
  assert.deepEqual(await denied.coordinator.register({ requestPermission: true }), {
    kind: "permission-denied",
    canAskAgain: false,
  });
  assert.deepEqual(deniedApi.calls, ["channel", "permission:get"]);

  const legacy = registrationFixture({ runtimePermissionRequired: false });
  legacy.api.currentPermission = {
    status: "denied",
    granted: false,
    canAskAgain: false,
  };
  assert.deepEqual(await legacy.coordinator.register({ requestPermission: true }), {
    kind: "token-ready",
    permission: "not-required",
    token: "SECRET_EXPO_PUSH_TOKEN",
  });
  assert.deepEqual(legacy.api.calls, ["channel", "permission:get", "token"]);
});

test("permission request and token failures preserve the failed stage and safe reason", async () => {
  const api = new FakeNotificationsRegistrationApi();
  api.currentPermission = {
    status: "undetermined",
    granted: false,
    canAskAgain: true,
  };
  const fixture = registrationFixture({ api });
  assert.deepEqual(await fixture.coordinator.register({ requestPermission: false }), {
    kind: "permission-required",
  });
  assert.deepEqual(api.calls, ["channel", "permission:get"]);

  api.calls.length = 0;
  api.tokenFailure = true;
  assert.deepEqual(await fixture.coordinator.register({ requestPermission: true }), {
    kind: "token-failed",
    permission: "granted",
    reason: "token-acquisition-failed",
  });
  assert.deepEqual(api.calls, [
    "channel",
    "permission:get",
    "permission:request",
    "token",
  ]);
  assert.equal(JSON.stringify(api.calls).includes(api.token), false);
});

test("channel failure stops before permission and redacts the thrown value", async () => {
  const api = new FakeNotificationsRegistrationApi();
  api.channelFailure = true;
  const fixture = registrationFixture({ api });
  const result = await fixture.coordinator.register({ requestPermission: true });
  assert.deepEqual(result, {
    kind: "channel-failed",
    reason: "channel-setup-failed",
  });
  assert.deepEqual(api.calls, ["channel"]);
  assert.equal(JSON.stringify(result).includes(api.token), false);
});

type TestNotificationResponse = ExpoNotificationResponseShape & {
  notification: ExpoNotificationResponseShape["notification"] & {
    request: ExpoNotificationResponseShape["notification"]["request"] & {
      content: { data: { secret: string } };
    };
  };
};

function response(identifier: string): TestNotificationResponse {
  return {
    actionIdentifier: "expo.modules.notifications.actions.DEFAULT",
    notification: {
      request: {
        identifier,
        content: { data: { secret: `SECRET_PAYLOAD_${identifier}` } },
      },
    },
  };
}

class FakeNotificationResponseApi
  implements ExpoNotificationResponseApi<TestNotificationResponse>
{
  readonly calls: string[] = [];
  last: TestNotificationResponse | null = null;
  clearFails = false;
  #listener: ((value: TestNotificationResponse) => void) | null = null;

  getLastNotificationResponse(): TestNotificationResponse | null {
    this.calls.push("get-last");
    return this.last;
  }

  addNotificationResponseReceivedListener(
    listener: (response: TestNotificationResponse) => void,
  ): { remove(): void } {
    this.calls.push("listen");
    this.#listener = listener;
    return {
      remove: () => {
        this.calls.push("remove-listener");
        this.#listener = null;
      },
    };
  }

  clearLastNotificationResponse(): void {
    this.calls.push("clear-last");
    if (this.clearFails) throw new Error("SECRET_PAYLOAD_CLEAR_ERROR");
    this.last = null;
  }

  emit(value: TestNotificationResponse): void {
    this.last = value;
    this.#listener?.(value);
  }
}

function deferred(): { promise: Promise<void>; resolve(): void } {
  let resolve!: () => void;
  const promise = new Promise<void>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

test("cold and warm responses share one serialized queue and never clear a newer response", async () => {
  const api = new FakeNotificationResponseApi();
  const cold = response("cold-1");
  const warm = response("warm-1");
  api.last = cold;
  const firstGate = deferred();
  const events: string[] = [];
  const observed: NotificationResponseProcessingResult[] = [];
  let active = 0;
  let maxActive = 0;
  const source = new SerializedExpoNotificationResponseSource({
    api,
    keyOf: expoNotificationResponseKey,
    onResult: (result) => observed.push(result),
    handler: {
      handle: async (value) => {
        const id = value.notification.request.identifier;
        events.push(`handle:${id}:start`);
        active += 1;
        maxActive = Math.max(maxActive, active);
        if (id === "cold-1") await firstGate.promise;
        active -= 1;
        events.push(`handle:${id}:end`);
        return { kind: "acknowledged" };
      },
    },
  });

  const start = source.start();
  api.emit(warm);
  firstGate.resolve();
  const started = await start;
  await source.whenIdle();

  assert.equal(started.kind, "started");
  assert.equal(maxActive, 1);
  assert.deepEqual(events, [
    "handle:cold-1:start",
    "handle:cold-1:end",
    "handle:warm-1:start",
    "handle:warm-1:end",
  ]);
  assert.deepEqual(
    observed.map((result) =>
      result.kind === "acknowledged"
        ? `${result.responseLabel}:${result.clear}`
        : result.kind,
    ),
    ["response#1:not-current", "response#2:cleared"],
  );
  assert.equal(JSON.stringify(observed).includes("SECRET_PAYLOAD"), false);
  source.stop();
  assert.equal(api.calls.at(-1), "remove-listener");
});

test("duplicate enqueue is public and invokes the durable handler once", async () => {
  const api = new FakeNotificationResponseApi();
  const value = response("duplicate-1");
  api.last = value;
  const gate = deferred();
  let handlerCalls = 0;
  const source = new SerializedExpoNotificationResponseSource({
    api,
    keyOf: expoNotificationResponseKey,
    handler: {
      handle: async () => {
        handlerCalls += 1;
        api.calls.push("handler:acknowledged");
        await gate.promise;
        return { kind: "acknowledged" };
      },
    },
  });

  const first = source.enqueue("cold", value);
  assert.deepEqual(await source.enqueue("warm", value), {
    kind: "duplicate",
    origin: "warm",
    responseLabel: "response#1",
  });
  gate.resolve();
  assert.deepEqual(await first, {
    kind: "acknowledged",
    origin: "cold",
    responseLabel: "response#1",
    clear: "cleared",
  });
  assert.equal(handlerCalls, 1);
  assert.deepEqual(api.calls, [
    "handler:acknowledged",
    "get-last",
    "clear-last",
  ]);
});

test("retryable durable disposition does not clear the native response", async () => {
  const api = new FakeNotificationResponseApi();
  const value = response("retryable-1");
  api.last = value;
  const source = new SerializedExpoNotificationResponseSource({
    api,
    keyOf: expoNotificationResponseKey,
    handler: {
      handle: async () => ({ kind: "retryable", code: "repository-busy" }),
    },
  });

  assert.deepEqual(await source.enqueue("cold", value), {
    kind: "retryable",
    origin: "cold",
    responseLabel: "response#1",
    code: "repository-busy",
  });
  assert.equal(api.calls.includes("clear-last"), false);
  assert.equal(api.last, value);
});

test("clear failure replays through a messageId-idempotent durable handler", async () => {
  const api = new FakeNotificationResponseApi();
  const value = response("failure-1");
  api.last = value;
  let attempt = 0;
  let durableTerminalWrites = 0;
  let terminalPersisted = false;
  const source = new SerializedExpoNotificationResponseSource({
    api,
    keyOf: expoNotificationResponseKey,
    handler: {
      handle: async () => {
        attempt += 1;
        if (attempt === 1) throw new Error("SECRET_PAYLOAD_HANDLER_ERROR");
        if (!terminalPersisted) {
          terminalPersisted = true;
          durableTerminalWrites += 1;
        }
        return { kind: "terminal", code: "malformed" };
      },
    },
  });

  const handlerError = await source.enqueue("cold", value);
  assert.deepEqual(handlerError, {
    kind: "handler-error",
    origin: "cold",
    responseLabel: "response#1",
    code: "handler-threw",
  });
  assert.equal(api.calls.includes("clear-last"), false);

  api.clearFails = true;
  const clearError = await source.enqueue("cold", value);
  assert.deepEqual(clearError, {
    kind: "clear-error",
    origin: "cold",
    responseLabel: "response#1",
    disposition: "terminal",
    code: "clear-failed",
  });
  assert.equal(JSON.stringify([handlerError, clearError]).includes("SECRET_PAYLOAD"), false);

  api.clearFails = false;
  assert.deepEqual(await source.enqueue("cold", value), {
    kind: "terminal",
    origin: "cold",
    responseLabel: "response#1",
    code: "malformed",
    clear: "cleared",
  });
  assert.equal(attempt, 3);
  assert.equal(durableTerminalWrites, 1);
});

class FakeWallClockTimers implements WallClockTimerApi<number> {
  nowValue = 100;
  nextHandle = 1;
  readonly pending = new Map<number, { callback: () => void; delayMs: number }>();
  readonly cleared: number[] = [];

  now(): number {
    return this.nowValue;
  }

  setTimeout(callback: () => void, delayMs: number): number {
    const handle = this.nextHandle;
    this.nextHandle += 1;
    this.pending.set(handle, { callback, delayMs });
    return handle;
  }

  clearTimeout(handle: number): void {
    this.cleared.push(handle);
    this.pending.delete(handle);
  }

  fire(handle: number, now: number): void {
    const timer = this.pending.get(handle);
    if (timer === undefined) throw new Error("missing timer");
    this.pending.delete(handle);
    this.nowValue = now;
    timer.callback();
  }
}

test("wall-clock scheduler uses remaining delay and cleans fired, cancelled and disposed timers", () => {
  const timers = new FakeWallClockTimers();
  const scheduler = new WallClockDeadlineScheduler(timers);
  const fired: string[] = [];

  const cancel = scheduler.schedule(150, () => fired.push("first"));
  assert.equal(timers.pending.get(1)?.delayMs, 50);
  cancel();
  cancel();
  assert.deepEqual(timers.cleared, [1]);
  assert.equal(scheduler.pendingCount(), 0);

  timers.nowValue = 130;
  scheduler.schedule(120, () => fired.push("past"));
  assert.equal(timers.pending.get(2)?.delayMs, 0);
  timers.fire(2, 130);
  assert.deepEqual(fired, ["past"]);
  assert.equal(scheduler.pendingCount(), 0);

  scheduler.schedule(200, () => fired.push("disposed-a"));
  scheduler.schedule(250, () => fired.push("disposed-b"));
  assert.equal(scheduler.pendingCount(), 2);
  scheduler.dispose();
  assert.equal(scheduler.pendingCount(), 0);
  assert.equal(timers.pending.size, 0);
  assert.deepEqual(fired, ["past"]);
});

test("non-finite wall clock at timer callback cancels instead of firing success", () => {
  const timers = new FakeWallClockTimers();
  const observed: Array<{ kind: string; phase: string }> = [];
  const scheduler = new WallClockDeadlineScheduler(timers, (error) => {
    observed.push(error);
  });
  let fired = false;
  scheduler.schedule(150, () => {
    fired = true;
  });

  timers.fire(1, Number.NaN);
  assert.equal(fired, false);
  assert.equal(scheduler.pendingCount(), 0);
  assert.deepEqual(observed, [
    { kind: "invalid-clock", phase: "timer-callback" },
  ]);
});
