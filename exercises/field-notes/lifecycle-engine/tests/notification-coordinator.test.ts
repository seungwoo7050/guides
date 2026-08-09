import assert from "node:assert/strict";
import test from "node:test";
import { NotificationIntentCoordinator } from "../src/notification-coordinator.ts";
import { parseNotificationEnvelope } from "../src/notification-parser.ts";
import {
  Deferred,
  DeterministicClock,
  DeterministicNotificationRepository,
  InMemoryProcessedIntentClaims,
  SequentialNotificationOwnerIds,
} from "../src/testkit.ts";

const CONFLICT_MESSAGE = {
  schemaVersion: 1,
  messageId: "message-1",
  accountId: "account-1",
  intent: { kind: "record-conflict", recordId: "record-1" },
} as const;

function coordinator(input: {
  repository: DeterministicNotificationRepository;
  claims: InMemoryProcessedIntentClaims;
  clock: DeterministicClock;
}): NotificationIntentCoordinator {
  return new NotificationIntentCoordinator({
    repository: input.repository,
    claims: input.claims,
    clock: input.clock,
    owners: new SequentialNotificationOwnerIds(),
    claimLeaseMs: 1_000,
  });
}

test("parser accepts schema and intent only and rejects business snapshots", () => {
  assert.deepEqual(parseNotificationEnvelope(CONFLICT_MESSAGE), {
    kind: "valid",
    envelope: CONFLICT_MESSAGE,
  });
  assert.deepEqual(
    parseNotificationEnvelope({
      ...CONFLICT_MESSAGE,
      record: { title: "payload is not business truth" },
    }),
    { kind: "invalid", reason: "unexpected-field" },
  );
  assert.deepEqual(
    parseNotificationEnvelope({
      ...CONFLICT_MESSAGE,
      intent: { kind: "record-conflict", recordId: "bad/id" },
    }),
    { kind: "invalid", reason: "invalid-record-id" },
  );
  assert.deepEqual(
    parseNotificationEnvelope({ ...CONFLICT_MESSAGE, schemaVersion: 0 }),
    { kind: "invalid", reason: "unsupported-schema" },
  );
});

test("cold start waits for readiness, rereads business state, then durably deduplicates", async () => {
  const ready = new Deferred<void>();
  const repository = new DeterministicNotificationRepository({
    account: { kind: "active", accountId: "account-1" },
    readyGate: ready.promise,
  });
  repository.setRecord("record-1", "active");
  repository.setConflict("record-1", "active");
  const claims = new InMemoryProcessedIntentClaims();
  const clock = new DeterministicClock();
  const firstCoordinator = coordinator({ repository, claims, clock });

  const pending = firstCoordinator.prepare(CONFLICT_MESSAGE);
  assert.deepEqual(repository.calls, ["ready:start"]);
  assert.equal(claims.state("message-1"), "absent");

  ready.resolve();
  const prepared = await pending;
  assert.equal(prepared.kind, "prepared");
  if (prepared.kind !== "prepared") return;
  assert.deepEqual(repository.calls, [
    "ready:start",
    "ready:complete",
    "account",
    "record:record-1",
    "conflict:record-1",
  ]);
  assert.deepEqual(prepared.navigation, {
    kind: "open-sync",
    focus: "conflict",
    recordId: "record-1",
  });
  assert.equal(claims.state("message-1"), "claimed");

  await firstCoordinator.acknowledge(prepared.claim);
  const afterRestart = coordinator({ repository, claims, clock });
  assert.deepEqual(await afterRestart.prepare(CONFLICT_MESSAGE), {
    kind: "rejected",
    reason: "duplicate",
  });
});

test("an unacknowledged cold-start claim is busy, then recoverable after lease expiry", async () => {
  const repository = new DeterministicNotificationRepository({
    account: { kind: "active", accountId: "account-1" },
  });
  repository.setRecord("record-1", "active");
  repository.setConflict("record-1", "active");
  const claims = new InMemoryProcessedIntentClaims();
  const clock = new DeterministicClock();

  const first = await coordinator({ repository, claims, clock }).prepare(
    CONFLICT_MESSAGE,
  );
  assert.equal(first.kind, "prepared");
  assert.deepEqual(
    await coordinator({ repository, claims, clock }).prepare(CONFLICT_MESSAGE),
    { kind: "rejected", reason: "in-progress" },
  );

  clock.advanceTo(1_000);
  const recovered = await coordinator({ repository, claims, clock }).prepare(
    CONFLICT_MESSAGE,
  );
  assert.equal(recovered.kind, "prepared");
  if (first.kind === "prepared" && recovered.kind === "prepared") {
    assert.notEqual(first.claim.token, recovered.claim.token);
  }
});

test("resolved conflict rejects stale payload and uses only a safe current-state route", async () => {
  const repository = new DeterministicNotificationRepository({
    account: { kind: "active", accountId: "account-1" },
  });
  repository.setRecord("record-1", "active");
  repository.setConflict("record-1", "resolved");
  const claims = new InMemoryProcessedIntentClaims();
  const clock = new DeterministicClock();
  const lifecycle = coordinator({ repository, claims, clock });

  assert.deepEqual(await lifecycle.prepare(CONFLICT_MESSAGE), {
    kind: "rejected",
    reason: "stale",
    safeNavigation: { kind: "open-record", recordId: "record-1" },
  });
  assert.equal(claims.state("message-1"), "processed");
  assert.deepEqual(await lifecycle.prepare(CONFLICT_MESSAGE), {
    kind: "rejected",
    reason: "duplicate",
  });
});

test("deleted records and previous-account messages never open protected targets", async () => {
  const repository = new DeterministicNotificationRepository({
    account: { kind: "active", accountId: "account-1" },
  });
  repository.setRecord("record-1", "deleted");
  const claims = new InMemoryProcessedIntentClaims();
  const clock = new DeterministicClock();
  const lifecycle = coordinator({ repository, claims, clock });

  assert.deepEqual(await lifecycle.prepare(CONFLICT_MESSAGE), {
    kind: "rejected",
    reason: "record-deleted",
    safeNavigation: { kind: "open-records" },
  });

  const previousAccount = {
    ...CONFLICT_MESSAGE,
    messageId: "message-previous-account",
    accountId: "account-old",
  };
  assert.deepEqual(await lifecycle.prepare(previousAccount), {
    kind: "rejected",
    reason: "account-mismatch",
  });
  assert.equal(claims.state("message-previous-account"), "absent");
  assert.equal(
    repository.calls.filter((call) => call === "record:record-1").length,
    1,
  );
});

test("deleted account, malformed and stale sync notification are rejected", async () => {
  const deletedRepository = new DeterministicNotificationRepository({
    account: { kind: "deleted" },
  });
  const claims = new InMemoryProcessedIntentClaims();
  const clock = new DeterministicClock();
  const deletedLifecycle = coordinator({
    repository: deletedRepository,
    claims,
    clock,
  });
  assert.deepEqual(await deletedLifecycle.prepare(CONFLICT_MESSAGE), {
    kind: "rejected",
    reason: "account-deleted",
  });

  const activeRepository = new DeterministicNotificationRepository({
    account: { kind: "active", accountId: "account-1" },
  });
  const lifecycle = coordinator({ repository: activeRepository, claims, clock });
  assert.deepEqual(await lifecycle.prepare({ type: "unknown" }), {
    kind: "rejected",
    reason: "malformed",
    parseReason: "unexpected-field",
  });
  assert.deepEqual(
    await lifecycle.prepare({
      schemaVersion: 1,
      messageId: "sync-message",
      accountId: "account-1",
      intent: { kind: "sync-blocked" },
    }),
    {
      kind: "rejected",
      reason: "stale",
      safeNavigation: { kind: "open-records" },
    },
  );
});
