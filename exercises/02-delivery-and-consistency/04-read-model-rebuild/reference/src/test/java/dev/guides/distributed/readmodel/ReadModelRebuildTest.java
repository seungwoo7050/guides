package dev.guides.distributed.readmodel;

import dev.guides.distributed.testing.Checks;

public final class ReadModelRebuildTest {
    public static void main(String[] args) {
        checkpointDoesNotAdvanceBeforeApply();
        replayAfterApplyBeforeCheckpointIsIdempotent();
        emptyProjectionCanBeRebuilt();
        reusedIdWithDifferentPayloadIsRejected();
    }

    private static void checkpointDoesNotAdvanceBeforeApply() {
        ReadModelRebuild.EventLog log = new ReadModelRebuild.EventLog();
        log.append(new ReadModelRebuild.Event("e-1", "a-1", 1));
        log.append(new ReadModelRebuild.Event("e-2", "a-1", 2));

        ReadModelRebuild.Projection projection = new ReadModelRebuild.Projection();
        ReadModelRebuild.Runner runner = new ReadModelRebuild.Runner(log, projection);
        runner.processNext(false, false);

        Checks.throwsType(
            ReadModelRebuild.SimulatedCrashException.class,
            () -> runner.processNext(true, false),
            "적용 전 중단을 재현해야 합니다"
        );
        Checks.equals(1L, runner.checkpoint(), "적용되지 않은 이벤트를 건너뛰면 안 됩니다");
        Checks.equals(1, projection.total("a-1"), "두 번째 이벤트는 아직 적용되지 않았습니다");

        runner.processNext(false, false);
        Checks.equals(3, projection.total("a-1"), "재시작 뒤 잃은 이벤트 없이 처리해야 합니다");
    }

    private static void replayAfterApplyBeforeCheckpointIsIdempotent() {
        ReadModelRebuild.EventLog log = new ReadModelRebuild.EventLog();
        log.append(new ReadModelRebuild.Event("e-3", "a-2", 5));

        ReadModelRebuild.Projection projection = new ReadModelRebuild.Projection();
        ReadModelRebuild.Runner runner = new ReadModelRebuild.Runner(log, projection);

        Checks.throwsType(
            ReadModelRebuild.SimulatedCrashException.class,
            () -> runner.processNext(false, true),
            "적용 뒤 checkpoint 전 중단을 재현해야 합니다"
        );
        Checks.equals(0L, runner.checkpoint(), "ACK 전에는 같은 위치를 다시 읽어야 합니다");
        Checks.equals(5, projection.total("a-2"), "첫 적용은 보존되어 있습니다");

        runner.processNext(false, false);
        Checks.equals(5, projection.total("a-2"), "재전달이 집계를 두 번 늘리면 안 됩니다");
        Checks.equals(1, projection.appliedCount(), "event ID 중복 제거가 필요합니다");
    }

    private static void emptyProjectionCanBeRebuilt() {
        ReadModelRebuild.EventLog log = new ReadModelRebuild.EventLog();
        log.append(new ReadModelRebuild.Event("e-a", "a-3", 2));
        log.append(new ReadModelRebuild.Event("e-b", "a-3", 4));

        ReadModelRebuild.Projection rebuilt = new ReadModelRebuild.Projection();
        ReadModelRebuild.Runner runner = new ReadModelRebuild.Runner(log, rebuilt);
        runner.replayAll();

        Checks.equals(6, rebuilt.total("a-3"), "전체 로그로 projection을 재구축해야 합니다");
        Checks.equals(2, rebuilt.appliedCount(), "모든 고유 이벤트가 반영되어야 합니다");
        Checks.equals(2L, runner.checkpoint(), "rebuild checkpoint는 로그 끝에 수렴해야 합니다");
    }

    private static void reusedIdWithDifferentPayloadIsRejected() {
        ReadModelRebuild.Projection projection = new ReadModelRebuild.Projection();
        projection.apply(new ReadModelRebuild.Event("e-conflict", "a-4", 2));

        Checks.throwsType(
            IllegalArgumentException.class,
            () -> projection.apply(new ReadModelRebuild.Event("e-conflict", "a-4", 5)),
            "같은 event ID의 다른 payload를 중복으로 숨기면 안 됩니다"
        );
        Checks.equals(2, projection.total("a-4"), "충돌한 이벤트는 projection을 바꾸면 안 됩니다");
        Checks.equals(1, projection.appliedCount(), "충돌은 적용 수를 늘리면 안 됩니다");
    }
}
