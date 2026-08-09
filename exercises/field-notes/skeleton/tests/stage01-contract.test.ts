import { evaluateStage01Contract } from "@field-notes/shared/testkit";
import { stage01Navigation } from "../src/navigation/stage01";

describe("Stage 01 learner contract", () => {
  it("normalizes routes, duplicate intent identity, and dirty back behavior", () => {
    // This assertion intentionally fails in the starting skeleton. Make it pass
    // by implementing behavior; do not replace the expected empty list.
    expect(evaluateStage01Contract(stage01Navigation)).toEqual([]);
  });
});

