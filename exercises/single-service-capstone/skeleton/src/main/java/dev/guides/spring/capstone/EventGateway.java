package dev.guides.spring.capstone;

import java.util.UUID;

public interface EventGateway {
  void publish(UUID eventId, UUID aggregateId, String eventType, String payload);
}
