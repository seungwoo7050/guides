package dev.guides.java.jobledger;

import java.util.Objects;

public record JobId(String value) {
  public JobId {
    Objects.requireNonNull(value, "작업 식별자가 필요합니다.");
    if (value.isBlank()) {
      throw new IllegalArgumentException("작업 식별자는 비어 있을 수 없습니다.");
    }
  }
}
