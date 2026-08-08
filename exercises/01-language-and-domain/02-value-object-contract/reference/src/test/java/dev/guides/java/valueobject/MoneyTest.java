package dev.guides.java.valueobject;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class MoneyTest {
  @Test
  void rejectsNegativeAmount() {
    assertThatThrownBy(() -> new Money(-1, Currency.KRW))
        .isInstanceOf(IllegalArgumentException.class);
  }

  @Test
  void rejectsNullCurrencyAndNullOperands() {
    assertThatThrownBy(() -> new Money(1, null)).isInstanceOf(NullPointerException.class);
    Money money = new Money(1, Currency.KRW);
    assertThatThrownBy(() -> money.add(null)).isInstanceOf(NullPointerException.class);
    assertThatThrownBy(() -> money.subtract(null)).isInstanceOf(NullPointerException.class);
  }

  @Test
  void addsSameCurrency() {
    assertThat(new Money(100, Currency.KRW).add(new Money(20, Currency.KRW)))
        .isEqualTo(new Money(120, Currency.KRW));
  }

  @Test
  void rejectsCurrencyMismatch() {
    assertThatThrownBy(() -> new Money(100, Currency.KRW).add(new Money(20, Currency.USD)))
        .isInstanceOf(IllegalArgumentException.class);
  }

  @Test
  void rejectsOverflow() {
    assertThatThrownBy(
            () -> new Money(Long.MAX_VALUE, Currency.KRW).add(new Money(1, Currency.KRW)))
        .isInstanceOf(ArithmeticException.class);
  }

  @Test
  void rejectsNegativeSubtractionResult() {
    assertThatThrownBy(() -> new Money(10, Currency.KRW).subtract(new Money(11, Currency.KRW)))
        .isInstanceOf(IllegalArgumentException.class);
  }
}
