package dev.guides.distributed.retry;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.List;
import java.util.Queue;

public final class RetryBudget {
    // [Implementation 1] 업무 거절, 일시 실패, deadline, open circuit를 서로 다른 실패 어휘로 둡니다.
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

    // [Implementation 2] VirtualClock이 deadline과 backoff의 결정적인 시간 소유자가 됩니다.
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

    // [Implementation 3] Dependency 경계가 operation ID 보존 여부와 호출 결과를 관찰하게 합니다.
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

    // [Implementation 4] CircuitBreaker가 연속 일시 실패와 probe lifecycle을 소유합니다.
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

        // [Implementation 4-1] 호출 직전에 OPEN 대기 시간과 HALF_OPEN 전이를 판정합니다.
        public void beforeCall() {
            if (state == State.OPEN && clock.nowMillis() >= nextProbeAt) {
                state = State.HALF_OPEN;
            }
            if (state == State.OPEN) {
                throw new CircuitOpen();
            }
        }

        // [Implementation 4-2] 의존성이 응답하면 transient failure 표본을 지우고 회로를 닫습니다.
        public void recordSuccess() {
            consecutiveFailures = 0;
            state = State.CLOSED;
        }

        // [Implementation 4-3] transient failure만 집계하고 실패한 probe에는 새 open window를 둡니다.
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

    // [Implementation 5] DeadLetter가 재생에 필요한 event, operation, payload 근거를 한데 묶습니다.
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

    // [Implementation 5-1] DeadLetterQueue가 성공한 재생만 원본을 제거하는 resource owner입니다.
    public static final class DeadLetterQueue {
        private final Queue<DeadLetter> messages = new ArrayDeque<>();

        public void add(DeadLetter message) {
            messages.add(message);
        }

        // [Implementation 5-2] handler 성공 뒤에만 dequeue해 실패 근거를 잃지 않습니다.
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

    // [Implementation 6] Executor가 하나의 deadline 안에서 retry, backoff, breaker를 조정합니다.
    public static final class Executor {
        private final VirtualClock clock;
        private final long backoffMillis;

        public Executor(VirtualClock clock, long backoffMillis) {
            if (backoffMillis <= 0) {
                throw new IllegalArgumentException("backoffMillis must be positive");
            }
            this.clock = clock;
            this.backoffMillis = backoffMillis;
        }

        // [Implementation 6-1] 같은 operation ID를 유지하며 분류된 실패에만 재시도를 허용합니다.
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
                    breaker.recordSuccess();
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
