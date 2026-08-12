package dev.guides.java.executor;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

public final class ExecutorProbe {
  private ExecutorProbe() {}

  // [Implementation 5] bounded workload를 조립하고 try-with-resources로 runner lifetime을 닫습니다.
  public static void main(String[] arguments) throws Exception {
    List<Future<Long>> results = new ArrayList<>();
    try (BoundedTaskRunner runner = new BoundedTaskRunner(2, 8, Duration.ofSeconds(2))) {
      for (int task = 0; task < 8; task++) {
        int seed = task;
        results.add(runner.submit(() -> checksum(seed)));
      }
      long checksum = 0;
      for (Future<Long> result : results) {
        checksum ^= result.get(2, TimeUnit.SECONDS);
      }
      System.out.printf("완료한 작업=%d 체크섬=%d%n", results.size(), checksum);
    }
  }

  private static long checksum(int seed) {
    long value = seed + 1L;
    for (int index = 0; index < 100_000; index++) {
      value = value * 1_664_525L + 1_013_904_223L;
    }
    return value;
  }
}
