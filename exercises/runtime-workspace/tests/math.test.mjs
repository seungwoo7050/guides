import assert from "node:assert/strict";
import test from "node:test";
import { parsePort, sum } from "../packages/math/src/index.ts";

test("sum is pure for the supplied collection", () => {
  const values = Object.freeze([1, 2, 3]);
  assert.equal(sum(values), 6);
  assert.deepEqual(values, [1, 2, 3]);
});

test("parsePort accepts the complete valid boundary", () => {
  assert.equal(parsePort("1"), 1);
  assert.equal(parsePort(65535), 65535);
});

test("parsePort rejects malformed and out-of-range input", () => {
  for (const value of [undefined, null, "", "12.5", 0, 65536, Number.NaN]) {
    assert.throws(() => parsePort(value));
  }
});
