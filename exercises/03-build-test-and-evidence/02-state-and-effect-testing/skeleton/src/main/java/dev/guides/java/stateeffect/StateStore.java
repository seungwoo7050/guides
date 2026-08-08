package dev.guides.java.stateeffect;

import java.util.ArrayList;
import java.util.List;

public final class StateStore {
  private final List<Change> changes = new ArrayList<>();

  public void append(String operationId, long delta) {
    changes.add(new Change(operationId, delta));
  }

  public List<Change> changes() {
    return List.copyOf(changes);
  }

  public long netChange() {
    return changes.stream().mapToLong(Change::delta).sum();
  }

  public record Change(String operationId, long delta) {}
}
