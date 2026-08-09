import assert from "node:assert/strict";
import test from "node:test";
import { LifecycleSyncCoordinator } from "../src/sync-coordinator.ts";
import {
  Deferred,
  DeterministicBoundedWorker,
  DeterministicClock,
  DeterministicCommandRepository,
  SequentialWorkerIds,
} from "../src/testkit.ts";
import type { LifecycleSyncTrigger } from "../src/types.ts";

function coordinator(input: {
  worker: DeterministicBoundedWorker;
  clock: DeterministicClock;
}): LifecycleSyncCoordinator {
  return new LifecycleSyncCoordinator({
    worker: input.worker,
    clock: input.clock,
    deadlines: input.clock,
    workerIds: new SequentialWorkerIds(),
  });
}

test("manual, app-active, background and notification use the same worker contract", async () => {
  for (const trigger of [
    "manual",
    "app-active",
    "background",
    "notification",
  ] as const satisfies readonly LifecycleSyncTrigger[]) {
    const clock = new DeterministicClock(1_000);
    const repository = new DeterministicCommandRepository(["command-1"]);
    const worker = new DeterministicBoundedWorker({ repository, clock });
    const result = await coordinator({ worker, clock }).runOpportunity(trigger);

    assert.equal(result.kind, "ran");
    assert.deepEqual(worker.calls.map((call) => call.trigger), [trigger]);
    assert.deepEqual(repository.snapshot(), [
      { commandId: "command-1", state: { kind: "completed", attempt: 1 } },
    ]);
  }
});

test("app-active converges pending work even when background never ran", async () => {
  const clock = new DeterministicClock();
  const repository = new DeterministicCommandRepository(["command-1", "command-2"]);
  const worker = new DeterministicBoundedWorker({ repository, clock });
  const lifecycle = coordinator({ worker, clock });

  assert.deepEqual(
    repository.snapshot().map((entry) => entry.state.kind),
    ["pending", "pending"],
  );
  assert.equal(worker.calls.length, 0);

  const result = await lifecycle.runOpportunity("app-active");
  assert.equal(result.kind, "ran");
  assert.deepEqual(
    repository.snapshot().map((entry) => entry.state.kind),
    ["completed", "completed"],
  );
});

test("deadline abort keeps UNKNOWN retryable and starts no second command", async () => {
  const clock = new DeterministicClock();
  const repository = new DeterministicCommandRepository(["command-1", "command-2"]);
  const gate = new Deferred<void>();
  const worker = new DeterministicBoundedWorker({
    repository,
    clock,
    pauseAfterClaim: gate.promise,
    retryDelayMs: 500,
  });
  const lifecycle = coordinator({ worker, clock });

  const pending = lifecycle.runOpportunity("background", { deadlineAt: 100 });
  assert.deepEqual(
    repository.snapshot().map((entry) => entry.state.kind),
    ["leased", "pending"],
  );

  clock.advanceTo(100);
  const expired = await pending;
  assert.equal(expired.kind, "ran");
  if (expired.kind !== "ran") return;
  assert.equal(expired.worker.stopped, "aborted");
  assert.equal(expired.worker.claimed, 1);
  assert.deepEqual(
    repository.snapshot().map((entry) => entry.state.kind),
    ["retry-wait", "pending"],
  );

  gate.resolve();
  clock.advanceTo(600);
  await lifecycle.runOpportunity("app-active");
  assert.deepEqual(repository.snapshot(), [
    { commandId: "command-1", state: { kind: "completed", attempt: 2 } },
    { commandId: "command-2", state: { kind: "completed", attempt: 1 } },
  ]);
});

test("expired or already-aborted opportunities do not enter the worker", async () => {
  const clock = new DeterministicClock(100);
  const repository = new DeterministicCommandRepository(["command-1"]);
  const worker = new DeterministicBoundedWorker({ repository, clock });
  const lifecycle = coordinator({ worker, clock });
  const aborted = new AbortController();
  aborted.abort();

  assert.deepEqual(await lifecycle.runOpportunity("background", { deadlineAt: 100 }), {
    kind: "not-started",
    trigger: "background",
    reason: "deadline",
  });
  assert.deepEqual(await lifecycle.runOpportunity("manual", { signal: aborted.signal }), {
    kind: "not-started",
    trigger: "manual",
    reason: "aborted",
  });
  assert.equal(worker.calls.length, 0);
  assert.equal(repository.snapshot()[0]?.state.kind, "pending");
});

test("concurrent triggers coalesce in-process without weakening durable lease ownership", async () => {
  const clock = new DeterministicClock();
  const repository = new DeterministicCommandRepository(["command-1"]);
  const gate = new Deferred<void>();
  const worker = new DeterministicBoundedWorker({
    repository,
    clock,
    pauseAfterClaim: gate.promise,
  });
  const lifecycle = coordinator({ worker, clock });

  const leader = lifecycle.runOpportunity("background");
  const joined = lifecycle.runOpportunity("app-active");
  assert.equal(worker.calls.length, 1);
  assert.equal(repository.snapshot()[0]?.state.kind, "leased");

  gate.resolve();
  const [leaderResult, joinedResult] = await Promise.all([leader, joined]);
  assert.equal(leaderResult.kind, "ran");
  assert.equal(joinedResult.kind, "coalesced");
  if (joinedResult.kind === "coalesced") {
    assert.equal(joinedResult.leaderTrigger, "background");
    assert.equal(joinedResult.execution.kind, "ran");
  }
  assert.equal(repository.snapshot()[0]?.state.kind, "completed");
});

test("separate coordinators rely on the repository lease, not memory coalescing", async () => {
  const clock = new DeterministicClock();
  const repository = new DeterministicCommandRepository(["command-1"]);
  const gate = new Deferred<void>();
  const firstWorker = new DeterministicBoundedWorker({
    repository,
    clock,
    pauseAfterClaim: gate.promise,
  });
  const secondWorker = new DeterministicBoundedWorker({ repository, clock });

  const first = coordinator({ worker: firstWorker, clock }).runOpportunity("background");
  const contender = await coordinator({
    worker: secondWorker,
    clock,
  }).runOpportunity("app-active");

  assert.equal(contender.kind, "ran");
  if (contender.kind === "ran") assert.equal(contender.worker.claimed, 0);
  gate.resolve();
  await first;
  assert.equal(repository.snapshot()[0]?.state.kind, "completed");
});

test("a process-death lease is reclaimed only after expiry", async () => {
  const clock = new DeterministicClock();
  const repository = new DeterministicCommandRepository(["command-1"]);
  assert.ok(
    repository.claim({ workerId: "dead-process", now: 0, leaseDurationMs: 1_000 }),
  );

  const worker = new DeterministicBoundedWorker({ repository, clock });
  const lifecycle = coordinator({ worker, clock });
  const early = await lifecycle.runOpportunity("app-active");
  assert.equal(early.kind, "ran");
  if (early.kind === "ran") assert.equal(early.worker.claimed, 0);

  clock.advanceTo(1_000);
  await lifecycle.runOpportunity("app-active");
  assert.deepEqual(repository.snapshot(), [
    { commandId: "command-1", state: { kind: "completed", attempt: 2 } },
  ]);
});
