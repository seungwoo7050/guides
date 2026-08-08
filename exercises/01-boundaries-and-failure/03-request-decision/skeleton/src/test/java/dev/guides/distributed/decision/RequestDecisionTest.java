package dev.guides.distributed.decision;

import dev.guides.distributed.testing.Checks;

public final class RequestDecisionTest {
    public static void main(String[] args) {
        synchronousDenialDoesNotChangeCapacity();
        unavailablePolicyDoesNotChangeCapacity();
        asynchronousAcceptanceOnlyPromisesOwnership();
    }

    private static void synchronousDenialDoesNotChangeCapacity() {
        RequestDecision.CapacityLedger ledger = new RequestDecision.CapacityLedger();
        RequestDecision.Coordinator coordinator = new RequestDecision.Coordinator(ledger);

        RequestDecision.Decision decision = coordinator.submit(
            new RequestDecision.Request("deny-1", 4),
            RequestDecision.Mode.SYNCHRONOUS,
            ignored -> RequestDecision.PolicyResult.DENY
        );

        Checks.equals(
            RequestDecision.Status.REJECTED,
            decision.status(),
            "정책 거절은 REJECTED여야 합니다"
        );
        Checks.equals(0, ledger.reserved(), "거절된 요청은 수량을 바꾸면 안 됩니다");
    }

    private static void unavailablePolicyDoesNotChangeCapacity() {
        RequestDecision.CapacityLedger ledger = new RequestDecision.CapacityLedger();
        RequestDecision.Coordinator coordinator = new RequestDecision.Coordinator(ledger);

        RequestDecision.Decision decision = coordinator.submit(
            new RequestDecision.Request("down-1", 2),
            RequestDecision.Mode.SYNCHRONOUS,
            ignored -> RequestDecision.PolicyResult.UNAVAILABLE
        );

        Checks.equals(
            RequestDecision.Status.REJECTED,
            decision.status(),
            "정책을 확인할 수 없으면 보수적으로 거절합니다"
        );
        Checks.equals(0, ledger.reserved(), "정책 장애가 상태 변경을 만들면 안 됩니다");
    }

    private static void asynchronousAcceptanceOnlyPromisesOwnership() {
        RequestDecision.CapacityLedger ledger = new RequestDecision.CapacityLedger();
        RequestDecision.Coordinator coordinator = new RequestDecision.Coordinator(ledger);
        RequestDecision.Request request = new RequestDecision.Request("async-1", 3);

        RequestDecision.Decision queued = coordinator.submit(
            request,
            RequestDecision.Mode.ASYNCHRONOUS,
            ignored -> RequestDecision.PolicyResult.ALLOW
        );

        Checks.equals(RequestDecision.Status.PENDING, queued.status(), "비동기 수락은 PENDING입니다");
        Checks.equals(0, ledger.reserved(), "queue 등록만으로 수량을 바꾸면 안 됩니다");
        Checks.equals(1, coordinator.pendingCount(), "시스템이 진행 책임을 보유해야 합니다");

        RequestDecision.Decision completed = coordinator.processNext(
            ignored -> RequestDecision.PolicyResult.ALLOW
        );
        Checks.equals(
            RequestDecision.Status.ACCEPTED,
            completed.status(),
            "후속 처리에서 결과를 확정합니다"
        );
        Checks.equals(3, ledger.reserved(), "허용된 처리만 수량을 변경합니다");
    }
}
