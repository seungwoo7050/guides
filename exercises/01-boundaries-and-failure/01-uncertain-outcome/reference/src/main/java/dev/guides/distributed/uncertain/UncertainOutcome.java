package dev.guides.distributed.uncertain;

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

public final class UncertainOutcome {
    public enum Status {
        ACCEPTED,
        REJECTED,
        UNKNOWN
    }

    public record Result(String operationId, Status status, int units) {
    }

    public static final class ResponseLostException extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public ResponseLostException() {
            super("response lost after commit");
        }
    }

    public static final class Gateway {
        private final Map<String, Result> results = new HashMap<>();
        private final Map<String, Integer> fingerprints = new HashMap<>();
        private int effectCount;

        public synchronized Result reserve(
            String operationId,
            int units,
            boolean loseResponseAfterCommit
        ) {
            requireInput(operationId, units);

            Result existing = results.get(operationId);
            if (existing != null) {
                if (fingerprints.get(operationId) != units) {
                    throw new IllegalArgumentException(
                        "operation id was reused with different input"
                    );
                }
                return existing;
            }

            Result created = new Result(operationId, Status.ACCEPTED, units);
            fingerprints.put(operationId, units);
            results.put(operationId, created);
            effectCount++;

            if (loseResponseAfterCommit) {
                throw new ResponseLostException();
            }
            return created;
        }

        public synchronized Optional<Result> query(String operationId) {
            return Optional.ofNullable(results.get(operationId));
        }

        public synchronized int effectCount() {
            return effectCount;
        }

        private static void requireInput(String operationId, int units) {
            if (operationId == null || operationId.isBlank()) {
                throw new IllegalArgumentException("operationId is required");
            }
            if (units <= 0) {
                throw new IllegalArgumentException("units must be positive");
            }
        }
    }

    public static final class Client {
        private final Gateway gateway;

        public Client(Gateway gateway) {
            this.gateway = gateway;
        }

        public Result reserve(
            String operationId,
            int units,
            boolean loseFirstResponse
        ) {
            try {
                return gateway.reserve(operationId, units, loseFirstResponse);
            } catch (ResponseLostException lost) {
                return gateway.query(operationId)
                    .orElse(new Result(operationId, Status.UNKNOWN, 0));
            }
        }
    }

    private UncertainOutcome() {
    }
}
