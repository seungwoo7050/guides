package dev.guides.distributed.backpressure;

import java.util.ArrayDeque;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Queue;
import java.util.Set;

public final class Backpressure {
    public enum Admission {
        STARTED,
        QUEUED,
        REJECTED
    }

    private record Queued(String requestId, long enqueuedAt, long deadline) {
    }

    private static final class Lane {
        private final int maxInFlight;
        private final int maxQueued;
        private final long maxQueueAge;
        private final Set<String> inFlight = new LinkedHashSet<>();
        private final Queue<Queued> queued = new ArrayDeque<>();
        private final Set<String> completed = new LinkedHashSet<>();
        private int rejected;
        private int expired;

        private Lane(int maxInFlight, int maxQueued, long maxQueueAge) {
            if (maxInFlight <= 0 || maxQueued < 0 || maxQueueAge < 0) {
                throw new IllegalArgumentException("invalid lane limits");
            }
            this.maxInFlight = maxInFlight;
            this.maxQueued = maxQueued;
            this.maxQueueAge = maxQueueAge;
        }

        private Admission submit(String requestId, long now, long deadline) {
            if (inFlight.contains(requestId)
                || queued.stream().anyMatch(entry -> entry.requestId().equals(requestId))
                || completed.contains(requestId)) {
                throw new IllegalArgumentException("duplicate request ID: " + requestId);
            }
            expire(now);
            if (now >= deadline) {
                expired++;
                return Admission.REJECTED;
            }
            if (inFlight.size() < maxInFlight) {
                inFlight.add(requestId);
                return Admission.STARTED;
            }
            if (queued.size() <= maxQueued) {
                queued.add(new Queued(requestId, now, deadline));
                return Admission.QUEUED;
            }
            rejected++;
            return Admission.REJECTED;
        }

        private String completeOne(long now) {
            if (inFlight.isEmpty()) {
                throw new IllegalStateException("no in-flight work");
            }
            String finished = inFlight.iterator().next();
            inFlight.remove(finished);
            completed.add(finished);

            expire(now);
            Queued next = queued.poll();
            if (next != null) {
                inFlight.add(next.requestId());
            }
            return next == null ? null : next.requestId();
        }

        private void expire(long now) {
            while (!queued.isEmpty()) {
                Queued head = queued.element();
                boolean tooOld = maxQueueAge != Long.MAX_VALUE
                    && now - head.enqueuedAt() >= maxQueueAge;
                if (now < head.deadline() && !tooOld) {
                    return;
                }
                queued.remove();
                expired++;
            }
        }

        private long oldestAge(long now) {
            Queued head = queued.peek();
            return head == null ? 0 : Math.max(0, now - head.enqueuedAt());
        }
    }

    public static final class AdmissionSystem {
        private final Map<String, Lane> lanes = new HashMap<>();

        public void register(String name, int maxInFlight, int maxQueued) {
            register(name, maxInFlight, maxQueued, Long.MAX_VALUE);
        }

        public void register(String name, int maxInFlight, int maxQueued, long maxQueueAge) {
            if (lanes.putIfAbsent(name, new Lane(maxInFlight, maxQueued, maxQueueAge)) != null) {
                throw new IllegalArgumentException("lane already registered: " + name);
            }
        }

        public Admission submit(String lane, String requestId) {
            return submit(lane, requestId, 0, Long.MAX_VALUE);
        }

        public Admission submit(String lane, String requestId, long now, long deadline) {
            return lane(lane).submit(requestId, now, deadline);
        }

        public String completeOne(String lane) {
            return completeOne(lane, 0);
        }

        public String completeOne(String lane, long now) {
            return lane(lane).completeOne(now);
        }

        public int inFlight(String lane) {
            return lane(lane).inFlight.size();
        }

        public int queued(String lane) {
            return lane(lane).queued.size();
        }

        public int rejected(String lane) {
            return lane(lane).rejected;
        }

        public int expire(String lane, long now) {
            Lane selected = lane(lane);
            int before = selected.expired;
            selected.expire(now);
            return selected.expired - before;
        }

        public int expired(String lane) {
            return lane(lane).expired;
        }

        public long oldestQueueAge(String lane, long now) {
            return lane(lane).oldestAge(now);
        }

        public boolean completed(String lane, String requestId) {
            return lane(lane).completed.contains(requestId);
        }

        private Lane lane(String name) {
            Lane lane = lanes.get(name);
            if (lane == null) {
                throw new IllegalArgumentException("unknown lane: " + name);
            }
            return lane;
        }
    }

    private Backpressure() {
    }
}
