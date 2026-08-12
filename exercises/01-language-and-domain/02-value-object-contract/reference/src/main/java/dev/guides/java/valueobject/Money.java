package dev.guides.java.valueobject;

import java.util.Objects;

public record Money(long minor, Currency currency) {
  // [Implementation 2] 유효하지 않은 금액과 통화는 Money instance가 생기기 전에 거절합니다.
  public Money {
    if (minor < 0) {
      throw new IllegalArgumentException("금액은 음수일 수 없습니다.");
    }
    Objects.requireNonNull(currency, "통화가 필요합니다.");
  }

  // [Implementation 4] 통화 확인과 checked addition 뒤 원본을 바꾸지 않는 새 값을 만듭니다.
  public Money add(Money other) {
    requireSameCurrency(other);
    return new Money(Math.addExact(minor, other.minor), currency);
  }

  // [Implementation 5] checked subtraction과 음수 결과 거절을 같은 value boundary에 둡니다.
  public Money subtract(Money other) {
    requireSameCurrency(other);
    long result = Math.subtractExact(minor, other.minor);
    if (result < 0) {
      throw new IllegalArgumentException("연산 결과는 음수일 수 없습니다.");
    }
    return new Money(result, currency);
  }

  // [Implementation 3] operand ownership과 통화 호환성 검사를 한 공통 경계가 소유합니다.
  private void requireSameCurrency(Money other) {
    Objects.requireNonNull(other, "비교할 금액이 필요합니다.");
    if (currency != other.currency) {
      throw new IllegalArgumentException("통화가 서로 다릅니다.");
    }
  }
}
