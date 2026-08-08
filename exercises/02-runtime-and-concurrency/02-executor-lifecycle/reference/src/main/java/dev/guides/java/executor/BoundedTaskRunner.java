package dev.guides.java.executor;

import java.time.Duration;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Future;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicInteger;

public final class BoundedTaskRunner implements AutoCloseable {
  private final ThreadPoolExecutor executor;
  private final Duration shutdownTimeout;

  public BoundedTaskRunner(int workers, int queueCapacity, Duration shutdownTimeout) {
    if (workers < 1) {
      throw new IllegalArgumentException("작업자 수는 1 이상이어야 합니다.");
    }
    if (queueCapacity < 1) {
      throw new IllegalArgumentException("대기열 크기는 1 이상이어야 합니다.");
    }
    this.shutdownTimeout = Objects.requireNonNull(shutdownTimeout);
    if (shutdownTimeout.isNegative()) {
      throw new IllegalArgumentException("종료 제한 시간은 음수일 수 없습니다.");
    }
    AtomicInteger sequence = new AtomicInteger();
    executor =
        new ThreadPoolExecutor(
            workers,
            workers,
            0L,
            TimeUnit.MILLISECONDS,
            new ArrayBlockingQueue<>(queueCapacity),
            runnable -> {
              Thread thread = new Thread(runnable, "bounded-task-" + sequence.incrementAndGet());
              thread.setDaemon(false);
              return thread;
            },
            new ThreadPoolExecutor.AbortPolicy());
  }

  public <T> Future<T> submit(Callable<T> task) throws RejectedExecutionException {
    return executor.submit(Objects.requireNonNull(task));
  }

  public <T> T run(Callable<T> task, Duration timeout)
      throws InterruptedException, ExecutionException, TimeoutException {
    Objects.requireNonNull(timeout, "작업 제한 시간이 필요합니다.");
    if (timeout.isNegative()) {
      throw new IllegalArgumentException("작업 제한 시간은 음수일 수 없습니다.");
    }
    Future<T> future = submit(task);
    try {
      return future.get(timeout.toNanos(), TimeUnit.NANOSECONDS);
    } catch (TimeoutException exception) {
      future.cancel(true);
      throw exception;
    }
  }

  @Override
  public void close() {
    executor.shutdown();
    boolean interrupted = false;
    try {
      if (!executor.awaitTermination(shutdownTimeout.toNanos(), TimeUnit.NANOSECONDS)) {
        cancelQueued(executor.shutdownNow());
        if (!executor.awaitTermination(shutdownTimeout.toNanos(), TimeUnit.NANOSECONDS)) {
          throw new IllegalStateException("실행기가 제한 시간 안에 종료되지 않았습니다.");
        }
      }
    } catch (InterruptedException exception) {
      interrupted = true;
      cancelQueued(executor.shutdownNow());
    } finally {
      if (interrupted) {
        Thread.currentThread().interrupt();
      }
    }
  }

  private static void cancelQueued(List<Runnable> queued) {
    for (Runnable task : queued) {
      if (task instanceof Future<?> future) {
        future.cancel(false);
      }
    }
  }
}
