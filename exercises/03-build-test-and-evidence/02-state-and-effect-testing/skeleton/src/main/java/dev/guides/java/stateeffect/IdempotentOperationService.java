package dev.guides.java.stateeffect;

import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

public final class IdempotentOperationService {
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

  public synchronized OperationResult apply(String key, long delta) {
    OperationResult existing = results.get(key);
    if (existing != null) {
      // TODO: 중복 호출은 새 식별자가 아니라 기존 완료 결과를 그대로 공유해야 합니다.
      return new OperationResult(UUID.randomUUID().toString(), existing.currentValue());
    }
    if (delta <= 0) {
      throw new IllegalArgumentException("변경량은 0보다 커야 합니다.");
    }
    if (currentValue < delta) {
      throw new IllegalArgumentException("현재 값보다 큰 변경량입니다.");
    }

    currentValue -= delta;
    String operationId = UUID.nameUUIDFromBytes(key.getBytes(StandardCharsets.UTF_8)).toString();
    stateStore.append(operationId, -delta);
    effect.send(operationId, -delta);
    OperationResult created = new OperationResult(operationId, currentValue);
    results.put(key, created);
    return created;
  }

  public long currentValue() {
    return currentValue;
  }
}
