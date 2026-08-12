export type CoordinatedRequest = {
  generation: number;
  signal: AbortSignal;
};

export type RequestCoordinator = {
  begin(): CoordinatedRequest;
  isCurrent(generation: number): boolean;
  cancel(): void;
};

// [Implementation 4] abort는 transport에 알리고 monotonic generation은 이미 늦어진 응답의 state commit까지 차단한다.
export function createRequestCoordinator(): RequestCoordinator {
  let generation = 0;
  let controller: AbortController | null = null;

  return {
    begin() {
      controller?.abort();
      controller = new AbortController();
      generation += 1;
      return { generation, signal: controller.signal };
    },
    isCurrent(candidate) {
      return candidate === generation;
    },
    cancel() {
      controller?.abort();
      controller = null;
      generation += 1;
    }
  };
}
