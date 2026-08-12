package dev.guides.java.concurrentstate;

import java.util.concurrent.locks.ReentrantLock;

public final class LockedCounter {
  private final ReentrantLock lock = new ReentrantLock();
  private long value;

  public LockedCounter(long initialValue) {
    this.value = initialValue;
  }

  // [Implementation 3] lock이 read-decide-write 전체를 소유해 conservation invariant를 지킵니다.
  public boolean trySubtract(long delta) {
    lock.lock();
    try {
      if (value < delta) {
        return false;
      }
      value -= delta;
      return true;
    } finally {
      lock.unlock();
    }
  }

  // [Implementation 3-1] 관찰도 같은 lock을 거쳐 state ownership 밖의 race를 만들지 않습니다.
  public long value() {
    lock.lock();
    try {
      return value;
    } finally {
      lock.unlock();
    }
  }
}
