package dev.guides.distributed.readmodel;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public final class ReadModelRebuild {
    // [Implementation 1] Event에 재전달 식별자와 aggregate별 변화량을 함께 고정합니다.
    public record Event(String eventId, String aggregateId, int delta) {
    }

    public static final class SimulatedCrashException extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public SimulatedCrashException(String point) {
            super(point);
        }
    }

    // [Implementation 2] EventLog가 재생 가능한 입력 순서의 소유자가 됩니다.
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

    // [Implementation 3] Projection이 집계와 적용된 event ID 근거를 함께 소유합니다.
    public static final class Projection {
        private final Map<String, Integer> totals = new HashMap<>();
        private final Map<String, Event> appliedEvents = new HashMap<>();

        // [Implementation 3-1] 같은 ID의 재전달은 멱등 처리하고 다른 payload 재사용은 거절합니다.
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

    // [Implementation 4] Runner가 로그 위치와 projection 적용 사이의 lifecycle을 조정합니다.
    public static final class Runner {
        private final EventLog log;
        private final Projection projection;
        private long checkpoint;

        public Runner(EventLog log, Projection projection) {
            this.log = log;
            this.projection = projection;
        }

        // [Implementation 4-1] 적용 성공 뒤에만 checkpoint를 전진해 중단 시 유실을 막습니다.
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

        // [Implementation 4-2] 같은 처리 경로를 끝까지 반복해 온라인 처리와 재구축을 수렴시킵니다.
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
