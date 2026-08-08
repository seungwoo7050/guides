package dev.guides.distributed.chaos;

import java.util.ArrayList;
import java.util.EnumSet;
import java.util.List;
import java.util.Set;

public final class ChaosEvidence {
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
            List<Snapshot> evidence = new ArrayList<>();
            evidence.add(snapshot(Phase.BEFORE, operationId, 0));

            if (failure == Failure.DATABASE_DOWN) {
                processUp = true;
                evidence.add(snapshot(Phase.DURING, operationId, elapsedMillis / 2));
                evidence.add(snapshot(Phase.AFTER, operationId, elapsedMillis));
                return report(
                    operationId, hypothesis, timeBudgetMillis, elapsedMillis,
                    cleanupSucceeds, evidence
                );
            }

            primaryRows++;
            pendingOutbox++;
            publishPending();
            evidence.add(snapshot(Phase.DURING, operationId, elapsedMillis / 2));
            evidence.add(snapshot(Phase.AFTER, operationId, elapsedMillis));
            return report(
                operationId, hypothesis, timeBudgetMillis, elapsedMillis,
                cleanupSucceeds, evidence
            );
        }

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
