package dev.guides.java.concurrentstate;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import java.util.concurrent.CyclicBarrier;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.Test;

class CounterConcurrencyTest {
  @Test
  void deterministicRaceBreaksConservationInvariant() throws Exception {
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
      assertThat(accepted).isEqualTo(160);
      assertThat(counter.value()).isEqualTo(20);
      assertThat(accepted + counter.value()).isNotEqualTo(100);
    } finally {
      executor.shutdownNow();
      assertThat(executor.awaitTermination(2, TimeUnit.SECONDS)).isTrue();
    }
  }

  @Test
  void lockPreservesConservationInvariant() throws Exception {
    LockedCounter counter = new LockedCounter(100);
    var executor = Executors.newFixedThreadPool(2);
    try {
      List<Future<Boolean>> results =
          List.of(
              executor.submit(() -> counter.trySubtract(80)),
              executor.submit(() -> counter.trySubtract(80)));
      long accepted = 0;
      for (Future<Boolean> result : results) {
        if (result.get(2, TimeUnit.SECONDS)) accepted += 80;
      }
      assertThat(accepted).isEqualTo(80);
      assertThat(counter.value()).isEqualTo(20);
      assertThat(accepted + counter.value()).isEqualTo(100);
    } finally {
      executor.shutdownNow();
      assertThat(executor.awaitTermination(2, TimeUnit.SECONDS)).isTrue();
    }
  }
}
