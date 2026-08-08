package dev.guides.distributed.backpressure;

import dev.guides.distributed.testing.Checks;

public final class BackpressureTest {
    public static void main(String[] args) {
        queueIsBoundedAndShedsExcessLoad();
        lanesDoNotShareFailureCapacity();
        completionPromotesExactlyOneQueuedRequest();
        expiredQueuedWorkIsNeverPromoted();
    }

    private static void queueIsBoundedAndShedsExcessLoad() {
        Backpressure.AdmissionSystem system = new Backpressure.AdmissionSystem();
        system.register("inventory", 1, 1);

        Checks.equals(
            Backpressure.Admission.STARTED,
            system.submit("inventory", "i-1"),
            "첫 요청은 즉시 실행해야 합니다"
        );
        Checks.equals(
            Backpressure.Admission.QUEUED,
            system.submit("inventory", "i-2"),
            "두 번째 요청은 제한된 대기열에 들어가야 합니다"
        );
        Checks.equals(
            Backpressure.Admission.REJECTED,
            system.submit("inventory", "i-3"),
            "대기열 상한을 넘은 요청은 즉시 거절해야 합니다"
        );
        Checks.equals(1, system.inFlight("inventory"), "실행 수가 상한을 넘으면 안 됩니다");
        Checks.equals(1, system.queued("inventory"), "대기 수가 상한을 넘으면 안 됩니다");
        Checks.equals(1, system.rejected("inventory"), "거절 수를 관찰할 수 있어야 합니다");
    }

    private static void lanesDoNotShareFailureCapacity() {
        Backpressure.AdmissionSystem system = new Backpressure.AdmissionSystem();
        system.register("email", 1, 0);
        system.register("inventory", 1, 0);

        Checks.equals(
            Backpressure.Admission.STARTED,
            system.submit("email", "e-1"),
            "email 첫 요청은 실행해야 합니다"
        );
        Checks.equals(
            Backpressure.Admission.REJECTED,
            system.submit("email", "e-2"),
            "포화된 email lane은 추가 요청을 거절해야 합니다"
        );
        Checks.equals(
            Backpressure.Admission.STARTED,
            system.submit("inventory", "i-1"),
            "email 포화가 inventory 용량을 소모하면 안 됩니다"
        );
    }

    private static void completionPromotesExactlyOneQueuedRequest() {
        Backpressure.AdmissionSystem system = new Backpressure.AdmissionSystem();
        system.register("inventory", 1, 2);
        system.submit("inventory", "i-1");
        system.submit("inventory", "i-2");
        system.submit("inventory", "i-3");

        String promoted = system.completeOne("inventory");

        Checks.equals("i-2", promoted, "가장 먼저 대기한 요청을 실행해야 합니다");
        Checks.isTrue(system.completed("inventory", "i-1"), "완료한 요청을 기록해야 합니다");
        Checks.equals(1, system.inFlight("inventory"), "한 작업만 실행 상태여야 합니다");
        Checks.equals(1, system.queued("inventory"), "나머지 한 작업은 계속 대기해야 합니다");
        Checks.isFalse(
            system.completed("inventory", "i-3"),
            "아직 대기 중인 요청을 완료로 기록하면 안 됩니다"
        );
    }

    private static void expiredQueuedWorkIsNeverPromoted() {
        Backpressure.AdmissionSystem system = new Backpressure.AdmissionSystem();
        system.register("payments", 1, 2, 20);
        system.submit("payments", "p-1", 0, 100);
        system.submit("payments", "p-2", 5, 100);

        Checks.equals(10L, system.oldestQueueAge("payments", 15), "가장 오래 기다린 시간을 관찰해야 합니다");
        Checks.equals(1, system.expire("payments", 25), "queue age를 넘은 작업을 만료해야 합니다");
        Checks.equals(0, system.queued("payments"), "만료된 작업은 대기열에서 제거되어야 합니다");
        Checks.equals(null, system.completeOne("payments", 25), "만료 요청을 실행 상태로 올리면 안 됩니다");
        Checks.equals(1, system.expired("payments"), "만료 근거를 집계해야 합니다");

        Checks.equals(
            Backpressure.Admission.REJECTED,
            system.submit("payments", "p-late", 30, 30),
            "이미 지난 deadline의 요청은 즉시 거절해야 합니다"
        );
        Checks.equals(2, system.expired("payments"), "deadline 만료도 별도로 남아야 합니다");
    }
}
