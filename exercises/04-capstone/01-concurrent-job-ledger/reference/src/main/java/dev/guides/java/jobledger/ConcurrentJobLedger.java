package dev.guides.java.jobledger;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.locks.ReentrantLock;

public final class ConcurrentJobLedger implements AutoCloseable {
  private static final Duration DEFAULT_CLOSE_TIMEOUT = Duration.ofSeconds(5);

  private final Clock clock;
  private final ThreadPoolExecutor executor;
  private final ConcurrentHashMap<JobId, JobSlot> jobs = new ConcurrentHashMap<>();
  private final ReentrantLock balanceLock = new ReentrantLock();
  private final AtomicBoolean closed = new AtomicBoolean();

  private long balance;
  private long appliedJobCount;

  public ConcurrentJobLedger(long initialBalance, int workerCount, int queueCapacity, Clock clock) {
    if (initialBalance < 0) {
      throw new IllegalArgumentException("초기 잔액은 음수일 수 없습니다.");
    }
    if (workerCount <= 0) {
      throw new IllegalArgumentException("작업자 수는 양수여야 합니다.");
    }
    if (queueCapacity <= 0) {
      throw new IllegalArgumentException("대기열 용량은 양수여야 합니다.");
    }
    this.balance = initialBalance;
    this.clock = Objects.requireNonNull(clock, "Clock이 필요합니다.");
    this.executor =
        new ThreadPoolExecutor(
            workerCount,
            workerCount,
            0L,
            TimeUnit.MILLISECONDS,
            new ArrayBlockingQueue<>(queueCapacity),
            new ThreadPoolExecutor.AbortPolicy());
  }

  public CompletableFuture<JobReceipt> submit(JobCommand command) {
    Objects.requireNonNull(command, "작업 명령이 필요합니다.");
    if (closed.get()) {
      throw new IllegalStateException("종료된 원장에는 작업을 제출할 수 없습니다.");
    }

    AtomicBoolean created = new AtomicBoolean();
    JobSlot slot =
        jobs.compute(
            command.id(),
            (id, existing) -> {
              if (existing == null) {
                created.set(true);
                return new JobSlot(command, new CompletableFuture<>());
              }
              if (!existing.command().equals(command)) {
                throw new IllegalArgumentException("같은 작업 식별자에 다른 명령을 사용할 수 없습니다: " + id.value());
              }
              return existing;
            });

    if (created.get()) {
      try {
        executor.execute(new JobTask(slot));
      } catch (RejectedExecutionException exception) {
        jobs.remove(command.id(), slot);
        slot.result().completeExceptionally(exception);
        throw exception;
      }
    }
    return slot.result();
  }

  public long currentBalance() {
    balanceLock.lock();
    try {
      return balance;
    } finally {
      balanceLock.unlock();
    }
  }

  public long appliedJobCount() {
    balanceLock.lock();
    try {
      return appliedJobCount;
    } finally {
      balanceLock.unlock();
    }
  }

  public void close(Duration timeout) {
    Objects.requireNonNull(timeout, "종료 제한 시간이 필요합니다.");
    if (timeout.isNegative()) {
      throw new IllegalArgumentException("종료 제한 시간은 음수일 수 없습니다.");
    }
    if (!closed.compareAndSet(false, true)) {
      return;
    }

    executor.shutdown();
    long timeoutNanos = timeout.toNanos();
    try {
      if (!executor.awaitTermination(timeoutNanos, TimeUnit.NANOSECONDS)) {
        cancelQueued(executor.shutdownNow());
        if (!executor.awaitTermination(timeoutNanos, TimeUnit.NANOSECONDS)) {
          throw new IllegalStateException("실행기가 제한 시간 안에 종료되지 않았습니다.");
        }
      }
    } catch (InterruptedException exception) {
      cancelQueued(executor.shutdownNow());
      Thread.currentThread().interrupt();
      throw new IllegalStateException("실행기 종료 대기가 중단되었습니다.", exception);
    }
  }

  @Override
  public void close() {
    close(DEFAULT_CLOSE_TIMEOUT);
  }

  private void execute(JobSlot slot) {
    try {
      slot.result().complete(apply(slot.command()));
    } catch (RuntimeException exception) {
      slot.result().completeExceptionally(exception);
    }
  }

  private JobReceipt apply(JobCommand command) {
    Instant completedAt = clock.instant();
    balanceLock.lock();
    try {
      JobKind kind;
      long nextBalance;
      if (command instanceof CreditJob credit) {
        kind = JobKind.CREDIT;
        nextBalance = Math.addExact(balance, credit.amount());
      } else if (command instanceof DebitJob debit) {
        kind = JobKind.DEBIT;
        if (debit.amount() > balance) {
          throw new IllegalStateException("잔액이 부족합니다.");
        }
        nextBalance = Math.subtractExact(balance, debit.amount());
      } else {
        throw new IllegalStateException("지원하지 않는 작업 명령입니다.");
      }

      long nextAppliedJobCount = Math.addExact(appliedJobCount, 1L);
      balance = nextBalance;
      appliedJobCount = nextAppliedJobCount;
      return new JobReceipt(command.id(), kind, command.amount(), nextBalance, completedAt);
    } finally {
      balanceLock.unlock();
    }
  }

  private static void cancelQueued(List<Runnable> queued) {
    for (Runnable task : queued) {
      if (task instanceof JobTask jobTask) {
        jobTask.slot.result().cancel(false);
      }
    }
  }

  private final class JobTask implements Runnable {
    private final JobSlot slot;

    private JobTask(JobSlot slot) {
      this.slot = slot;
    }

    @Override
    public void run() {
      execute(slot);
    }
  }

  private record JobSlot(JobCommand command, CompletableFuture<JobReceipt> result) {}
}
