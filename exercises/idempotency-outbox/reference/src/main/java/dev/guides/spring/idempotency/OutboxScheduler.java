package dev.guides.spring.idempotency;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(
    name = "guide.outbox.scheduler-enabled",
    havingValue = "true",
    matchIfMissing = true)
public class OutboxScheduler {
  private final OutboxPublisher publisher;

  public OutboxScheduler(OutboxPublisher publisher) {
    this.publisher = publisher;
  }

  @Scheduled(
      initialDelayString = "${guide.outbox.initial-delay-ms:1000}",
      fixedDelayString = "${guide.outbox.poll-delay-ms:1000}")
  public void publishDueEvents() {
    publisher.publishDueEvents();
  }
}
