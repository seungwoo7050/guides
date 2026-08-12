package dev.guides.java.concurrentstate;

import java.util.List;
import java.util.concurrent.CyclicBarrier;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

public final class DeterministicRaceDemo {
  private DeterministicRaceDemo() {}

  // [Implementation 2] 재현, Future 실패 전달, 보존 법칙 evidence와 executor 정리를 조립합니다.
  public static void main(String[] args) throws Exception {
    RacyCounter counter = new RacyCounter(100);
    CyclicBarrier barrier = new CyclicBarrier(2);
    var executor = Executors.newFixedThreadPool(2);
    try {
      List<Future<Boolean>> results =
          List.of(
              executor.submit(() -> counter.trySubtract(80, barrier)),
              executor.submit(() -> counter.trySubtract(80, barrier)));
      long accepted = 0;
      for (Future<Boolean> result : results) {
        if (result.get(2, TimeUnit.SECONDS)) accepted += 80;
      }
      System.out.printf(
          "accepted=%d value=%d invariant=%s%n",
          accepted, counter.value(), accepted + counter.value() == 100);
    } finally {
      executor.shutdownNow();
      if (!executor.awaitTermination(2, TimeUnit.SECONDS)) {
        throw new IllegalStateException("실행기가 종료되지 않았습니다.");
      }
    }
  }
}
