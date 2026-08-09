import assert from "node:assert/strict";
import test from "node:test";
import { AndroidNotificationRegistrationCoordinator } from "../src/android-registration.ts";
import {
  ScriptedAndroidChannel,
  ScriptedNotificationPermission,
  ScriptedPushToken,
} from "../src/testkit.ts";
import type { NotificationPermissionState } from "../src/types.ts";

function registration(input: {
  current: NotificationPermissionState;
  request?: NotificationPermissionState;
  token?: Awaited<ReturnType<ScriptedPushToken["getToken"]>>;
  channel?: Awaited<ReturnType<ScriptedAndroidChannel["ensureChannel"]>>;
}) {
  const calls: string[] = [];
  const coordinator = new AndroidNotificationRegistrationCoordinator({
    channels: new ScriptedAndroidChannel(
      calls,
      input.channel ?? { kind: "ready" },
    ),
    permissions: new ScriptedNotificationPermission({
      calls,
      current: input.current,
      ...(input.request === undefined ? {} : { request: input.request }),
    }),
    tokens: new ScriptedPushToken(
      calls,
      input.token ?? { kind: "token", token: "redacted-test-token" },
    ),
  });
  return { calls, coordinator };
}

test("Android registration enforces channel then permission then token", async () => {
  const { calls, coordinator } = registration({ current: { kind: "granted" } });
  assert.deepEqual(await coordinator.register({ requestPermission: true }), {
    kind: "token-ready",
    permission: "granted",
    token: "redacted-test-token",
  });
  assert.deepEqual(calls, ["channel", "permission:current", "token"]);
});

test("not-determined requests only in explicit user context", async () => {
  const noRequest = registration({ current: { kind: "not-determined" } });
  assert.deepEqual(
    await noRequest.coordinator.register({ requestPermission: false }),
    { kind: "permission-required" },
  );
  assert.deepEqual(noRequest.calls, ["channel", "permission:current"]);

  const requested = registration({
    current: { kind: "not-determined" },
    request: { kind: "granted" },
  });
  assert.equal(
    (await requested.coordinator.register({ requestPermission: true })).kind,
    "token-ready",
  );
  assert.deepEqual(requested.calls, [
    "channel",
    "permission:current",
    "permission:request",
    "token",
  ]);
});

test("denied and restricted never acquire a token", async () => {
  const denied = registration({
    current: { kind: "denied", canAskAgain: false },
  });
  assert.deepEqual(await denied.coordinator.register({ requestPermission: true }), {
    kind: "permission-denied",
    canAskAgain: false,
  });
  assert.deepEqual(denied.calls, ["channel", "permission:current"]);

  const restricted = registration({
    current: { kind: "restricted", reason: "device-policy" },
  });
  assert.deepEqual(
    await restricted.coordinator.register({ requestPermission: true }),
    { kind: "permission-restricted", reason: "device-policy" },
  );
  assert.deepEqual(restricted.calls, ["channel", "permission:current"]);
});

test("not-required remains distinct from granted while still allowing token acquisition", async () => {
  const { calls, coordinator } = registration({
    current: { kind: "not-required" },
  });
  assert.deepEqual(await coordinator.register({ requestPermission: true }), {
    kind: "token-ready",
    permission: "not-required",
    token: "redacted-test-token",
  });
  assert.deepEqual(calls, ["channel", "permission:current", "token"]);
});

test("channel and token failures preserve the failed stage", async () => {
  const channelFailure = registration({
    current: { kind: "granted" },
    channel: { kind: "failed", reason: "channel-unavailable" },
  });
  assert.deepEqual(
    await channelFailure.coordinator.register({ requestPermission: true }),
    { kind: "channel-failed", reason: "channel-unavailable" },
  );
  assert.deepEqual(channelFailure.calls, ["channel"]);

  const tokenFailure = registration({
    current: { kind: "granted" },
    token: { kind: "failed", reason: "project-id-missing" },
  });
  assert.deepEqual(
    await tokenFailure.coordinator.register({ requestPermission: true }),
    {
      kind: "token-failed",
      permission: "granted",
      reason: "project-id-missing",
    },
  );
  assert.deepEqual(tokenFailure.calls, ["channel", "permission:current", "token"]);
});
