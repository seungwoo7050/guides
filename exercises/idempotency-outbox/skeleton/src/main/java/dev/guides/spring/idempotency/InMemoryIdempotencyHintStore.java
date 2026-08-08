package dev.guides.spring.idempotency;

import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Component;

@Component
public class InMemoryIdempotencyHintStore implements IdempotencyHintStore {
  private final ConcurrentHashMap<String, OperationResult> values = new ConcurrentHashMap<>();

  @Override
  public Optional<OperationResult> get(String key) {
    return Optional.ofNullable(values.get(key));
  }

  @Override
  public void put(String key, OperationResult result) {
    values.put(key, result);
  }
}
