package dev.guides.spring.idempotency;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.util.UUID;

// [Implementation 2] PostgreSQL row가 멱등 처리 완료 결과의 정본을 소유한다.
@Entity
@Table(name = "operation_record")
public class OperationRecord {
  @Id private UUID id;

  @Column(name = "idempotency_key", nullable = false, unique = true)
  private String idempotencyKey;

  @Column(nullable = false)
  private long quantity;

  protected OperationRecord() {}

  public OperationRecord(UUID id, String idempotencyKey, long quantity) {
    this.id = id;
    this.idempotencyKey = idempotencyKey;
    this.quantity = quantity;
  }

  public OperationResult result() {
    return new OperationResult(id, quantity);
  }
}
