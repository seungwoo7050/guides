import { expect, it } from "vitest";
import { reduceCounter } from "./counter";
it("increments deterministically", () => { expect(reduceCounter(2, { type: "increment" })).toBe(3); });
it("decrements without crossing zero", () => {
  expect(reduceCounter(2, { type: "decrement" })).toBe(1);
  expect(reduceCounter(0, { type: "decrement" })).toBe(0);
});
it("resets", () => { expect(reduceCounter(2, { type: "reset" })).toBe(0); });
