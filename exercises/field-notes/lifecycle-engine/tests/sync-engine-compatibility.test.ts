import assert from "node:assert/strict";
import test from "node:test";
import type { BoundedSyncWorker } from "../../sync-engine/src/index.ts";
import type { BoundedWorkerPort } from "../src/ports.ts";

const asLifecycleWorker = (worker: BoundedSyncWorker): BoundedWorkerPort => worker;

test("lifecycle worker port remains structurally compatible with sync-engine", () => {
  assert.equal(typeof asLifecycleWorker, "function");
});
