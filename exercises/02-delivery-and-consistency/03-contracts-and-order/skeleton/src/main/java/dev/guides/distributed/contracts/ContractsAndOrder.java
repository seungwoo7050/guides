package dev.guides.distributed.contracts;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

public final class ContractsAndOrder {
    public enum Outcome {
        APPLIED,
        BUFFERED,
        DUPLICATE,
        STALE,
        ISOLATED
    }

    public record Event(
        String channel,
        int schemaVersion,
        String eventId,
        String aggregateId,
        long sequence,
        String state
    ) {
    }

    public static final class ContractViolationException extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public ContractViolationException(String message) {
            super(message);
        }
    }

    public static final class Projection {
        private final String expectedChannel;
        private final int supportedSchemaVersion;
        private final Map<String, String> states = new HashMap<>();
        private final Map<String, Long> nextSequence = new HashMap<>();
        private final Map<String, TreeMap<Long, Event>> buffers = new HashMap<>();
        private final Set<String> knownEventIds = new HashSet<>();
        private final List<Event> isolated = new ArrayList<>();

        public Projection(String expectedChannel, int supportedSchemaVersion) {
            this.expectedChannel = expectedChannel;
            this.supportedSchemaVersion = supportedSchemaVersion;
        }

        public synchronized Outcome onEvent(Event event) {
            if (!knownEventIds.add(event.eventId())) {
                return Outcome.DUPLICATE;
            }

            // 결함: channel, schema version과 aggregate sequence를 검사하지 않습니다.
            states.put(event.aggregateId(), event.state());
            nextSequence.put(event.aggregateId(), event.sequence() + 1);
            return Outcome.APPLIED;
        }

        public synchronized String state(String aggregateId) {
            return states.get(aggregateId);
        }

        public synchronized int bufferedCount(String aggregateId) {
            return buffers.getOrDefault(aggregateId, new TreeMap<>()).size();
        }

        public synchronized int isolatedCount() {
            return isolated.size();
        }
    }

    private ContractsAndOrder() {
    }
}
