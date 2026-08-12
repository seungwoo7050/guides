package dev.guides.distributed.duplicate;

import java.util.HashMap;
import java.util.Map;

public final class DuplicateDelivery {
    // [Implementation 1] Event는 중복 판정에 쓰는 식별자와 업무 입력을 함께 묶어,
    // 같은 ID가 다른 payload로 재사용되는 충돌도 탐지할 수 있게 한다.
    public record Event(String eventId, String accountId, int amount) {
    }

    public static final class SimulatedCrashException extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public SimulatedCrashException() {
            super("crash after commit and before acknowledgement");
        }
    }

    // [Implementation 2] EffectStore가 잔액, 처리 결과, 입력 지문을 함께 소유한다.
    // 중복 기록과 업무 상태가 갈라지지 않는 원자적 경계다.
    public static final class EffectStore {
        private final Map<String, Integer> balances = new HashMap<>();
        private final Map<String, Integer> appliedEvents = new HashMap<>();
        private final Map<String, Event> appliedInputs = new HashMap<>();

        // [Implementation 2-1] 이미 처리한 이벤트는 입력 일치 여부를 확인한 뒤
        // 저장된 결과를 반환하고, 신규 이벤트에서만 세 상태를 함께 갱신한다.
        public synchronized int applyOnce(Event event) {
            Integer previous = appliedEvents.get(event.eventId());
            if (previous != null) {
                if (!event.equals(appliedInputs.get(event.eventId()))) {
                    throw new IllegalArgumentException(
                        "event ID was reused with different payload"
                    );
                }
                return previous;
            }

            int updated = balances.getOrDefault(event.accountId(), 0) + event.amount();
            balances.put(event.accountId(), updated);
            appliedEvents.put(event.eventId(), updated);
            appliedInputs.put(event.eventId(), event);
            return updated;
        }

        public synchronized int balance(String accountId) {
            return balances.getOrDefault(accountId, 0);
        }

        public synchronized int appliedEventCount() {
            return appliedEvents.size();
        }
    }

    // [Implementation 3] Handler는 전달 lifecycle과 저장소의 단일 효과 계약을 연결한다.
    // ACK 직전 중단은 재전달을 일으키지만 저장된 효과를 되돌리지는 않는다.
    public static final class Handler {
        private final EffectStore store;

        public Handler(EffectStore store) {
            this.store = store;
        }

        // [Implementation 3-1] commit을 먼저 끝내고 ACK 실패를 별도로 드러내,
        // 재전달에서도 applyOnce가 이전 결과로 수렴하는 경계를 재현한다.
        public int handle(Event event, boolean crashAfterCommit) {
            int result = store.applyOnce(event);
            if (crashAfterCommit) {
                throw new SimulatedCrashException();
            }
            return result;
        }
    }

    private DuplicateDelivery() {
    }
}
