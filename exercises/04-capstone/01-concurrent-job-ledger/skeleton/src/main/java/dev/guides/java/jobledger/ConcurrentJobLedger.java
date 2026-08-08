package dev.guides.java.jobledger;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.Objects;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

public final class ConcurrentJobLedger implements AutoCloseable {
  private final Clock clock;
  private final ExecutorService executor;
  private final AtomicBoolean closed = new AtomicBoolean();

  private long balance;
  private long appliedJobCount;

  public ConcurrentJobLedger(long initialBalance, int workerCount, int queueCapacity, Clock clock) {
    if (initialBalance < 0 || workerCount <= 0 || queueCapacity <= 0) {
      throw new IllegalArgumentException("생성 인자가 올바르지 않습니다.");
    }
    this.balance = initialBalance;
    this.clock = Objects.requireNonNull(clock, "Clock이 필요합니다.");
    // TODO: 작업자 수와 대기열 용량이 모두 제한된 실행기를 사용합니다.
    this.executor = Executors.newFixedThreadPool(workerCount);
  }

  public CompletableFuture<JobReceipt> submit(JobCommand command) {
    Objects.requireNonNull(command, "작업 명령이 필요합니다.");
    if (closed.get()) {
      throw new IllegalStateException("종료된 원장에는 작업을 제출할 수 없습니다.");
    }
    // TODO: 작업 식별자별 결과 공유와 원자적 상태 변경을 구현합니다.
    return CompletableFuture.supplyAsync(() -> apply(command), executor);
  }

  public long currentBalance() {
    return balance;
  }

  public long appliedJobCount() {
    return appliedJobCount;
  }

  public void close(Duration timeout) {
    Objects.requireNonNull(timeout, "종료 제한 시간이 필요합니다.");
    closed.set(true);
    executor.shutdownNow();
  }

  @Override
  public void close() {
    close(Duration.ofSeconds(5));
  }

  private JobReceipt apply(JobCommand command) {
    Instant completedAt = clock.instant();
    JobKind kind;
    if (command instanceof CreditJob credit) {
      kind = JobKind.CREDIT;
      balance += credit.amount();
    } else if (command instanceof DebitJob debit) {
      kind = JobKind.DEBIT;
      balance -= debit.amount();
    } else {
      throw new IllegalStateException("지원하지 않는 작업 명령입니다.");
    }
    appliedJobCount += 1;
    return new JobReceipt(command.id(), kind, command.amount(), balance, completedAt);
  }
}
