package dev.guides.java.concurrentstate;

import java.util.concurrent.CyclicBarrier;
import java.util.concurrent.TimeUnit;

public final class RacyCounter {
  private long value;

  public RacyCounter(long initialValue) {
    this.value = initialValue;
  }

  // [Implementation 1] 의도적으로 read-decide-write를 나눠 손실 갱신의 failure state를 드러냅니다.
  public boolean trySubtract(long delta, CyclicBarrier afterRead) {
    long observed = value;
    if (observed < delta) {
      return false;
    }
    await(afterRead);
    value = observed - delta;
    return true;
  }

  public long value() {
    return value;
  }

  // [Implementation 1-1] sleep 대신 barrier가 재현할 interleaving과 최대 대기 시간을 소유합니다.
  private static void await(CyclicBarrier barrier) {
    try {
      barrier.await(2, TimeUnit.SECONDS);
    } catch (Exception exception) {
      throw new IllegalStateException("배리어 대기가 실패했습니다.", exception);
    }
  }
}
