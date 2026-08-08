package dev.guides.distributed.decision;

import java.util.ArrayDeque;
import java.util.HashMap;
import java.util.Map;
import java.util.Queue;

public final class RequestDecision {
    public enum Mode {
        SYNCHRONOUS,
        ASYNCHRONOUS
    }

    public enum PolicyResult {
        ALLOW,
        DENY,
        UNAVAILABLE
    }

    public enum Status {
        ACCEPTED,
        REJECTED,
        PENDING
    }

    public record Request(String operationId, int units) {
    }

    public record Decision(Status status, String reason) {
    }

    private record Submission(Request request, Mode mode) {
    }

    @FunctionalInterface
    public interface Policy {
        PolicyResult evaluate(Request request);
    }

    public static final class CapacityLedger {
        private int reserved;

        public synchronized void reserve(int units) {
            if (units <= 0) {
                throw new IllegalArgumentException("units must be positive");
            }
            reserved += units;
        }

        public synchronized int reserved() {
            return reserved;
        }
    }

    public static final class Coordinator {
        private final CapacityLedger ledger;
        private final Queue<Request> pending = new ArrayDeque<>();
        private final Map<String, Decision> results = new HashMap<>();
        private final Map<String, Submission> submissions = new HashMap<>();

        public Coordinator(CapacityLedger ledger) {
            this.ledger = ledger;
        }

        public synchronized Decision submit(Request request, Mode mode, Policy policy) {
            if (request == null || request.operationId() == null
                || request.operationId().isBlank() || request.units() <= 0
                || mode == null || policy == null) {
                throw new IllegalArgumentException("valid request, mode, and policy are required");
            }
            Submission input = new Submission(request, mode);
            Submission previousInput = submissions.get(request.operationId());
            Decision existing = results.get(request.operationId());
            if (previousInput != null) {
                if (!previousInput.equals(input)) {
                    throw new IllegalArgumentException(
                        "operation ID was reused with a different decision input"
                    );
                }
                return existing;
            }

            if (mode == Mode.ASYNCHRONOUS) {
                Decision result = new Decision(Status.PENDING, "queued");
                submissions.put(request.operationId(), input);
                pending.add(request);
                results.put(request.operationId(), result);
                return result;
            }

            Decision result = decideNow(request, policy);
            submissions.put(request.operationId(), input);
            return result;
        }

        public synchronized Decision processNext(Policy policy) {
            Request request = pending.remove();
            Decision result = decideNow(request, policy);
            results.put(request.operationId(), result);
            return result;
        }

        public synchronized int pendingCount() {
            return pending.size();
        }

        private Decision decideNow(Request request, Policy policy) {
            // 결함: 원격 정책 판정 전에 상태를 먼저 바꿉니다.
            ledger.reserve(request.units());
            PolicyResult policyResult = policy.evaluate(request);
            Decision result;

            if (policyResult == PolicyResult.ALLOW) {
                result = new Decision(Status.ACCEPTED, "policy allowed");
            } else if (policyResult == PolicyResult.DENY) {
                result = new Decision(Status.REJECTED, "policy denied");
            } else {
                result = new Decision(Status.REJECTED, "policy unavailable");
            }

            results.put(request.operationId(), result);
            return result;
        }
    }

    private RequestDecision() {
    }
}
