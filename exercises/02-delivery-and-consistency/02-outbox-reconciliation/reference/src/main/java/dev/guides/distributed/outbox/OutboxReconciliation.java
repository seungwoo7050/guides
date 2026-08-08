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
        private final Map<String, String> eventByOrder = new HashMap<>();
        private final Map<String, DomainEvent> eventsById = new HashMap<>();
        private final List<OutboxRow> outbox = new ArrayList<>();

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

    public static final class Consumer {
        private final Map<String, DomainEvent> processed = new HashMap<>();
        private final Set<String> projectedOrders = new HashSet<>();

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
            broker.send(row.event());

            if (crashAfterSend) {
                throw new SimulatedCrashException();
            }

            row.markPublished();
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
        private final Set<String> releasedOrders = new HashSet<>();
        private boolean releaseAvailable = true;
        private int releaseEffects;

        public InventoryParticipant(int available) {
            this.available = available;
        }

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

        public void reconcile() {
            if (state == SagaState.COMPENSATING) {
                compensate();
            }
        }

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
