package dev.guides.java.executor;

import java.time.Duration;
import java.util.concurrent.Callable;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

public final class BoundedTaskRunner implements AutoCloseable {
  private final ThreadPoolExecutor executor;

  public BoundedTaskRunner(int workers, int queueCapacity, Duration shutdownTimeout) {
    executor = (ThreadPoolExecutor) Executors.newFixedThreadPool(workers);
  }

  public <T> Future<T> submit(Callable<T> task) {
    return executor.submit(task);
  }

  public <T> T run(Callable<T> task, Duration timeout) throws Exception {
    // TODO: 제한 시간 뒤에는 Future를 인터럽트 취소해야 합니다.
    return submit(task).get(timeout.toNanos(), TimeUnit.NANOSECONDS);
  }

  @Override
  public void close() {
    executor.shutdownNow();
  }
}
