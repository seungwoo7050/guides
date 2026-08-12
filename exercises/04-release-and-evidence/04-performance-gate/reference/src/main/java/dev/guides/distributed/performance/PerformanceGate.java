package dev.guides.distributed.performance;

import java.util.HashSet;
import java.util.List;
import java.util.Set;

public final class PerformanceGate {
    // [Implementation 1] Decision은 완전한 근거의 PASS·FAIL과 근거 부족의 UNVERIFIED를 구분합니다.
    public enum Decision {
        PASS,
        FAIL,
        UNVERIFIED
    }

    // [Implementation 2] Run과 Goal을 분리해 측정 근거와 판정 정책의 소유자를 구분합니다.
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
        // [Implementation 2-1] 잘못된 반복 수와 시간 정책은 실행을 평가하기 전에 거절합니다.
        public Goal {
            if (requiredRuns <= 0 || expectedEffectsPerRun < 0 || maxElapsedMillis < 0) {
                throw new IllegalArgumentException("invalid performance goal");
            }
        }
    }

    // [Implementation 3] evaluate는 근거 완전성, 환경, 정확성, 시간을 차례로 gate합니다.
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
