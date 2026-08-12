package dev.guides.distributed.decision;

import java.util.ArrayDeque;
import java.util.HashMap;
import java.util.Map;
import java.util.Queue;

public final class RequestDecision {
    // [Implementation 1] 요청 방식, 정책 응답, 공개 상태와 입력/결과 값을 먼저
    // 고정해 동기 확정과 비동기 접수의 서로 다른 약속을 표현한다.
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

    // [Implementation 2] CapacityLedger만 예약 수량을 소유하고 변경한다.
    // 원격 정책 판정은 이 로컬 자원을 직접 선점하지 못한다.
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

    // [Implementation 3] Coordinator가 연산별 입력/결과와 대기열 lifecycle을
    // 함께 소유해 중복 접수와 최종 판정을 하나의 경계에서 조정한다.
    public static final class Coordinator {
        private final CapacityLedger ledger;
        private final Queue<Request> pending = new ArrayDeque<>();
        private final Map<String, Decision> results = new HashMap<>();
        private final Map<String, Submission> submissions = new HashMap<>();

        public Coordinator(CapacityLedger ledger) {
            this.ledger = ledger;
        }

        // [Implementation 3-1] 기존 연산은 입력 지문을 검증해 이전 결과를 돌려주고,
        // 비동기 신규 요청은 효과를 실행하지 않은 채 PENDING과 대기열 소유권만 기록한다.
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

        // [Implementation 3-2] 대기열에서 꺼낸 요청의 정책 판정과 결과 갱신을
        // 한 동기화 경계에서 끝내 PENDING 항목의 lifecycle을 종결한다.
        public synchronized Decision processNext(Policy policy) {
            Request request = pending.remove();
            Decision result = decideNow(request, policy);
            results.put(request.operationId(), result);
            return result;
        }

        public synchronized int pendingCount() {
            return pending.size();
        }

        // [Implementation 3-3] 정책이 ALLOW로 확정된 뒤에만 ledger를 변경한다.
        // 거절과 원격 장애 경로에서는 로컬 예약 상태가 그대로인 것이 핵심 불변식이다.
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
