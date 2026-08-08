package dev.guides.java.valueobject;

public record Money(long minor, Currency currency) {
  public Money add(Money other) {
    return new Money(minor + other.minor, currency);
  }

  public Money subtract(Money other) {
    return new Money(minor - other.minor, currency);
  }
}
