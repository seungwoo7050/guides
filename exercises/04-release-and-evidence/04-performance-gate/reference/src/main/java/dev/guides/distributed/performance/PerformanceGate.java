package dev.guides.distributed.performance;

import java.util.HashSet;
import java.util.List;
import java.util.Set;

public final class PerformanceGate {
    public enum Decision {
        PASS,
        FAIL,
        UNVERIFIED
    }

    public record Run(
        String environment,
        int attempted,
        int completedEffects,
        int duplicateEffects,
        int errors,
        long elapsedMillis
    ) {
    }

    public record Goal(
        int requiredRuns,
        int expectedEffectsPerRun,
        long maxElapsedMillis
    ) {
        public Goal {
            if (requiredRuns <= 0 || expectedEffectsPerRun < 0 || maxElapsedMillis < 0) {
                throw new IllegalArgumentException("invalid performance goal");
            }
        }
    }

    public static Decision evaluate(Goal goal, List<Run> runs) {
        if (runs == null || runs.size() < goal.requiredRuns()) {
            return Decision.UNVERIFIED;
        }
        Set<String> environments = new HashSet<>();
        for (Run run : runs) {
            if (run == null || run.environment() == null || run.environment().isBlank()) {
                return Decision.UNVERIFIED;
            }
            environments.add(run.environment());
        }
        if (environments.size() != 1) {
            return Decision.UNVERIFIED;
        }

        for (Run run : runs) {
            boolean correct = run.attempted() == goal.expectedEffectsPerRun()
                && run.completedEffects() == goal.expectedEffectsPerRun()
                && run.duplicateEffects() == 0
                && run.errors() == 0;
            boolean withinTime = run.elapsedMillis() <= goal.maxElapsedMillis();
            if (!correct || !withinTime) {
                return Decision.FAIL;
            }
        }
        return Decision.PASS;
    }

    private PerformanceGate() {
    }
}
