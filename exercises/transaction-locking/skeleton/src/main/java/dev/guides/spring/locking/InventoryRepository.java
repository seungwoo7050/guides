
package dev.guides.spring.locking;

import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface InventoryRepository extends JpaRepository<InventoryItem, UUID> {
  default Optional<InventoryItem> findByIdForUpdate(UUID id) { return findById(id); }
}
