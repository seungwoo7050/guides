package dev.guides.distributed.chaos;

import java.util.ArrayList;
import java.util.EnumSet;
import java.util.List;
import java.util.Set;

public final class ChaosEvidence {
    // [Implementation 1] Phase를 중심으로 지원 failure와 독립 판정 vocabulary를 고정합니다.
    public enum Phase {
        BEFORE,
        DURING,
        AFTER
    }

    public enum Failure {
        BROKER_DOWN,
        DATABASE_DOWN
    }

    public enum Result {
        PASS,
        FAIL
    }

    // [Implementation 2] Snapshot은 한 시점의 업무 상태를 이후 mutation과 분리해 보존합니다.
    public record Snapshot(
        Phase phase,
        String operationId,
        long elapsedMillis,
        int primaryRows,
        int pendingOutbox,
        int readModelRows,
        boolean processUp
    ) {
        public boolean converged() {
            return primaryRows == readModelRows && pendingOutbox == 0;
        }
    }

    // [Implementation 2-1] Report는 가설·예산·primary·cleanup과 모든 snapshot을 하나로 묶습니다.
    public record Report(
        String operationId,
        String hypothesis,
        long timeBudgetMillis,
        long elapsedMillis,
        Result primaryResult,
        Result cleanupResult,
        List<Snapshot> snapshots
    ) {
        public Report {
            snapshots = List.copyOf(snapshots);
        }

        public Snapshot at(Phase phase) {
            return snapshots.stream()
                .filter(snapshot -> snapshot.phase() == phase)
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("missing phase: " + phase));
        }
    }

    // [Implementation 3] Scenario가 실험 중인 업무 상태와 Outbox 상태의 유일한 소유자입니다.
    public static final class Scenario {
        private int primaryRows;
        private int pendingOutbox;
        private int readModelRows;
        private boolean processUp = true;

        public Report run(Set<Failure> failures) {
            return run(
                failures,
                "chaos-operation",
                "the system preserves evidence and converges after one failure",
                1_000,
                10,
                true
            );
        }

        public Report run(
            Set<Failure> failures,
            String hypothesis,
            long timeBudgetMillis,
            boolean cleanupSucceeds
        ) {
            return run(
                failures,
                "chaos-operation",
                hypothesis,
                timeBudgetMillis,
                Math.min(10, timeBudgetMillis),
                cleanupSucceeds
            );
        }

        // [Implementation 3-1] canonical run은 단일 지원 실패와 evidence budget을 mutation 전에 검증합니다.
        public Report run(
            Set<Failure> failures,
            String operationId,
            String hypothesis,
            long timeBudgetMillis,
            long elapsedMillis,
            boolean cleanupSucceeds
        ) {
            if (failures.size() != 1) {
                throw new IllegalArgumentException("inject exactly one failure");
            }
            if (operationId == null || operationId.isBlank()
                || hypothesis == null || hypothesis.isBlank()
                || timeBudgetMillis <= 0 || elapsedMillis < 0) {
                throw new IllegalArgumentException(
                    "operation, hypothesis, positive time budget and elapsed time are required"
                );
            }
            Failure failure = failures.iterator().next();
            if (failure != Failure.BROKER_DOWN) {
                throw new IllegalArgumentException("unsupported failure: " + failure);
            }

            List<Snapshot> evidence = new ArrayList<>();
            evidence.add(snapshot(Phase.BEFORE, operationId, 0));

            primaryRows++;
            pendingOutbox++;
            evidence.add(snapshot(Phase.DURING, operationId, elapsedMillis / 2));

            publishPending();
            evidence.add(snapshot(Phase.AFTER, operationId, elapsedMillis));
            return report(
                operationId, hypothesis, timeBudgetMillis, elapsedMillis,
                cleanupSucceeds, evidence
            );
        }

        // [Implementation 3-2] 업무 수렴 결과와 cleanup 결과를 독립적으로 판정해 원인을 보존합니다.
        private Report report(
            String operationId,
            String hypothesis,
            long timeBudgetMillis,
            long elapsedMillis,
            boolean cleanupSucceeds,
            List<Snapshot> evidence
        ) {
            boolean convergedInTime = evidence.get(evidence.size() - 1).converged()
                && elapsedMillis <= timeBudgetMillis;
            return new Report(
                operationId,
                hypothesis,
                timeBudgetMillis,
                elapsedMillis,
                convergedInTime ? Result.PASS : Result.FAIL,
                cleanupSucceeds ? Result.PASS : Result.FAIL,
                evidence
            );
        }

        // [Implementation 3-3] broker 복구 뒤 pending Outbox를 읽기 모델에 반영하고 종료 상태를 만듭니다.
        private void publishPending() {
            readModelRows += pendingOutbox;
            pendingOutbox = 0;
        }

        private Snapshot snapshot(Phase phase, String operationId, long elapsedMillis) {
            return new Snapshot(
                phase,
                operationId,
                elapsedMillis,
                primaryRows,
                pendingOutbox,
                readModelRows,
                processUp
            );
        }
    }

    public static Set<Failure> one(Failure failure) {
        return EnumSet.of(failure);
    }

    private ChaosEvidence() {
    }
}
