package dev.guides.spring.capstone;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(
    prefix = "publication.outbox",
    name = "publisher-enabled",
    havingValue = "true")
public final class OutboxPublisher {
  private final OutboxEventRepository events;
  private final EventGateway gateway;
  private final OutboxCompletionService completion;

  public OutboxPublisher(
      OutboxEventRepository events,
      EventGateway gateway,
      OutboxCompletionService completion) {
    this.events = events;
    this.gateway = gateway;
    this.completion = completion;
  }

  @Scheduled(fixedDelayString = "${publication.outbox.poll-interval:1s}")
  public void publishPending() {
    for (OutboxEventEntity event
        : events.findTop50ByPublishedAtIsNullOrderByCreatedAtAsc()) {
      gateway.publish(
          event.id(),
          event.aggregateId(),
          event.eventType(),
          event.payload());
      completion.markPublished(event.id());
    }
  }
}
