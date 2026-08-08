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
  let controller = new AbortController();

  return {
    begin() {
      // TODO(stage-03): 이전 signal을 abort하고 새 generation을 만드세요.
      generation += 1;
      controller = new AbortController();
      return { generation, signal: controller.signal };
    },
    isCurrent() {
      // TODO(stage-03): 현재 generation만 허용하세요.
      return true;
    },
    cancel() {
      // TODO(stage-03): 현재 request를 abort하고 기존 generation을 무효화하세요.
    }
  };
}
