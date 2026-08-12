
package dev.guides.spring.locking;

import jakarta.persistence.LockModeType;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface InventoryRepository extends JpaRepository<InventoryItem, UUID> {
  // [Implementation 4] 같은 inventory row를 write lock으로 읽어 동시 mutation을 직렬화한다.
  @Lock(LockModeType.PESSIMISTIC_WRITE)
  @Query("select item from InventoryItem item where item.id = :id")
  Optional<InventoryItem> findByIdForUpdate(@Param("id") UUID id);
}
