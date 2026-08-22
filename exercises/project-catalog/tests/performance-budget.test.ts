import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const budget = JSON.parse(
  readFileSync(join(process.cwd(), "performance-budget.json"), "utf8")
) as Record<string, unknown>;

// [Implementation 14-7]
// Performance-budget verification.
describe("performance budget", () => {
  it("publishes only measurable positive limits", () => {
    expect(Object.keys(budget).sort()).toEqual([
      "maximumDomNodes",
      "maximumInitialJavaScriptBytes"
    ]);
    expect(budget.maximumInitialJavaScriptBytes).toBe(800_000);
    expect(budget.maximumDomNodes).toBe(180);
  });
});
