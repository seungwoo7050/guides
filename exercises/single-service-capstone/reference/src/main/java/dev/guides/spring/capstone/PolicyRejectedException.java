package dev.guides.spring.capstone;

public final class PolicyRejectedException extends RuntimeException {
  public PolicyRejectedException() {
    super("외부 정책이 publication 생성을 거절했습니다.");
  }
}
