
package dev.guides.spring.locking;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.util.UUID;

// [Implementation 3] aggregate가 가용 수량 state와 차감 불변식을 함께 소유한다.
@Entity
@Table(name = "inventory_item")
public class InventoryItem {
  @Id private UUID id;

  @Column(nullable = false)
  private long availableQuantity;

  protected InventoryItem() {}

  public InventoryItem(UUID id, long availableQuantity) {
    if (availableQuantity < 0) {
      throw new IllegalArgumentException("가용 수량은 음수가 될 수 없습니다.");
    }
    this.id = id;
    this.availableQuantity = availableQuantity;
  }

  public UUID id() { return id; }
  public long availableQuantity() { return availableQuantity; }

  public boolean reserve(long quantity) {
    if (quantity <= 0) throw new IllegalArgumentException("예약 수량은 0보다 커야 합니다.");
    if (availableQuantity < quantity) return false;
    availableQuantity -= quantity;
    return true;
  }
}
