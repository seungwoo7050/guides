import { describe, expect, it } from "vitest";

import { reduceCounter } from "./counter";

// [Implementation 2] Prove the pure transition and its zero boundary with the smallest deterministic verification layer.
describe("reduceCounter", () => {
  it("increments", () => {
    expect(reduceCounter(2, { type: "increment" })).toBe(3);
  });

  it("decrements without crossing zero", () => {
    expect(reduceCounter(2, { type: "decrement" })).toBe(1);
    expect(reduceCounter(0, { type: "decrement" })).toBe(0);
  });

  it("resets", () => {
    expect(reduceCounter(2, { type: "reset" })).toBe(0);
  });

  it("rejects an invalid initial state and overflow", () => {
    expect(() => reduceCounter(-1, { type: "increment" })).toThrow(/non-negative/);
    expect(() => reduceCounter(Number.MAX_SAFE_INTEGER, { type: "increment" })).toThrow(/overflow/);
  });
});
