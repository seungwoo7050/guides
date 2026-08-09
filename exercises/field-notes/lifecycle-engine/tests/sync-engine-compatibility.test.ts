import assert from "node:assert/strict";
import test from "node:test";
import type {
  BoundedSyncWorker,
  SyncTrigger,
} from "../../sync-engine/src/index.ts";
import type { BoundedWorkerPort } from "../src/ports.ts";
import type { LifecycleSyncTrigger } from "../src/types.ts";

type AssertTrue<Value extends true> = Value;
type CoversEveryLifecycleTrigger = AssertTrue<
  Exclude<LifecycleSyncTrigger, SyncTrigger> extends never ? true : false
>;
type DirectCompatibility = AssertTrue<
  BoundedSyncWorker extends BoundedWorkerPort ? true : false
>;

const coversEveryLifecycleTrigger: CoversEveryLifecycleTrigger = true;
const directlyCompatible: DirectCompatibility = true;

test("Stage 04 worker covers every lifecycle trigger without a cast", () => {
  assert.equal(coversEveryLifecycleTrigger, true);
  assert.equal(directlyCompatible, true);
});
