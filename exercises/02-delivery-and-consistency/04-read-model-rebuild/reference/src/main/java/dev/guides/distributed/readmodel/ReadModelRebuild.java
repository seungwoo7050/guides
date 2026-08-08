package dev.guides.distributed.readmodel;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public final class ReadModelRebuild {
    public record Event(String eventId, String aggregateId, int delta) {
    }

    public static final class SimulatedCrashException extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public SimulatedCrashException(String point) {
            super(point);
        }
    }

    public static final class EventLog {
        private final List<Event> events = new ArrayList<>();

        public synchronized void append(Event event) {
            events.add(event);
        }

        public synchronized Event at(long position) {
            return events.get(Math.toIntExact(position));
        }

        public synchronized int size() {
            return events.size();
        }
    }

    public static final class Projection {
        private final Map<String, Integer> totals = new HashMap<>();
        private final Map<String, Event> appliedEvents = new HashMap<>();

        public synchronized void apply(Event event) {
            Event previous = appliedEvents.get(event.eventId());
            if (previous != null) {
                if (!previous.equals(event)) {
                    throw new IllegalArgumentException(
                        "event ID was reused with different payload"
                    );
                }
                return;
            }
            appliedEvents.put(event.eventId(), event);
            totals.merge(event.aggregateId(), event.delta(), Integer::sum);
        }

        public synchronized int total(String aggregateId) {
            return totals.getOrDefault(aggregateId, 0);
        }

        public synchronized int appliedCount() {
            return appliedEvents.size();
        }
    }

    public static final class Runner {
        private final EventLog log;
        private final Projection projection;
        private long checkpoint;

        public Runner(EventLog log, Projection projection) {
            this.log = log;
            this.projection = projection;
        }

        public boolean processNext(
            boolean crashBeforeApply,
            boolean crashAfterApplyBeforeCheckpoint
        ) {
            if (checkpoint >= log.size()) {
                return false;
            }

            Event event = log.at(checkpoint);
            if (crashBeforeApply) {
                throw new SimulatedCrashException("before apply");
            }

            projection.apply(event);
            if (crashAfterApplyBeforeCheckpoint) {
                throw new SimulatedCrashException("after apply before checkpoint");
            }

            checkpoint++;
            return true;
        }

        public void replayAll() {
            while (processNext(false, false)) {
                // 계속 처리합니다.
            }
        }

        public long checkpoint() {
            return checkpoint;
        }
    }

    private ReadModelRebuild() {
    }
}
