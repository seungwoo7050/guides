package dev.guides.java.concurrentstate;

import java.util.concurrent.CyclicBarrier;
import java.util.concurrent.TimeUnit;

public final class RacyCounter {
  private long value;

  public RacyCounter(long initialValue) {
    this.value = initialValue;
  }

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

  private static void await(CyclicBarrier barrier) {
    try {
      barrier.await(2, TimeUnit.SECONDS);
    } catch (Exception exception) {
      throw new IllegalStateException("배리어 대기가 실패했습니다.", exception);
    }
  }
}
