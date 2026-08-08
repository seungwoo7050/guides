export type CoordinatedRequest = {
  generation: number;
  signal: AbortSignal;
};

export type RequestCoordinator = {
  begin(): CoordinatedRequest;
  isCurrent(generation: number): boolean;
  cancel(): void;
};

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
