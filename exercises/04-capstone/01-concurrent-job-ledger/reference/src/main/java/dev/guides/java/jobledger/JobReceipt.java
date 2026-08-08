package dev.guides.java.jobledger;

import java.time.Instant;
import java.util.Objects;

public record JobReceipt(JobId id, JobKind kind, long amount, long balance, Instant completedAt) {
  public JobReceipt {
    Objects.requireNonNull(id, "작업 식별자가 필요합니다.");
    Objects.requireNonNull(kind, "작업 종류가 필요합니다.");
    Objects.requireNonNull(completedAt, "완료 시각이 필요합니다.");
  }
}
