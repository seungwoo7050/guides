package dev.guides.java.stateeffect;

import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

public final class IdempotentOperationService {
  // [Implementation 4] 현재 state, collaborator와 key별 completion registry의 ownership을 모읍니다.
  private final Map<String, OperationResult> results = new HashMap<>();
  private final StateStore stateStore;
  private final ExternalEffect effect;
  private long currentValue;

  public IdempotentOperationService(
      long initialValue, StateStore stateStore, ExternalEffect effect) {
    this.currentValue = initialValue;
    this.stateStore = stateStore;
    this.effect = effect;
  }

  // [Implementation 5] 기존 completion을 effect보다 먼저 찾아 repeated key의 transition을 공유합니다.
  public synchronized OperationResult apply(String key, long delta) {
    OperationResult existing = results.get(key);
    if (existing != null) {
      return existing;
    }
    if (delta <= 0) {
      throw new IllegalArgumentException("변경량은 0보다 커야 합니다.");
    }
    if (currentValue < delta) {
      throw new IllegalArgumentException("현재 값보다 큰 변경량입니다.");
    }

    // [Implementation 5-1] state, effect와 completion publication 순서를 한 synchronized 경계에 둡니다.
    currentValue -= delta;
    String operationId = UUID.nameUUIDFromBytes(key.getBytes(StandardCharsets.UTF_8)).toString();
    stateStore.append(operationId, -delta);
    effect.send(operationId, -delta);
    OperationResult created = new OperationResult(operationId, currentValue);
    results.put(key, created);
    return created;
  }

  // [Implementation 5-2] mutation 권한을 노출하지 않고 현재 state evidence를 제공합니다.
  public long currentValue() {
    return currentValue;
  }
}
