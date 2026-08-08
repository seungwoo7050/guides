package dev.guides.distributed.retry;

import dev.guides.distributed.testing.Checks;
import java.util.List;

public final class RetryBudgetTest {
    public static void main(String[] args) {
        transientFailureUsesSameOperationId();
        businessRejectionIsNotRetried();
        nextBackoffCannotCrossDeadline();
        circuitBreakerStopsNewCalls();
        halfOpenProbeAndDlqReplayPreserveContracts();
    }

    private static void transientFailureUsesSameOperationId() {
        RetryBudget.VirtualClock clock = new RetryBudget.VirtualClock();
        RetryBudget.ScriptedDependency dependency = new RetryBudget.ScriptedDependency()
            .thenThrow(new RetryBudget.TransientFailure("temporary"))
            .thenReturn("accepted");
        RetryBudget.CircuitBreaker breaker = new RetryBudget.CircuitBreaker(3);

        String result = new RetryBudget.Executor(clock, 10)
            .execute("op-1", 100, dependency, breaker);

        Checks.equals("accepted", result, "일시 실패 뒤 성공 결과를 반환해야 합니다");
        Checks.equals(
            List.of("op-1", "op-1"),
            dependency.receivedOperationIds(),
            "재시도는 같은 operation ID를 사용해야 합니다"
        );
        Checks.equals(10L, clock.nowMillis(), "결정적인 backoff만 경과해야 합니다");
    }

    private static void businessRejectionIsNotRetried() {
        RetryBudget.VirtualClock clock = new RetryBudget.VirtualClock();
        RetryBudget.ScriptedDependency dependency = new RetryBudget.ScriptedDependency()
            .thenThrow(new RetryBudget.BusinessRejection("insufficient capacity"))
            .thenReturn("should-not-run");
        RetryBudget.CircuitBreaker breaker = new RetryBudget.CircuitBreaker(3);

        Checks.throwsType(
            RetryBudget.BusinessRejection.class,
            () -> new RetryBudget.Executor(clock, 10)
                .execute("op-2", 100, dependency, breaker),
            "업무 거절은 즉시 반환해야 합니다"
        );
        Checks.equals(1, dependency.calls(), "업무 거절을 재시도하면 안 됩니다");
        Checks.isFalse(breaker.isOpen(), "업무 거절은 breaker 실패 표본이 아닙니다");
    }

    private static void nextBackoffCannotCrossDeadline() {
        RetryBudget.VirtualClock clock = new RetryBudget.VirtualClock();
        RetryBudget.ScriptedDependency dependency = new RetryBudget.ScriptedDependency()
            .thenThrow(new RetryBudget.TransientFailure("slow"))
            .thenReturn("too-late");
        RetryBudget.CircuitBreaker breaker = new RetryBudget.CircuitBreaker(3);

        Checks.throwsType(
            RetryBudget.DeadlineExceeded.class,
            () -> new RetryBudget.Executor(clock, 20)
                .execute("op-3", 15, dependency, breaker),
            "다음 backoff가 deadline을 넘으면 중단해야 합니다"
        );
        Checks.equals(1, dependency.calls(), "deadline 밖의 새 시도를 시작하면 안 됩니다");
        Checks.equals(0L, clock.nowMillis(), "실행하지 않을 backoff를 적용하면 안 됩니다");
    }

    private static void circuitBreakerStopsNewCalls() {
        RetryBudget.VirtualClock clock = new RetryBudget.VirtualClock();
        RetryBudget.ScriptedDependency dependency = new RetryBudget.ScriptedDependency()
            .thenThrow(new RetryBudget.TransientFailure("down-1"))
            .thenThrow(new RetryBudget.TransientFailure("down-2"))
            .thenReturn("must-not-run");
        RetryBudget.CircuitBreaker breaker = new RetryBudget.CircuitBreaker(2);
        RetryBudget.Executor executor = new RetryBudget.Executor(clock, 1);

        Checks.throwsType(
            RetryBudget.CircuitOpen.class,
            () -> executor.execute("op-4", 100, dependency, breaker),
            "연속 실패 뒤 breaker가 열려야 합니다"
        );
        int callsBefore = dependency.calls();

        Checks.throwsType(
            RetryBudget.CircuitOpen.class,
            () -> executor.execute("op-5", 100, dependency, breaker),
            "열린 breaker는 새 호출을 빠르게 거절해야 합니다"
        );
        Checks.equals(callsBefore, dependency.calls(), "열린 상태에서 의존성을 호출하면 안 됩니다");
    }

    private static void halfOpenProbeAndDlqReplayPreserveContracts() {
        RetryBudget.VirtualClock clock = new RetryBudget.VirtualClock();
        RetryBudget.CircuitBreaker breaker =
            new RetryBudget.CircuitBreaker(1, 20, clock);
        RetryBudget.ScriptedDependency dependency = new RetryBudget.ScriptedDependency()
            .thenThrow(new RetryBudget.TransientFailure("down"))
            .thenReturn("recovered");
        RetryBudget.Executor executor = new RetryBudget.Executor(clock, 1);

        Checks.throwsType(
            RetryBudget.CircuitOpen.class,
            () -> executor.execute("op-probe", 100, dependency, breaker),
            "임계값 뒤 breaker가 열려야 합니다"
        );
        Checks.equals(
            RetryBudget.CircuitBreaker.State.OPEN,
            breaker.state(),
            "복구 대기 중에는 OPEN이어야 합니다"
        );
        clock.advance(20);
        Checks.equals(
            "recovered",
            executor.execute("op-probe", 100, dependency, breaker),
            "대기 시간이 지나면 반개방 probe를 허용해야 합니다"
        );
        Checks.equals(
            RetryBudget.CircuitBreaker.State.CLOSED,
            breaker.state(),
            "probe 성공 뒤 breaker가 닫혀야 합니다"
        );

        RetryBudget.DeadLetterQueue dlq = new RetryBudget.DeadLetterQueue();
        dlq.add(new RetryBudget.DeadLetter("op-dlq", "reservation"));
        RetryBudget.ScriptedDependency replay =
            new RetryBudget.ScriptedDependency().thenReturn("replayed");
        Checks.equals("replayed", dlq.replayNext(replay), "DLQ 메시지를 재생해야 합니다");
        Checks.equals(
            List.of("op-dlq"),
            replay.receivedOperationIds(),
            "DLQ replay도 원래 operation ID를 유지해야 합니다"
        );
        Checks.equals(0, dlq.size(), "성공한 replay는 DLQ에서 제거되어야 합니다");
    }
}
