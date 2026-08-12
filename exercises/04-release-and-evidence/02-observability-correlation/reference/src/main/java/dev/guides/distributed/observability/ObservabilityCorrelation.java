package dev.guides.distributed.observability;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

public final class ObservabilityCorrelation {
    // [Implementation 1] Command를 중심으로 Event와 Observation까지 식별자의 수명 주기를 고정합니다.
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

    // [Implementation 2] Flow가 hop별 관찰 기록, event claim과 bounded metric의 상태를 소유합니다.
    public static final class Flow {
        private final List<Observation> observations = new ArrayList<>();
        private final Map<String, Event> appliedEvents = new LinkedHashMap<>();
        private final Map<String, Integer> metrics = new LinkedHashMap<>();
        private int effects;

        // [Implementation 2-1] 명시적 ingress 값은 보존하고 기존 overload는 기본값을 이 경계에 위임합니다.
        public Command receive(
            String requestId,
            String operationId,
            String traceId,
            String correlationId,
            String aggregateId
        ) {
            Command command = new Command(
                requestId,
                operationId,
                traceId,
                correlationId,
                aggregateId
            );
            observe("gateway", "command.received", command.traceId(), command.correlationId(),
                command.operationId(), null, "accepted");
            return command;
        }

        public Command receive(String requestId, String operationId, String aggregateId) {
            return receive(
                requestId,
                operationId,
                "trace-" + requestId,
                requestId,
                aggregateId
            );
        }

        // [Implementation 2-2] 발행자는 명령의 식별자를 새로 만들지 않고 event와 causation에 전달합니다.
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

        // [Implementation 2-3] event ID의 소유 기록으로 중복 효과와 식별자 충돌을 분리합니다.
        public void consume(Event event) {
            Event previous = appliedEvents.get(event.eventId());
            if (previous != null && !previous.equals(event)) {
                throw new IllegalArgumentException("event ID reused with different identifiers");
            }
            boolean first = previous == null;
            if (first) {
                appliedEvents.put(event.eventId(), event);
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

        // [Implementation 2-4] metric 차원은 값 종류가 제한된 component와 outcome만 허용합니다.
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

        // [Implementation 2-5] 로그성 관찰값과 bounded metric을 한 경계에서 함께 기록합니다.
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
