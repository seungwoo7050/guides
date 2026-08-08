package dev.guides.distributed.contracts;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
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
        private final Map<String, Event> knownEvents = new HashMap<>();
        private final List<Event> isolated = new ArrayList<>();

        public Projection(String expectedChannel, int supportedSchemaVersion) {
            this.expectedChannel = expectedChannel;
            this.supportedSchemaVersion = supportedSchemaVersion;
        }

        public synchronized Outcome onEvent(Event event) {
            if (!expectedChannel.equals(event.channel())) {
                throw new ContractViolationException(
                    "unexpected channel: " + event.channel()
                );
            }
            if (event.eventId() == null || event.eventId().isBlank()
                || event.aggregateId() == null || event.aggregateId().isBlank()
                || event.sequence() <= 0) {
                throw new ContractViolationException("invalid event identity or sequence");
            }
            Event known = knownEvents.get(event.eventId());
            if (known != null) {
                if (!known.equals(event)) {
                    throw new ContractViolationException(
                        "event ID was reused with different payload: " + event.eventId()
                    );
                }
                return Outcome.DUPLICATE;
            }
            if (event.schemaVersion() > supportedSchemaVersion) {
                knownEvents.put(event.eventId(), event);
                isolated.add(event);
                return Outcome.ISOLATED;
            }

            long expected = nextSequence.getOrDefault(event.aggregateId(), 1L);
            if (event.sequence() < expected) {
                knownEvents.put(event.eventId(), event);
                return Outcome.STALE;
            }
            if (event.sequence() > expected) {
                TreeMap<Long, Event> buffer = buffers.computeIfAbsent(
                    event.aggregateId(), ignored -> new TreeMap<>()
                );
                Event competing = buffer.get(event.sequence());
                if (competing != null && !competing.equals(event)) {
                    throw new ContractViolationException(
                        "different events claim aggregate sequence " + event.sequence()
                    );
                }
                knownEvents.put(event.eventId(), event);
                buffer.put(event.sequence(), event);
                return Outcome.BUFFERED;
            }

            knownEvents.put(event.eventId(), event);
            apply(event);
            drain(event.aggregateId());
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

        private void apply(Event event) {
            states.put(event.aggregateId(), event.state());
            nextSequence.put(event.aggregateId(), event.sequence() + 1);
        }

        private void drain(String aggregateId) {
            TreeMap<Long, Event> buffer = buffers.get(aggregateId);
            if (buffer == null) {
                return;
            }
            while (true) {
                long expected = nextSequence.getOrDefault(aggregateId, 1L);
                Event next = buffer.remove(expected);
                if (next == null) {
                    return;
                }
                apply(next);
            }
        }
    }

    private ContractsAndOrder() {
    }
}
