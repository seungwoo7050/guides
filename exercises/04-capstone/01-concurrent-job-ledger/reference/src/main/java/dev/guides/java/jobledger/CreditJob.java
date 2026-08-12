package dev.guides.java.jobledger;

import java.util.Objects;

// [Implementation 2-1] credit command가 유효한 identity와 양수 금액으로만 생성되게 합니다.
public record CreditJob(JobId id, long amount) implements JobCommand {
  public CreditJob {
    Objects.requireNonNull(id, "작업 식별자가 필요합니다.");
    if (amount <= 0) {
      throw new IllegalArgumentException("크레딧 금액은 양수여야 합니다.");
    }
  }
}
