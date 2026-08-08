package dev.guides.distributed.contracts;

import dev.guides.distributed.testing.Checks;

public final class ContractsAndOrderTest {
    private static final String CHANNEL = "reservation.events";

    public static void main(String[] args) {
        mismatchedChannelIsRejected();
        unsupportedVersionIsIsolated();
        sequenceGapIsBufferedAndDrained();
        duplicateEventIsIgnored();
        reusedIdAndCompetingSequenceAreRejected();
    }

    private static void mismatchedChannelIsRejected() {
        ContractsAndOrder.Projection projection =
            new ContractsAndOrder.Projection(CHANNEL, 2);

        Checks.throwsType(
            ContractsAndOrder.ContractViolationException.class,
            () -> projection.onEvent(
                new ContractsAndOrder.Event(
                    "reservation.event",
                    1,
                    "event-wrong",
                    "r-1",
                    1,
                    "CREATED"
                )
            ),
            "채널 drift를 조용히 허용하면 안 됩니다"
        );
    }

    private static void unsupportedVersionIsIsolated() {
        ContractsAndOrder.Projection projection =
            new ContractsAndOrder.Projection(CHANNEL, 2);

        ContractsAndOrder.Outcome outcome = projection.onEvent(
            new ContractsAndOrder.Event(
                CHANNEL,
                3,
                "event-v3",
                "r-2",
                1,
                "CREATED"
            )
        );

        Checks.equals(
            ContractsAndOrder.Outcome.ISOLATED,
            outcome,
            "지원하지 않는 버전은 격리해야 합니다"
        );
        Checks.equals(1, projection.isolatedCount(), "격리 근거를 보존해야 합니다");
        Checks.equals(null, projection.state("r-2"), "격리 이벤트를 적용하면 안 됩니다");
    }

    private static void sequenceGapIsBufferedAndDrained() {
        ContractsAndOrder.Projection projection =
            new ContractsAndOrder.Projection(CHANNEL, 2);

        ContractsAndOrder.Outcome second = projection.onEvent(
            new ContractsAndOrder.Event(
                CHANNEL,
                1,
                "event-2",
                "r-3",
                2,
                "ACCEPTED"
            )
        );

        Checks.equals(
            ContractsAndOrder.Outcome.BUFFERED,
            second,
            "sequence gap은 보류해야 합니다"
        );
        Checks.equals(1, projection.bufferedCount("r-3"), "보류 이벤트를 보존해야 합니다");
        Checks.equals(null, projection.state("r-3"), "선행 이벤트 전에는 상태를 적용하면 안 됩니다");

        projection.onEvent(
            new ContractsAndOrder.Event(
                CHANNEL,
                1,
                "event-1",
                "r-3",
                1,
                "CREATED"
            )
        );

        Checks.equals("ACCEPTED", projection.state("r-3"), "보류 이벤트까지 순서대로 적용해야 합니다");
        Checks.equals(0, projection.bufferedCount("r-3"), "gap이 채워지면 buffer가 비어야 합니다");
    }

    private static void duplicateEventIsIgnored() {
        ContractsAndOrder.Projection projection =
            new ContractsAndOrder.Projection(CHANNEL, 2);
        ContractsAndOrder.Event event =
            new ContractsAndOrder.Event(CHANNEL, 1, "event-d", "r-4", 1, "CREATED");

        projection.onEvent(event);
        ContractsAndOrder.Outcome duplicate = projection.onEvent(event);

        Checks.equals(
            ContractsAndOrder.Outcome.DUPLICATE,
            duplicate,
            "같은 event ID는 중복으로 분류해야 합니다"
        );
        Checks.equals("CREATED", projection.state("r-4"), "중복이 상태를 되돌리면 안 됩니다");
    }

    private static void reusedIdAndCompetingSequenceAreRejected() {
        ContractsAndOrder.Projection projection =
            new ContractsAndOrder.Projection(CHANNEL, 2);
        projection.onEvent(
            new ContractsAndOrder.Event(CHANNEL, 1, "event-gap", "r-5", 2, "ACCEPTED")
        );

        Checks.throwsType(
            ContractsAndOrder.ContractViolationException.class,
            () -> projection.onEvent(
                new ContractsAndOrder.Event(CHANNEL, 1, "event-other", "r-5", 2, "REJECTED")
            ),
            "같은 aggregate sequence의 다른 이벤트를 덮어쓰면 안 됩니다"
        );
        Checks.throwsType(
            ContractsAndOrder.ContractViolationException.class,
            () -> projection.onEvent(
                new ContractsAndOrder.Event(CHANNEL, 1, "event-gap", "r-6", 2, "REJECTED")
            ),
            "같은 event ID의 다른 payload를 중복으로 숨기면 안 됩니다"
        );
        Checks.equals(1, projection.bufferedCount("r-5"), "충돌은 기존 buffer를 바꾸면 안 됩니다");
    }
}
