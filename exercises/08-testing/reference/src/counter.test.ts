import { expect, it } from "vitest";
import { reduceCounter } from "./counter";
it("increments deterministically", () => { expect(reduceCounter(2, { type: "increment" })).toBe(3); });
it("resets", () => { expect(reduceCounter(2, { type: "reset" })).toBe(0); });
