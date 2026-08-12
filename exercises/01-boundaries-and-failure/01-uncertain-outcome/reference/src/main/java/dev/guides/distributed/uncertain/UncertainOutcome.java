package dev.guides.distributed.uncertain;

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

public final class UncertainOutcome {
    // [Implementation 1] 응답 유실 뒤에도 공유할 결과 어휘를 먼저 고정해,
    // 서버의 확정 상태와 클라이언트의 아직 모르는 상태를 구분한다.
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

    // [Implementation 2] Gateway가 연산별 입력과 결과, 업무 효과 횟수의 소유자다.
    // 이 상태를 한 경계에 두어 재시도가 새 효과를 만들지 못하게 한다.
    public static final class Gateway {
        private final Map<String, Result> results = new HashMap<>();
        private final Map<String, Integer> fingerprints = new HashMap<>();
        private int effectCount;

        // [Implementation 2-1] 같은 연산 ID의 입력 지문을 먼저 대조하고,
        // 처음 본 요청에서만 결과 저장과 효과 증가를 함께 수행한다.
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

        // [Implementation 2-2] 응답이 사라졌을 때 추측 대신 서버가 소유한
        // 확정 결과를 다시 읽을 수 있는 복구 경계를 제공한다.
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

    // [Implementation 3] Client는 전송 실패와 업무 실패를 구분하고,
    // 유실 예외에서는 같은 연산 ID를 조회한 뒤에만 UNKNOWN을 선택한다.
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
