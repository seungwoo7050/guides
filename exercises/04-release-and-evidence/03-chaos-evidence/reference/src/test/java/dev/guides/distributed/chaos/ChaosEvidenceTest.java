package dev.guides.distributed.chaos;

import dev.guides.distributed.testing.Checks;
import java.util.EnumSet;

public final class ChaosEvidenceTest {
    public static void main(String[] args) {
        evidenceContainsAllPhases();
        recoveryUsesBusinessConvergence();
        multipleFailuresAreRejected();
        hypothesisBudgetAndCleanupEvidenceRemainSeparate();
        operationAndElapsedEvidenceStayConnected();
        lateConvergenceFailsThePrimaryResult();
        unsupportedFailureIsRejected();
    }

    private static void evidenceContainsAllPhases() {
        ChaosEvidence.Report report = new ChaosEvidence.Scenario()
            .run(ChaosEvidence.one(ChaosEvidence.Failure.BROKER_DOWN));

        ChaosEvidence.Snapshot before = report.at(ChaosEvidence.Phase.BEFORE);
        ChaosEvidence.Snapshot during = report.at(ChaosEvidence.Phase.DURING);
        ChaosEvidence.Snapshot after = report.at(ChaosEvidence.Phase.AFTER);

        Checks.equals(0, before.primaryRows(), "장애 전 기준 상태가 필요합니다");
        Checks.equals(1, during.primaryRows(), "장애 중 원본 변경은 남아야 합니다");
        Checks.equals(1, during.pendingOutbox(), "장애 중 Outbox 대기 건을 보존해야 합니다");
        Checks.equals(0, during.readModelRows(), "장애 중 읽기 모델은 아직 갱신되지 않아야 합니다");
        Checks.equals(0, after.pendingOutbox(), "복구 뒤 Outbox가 비어야 합니다");
        Checks.equals(1, after.readModelRows(), "복구 뒤 읽기 모델이 수렴해야 합니다");

        Checks.equals(
            1,
            during.pendingOutbox(),
            "복구가 과거 snapshot을 덮어쓰면 안 됩니다"
        );
    }

    private static void recoveryUsesBusinessConvergence() {
        ChaosEvidence.Report report = new ChaosEvidence.Scenario()
            .run(ChaosEvidence.one(ChaosEvidence.Failure.BROKER_DOWN));

        Checks.isFalse(
            report.at(ChaosEvidence.Phase.DURING).converged(),
            "프로세스가 실행 중이어도 업무 상태가 어긋나면 복구된 것이 아닙니다"
        );
        Checks.isTrue(
            report.at(ChaosEvidence.Phase.AFTER).converged(),
            "원본, Outbox와 읽기 모델이 수렴해야 복구입니다"
        );
    }

    private static void multipleFailuresAreRejected() {
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> new ChaosEvidence.Scenario().run(
                EnumSet.of(
                    ChaosEvidence.Failure.BROKER_DOWN,
                    ChaosEvidence.Failure.DATABASE_DOWN
                )
            ),
            "한 시나리오에는 실패 조건 하나만 주입해야 합니다"
        );
    }

    private static void hypothesisBudgetAndCleanupEvidenceRemainSeparate() {
        ChaosEvidence.Report report = new ChaosEvidence.Scenario().run(
            ChaosEvidence.one(ChaosEvidence.Failure.BROKER_DOWN),
            "Outbox replay converges within 250 ms",
            250,
            false
        );

        Checks.equals(
            "Outbox replay converges within 250 ms",
            report.hypothesis(),
            "실험 전에 검증할 가설을 고정해야 합니다"
        );
        Checks.equals(250L, report.timeBudgetMillis(), "시간 제한을 증거에 남겨야 합니다");
        Checks.equals(
            ChaosEvidence.Result.PASS,
            report.primaryResult(),
            "업무 수렴 결과는 정리 결과와 독립적으로 판정해야 합니다"
        );
        Checks.equals(
            ChaosEvidence.Result.FAIL,
            report.cleanupResult(),
            "정리 실패를 primary 실패로 덮어쓰면 안 됩니다"
        );
        Checks.equals(
            1,
            report.at(ChaosEvidence.Phase.DURING).pendingOutbox(),
            "정리 실패 뒤에도 장애 중 증거가 남아야 합니다"
        );
    }

    private static void operationAndElapsedEvidenceStayConnected() {
        ChaosEvidence.Report report = new ChaosEvidence.Scenario().run(
            ChaosEvidence.one(ChaosEvidence.Failure.BROKER_DOWN),
            "op-chaos-7",
            "the projection converges within 100 ms",
            100,
            80,
            true
        );

        Checks.equals("op-chaos-7", report.operationId(), "보고서가 operation ID를 보존해야 합니다");
        Checks.equals(80L, report.elapsedMillis(), "실제 경과 시간을 보고서에 남겨야 합니다");
        for (ChaosEvidence.Snapshot snapshot : report.snapshots()) {
            Checks.equals(
                "op-chaos-7",
                snapshot.operationId(),
                "모든 장애 단계가 같은 operation ID로 연결되어야 합니다"
            );
        }
        Checks.equals(0L, report.at(ChaosEvidence.Phase.BEFORE).elapsedMillis(),
            "장애 전 기준 시각은 0이어야 합니다");
        Checks.equals(80L, report.at(ChaosEvidence.Phase.AFTER).elapsedMillis(),
            "복구 후 snapshot이 최종 경과 시간을 가져야 합니다");
    }

    private static void lateConvergenceFailsThePrimaryResult() {
        ChaosEvidence.Report report = new ChaosEvidence.Scenario().run(
            ChaosEvidence.one(ChaosEvidence.Failure.BROKER_DOWN),
            "op-chaos-late",
            "the projection converges within 50 ms",
            50,
            51,
            true
        );

        Checks.isTrue(
            report.at(ChaosEvidence.Phase.AFTER).converged(),
            "시간 초과 여부와 별개로 최종 업무 상태는 수렴할 수 있습니다"
        );
        Checks.equals(
            ChaosEvidence.Result.FAIL,
            report.primaryResult(),
            "시간 한도를 넘긴 수렴을 실험 성공으로 판정하면 안 됩니다"
        );
    }

    private static void unsupportedFailureIsRejected() {
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> new ChaosEvidence.Scenario().run(
                ChaosEvidence.one(ChaosEvidence.Failure.DATABASE_DOWN)
            ),
            "지원하지 않는 database 장애를 성공 증거로 만들면 안 됩니다"
        );
    }
}
