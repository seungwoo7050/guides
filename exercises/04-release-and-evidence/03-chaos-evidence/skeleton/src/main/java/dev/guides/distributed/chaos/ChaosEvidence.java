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
        String hypothesis,
        long timeBudgetMillis,
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
                "the system preserves evidence and converges after one failure",
                1_000,
                true
            );
        }

        public Report run(
            Set<Failure> failures,
            String hypothesis,
            long timeBudgetMillis,
            boolean cleanupSucceeds
        ) {
            if (failures.size() != 1) {
                throw new IllegalArgumentException("inject exactly one failure");
            }
            if (hypothesis == null || hypothesis.isBlank() || timeBudgetMillis <= 0) {
                throw new IllegalArgumentException("hypothesis and positive time budget are required");
            }
            Failure failure = failures.iterator().next();
            List<Snapshot> evidence = new ArrayList<>();
            evidence.add(snapshot(Phase.BEFORE));

            if (failure == Failure.DATABASE_DOWN) {
                processUp = true;
                evidence.add(snapshot(Phase.DURING));
                evidence.add(snapshot(Phase.AFTER));
                return report(hypothesis, timeBudgetMillis, cleanupSucceeds, evidence);
            }

            primaryRows++;
            pendingOutbox++;
            publishPending();
            evidence.add(snapshot(Phase.DURING));
            evidence.add(snapshot(Phase.AFTER));
            return report(hypothesis, timeBudgetMillis, cleanupSucceeds, evidence);
        }

        private Report report(
            String hypothesis,
            long timeBudgetMillis,
            boolean cleanupSucceeds,
            List<Snapshot> evidence
        ) {
            boolean converged = evidence.get(evidence.size() - 1).converged();
            return new Report(
                hypothesis,
                timeBudgetMillis,
                converged ? Result.PASS : Result.FAIL,
                cleanupSucceeds ? Result.PASS : Result.FAIL,
                evidence
            );
        }

        private void publishPending() {
            readModelRows += pendingOutbox;
            pendingOutbox = 0;
        }

        private Snapshot snapshot(Phase phase) {
            return new Snapshot(
                phase,
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
