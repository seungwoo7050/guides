package dev.guides.distributed.performance;

import dev.guides.distributed.testing.Checks;
import java.util.List;

public final class PerformanceGateTest {
    public static void main(String[] args) {
        missingEvidenceIsUnverified();
        mixedEnvironmentIsUnverified();
        fastButIncorrectRunFails();
        completeCorrectRunsPass();
    }

    private static PerformanceGate.Goal goal() {
        return new PerformanceGate.Goal(3, 100, 50);
    }

    private static void missingEvidenceIsUnverified() {
        Checks.equals(
            PerformanceGate.Decision.UNVERIFIED,
            PerformanceGate.evaluate(
                goal(),
                List.of(
                    new PerformanceGate.Run("jdk17-linux-x86", 100, 100, 0, 0, 30),
                    new PerformanceGate.Run("jdk17-linux-x86", 100, 100, 0, 0, 31)
                )
            ),
            "필수 반복 수가 없으면 성능을 판정할 수 없습니다"
        );
    }

    private static void mixedEnvironmentIsUnverified() {
        Checks.equals(
            PerformanceGate.Decision.UNVERIFIED,
            PerformanceGate.evaluate(
                goal(),
                List.of(
                    new PerformanceGate.Run("jdk17-linux-x86", 100, 100, 0, 0, 30),
                    new PerformanceGate.Run("jdk21-macos-arm", 100, 100, 0, 0, 20),
                    new PerformanceGate.Run("jdk17-linux-x86", 100, 100, 0, 0, 32)
                )
            ),
            "다른 환경의 결과를 하나의 기준으로 합치면 안 됩니다"
        );
    }

    private static void fastButIncorrectRunFails() {
        Checks.equals(
            PerformanceGate.Decision.FAIL,
            PerformanceGate.evaluate(
                goal(),
                List.of(
                    new PerformanceGate.Run("jdk17-linux-x86", 100, 100, 0, 0, 20),
                    new PerformanceGate.Run("jdk17-linux-x86", 100, 101, 1, 0, 19),
                    new PerformanceGate.Run("jdk17-linux-x86", 100, 100, 0, 0, 21)
                )
            ),
            "빠르더라도 중복 효과가 있으면 실패입니다"
        );
    }

    private static void completeCorrectRunsPass() {
        Checks.equals(
            PerformanceGate.Decision.PASS,
            PerformanceGate.evaluate(
                goal(),
                List.of(
                    new PerformanceGate.Run("jdk17-linux-x86", 100, 100, 0, 0, 30),
                    new PerformanceGate.Run("jdk17-linux-x86", 100, 100, 0, 0, 32),
                    new PerformanceGate.Run("jdk17-linux-x86", 100, 100, 0, 0, 31)
                )
            ),
            "완전한 정확성 근거와 시간 조건을 모두 만족해야 통과합니다"
        );
    }
}
