import assert from "node:assert/strict";
import test from "node:test";
import { NotificationInstallationCoordinator } from "../src/installation-coordinator.ts";
import {
  DeterministicClock,
  DeterministicNotificationInstallationRegistry,
} from "../src/testkit.ts";

function fixture(now = 100) {
  const clock = new DeterministicClock(now);
  const registry = new DeterministicNotificationInstallationRegistry();
  const coordinator = new NotificationInstallationCoordinator({ registry, clock });
  return { clock, coordinator, registry };
}

test("token rotation replaces one installation binding without logging token contents", async () => {
  const { clock, coordinator, registry } = fixture();
  assert.deepEqual(
    await coordinator.register({
      installationId: "installation-1",
      accountId: "account-1",
      token: { kind: "token", token: "secret-device-token-a" },
    }),
    {
      kind: "registered",
      installationId: "installation-1",
      accountId: "account-1",
      updatedAt: 100,
      change: { kind: "created" },
    },
  );

  clock.advanceTo(200);
  const unchanged = await coordinator.register({
    installationId: "installation-1",
    accountId: "account-1",
    token: { kind: "token", token: "secret-device-token-a" },
  });
  assert.equal(unchanged.kind, "registered");
  if (unchanged.kind === "registered") {
    assert.deepEqual(unchanged.change, { kind: "unchanged" });
  }

  clock.advanceTo(300);
  const rotated = await coordinator.register({
    installationId: "installation-1",
    accountId: "account-1",
    token: { kind: "token", token: "secret-device-token-b" },
  });
  assert.equal(rotated.kind, "registered");
  if (rotated.kind === "registered") {
    assert.deepEqual(rotated.change, { kind: "rotated" });
  }
  assert.deepEqual(registry.snapshot(), [
    {
      installationId: "installation-1",
      accountId: "account-1",
      token: "secret-device-token-b",
      updatedAt: 300,
    },
  ]);
  assert.deepEqual(
    registry.calls.map((call) =>
      call.operation === "upsert" ? call.tokenLabel : call.operation,
    ),
    ["token#1", "token#1", "token#2"],
  );
  assert.equal(JSON.stringify(registry.calls).includes("secret-device-token"), false);
});

test("account switch is atomic and stale logout cannot remove the new binding", async () => {
  const { coordinator, registry } = fixture();
  await coordinator.register({
    installationId: "installation-1",
    accountId: "account-old",
    token: { kind: "token", token: "token-old" },
  });
  const switched = await coordinator.register({
    installationId: "installation-1",
    accountId: "account-new",
    token: { kind: "token", token: "token-new" },
  });
  assert.equal(switched.kind, "registered");
  if (switched.kind === "registered") {
    assert.deepEqual(switched.change, {
      kind: "account-switched",
      previousAccountId: "account-old",
    });
  }

  assert.deepEqual(
    await coordinator.logout({
      installationId: "installation-1",
      accountId: "account-old",
    }),
    {
      kind: "account-mismatch",
      installationId: "installation-1",
      accountId: "account-old",
      boundAccountId: "account-new",
    },
  );
  assert.equal(registry.snapshot()[0]?.accountId, "account-new");

  assert.deepEqual(
    await coordinator.logout({
      installationId: "installation-1",
      accountId: "account-new",
    }),
    {
      kind: "logged-out",
      installationId: "installation-1",
      accountId: "account-new",
    },
  );
  assert.deepEqual(
    await coordinator.logout({
      installationId: "installation-1",
      accountId: "account-new",
    }),
    {
      kind: "already-logged-out",
      installationId: "installation-1",
      accountId: "account-new",
    },
  );
  assert.deepEqual(registry.snapshot(), []);
  assert.deepEqual(
    registry.calls.map((call) => `${call.operation}:${call.accountId}`),
    [
      "upsert:account-old",
      "upsert:account-new",
      "remove:account-old",
      "remove:account-new",
      "remove:account-new",
    ],
  );
});

test("token and registry failures are public and leave durable fake state unchanged", async () => {
  const { coordinator, registry } = fixture();
  assert.deepEqual(
    await coordinator.register({
      installationId: "installation-1",
      accountId: "account-1",
      token: { kind: "failed", reason: "native-token-unavailable" },
    }),
    {
      kind: "token-unavailable",
      installationId: "installation-1",
      accountId: "account-1",
      reason: "native-token-unavailable",
    },
  );
  assert.equal(registry.calls.length, 0);

  await coordinator.register({
    installationId: "installation-1",
    accountId: "account-1",
    token: { kind: "token", token: "token-a" },
  });
  registry.failNext("upsert", "registry-offline");
  assert.deepEqual(
    await coordinator.register({
      installationId: "installation-1",
      accountId: "account-1",
      token: { kind: "token", token: "token-b" },
    }),
    {
      kind: "registry-failed",
      operation: "upsert",
      installationId: "installation-1",
      accountId: "account-1",
      reason: "registry-offline",
    },
  );
  assert.equal(registry.snapshot()[0]?.token, "token-a");

  registry.failNext("remove", "logout-timeout");
  assert.deepEqual(
    await coordinator.logout({
      installationId: "installation-1",
      accountId: "account-1",
    }),
    {
      kind: "registry-failed",
      operation: "remove",
      installationId: "installation-1",
      accountId: "account-1",
      reason: "logout-timeout",
    },
  );
  assert.equal(registry.snapshot()[0]?.accountId, "account-1");
  assert.deepEqual(
    registry.calls.map((call) => call.operation),
    ["upsert", "upsert", "remove"],
  );
});
