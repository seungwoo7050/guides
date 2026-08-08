import { describe, expect, it } from "vitest";
import { createRequestCoordinator } from "../../lib/request-coordinator";

describe("Stage 03: request coordinator", () => {
  it("새 요청이 이전 signal을 중단하고 generation을 교체합니다", () => {
    const coordinator = createRequestCoordinator();
    const first = coordinator.begin();
    const second = coordinator.begin();

    expect(first.signal.aborted).toBe(true);
    expect(second.signal.aborted).toBe(false);
    expect(coordinator.isCurrent(first.generation)).toBe(false);
    expect(coordinator.isCurrent(second.generation)).toBe(true);
  });

  it("cancel 뒤 도착한 결과를 current로 보지 않습니다", () => {
    const coordinator = createRequestCoordinator();
    const request = coordinator.begin();
    coordinator.cancel();

    expect(request.signal.aborted).toBe(true);
    expect(coordinator.isCurrent(request.generation)).toBe(false);
  });
});
