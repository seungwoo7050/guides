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

        public Coordinator(CapacityLedger ledger) {
            this.ledger = ledger;
        }

        public synchronized Decision submit(Request request, Mode mode, Policy policy) {
            Decision existing = results.get(request.operationId());
            if (existing != null) {
                return existing;
            }

            if (mode == Mode.ASYNCHRONOUS) {
                Decision result = new Decision(Status.PENDING, "queued");
                pending.add(request);
                results.put(request.operationId(), result);
                return result;
            }

            return decideNow(request, policy);
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
            PolicyResult policyResult = policy.evaluate(request);
            Decision result;

            if (policyResult == PolicyResult.ALLOW) {
                ledger.reserve(request.units());
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
