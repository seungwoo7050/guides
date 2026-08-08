package dev.guides.distributed.outbox;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public final class OutboxReconciliation {
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

    public static final class Database {
        private final Map<String, String> orders = new HashMap<>();
        private final List<OutboxRow> outbox = new ArrayList<>();

        public synchronized void createOrder(String orderId, String eventId) {
            if (orders.containsKey(orderId)) {
                return;
            }
            orders.put(orderId, "CREATED");
            outbox.add(new OutboxRow(new DomainEvent(eventId, orderId)));
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

    public static final class Consumer {
        private final Set<String> processed = new HashSet<>();
        private final Set<String> projectedOrders = new HashSet<>();

        public synchronized void onEvent(DomainEvent event) {
            if (!processed.add(event.eventId())) {
                return;
            }
            projectedOrders.add(event.orderId());
        }

        public synchronized int effectCount() {
            return projectedOrders.size();
        }
    }

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

    public static final class Publisher {
        private final Database database;
        private final Broker broker;

        public Publisher(Database database, Broker broker) {
            this.database = database;
            this.broker = broker;
        }

        public boolean publishNext(boolean crashAfterSend) {
            List<OutboxRow> pending = database.pending();
            if (pending.isEmpty()) {
                return false;
            }

            OutboxRow row = pending.get(0);
            row.recordAttempt();

            // 결함: 실제 발행보다 먼저 완료로 표시합니다.
            row.markPublished();
            broker.send(row.event());

            if (crashAfterSend) {
                throw new SimulatedCrashException();
            }
            return true;
        }

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

    public static final class InventoryParticipant {
        private int available;
        private final Set<String> reservedOrders = new HashSet<>();
        private boolean releaseAvailable = true;
        private int releaseEffects;

        public InventoryParticipant(int available) {
            this.available = available;
        }

        public void reserve(String orderId) {
            if (reservedOrders.add(orderId)) {
                available--;
            }
        }

        public void setReleaseAvailable(boolean releaseAvailable) {
            this.releaseAvailable = releaseAvailable;
        }

        public void release(String orderId) {
            if (!releaseAvailable) {
                throw new CompensationUnavailableException();
            }
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

        public void execute() {
            inventory.reserve(orderId);
            state = SagaState.INVENTORY_RESERVED;
            try {
                payment.charge(orderId);
                state = SagaState.COMPLETED;
            } catch (PaymentRejectedException rejection) {
                state = SagaState.CANCELLED;
                try {
                    inventory.release(orderId);
                } catch (CompensationUnavailableException ignored) {
                    // The skeleton hides an unfinished compensation.
                }
            }
        }

        public void reconcile() {
            // The skeleton loses the fact that compensation is still required.
        }

        public SagaState state() {
            return state;
        }
    }

    private OutboxReconciliation() {
    }
}
