package dev.guides.distributed.outbox;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public final class OutboxReconciliation {
    // [Implementation 1] DomainEvent는 Outbox와 소비자가 공유하는 식별자와
    // 업무 대상을 묶어 재전달에서도 같은 논리 이벤트를 판별하게 한다.
    public record DomainEvent(String eventId, String orderId) {
    }

    public static final class SimulatedCrashException extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public SimulatedCrashException() {
            super("crash after publish and before outbox acknowledgement");
        }
    }

    public static final class BrokerUnavailableException extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public BrokerUnavailableException() {
            super("broker unavailable");
        }
    }

    // [Implementation 2] OutboxRow가 발행 완료 여부와 시도 횟수를 소유한다.
    // broker 전송 성공 전에는 published가 바뀌지 않는 것이 복구 불변식이다.
    public static final class OutboxRow {
        private final DomainEvent event;
        private boolean published;
        private int attempts;

        private OutboxRow(DomainEvent event) {
            this.event = event;
        }

        public DomainEvent event() {
            return event;
        }

        public boolean published() {
            return published;
        }

        public int attempts() {
            return attempts;
        }

        private void recordAttempt() {
            attempts++;
        }

        private void markPublished() {
            published = true;
        }
    }

    // [Implementation 3] Database는 주문 상태와 대응 이벤트, Outbox 행을 함께 소유해
    // 업무 commit과 발행 근거가 서로 빠질 수 없는 로컬 원자 경계를 만든다.
    public static final class Database {
        private final Map<String, String> orders = new HashMap<>();
        private final Map<String, String> eventByOrder = new HashMap<>();
        private final Map<String, DomainEvent> eventsById = new HashMap<>();
        private final List<OutboxRow> outbox = new ArrayList<>();

        // [Implementation 3-1] 주문 ID와 이벤트 ID의 양방향 재사용을 검증하고,
        // 신규 주문에서만 업무 상태와 Outbox 행을 한 번에 생성한다.
        public synchronized void createOrder(String orderId, String eventId) {
            if (orderId == null || orderId.isBlank()
                || eventId == null || eventId.isBlank()) {
                throw new IllegalArgumentException("order and event IDs are required");
            }
            DomainEvent candidate = new DomainEvent(eventId, orderId);
            DomainEvent claimedEvent = eventsById.get(eventId);
            if (claimedEvent != null && !claimedEvent.equals(candidate)) {
                throw new IllegalArgumentException(
                    "event ID was reused by a different order"
                );
            }
            if (orders.containsKey(orderId)) {
                if (!eventId.equals(eventByOrder.get(orderId))) {
                    throw new IllegalArgumentException(
                        "order ID was reused with a different event ID"
                    );
                }
                return;
            }
            orders.put(orderId, "CREATED");
            eventByOrder.put(orderId, eventId);
            eventsById.put(eventId, candidate);
            outbox.add(new OutboxRow(candidate));
        }

        public synchronized List<OutboxRow> pending() {
            return outbox.stream().filter(row -> !row.published()).toList();
        }

        public synchronized int orderCount() {
            return orders.size();
        }

        public synchronized int outboxCount() {
            return outbox.size();
        }
    }

    // [Implementation 4] Consumer가 처리한 이벤트 지문과 투영 결과를 함께 소유해,
    // at-least-once 전달 횟수와 업무 효과 횟수를 분리한다.
    public static final class Consumer {
        private final Map<String, DomainEvent> processed = new HashMap<>();
        private final Set<String> projectedOrders = new HashSet<>();

        // [Implementation 4-1] 같은 ID의 동일 payload는 효과 없이 반환하고,
        // 다른 payload는 충돌로 거절한 뒤 신규 이벤트만 투영한다.
        public synchronized void onEvent(DomainEvent event) {
            DomainEvent previous = processed.get(event.eventId());
            if (previous != null) {
                if (!previous.equals(event)) {
                    throw new IllegalArgumentException(
                        "event ID was reused with different payload"
                    );
                }
                return;
            }
            processed.put(event.eventId(), event);
            projectedOrders.add(event.orderId());
        }

        public synchronized int effectCount() {
            return projectedOrders.size();
        }
    }

    // [Implementation 5] Broker는 가용성과 실제 전달 횟수의 소유자이며,
    // 전송 실패와 소비자 처리 성공 사이의 외부 자원 경계를 재현한다.
    public static final class Broker {
        private final Consumer consumer;
        private boolean available = true;
        private int deliveryCount;

        public Broker(Consumer consumer) {
            this.consumer = consumer;
        }

        public synchronized void setAvailable(boolean available) {
            this.available = available;
        }

        public synchronized void send(DomainEvent event) {
            if (!available) {
                throw new BrokerUnavailableException();
            }
            deliveryCount++;
            consumer.onEvent(event);
        }

        public synchronized int deliveryCount() {
            return deliveryCount;
        }
    }

    // [Implementation 6] Publisher는 미발행 행의 전송 lifecycle을 조정하되,
    // 완료 근거는 broker가 수락한 뒤에만 Outbox에 기록한다.
    public static final class Publisher {
        private final Database database;
        private final Broker broker;

        public Publisher(Database database, Broker broker) {
            this.database = database;
            this.broker = broker;
        }

        // [Implementation 6-1] send 다음에 markPublished를 수행해 실패 시 재시도 근거를
        // 보존하고, send 뒤 중단은 중복 전달 가능성으로 명시적으로 드러낸다.
        public boolean publishNext(boolean crashAfterSend) {
            List<OutboxRow> pending = database.pending();
            if (pending.isEmpty()) {
                return false;
            }

            OutboxRow row = pending.get(0);
            row.recordAttempt();
            broker.send(row.event());

            if (crashAfterSend) {
                throw new SimulatedCrashException();
            }

            row.markPublished();
            return true;
        }

        // [Implementation 6-2] reconcile은 남은 행을 순서대로 비우되 broker 장애에서는
        // PENDING 상태를 보존하고 종료해 다음 실행이 같은 근거에서 재개되게 한다.
        public void reconcile() {
            while (true) {
                try {
                    if (!publishNext(false)) {
                        return;
                    }
                } catch (BrokerUnavailableException unavailable) {
                    return;
                }
            }
        }
    }


    // [Implementation 7] SagaState는 정방향 완료와 보상 진행/완료를 구분해,
    // 운영자가 아직 책임져야 할 미완료 보상을 숨기지 않는다.
    public enum SagaState {
        STARTED,
        INVENTORY_RESERVED,
        COMPENSATING,
        COMPLETED,
        CANCELLED
    }

    public static final class PaymentRejectedException extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public PaymentRejectedException() {
            super("payment rejected");
        }
    }

    public static final class CompensationUnavailableException extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public CompensationUnavailableException() {
            super("inventory compensation unavailable");
        }
    }

    // [Implementation 8] InventoryParticipant가 가용 재고와 주문별 예약/해제 효과를
    // 소유하며, 재시도 가능한 보상도 한 번의 자원 효과로 수렴시킨다.
    public static final class InventoryParticipant {
        private int available;
        private final Set<String> reservedOrders = new HashSet<>();
        private final Set<String> releasedOrders = new HashSet<>();
        private boolean releaseAvailable = true;
        private int releaseEffects;

        public InventoryParticipant(int available) {
            this.available = available;
        }

        // [Implementation 8-1] 주문별 예약 지문을 먼저 확보하고 자원이 없으면 되돌려,
        // 실패한 예약이 이후 재시도를 가로막지 않게 한다.
        public void reserve(String orderId) {
            if (!reservedOrders.add(orderId)) {
                return;
            }
            if (available <= 0) {
                reservedOrders.remove(orderId);
                throw new IllegalStateException("inventory unavailable");
            }
            available--;
        }

        public void setReleaseAvailable(boolean releaseAvailable) {
            this.releaseAvailable = releaseAvailable;
        }

        // [Implementation 8-2] 실제 예약이 있고 아직 해제하지 않은 주문만 복구하며,
        // 외부 장애에서는 해제 완료를 기록하지 않아 reconcile 근거를 남긴다.
        public void release(String orderId) {
            if (!reservedOrders.contains(orderId) || releasedOrders.contains(orderId)) {
                return;
            }
            if (!releaseAvailable) {
                throw new CompensationUnavailableException();
            }
            releasedOrders.add(orderId);
            available++;
            releaseEffects++;
        }

        public int available() {
            return available;
        }

        public int releaseEffects() {
            return releaseEffects;
        }
    }

    // [Implementation 9] PaymentParticipant는 결제 승인 여부라는 원격 실패 경계를
    // 캡슐화해 Saga가 성공과 보상 전이를 명시적으로 선택하게 한다.
    public static final class PaymentParticipant {
        private boolean accept;

        public PaymentParticipant(boolean accept) {
            this.accept = accept;
        }

        public void setAccept(boolean accept) {
            this.accept = accept;
        }

        public void charge(String orderId) {
            if (!accept) {
                throw new PaymentRejectedException();
            }
        }
    }

    // [Implementation 10] OrderSaga가 주문 단위 상태와 두 participant 호출 순서를
    // 소유해 정방향 작업과 미완료 보상의 lifecycle을 조정한다.
    public static final class OrderSaga {
        private final String orderId;
        private final InventoryParticipant inventory;
        private final PaymentParticipant payment;
        private SagaState state = SagaState.STARTED;

        public OrderSaga(
            String orderId,
            InventoryParticipant inventory,
            PaymentParticipant payment
        ) {
            this.orderId = orderId;
            this.inventory = inventory;
            this.payment = payment;
        }

        // [Implementation 10-1] 재고 예약 뒤 결제를 시도하고, 결제 거절 시에는
        // COMPENSATING을 먼저 기록한 다음 보상을 실행해 실패 상태를 관찰 가능하게 한다.
        public void execute() {
            if (state == SagaState.COMPLETED || state == SagaState.CANCELLED) {
                return;
            }
            inventory.reserve(orderId);
            state = SagaState.INVENTORY_RESERVED;
            try {
                payment.charge(orderId);
                state = SagaState.COMPLETED;
            } catch (PaymentRejectedException rejection) {
                state = SagaState.COMPENSATING;
                compensate();
            }
        }

        // [Implementation 10-2] 오직 미완료 보상 상태만 다시 실행해,
        // 완료된 Saga의 자원 효과를 반복하지 않고 남은 책임을 수렴시킨다.
        public void reconcile() {
            if (state == SagaState.COMPENSATING) {
                compensate();
            }
        }

        // [Implementation 10-3] 재고 해제가 성공한 뒤에만 CANCELLED로 전이한다.
        // 해제 예외가 발생하면 COMPENSATING이 유지되어 다음 재조정의 근거가 된다.
        private void compensate() {
            inventory.release(orderId);
            state = SagaState.CANCELLED;
        }

        public SagaState state() {
            return state;
        }
    }

    private OutboxReconciliation() {
    }
}
