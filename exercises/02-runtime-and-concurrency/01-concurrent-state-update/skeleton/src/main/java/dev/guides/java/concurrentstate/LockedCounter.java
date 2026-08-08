package dev.guides.java.concurrentstate;

public final class LockedCounter {
  private long value;

  public LockedCounter(long initialValue) {
    this.value = initialValue;
  }

  public boolean trySubtract(long delta) {
    // TODO: 잔액 확인과 변경을 하나의 잠금 경계로 묶습니다.
    value -= delta;
    return true;
  }

  public long value() {
    return value;
  }
}
