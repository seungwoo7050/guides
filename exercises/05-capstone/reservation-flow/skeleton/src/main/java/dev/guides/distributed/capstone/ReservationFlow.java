package dev.guides.distributed.capstone;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

public final class ReservationFlow {
    public enum Status {
        PENDING,
        ACCEPTED,
        REJECTED
    }

    public enum Kind {
        RESERVATION_REQUESTED,
        INVENTORY_ACCEPTED,
        INVENTORY_REJECTED,
        RESERVATION_ACCEPTED,
        RESERVATION_REJECTED
    }

    public static final class BrokerUnavailable extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public BrokerUnavailable() {
            super("broker unavailable");
        }
    }

    public static final class SimulatedCrash extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public SimulatedCrash() {
            super("crash after broker send");
        }
    }

    public static final class Overloaded extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public Overloaded() {
            super("too many pending reservations");
        }
    }

    public record CommandResult(String reservationId, Status status) {
    }

    public record Reservation(
        String reservationId,
        String operationId,
        int quantity,
        Status status,
        String correlationId
    ) {
    }

    public record Event(
        String eventId,
        Kind kind,
        String reservationId,
        int sequence,
        int quantity,
        String correlationId,
        String causationId
    ) {
    }

    public record Observation(
        String component,
        String action,
        String correlationId,
        String operationId,
        String eventId,
        String outcome
    ) {
    }

    private static final class OutboxRecord {
        private final Event event;
        private boolean published;

        private OutboxRecord(Event event) {
            this.event = event;
        }
    }

    public static final class ReservationService {
        private final int maxPending;
        private final Map<String, Reservation> reservations = new LinkedHashMap<>();
        private final Map<String, String> reservationByOperation = new HashMap<>();
        private final Map<String, Integer> inputByOperation = new HashMap<>();
        private final Map<String, String> correlationByOperation = new HashMap<>();
        private final Map<String, OutboxRecord> outbox = new LinkedHashMap<>();
        private final Map<String, Event> consumedInventoryEvents = new HashMap<>();
        private int nextReservation = 1;

        public ReservationService(int maxPending) {
            if (maxPending <= 0) {
                throw new IllegalArgumentException("maxPending must be positive");
            }
            this.maxPending = maxPending;
        }

        public CommandResult submit(
            String operationId,
            String correlationId,
            int quantity
        ) {
            if (operationId == null || operationId.isBlank()
                || correlationId == null || correlationId.isBlank()) {
                throw new IllegalArgumentException("operation and correlation IDs are required");
            }
            if (quantity <= 0) {
                throw new IllegalArgumentException("quantity must be positive");
            }
            String existingId = reservationByOperation.get(operationId);
            if (existingId != null) {
                int previousQuantity = inputByOperation.get(operationId);
                // 결함: 같은 키의 다른 입력도 기존 요청으로 잘못 취급합니다.
                Reservation existing = reservations.get(existingId);
                return new CommandResult(existing.reservationId(), existing.status());
            }
            if (pendingCount() >= maxPending) {
                throw new Overloaded();
            }

            String reservationId = "reservation-" + nextReservation++;
            Reservation reservation = new Reservation(
                reservationId,
                operationId,
                quantity,
                Status.PENDING,
                correlationId
            );
            reservations.put(reservationId, reservation);
            reservationByOperation.put(operationId, reservationId);
            inputByOperation.put(operationId, quantity);
            correlationByOperation.put(operationId, correlationId);

            Event requested = new Event(
                "reservation-requested-" + reservationId,
                Kind.RESERVATION_REQUESTED,
                reservationId,
                1,
                quantity,
                correlationId,
                operationId
            );
            outbox.put(requested.eventId(), new OutboxRecord(requested));
            return new CommandResult(reservationId, Status.PENDING);
        }

        public CommandResult findByOperation(String operationId) {
            String reservationId = reservationByOperation.get(operationId);
            if (reservationId == null) {
                return null;
            }
            Reservation reservation = reservations.get(reservationId);
            return new CommandResult(reservationId, reservation.status());
        }

        public void applyInventoryResult(Event result) {
            if (result.kind() != Kind.INVENTORY_ACCEPTED
                && result.kind() != Kind.INVENTORY_REJECTED) {
                throw new IllegalArgumentException("not an inventory result");
            }
            if (result.eventId() == null || result.eventId().isBlank()) {
                throw new IllegalArgumentException("inventory result event ID is required");
            }
            Event consumed = consumedInventoryEvents.get(result.eventId());
            if (consumed != null) {
                if (!consumed.equals(result)) {
                    throw new IllegalArgumentException(
                        "inventory result ID was reused with different payload"
                    );
                }
                return;
            }

            Reservation previous = requireReservation(result.reservationId());
            if (result.quantity() != previous.quantity()
                || !result.correlationId().equals(previous.correlationId())
                || !result.causationId().equals(
                    "reservation-requested-" + previous.reservationId()
                )) {
                throw new IllegalArgumentException("inventory result does not match reservation input");
            }
            Status nextStatus = result.kind() == Kind.INVENTORY_ACCEPTED
                ? Status.ACCEPTED
                : Status.REJECTED;
            if (previous.status() != Status.PENDING) {
                if (previous.status() != nextStatus) {
                    throw new IllegalStateException("contradictory terminal transition");
                }
                consumedInventoryEvents.put(result.eventId(), result);
                return;
            }
            consumedInventoryEvents.put(result.eventId(), result);
            Reservation updated = new Reservation(
                previous.reservationId(),
                previous.operationId(),
                previous.quantity(),
                nextStatus,
                previous.correlationId()
            );
            reservations.put(updated.reservationId(), updated);

            Kind statusKind = nextStatus == Status.ACCEPTED
                ? Kind.RESERVATION_ACCEPTED
                : Kind.RESERVATION_REJECTED;
            Event statusEvent = new Event(
                "reservation-status-" + updated.reservationId(),
                statusKind,
                updated.reservationId(),
                2,
                updated.quantity(),
                updated.correlationId(),
                result.eventId()
            );
            outbox.putIfAbsent(statusEvent.eventId(), new OutboxRecord(statusEvent));
        }

        public List<Event> pendingOutbox() {
            List<Event> pending = new ArrayList<>();
            for (OutboxRecord record : outbox.values()) {
                if (!record.published) {
                    pending.add(record.event);
                }
            }
            return List.copyOf(pending);
        }

        public void markPublished(String eventId) {
            OutboxRecord record = outbox.get(eventId);
            if (record == null) {
                throw new IllegalArgumentException("unknown outbox event: " + eventId);
            }
            record.published = true;
        }

        public int reservationCount() {
            return reservations.size();
        }

        public int pendingCount() {
            return (int) reservations.values().stream()
                .filter(reservation -> reservation.status() == Status.PENDING)
                .count();
        }

        public int outboxCount() {
            return outbox.size();
        }

        public int pendingOutboxCount() {
            return pendingOutbox().size();
        }

        public Status status(String reservationId) {
            return requireReservation(reservationId).status();
        }

        private Reservation requireReservation(String reservationId) {
            Reservation reservation = reservations.get(reservationId);
            if (reservation == null) {
                throw new IllegalArgumentException("unknown reservation: " + reservationId);
            }
            return reservation;
        }
    }

    public static final class InventoryService {
        private int available;
        private int allocationEffects;
        private final Map<String, Event> resultByRequestEvent = new HashMap<>();
        private final Map<String, Event> requestsByEventId = new HashMap<>();

        public InventoryService(int available) {
            if (available < 0) {
                throw new IllegalArgumentException("available must not be negative");
            }
            this.available = available;
        }

        public Event handle(Event request) {
            if (request.kind() != Kind.RESERVATION_REQUESTED) {
                throw new IllegalArgumentException("not a reservation request");
            }
            Event previous = resultByRequestEvent.get(request.eventId());
            if (previous != null) {
                if (!request.equals(requestsByEventId.get(request.eventId()))) {
                    throw new IllegalArgumentException(
                        "request event ID was reused with different payload"
                    );
                }
                return previous;
            }

            boolean accepted = request.quantity() <= available;
            if (accepted) {
                available -= request.quantity();
                allocationEffects++;
            }
            Event result = new Event(
                "inventory-result-" + request.reservationId(),
                accepted ? Kind.INVENTORY_ACCEPTED : Kind.INVENTORY_REJECTED,
                request.reservationId(),
                1,
                request.quantity(),
                request.correlationId(),
                request.eventId()
            );
            resultByRequestEvent.put(request.eventId(), result);
            requestsByEventId.put(request.eventId(), request);
            return result;
        }

        public int available() {
            return available;
        }

        public int allocationEffects() {
            return allocationEffects;
        }
    }

    public static final class Broker {
        private boolean available = true;
        private final List<Event> messages = new ArrayList<>();

        public void setAvailable(boolean available) {
            this.available = available;
        }

        public void send(Event event) {
            if (!available) {
                throw new BrokerUnavailable();
            }
            messages.add(event);
        }

        public List<Event> messages() {
            return List.copyOf(messages);
        }
    }

    public static final class Publisher {
        private final ReservationService reservations;
        private final Broker broker;

        public Publisher(ReservationService reservations, Broker broker) {
            this.reservations = reservations;
            this.broker = broker;
        }

        public void publishPending(boolean crashAfterFirstSend) {
            boolean first = true;
            for (Event event : reservations.pendingOutbox()) {
                broker.send(event);
                if (first && crashAfterFirstSend) {
                    throw new SimulatedCrash();
                }
                reservations.markPublished(event.eventId());
                first = false;
            }
        }
    }

    public static final class QueryService {
        private final Map<String, Status> statuses = new HashMap<>();
        private final Map<String, Integer> lastSequence = new HashMap<>();
        private final Map<String, TreeMap<Integer, Event>> pending = new HashMap<>();
        private final Map<String, Event> receivedEvents = new LinkedHashMap<>();
        private final List<Event> isolated = new ArrayList<>();

        public void consume(Event event) {
            consume(1, event);
        }

        public void consume(int schemaVersion, Event event) {
            if (schemaVersion != 1) {
                isolated.add(event);
                return;
            }
            if (event.kind() != Kind.RESERVATION_REQUESTED
                && event.kind() != Kind.RESERVATION_ACCEPTED
                && event.kind() != Kind.RESERVATION_REJECTED) {
                return;
            }
            Event received = receivedEvents.get(event.eventId());
            if (received != null) {
                if (!received.equals(event)) {
                    throw new IllegalArgumentException(
                        "projection event ID was reused with different payload"
                    );
                }
                return;
            }

            int expected = lastSequence.getOrDefault(event.reservationId(), 0) + 1;
            if (event.sequence() > expected) {
                TreeMap<Integer, Event> buffer = pending.computeIfAbsent(
                    event.reservationId(),
                    ignored -> new TreeMap<>()
                );
                Event competing = buffer.get(event.sequence());
                if (competing != null && !competing.equals(event)) {
                    throw new IllegalArgumentException(
                        "different projection events claim one sequence"
                    );
                }
                receivedEvents.put(event.eventId(), event);
                buffer.put(event.sequence(), event);
                return;
            }
            if (event.sequence() < expected) {
                receivedEvents.put(event.eventId(), event);
                return;
            }

            receivedEvents.put(event.eventId(), event);
            apply(event);
            drain(event.reservationId());
        }

        public Status status(String reservationId) {
            return statuses.get(reservationId);
        }

        public int pendingCount(String reservationId) {
            return pending.getOrDefault(reservationId, new TreeMap<>()).size();
        }

        public int isolatedCount() {
            return isolated.size();
        }

        private void drain(String reservationId) {
            TreeMap<Integer, Event> events = pending.get(reservationId);
            while (events != null) {
                int expected = lastSequence.getOrDefault(reservationId, 0) + 1;
                Event next = events.remove(expected);
                if (next == null) {
                    break;
                }
                apply(next);
                if (events.isEmpty()) {
                    pending.remove(reservationId);
                    break;
                }
            }
        }

        private void apply(Event event) {
            Status status = switch (event.kind()) {
                case RESERVATION_REQUESTED -> Status.PENDING;
                case RESERVATION_ACCEPTED -> Status.ACCEPTED;
                case RESERVATION_REJECTED -> Status.REJECTED;
                default -> throw new IllegalArgumentException("unsupported projection event");
            };
            Status previous = statuses.get(event.reservationId());
            if (previous != null && previous != Status.PENDING
                && status != previous) {
                throw new IllegalStateException("contradictory projection terminal transition");
            }
            statuses.put(event.reservationId(), status);
            lastSequence.put(event.reservationId(), event.sequence());
        }
    }

    public static final class SystemUnderTest {
        private final ReservationService reservations;
        private final InventoryService inventory;
        private final Broker broker = new Broker();
        private final Publisher publisher;
        private final QueryService query = new QueryService();
        private final List<Event> inventoryResults = new ArrayList<>();
        private final List<Observation> observations = new ArrayList<>();

        public SystemUnderTest(int maxPending, int inventoryAvailable) {
            reservations = new ReservationService(maxPending);
            inventory = new InventoryService(inventoryAvailable);
            publisher = new Publisher(reservations, broker);
        }

        public CommandResult submit(
            String operationId,
            String correlationId,
            int quantity
        ) {
            CommandResult result = reservations.submit(
                operationId,
                correlationId,
                quantity
            );
            observations.add(new Observation(
                "gateway",
                "reservation.submit",
                correlationId,
                operationId,
                null,
                "accepted"
            ));
            return result;
        }

        public CommandResult submit(
            String operationId,
            String correlationId,
            int quantity,
            long nowMillis,
            long deadlineMillis
        ) {
            if (nowMillis >= deadlineMillis) {
                throw new IllegalArgumentException("reservation deadline exceeded");
            }
            return submit(operationId, correlationId, quantity);
        }

        public void publishPending(boolean crashAfterFirstSend) {
            publisher.publishPending(crashAfterFirstSend);
        }

        public void consumeInventoryRequests() {
            for (Event event : broker.messages()) {
                if (event.kind() != Kind.RESERVATION_REQUESTED) {
                    continue;
                }
                Event result = inventory.handle(event);
                inventoryResults.add(result);
                observations.add(new Observation(
                    "inventory",
                    "inventory.result",
                    result.correlationId(),
                    null,
                    result.eventId(),
                    result.kind().name()
                ));
            }
        }

        public void applyInventoryResults() {
            for (Event result : inventoryResults) {
                reservations.applyInventoryResult(result);
            }
        }

        public void reconcile() {
            publishPending(false);
            consumeInventoryRequests();
            applyInventoryResults();
            publishPending(false);
            for (Event event : broker.messages()) {
                query.consume(event);
            }
        }

        public boolean converged(String reservationId) {
            return reservations.pendingOutboxCount() == 0
                && reservations.status(reservationId) == query.status(reservationId);
        }

        public List<Event> brokerMessages() {
            return broker.messages();
        }

        public List<Event> inventoryResults() {
            return List.copyOf(inventoryResults);
        }

        public List<Observation> observations() {
            return List.copyOf(observations);
        }

        public ReservationService reservations() {
            return reservations;
        }

        public InventoryService inventory() {
            return inventory;
        }

        public Broker broker() {
            return broker;
        }

        public QueryService query() {
            return query;
        }
    }

    private ReservationFlow() {
    }
}
