package dev.guides.java.stateeffect;

import java.util.ArrayList;
import java.util.List;

public final class ExternalEffect {
  private final List<Call> calls = new ArrayList<>();

  public void send(String operationId, long delta) {
    calls.add(new Call(operationId, delta));
  }

  public List<Call> calls() {
    return List.copyOf(calls);
  }

  public record Call(String operationId, long delta) {}
}
