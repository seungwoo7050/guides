package dev.guides.distributed.retry;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.List;
import java.util.Queue;

public final class RetryBudget {
    public static final class TransientFailure extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public TransientFailure(String message) {
            super(message);
        }
    }

    public static final class BusinessRejection extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public BusinessRejection(String message) {
            super(message);
        }
    }

    public static final class DeadlineExceeded extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public DeadlineExceeded() {
            super("operation deadline exceeded");
        }
    }

    public static final class CircuitOpen extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public CircuitOpen() {
            super("circuit breaker is open");
        }
    }

    public static final class VirtualClock {
        private long nowMillis;

        public long nowMillis() {
            return nowMillis;
        }

        public void advance(long millis) {
            if (millis < 0) {
                throw new IllegalArgumentException("millis must not be negative");
            }
            nowMillis += millis;
        }
    }

    @FunctionalInterface
    public interface Dependency {
        String call(String operationId);
    }

    public static final class ScriptedDependency implements Dependency {
        private final Queue<Object> outcomes = new ArrayDeque<>();
        private final List<String> receivedOperationIds = new ArrayList<>();
        private int calls;

        public ScriptedDependency thenReturn(String value) {
            outcomes.add(value);
            return this;
        }

        public ScriptedDependency thenThrow(RuntimeException error) {
            outcomes.add(error);
            return this;
        }

        @Override
        public String call(String operationId) {
            calls++;
            receivedOperationIds.add(operationId);
            Object outcome = outcomes.remove();
            if (outcome instanceof RuntimeException error) {
                throw error;
            }
            return (String) outcome;
        }

        public int calls() {
            return calls;
        }

        public List<String> receivedOperationIds() {
            return List.copyOf(receivedOperationIds);
        }
    }

    public static final class CircuitBreaker {
        public enum State {
            CLOSED,
            OPEN,
            HALF_OPEN
        }

        private final int failureThreshold;
        private final long openMillis;
        private final VirtualClock clock;
        private int consecutiveFailures;
        private long nextProbeAt;
        private State state = State.CLOSED;

        public CircuitBreaker(int failureThreshold) {
            this(failureThreshold, Long.MAX_VALUE, new VirtualClock());
        }

        public CircuitBreaker(int failureThreshold, long openMillis, VirtualClock clock) {
            if (failureThreshold <= 0) {
                throw new IllegalArgumentException("failureThreshold must be positive");
            }
            if (openMillis <= 0) {
                throw new IllegalArgumentException("openMillis must be positive");
            }
            this.failureThreshold = failureThreshold;
            this.openMillis = openMillis;
            this.clock = clock;
        }

        public void beforeCall() {
            if (state == State.OPEN && clock.nowMillis() >= nextProbeAt) {
                state = State.HALF_OPEN;
            }
            if (state == State.OPEN) {
                throw new CircuitOpen();
            }
        }

        public void recordSuccess() {
            consecutiveFailures = 0;
            state = State.CLOSED;
        }

        public void recordTransientFailure() {
            consecutiveFailures++;
            if (state == State.HALF_OPEN || consecutiveFailures >= failureThreshold) {
                state = State.OPEN;
                nextProbeAt = clock.nowMillis() + openMillis;
            }
        }

        public boolean isOpen() {
            return state == State.OPEN;
        }

        public State state() {
            return state;
        }
    }

    public record DeadLetter(String eventId, String operationId, String payload) {
        public DeadLetter {
            if (eventId == null || eventId.isBlank()
                || operationId == null || operationId.isBlank()
                || payload == null || payload.isBlank()) {
                throw new IllegalArgumentException(
                    "dead letter event, operation, and payload are required"
                );
            }
        }
    }

    @FunctionalInterface
    public interface DeadLetterHandler {
        String replay(DeadLetter message);
    }

    public static final class DeadLetterQueue {
        private final Queue<DeadLetter> messages = new ArrayDeque<>();

        public void add(DeadLetter message) {
            messages.add(message);
        }

        public String replayNext(DeadLetterHandler handler) {
            DeadLetter message = messages.element();
            String result = handler.replay(message);
            messages.remove();
            return result;
        }

        public int size() {
            return messages.size();
        }
    }

    public static final class Executor {
        private final VirtualClock clock;
        private final long backoffMillis;

        public Executor(VirtualClock clock, long backoffMillis) {
            this.clock = clock;
            this.backoffMillis = backoffMillis;
        }

        public String execute(
            String operationId,
            long deadlineMillis,
            Dependency dependency,
            CircuitBreaker breaker
        ) {
            while (true) {
                if (clock.nowMillis() >= deadlineMillis) {
                    throw new DeadlineExceeded();
                }

                breaker.beforeCall();
                try {
                    String result = dependency.call(operationId);
                    breaker.recordSuccess();
                    return result;
                } catch (BusinessRejection rejection) {
                    throw rejection;
                } catch (TransientFailure transientFailure) {
                    breaker.recordTransientFailure();
                    if (breaker.isOpen()) {
                        throw new CircuitOpen();
                    }
                    if (clock.nowMillis() + backoffMillis >= deadlineMillis) {
                        throw new DeadlineExceeded();
                    }
                    clock.advance(backoffMillis);
                }
            }
        }
    }

    private RetryBudget() {
    }
}
