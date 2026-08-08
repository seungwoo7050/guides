import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const budget = JSON.parse(
  readFileSync(new URL("../../performance-budget.json", import.meta.url), "utf8")
) as Record<string, unknown>;

describe("Stage 04: 성능 예산 계약", () => {
  it("측정 가능한 양의 예산만 공개합니다", () => {
    expect(Object.keys(budget).sort()).toEqual([
      "maximumDomNodes",
      "maximumInitialJavaScriptBytes"
    ]);
    expect(budget.maximumInitialJavaScriptBytes).toBe(800_000);
    expect(budget.maximumDomNodes).toBe(180);
  });
});
