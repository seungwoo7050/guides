package dev.guides.java.concurrentstate;

import java.util.concurrent.locks.ReentrantLock;

public final class LockedCounter {
  private final ReentrantLock lock = new ReentrantLock();
  private long value;

  public LockedCounter(long initialValue) {
    this.value = initialValue;
  }

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

  public long value() {
    lock.lock();
    try {
      return value;
    } finally {
      lock.unlock();
    }
  }
}
