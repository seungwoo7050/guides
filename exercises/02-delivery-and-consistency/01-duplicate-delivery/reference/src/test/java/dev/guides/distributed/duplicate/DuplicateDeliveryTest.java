package dev.guides.distributed.duplicate;

import dev.guides.distributed.testing.Checks;

public final class DuplicateDeliveryTest {
    public static void main(String[] args) {
        redeliveryAfterCrashKeepsOneEffect();
        differentEventsRemainIndependent();
        reusedIdWithDifferentPayloadIsRejected();
    }

    private static void redeliveryAfterCrashKeepsOneEffect() {
        DuplicateDelivery.EffectStore store = new DuplicateDelivery.EffectStore();
        DuplicateDelivery.Handler handler = new DuplicateDelivery.Handler(store);
        DuplicateDelivery.Event event =
            new DuplicateDelivery.Event("event-1", "account-1", 7);

        Checks.throwsType(
            DuplicateDelivery.SimulatedCrashException.class,
            () -> handler.handle(event, true),
            "첫 전달은 commit 뒤 중단되어야 합니다"
        );
        int replayResult = handler.handle(event, false);

        Checks.equals(7, replayResult, "재전달은 이전 결과를 반환해야 합니다");
        Checks.equals(7, store.balance("account-1"), "잔액 효과는 한 번이어야 합니다");
        Checks.equals(1, store.appliedEventCount(), "처리 이벤트는 하나여야 합니다");
    }

    private static void differentEventsRemainIndependent() {
        DuplicateDelivery.EffectStore store = new DuplicateDelivery.EffectStore();
        DuplicateDelivery.Handler handler = new DuplicateDelivery.Handler(store);

        handler.handle(new DuplicateDelivery.Event("event-a", "account-2", 3), false);
        handler.handle(new DuplicateDelivery.Event("event-b", "account-2", 4), false);

        Checks.equals(7, store.balance("account-2"), "다른 이벤트는 각각 적용되어야 합니다");
        Checks.equals(2, store.appliedEventCount(), "서로 다른 event ID를 보존해야 합니다");
    }

    private static void reusedIdWithDifferentPayloadIsRejected() {
        DuplicateDelivery.EffectStore store = new DuplicateDelivery.EffectStore();
        DuplicateDelivery.Handler handler = new DuplicateDelivery.Handler(store);
        handler.handle(new DuplicateDelivery.Event("event-c", "account-3", 5), false);

        Checks.throwsType(
            IllegalArgumentException.class,
            () -> handler.handle(
                new DuplicateDelivery.Event("event-c", "account-3", 9),
                false
            ),
            "같은 event ID의 다른 payload는 중복으로 숨기면 안 됩니다"
        );
        Checks.equals(5, store.balance("account-3"), "충돌한 입력은 상태를 바꾸면 안 됩니다");
        Checks.equals(1, store.appliedEventCount(), "충돌한 입력은 처리 기록을 추가하면 안 됩니다");
    }
}
