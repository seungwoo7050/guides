package dev.guides.distributed.retry;

import dev.guides.distributed.testing.Checks;
import java.util.ArrayList;
import java.util.List;

public final class RetryBudgetTest {
    public static void main(String[] args) {
        transientFailureUsesSameOperationId();
        businessRejectionIsNotRetried();
        nextBackoffCannotCrossDeadline();
        circuitBreakerStopsNewCalls();
        halfOpenProbeAndDlqReplayPreserveContracts();
        failedHalfOpenProbeStartsANewOpenWindow();
        nonPositiveBackoffIsRejected();
        halfOpenBusinessRejectionClosesBreaker();
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
        RetryBudget.DeadLetter message =
            new RetryBudget.DeadLetter("event-dlq", "op-dlq", "reservation");
        dlq.add(message);
        Checks.throwsType(
            RetryBudget.TransientFailure.class,
            () -> dlq.replayNext(ignored -> {
                throw new RetryBudget.TransientFailure("still unavailable");
            }),
            "실패한 DLQ replay는 원본 메시지를 제거하면 안 됩니다"
        );
        Checks.equals(1, dlq.size(), "실패한 replay 뒤 DLQ 근거를 보존해야 합니다");

        List<RetryBudget.DeadLetter> replayed = new ArrayList<>();
        Checks.equals(
            "replayed",
            dlq.replayNext(replayedMessage -> {
                replayed.add(replayedMessage);
                return "replayed";
            }),
            "DLQ 메시지를 재생해야 합니다"
        );
        Checks.equals(
            List.of(message),
            replayed,
            "DLQ replay는 원래 event ID, operation ID와 payload를 함께 유지해야 합니다"
        );
        Checks.equals(0, dlq.size(), "성공한 replay는 DLQ에서 제거되어야 합니다");
    }

    private static void failedHalfOpenProbeStartsANewOpenWindow() {
        RetryBudget.VirtualClock clock = new RetryBudget.VirtualClock();
        RetryBudget.CircuitBreaker breaker =
            new RetryBudget.CircuitBreaker(1, 20, clock);
        RetryBudget.ScriptedDependency dependency = new RetryBudget.ScriptedDependency()
            .thenThrow(new RetryBudget.TransientFailure("initial outage"))
            .thenThrow(new RetryBudget.TransientFailure("probe still failing"))
            .thenReturn("recovered later");
        RetryBudget.Executor executor = new RetryBudget.Executor(clock, 1);

        Checks.throwsType(
            RetryBudget.CircuitOpen.class,
            () -> executor.execute("op-window", 100, dependency, breaker),
            "첫 실패가 breaker를 열어야 합니다"
        );
        clock.advance(20);
        Checks.throwsType(
            RetryBudget.CircuitOpen.class,
            () -> executor.execute("op-window", 100, dependency, breaker),
            "실패한 half-open probe가 breaker를 다시 열어야 합니다"
        );
        Checks.equals(2, dependency.calls(), "half-open probe는 한 번만 호출해야 합니다");
        clock.advance(19);
        Checks.throwsType(
            RetryBudget.CircuitOpen.class,
            () -> executor.execute("op-window", 100, dependency, breaker),
            "실패한 probe 뒤 새 open window를 끝까지 지켜야 합니다"
        );
        Checks.equals(2, dependency.calls(), "새 open window 중 의존성을 호출하면 안 됩니다");
        clock.advance(1);
        Checks.equals(
            "recovered later",
            executor.execute("op-window", 100, dependency, breaker),
            "새 open window 뒤 다음 probe를 허용해야 합니다"
        );
        Checks.equals(
            RetryBudget.CircuitBreaker.State.CLOSED,
            breaker.state(),
            "후속 probe 성공 뒤 breaker가 닫혀야 합니다"
        );
    }

    private static void nonPositiveBackoffIsRejected() {
        RetryBudget.VirtualClock clock = new RetryBudget.VirtualClock();
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> new RetryBudget.Executor(clock, 0),
            "backoff는 양수여야 합니다"
        );
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> new RetryBudget.Executor(clock, -1),
            "음수 backoff를 허용하면 안 됩니다"
        );
    }

    private static void halfOpenBusinessRejectionClosesBreaker() {
        RetryBudget.VirtualClock clock = new RetryBudget.VirtualClock();
        RetryBudget.CircuitBreaker breaker =
            new RetryBudget.CircuitBreaker(1, 20, clock);
        RetryBudget.ScriptedDependency dependency = new RetryBudget.ScriptedDependency()
            .thenThrow(new RetryBudget.TransientFailure("initial outage"))
            .thenThrow(new RetryBudget.BusinessRejection("capacity unavailable"));
        RetryBudget.Executor executor = new RetryBudget.Executor(clock, 1);

        Checks.throwsType(
            RetryBudget.CircuitOpen.class,
            () -> executor.execute("op-business-probe", 100, dependency, breaker),
            "첫 transient failure가 breaker를 열어야 합니다"
        );
        clock.advance(20);
        Checks.throwsType(
            RetryBudget.BusinessRejection.class,
            () -> executor.execute("op-business-probe", 100, dependency, breaker),
            "half-open probe의 업무 응답은 호출자에게 그대로 전달해야 합니다"
        );
        Checks.equals(
            RetryBudget.CircuitBreaker.State.CLOSED,
            breaker.state(),
            "업무 거절도 의존성이 응답한 것이므로 half-open breaker를 닫아야 합니다"
        );
        Checks.equals(2, dependency.calls(), "half-open probe는 한 번만 실행해야 합니다");
    }
}
