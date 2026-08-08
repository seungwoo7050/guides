package dev.guides.distributed.performance;

import java.util.Comparator;
import java.util.List;

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
    }

    public static Decision evaluate(Goal goal, List<Run> runs) {
        if (runs == null || runs.isEmpty()) {
            return Decision.UNVERIFIED;
        }
        Run fastest = runs.stream()
            .min(Comparator.comparingLong(Run::elapsedMillis))
            .orElseThrow();
        return fastest.elapsedMillis() <= goal.maxElapsedMillis()
            ? Decision.PASS
            : Decision.FAIL;
    }

    private PerformanceGate() {
    }
}
