package dev.guides.distributed.uncertain;

import dev.guides.distributed.testing.Checks;

public final class UncertainOutcomeTest {
    public static void main(String[] args) {
        responseLossDoesNotEraseCommittedResult();
        sameOperationReturnsSameEffect();
        conflictingInputIsRejected();
    }

    private static void responseLossDoesNotEraseCommittedResult() {
        UncertainOutcome.Gateway gateway = new UncertainOutcome.Gateway();
        UncertainOutcome.Client client = new UncertainOutcome.Client(gateway);

        UncertainOutcome.Result result = client.reserve("op-1", 3, true);

        Checks.equals(
            UncertainOutcome.Status.ACCEPTED,
            result.status(),
            "응답 유실 뒤 저장된 결과를 조회해야 합니다"
        );
        Checks.equals(1, gateway.effectCount(), "업무 효과는 한 번이어야 합니다");
    }

    private static void sameOperationReturnsSameEffect() {
        UncertainOutcome.Gateway gateway = new UncertainOutcome.Gateway();
        UncertainOutcome.Client client = new UncertainOutcome.Client(gateway);

        UncertainOutcome.Result first = client.reserve("op-2", 2, false);
        UncertainOutcome.Result second = client.reserve("op-2", 2, false);

        Checks.equals(first, second, "같은 연산은 이전 결과를 반환해야 합니다");
        Checks.equals(1, gateway.effectCount(), "재시도가 효과를 추가하면 안 됩니다");
    }

    private static void conflictingInputIsRejected() {
        UncertainOutcome.Gateway gateway = new UncertainOutcome.Gateway();
        gateway.reserve("op-3", 1, false);

        Checks.throwsType(
            IllegalArgumentException.class,
            () -> gateway.reserve("op-3", 2, false),
            "같은 operation ID에 다른 입력을 허용하면 안 됩니다"
        );
        Checks.equals(1, gateway.effectCount(), "충돌 입력은 상태를 바꾸면 안 됩니다");
    }
}
