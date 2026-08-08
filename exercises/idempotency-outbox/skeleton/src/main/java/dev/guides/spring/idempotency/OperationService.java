package dev.guides.spring.idempotency;

import jakarta.persistence.EntityManager;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

@Service
public class OperationService {
  private final EntityManager entityManager;
  private final OperationRepository operations;
  private final OutboxRepository outbox;
  private final IdempotencyHintStore hints;

  public OperationService(
      EntityManager entityManager,
      OperationRepository operations,
      OutboxRepository outbox,
      IdempotencyHintStore hints) {
    this.entityManager = entityManager;
    this.operations = operations;
    this.outbox = outbox;
    this.hints = hints;
  }

  @Transactional
  public OperationResult apply(String key, long quantity) {
    if (key == null || key.isBlank()) throw new IllegalArgumentException("멱등성 키가 필요합니다.");
    if (quantity <= 0) throw new IllegalArgumentException("수량은 0보다 커야 합니다.");

    Optional<OperationResult> hinted = safeGet(key);
    if (hinted.isPresent()) return hinted.get();

    Optional<OperationRecord> existing = operations.findByIdempotencyKey(key);
    if (existing.isPresent()) {
      OperationResult result = existing.get().result();
      cacheAfterCommit(key, result);
      return result;
    }

    UUID operationId = UUID.nameUUIDFromBytes(key.getBytes(StandardCharsets.UTF_8));
    OperationResult result = new OperationResult(operationId, quantity);
    operations.save(new OperationRecord(operationId, key, quantity));
    outbox.save(new OutboxEvent(
        UUID.randomUUID(), operationId, "OperationApplied",
        "{\"operationId\":\"" + operationId + "\",\"quantity\":" + quantity + "}",
        Instant.now()));
    cacheAfterCommit(key, result);
    return result;
  }

  private Optional<OperationResult> safeGet(String key) {
    try {
      return hints.get(key);
    } catch (RuntimeException ignored) {
      return Optional.empty();
    }
  }

  private void cacheAfterCommit(String key, OperationResult result) {
    TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
      @Override
      public void afterCommit() {
        try {
          hints.put(key, result);
        } catch (RuntimeException ignored) {
          // 캐시는 조회를 돕는 힌트이며 데이터베이스가 결과의 정본입니다.
        }
      }
    });
  }
}
