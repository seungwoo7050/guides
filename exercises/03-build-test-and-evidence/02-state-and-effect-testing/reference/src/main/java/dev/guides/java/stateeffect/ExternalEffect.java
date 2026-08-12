package dev.guides.java.stateeffect;

import java.util.ArrayList;
import java.util.List;

public final class ExternalEffect {
  private final List<Call> calls = new ArrayList<>();

  // [Implementation 3] 외부 effect를 state store와 독립된 evidence channel에 기록합니다.
  public void send(String operationId, long delta) {
    calls.add(new Call(operationId, delta));
  }

  // [Implementation 3-1] caller가 기록 ownership을 얻지 않도록 snapshot만 반환합니다.
  public List<Call> calls() {
    return List.copyOf(calls);
  }

  public record Call(String operationId, long delta) {}
}
