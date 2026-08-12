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
  // [Implementation 4] balance, completion, clock, executor, lock과 close state의 ownership을 모읍니다.
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

  // [Implementation 7] ID별 dedup·conflict와 bounded admission을 원자적으로 연결합니다.
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

  // [Implementation 5-1] balance invariant를 소유한 같은 lock 아래에서 잔액을 관찰합니다.
  public long currentBalance() {
    balanceLock.lock();
    try {
      return balance;
    } finally {
      balanceLock.unlock();
    }
  }

  // [Implementation 5-2] balance와 짝을 이루는 적용 횟수도 같은 lock 아래에서 읽습니다.
  public long appliedJobCount() {
    balanceLock.lock();
    try {
      return appliedJobCount;
    } finally {
      balanceLock.unlock();
    }
  }

  // [Implementation 8] close를 idempotent하게 만들고 graceful·forced·interrupted 전이를 처리합니다.
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

  // [Implementation 6-1] executor의 성공과 실패를 모든 duplicate caller가 공유할 Future로 번역합니다.
  private void execute(JobSlot slot) {
    try {
      slot.result().complete(apply(slot.command()));
    } catch (RuntimeException exception) {
      slot.result().completeExceptionally(exception);
    }
  }

  // [Implementation 5] 다음 balance와 count를 먼저 계산한 뒤 두 state를 한 번에 commit합니다.
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

  // [Implementation 8-1] 승인됐지만 시작하지 못한 작업의 Future를 terminal cancellation로 만듭니다.
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

  // [Implementation 6] command와 shared completion identity를 한 immutable slot으로 묶습니다.
  private record JobSlot(JobCommand command, CompletableFuture<JobReceipt> result) {}
}
