package dev.guides.java.valueobject;

import java.util.Objects;

public record Money(long minor, Currency currency) {
  public Money {
    if (minor < 0) {
      throw new IllegalArgumentException("금액은 음수일 수 없습니다.");
    }
    Objects.requireNonNull(currency, "통화가 필요합니다.");
  }

  public Money add(Money other) {
    requireSameCurrency(other);
    return new Money(Math.addExact(minor, other.minor), currency);
  }

  public Money subtract(Money other) {
    requireSameCurrency(other);
    long result = Math.subtractExact(minor, other.minor);
    if (result < 0) {
      throw new IllegalArgumentException("연산 결과는 음수일 수 없습니다.");
    }
    return new Money(result, currency);
  }

  private void requireSameCurrency(Money other) {
    Objects.requireNonNull(other, "비교할 금액이 필요합니다.");
    if (currency != other.currency) {
      throw new IllegalArgumentException("통화가 서로 다릅니다.");
    }
  }
}
