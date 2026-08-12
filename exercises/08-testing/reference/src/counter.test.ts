import { expect, it } from "vitest";
import { reduceCounter } from "./counter";
// [Implementation 2] 순수 함수의 0 경계는 가장 작은 unit test에서 deterministic하게 증명합니다.
it("increments deterministically", () => { expect(reduceCounter(2, { type: "increment" })).toBe(3); });
it("decrements without crossing zero", () => {
  expect(reduceCounter(2, { type: "decrement" })).toBe(1);
  expect(reduceCounter(0, { type: "decrement" })).toBe(0);
});
it("resets", () => { expect(reduceCounter(2, { type: "reset" })).toBe(0); });
