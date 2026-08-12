package dev.guides.java.stateeffect;

import java.util.ArrayList;
import java.util.List;

public final class StateStore {
  private final List<Change> changes = new ArrayList<>();

  // [Implementation 2] state change evidence의 단일 owner가 append 순서를 보존합니다.
  public void append(String operationId, long delta) {
    changes.add(new Change(operationId, delta));
  }

  // [Implementation 2-1] 내부 collection을 노출하지 않고 snapshot과 aggregate evidence를 제공합니다.
  public List<Change> changes() {
    return List.copyOf(changes);
  }

  public long netChange() {
    return changes.stream().mapToLong(Change::delta).sum();
  }

  public record Change(String operationId, long delta) {}
}
