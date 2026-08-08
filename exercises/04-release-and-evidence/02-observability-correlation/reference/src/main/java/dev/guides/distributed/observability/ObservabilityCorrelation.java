package dev.guides.distributed.observability;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public final class ObservabilityCorrelation {
    public record Command(
        String requestId,
        String operationId,
        String traceId,
        String correlationId,
        String aggregateId
    ) {
    }

    public record Event(
        String eventId,
        String causationId,
        String traceId,
        String correlationId,
        String operationId,
        String aggregateId
    ) {
    }

    public record Observation(
        String component,
        String action,
        String traceId,
        String correlationId,
        String operationId,
        String eventId,
        String outcome
    ) {
    }

    public static final class Flow {
        private final List<Observation> observations = new ArrayList<>();
        private final Set<String> appliedEvents = new LinkedHashSet<>();
        private final Map<String, Integer> metrics = new LinkedHashMap<>();
        private int effects;

        public Command receive(String requestId, String operationId, String aggregateId) {
            Command command = new Command(
                requestId,
                operationId,
                "trace-" + requestId,
                requestId,
                aggregateId
            );
            observe("gateway", "command.received", command.traceId(), command.correlationId(),
                command.operationId(), null, "accepted");
            return command;
        }

        public Event publish(Command command) {
            Event event = new Event(
                "evt-" + command.operationId(),
                command.operationId(),
                command.traceId(),
                command.correlationId(),
                command.operationId(),
                command.aggregateId()
            );
            observe("reservation", "event.published", event.traceId(), event.correlationId(),
                command.operationId(), event.eventId(), "success");
            return event;
        }

        public void consume(Event event) {
            boolean first = appliedEvents.add(event.eventId());
            if (first) {
                effects++;
            }
            observe("inventory", "event.consumed", event.traceId(), event.correlationId(),
                event.operationId(), event.eventId(), first ? "applied" : "duplicate");
        }

        public List<Observation> observations() {
            return List.copyOf(observations);
        }

        public int effects() {
            return effects;
        }

        public Set<String> metricTagKeys() {
            return Set.of("component", "outcome");
        }

        public void validateMetricTagKeys(Set<String> keys) {
            Set<String> forbidden = Set.of(
                "requestId", "operationId", "eventId", "correlationId",
                "traceId", "aggregateId", "causationId"
            );
            if (!metricTagKeys().containsAll(keys) || keys.stream().anyMatch(forbidden::contains)) {
                throw new IllegalArgumentException("unbounded metric tag key");
            }
        }

        public int metricCount(String component, String outcome) {
            return metrics.getOrDefault(component + "|" + outcome, 0);
        }

        private void observe(
            String component,
            String action,
            String traceId,
            String correlationId,
            String operationId,
            String eventId,
            String outcome
        ) {
            observations.add(new Observation(
                component,
                action,
                traceId,
                correlationId,
                operationId,
                eventId,
                outcome
            ));
            metrics.merge(component + "|" + outcome, 1, Integer::sum);
        }
    }

    private ObservabilityCorrelation() {
    }
}
