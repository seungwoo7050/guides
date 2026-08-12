package dev.guides.distributed.capstone;

import java.util.ArrayList;
import java.util.ArrayDeque;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.OptionalLong;
import java.util.Queue;
import java.util.TreeMap;

public final class ReservationFlow {
    public enum Status {
        PENDING,
        UNKNOWN,
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

    public static final class DeadlineExceeded extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public DeadlineExceeded() {
            super("reservation deadline exceeded");
        }
    }

    public static final class InventoryQueryUnavailable extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public InventoryQueryUnavailable() {
            super("inventory operation lookup unavailable");
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

    public record EventEnvelope(int schemaVersion, Event event) {
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

    public enum ReconciliationOutcome {
        APPLIED,
        PENDING_NOT_FOUND,
        PENDING_SOURCE_UNAVAILABLE
    }

    public record ReconciliationRecord(
        String operationId,
        String reservationId,
        ReconciliationOutcome outcome,
        long nextAttemptAtMillis
    ) {
    }

    public record DispatchTask(
        String operationId,
        String correlationId,
        int quantity,
        long deadlineMillis
    ) {
    }

    private static final class OutboxRecord {
        private final Event event;
        private final long createdAtMillis;
        private boolean published;

        private OutboxRecord(Event event, long createdAtMillis) {
            this.event = event;
            this.createdAtMillis = createdAtMillis;
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
            return submit(operationId, correlationId, quantity, 0L);
        }

        public CommandResult submit(
            String operationId,
            String correlationId,
            int quantity,
            long nowMillis
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
            outbox.put(requested.eventId(), new OutboxRecord(requested, nowMillis));
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
            applyInventoryResult(result, 0L);
        }

        public void applyInventoryResult(Event result, long nowMillis) {
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
            if (previous.status() != Status.PENDING
                && previous.status() != Status.UNKNOWN) {
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
            outbox.putIfAbsent(
                statusEvent.eventId(),
                new OutboxRecord(statusEvent, nowMillis)
            );
        }

        public void markUnknown(String reservationId) {
            Reservation previous = requireReservation(reservationId);
            if (previous.status() == Status.PENDING) {
                reservations.put(
                    reservationId,
                    new Reservation(
                        previous.reservationId(),
                        previous.operationId(),
                        previous.quantity(),
                        Status.UNKNOWN,
                        previous.correlationId()
                    )
                );
            }
        }

        public void markPending(String reservationId) {
            Reservation previous = requireReservation(reservationId);
            if (previous.status() == Status.UNKNOWN) {
                reservations.put(
                    reservationId,
                    new Reservation(
                        previous.reservationId(),
                        previous.operationId(),
                        previous.quantity(),
                        Status.PENDING,
                        previous.correlationId()
                    )
                );
            }
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
                .filter(reservation -> reservation.status() == Status.PENDING
                    || reservation.status() == Status.UNKNOWN)
                .count();
        }

        public int outboxCount() {
            return outbox.size();
        }

        public int pendingOutboxCount() {
            return pendingOutbox().size();
        }

        public OptionalLong oldestPendingOutboxAge(long nowMillis) {
            return outbox.values().stream()
                .filter(record -> !record.published)
                .mapToLong(record -> Math.max(0L, nowMillis - record.createdAtMillis))
                .max();
        }

        public List<Reservation> pendingReservations() {
            return reservations.values().stream()
                .filter(reservation -> reservation.status() == Status.PENDING
                    || reservation.status() == Status.UNKNOWN)
                .toList();
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
        private final Map<String, Event> requestsByOperation = new HashMap<>();
        private final Map<String, Event> resultByOperation = new HashMap<>();
        private final List<String> lookupOperations = new ArrayList<>();
        private boolean lookupAvailable = true;

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
            Event previousOperation = requestsByOperation.get(request.causationId());
            if (previousOperation != null) {
                if (!sameOperationInput(previousOperation, request)) {
                    throw new IllegalArgumentException(
                        "inventory operation ID was reused with different input"
                    );
                }
                Event operationResult = resultByOperation.get(request.causationId());
                requestsByEventId.put(request.eventId(), request);
                resultByRequestEvent.put(request.eventId(), operationResult);
                return operationResult;
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
            requestsByOperation.put(request.causationId(), request);
            resultByOperation.put(request.causationId(), result);
            return result;
        }

        private static boolean sameOperationInput(Event left, Event right) {
            return left.kind() == right.kind()
                && left.reservationId().equals(right.reservationId())
                && left.sequence() == right.sequence()
                && left.quantity() == right.quantity()
                && left.correlationId().equals(right.correlationId())
                && left.causationId().equals(right.causationId());
        }

        public Event findResultByOperation(String operationId) {
            lookupOperations.add(operationId);
            if (!lookupAvailable) {
                throw new InventoryQueryUnavailable();
            }
            return resultByOperation.get(operationId);
        }

        public void setLookupAvailable(boolean lookupAvailable) {
            this.lookupAvailable = lookupAvailable;
        }

        public List<String> lookupOperations() {
            return List.copyOf(lookupOperations);
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
        private final Map<String, TreeMap<Integer, Event>> claimedSequences = new HashMap<>();
        private final Map<String, EventEnvelope> receivedEvents = new LinkedHashMap<>();
        private final List<Event> isolated = new ArrayList<>();

        public void consume(Event event) {
            consume(new EventEnvelope(1, event));
        }

        public void consume(int schemaVersion, Event event) {
            consume(new EventEnvelope(schemaVersion, event));
        }

        public void consume(EventEnvelope envelope) {
            int schemaVersion = envelope.schemaVersion();
            Event event = envelope.event();
            EventEnvelope received = receivedEvents.get(event.eventId());
            if (received != null) {
                if (!received.equals(envelope)) {
                    throw new IllegalArgumentException(
                        "projection event ID was reused with different payload"
                    );
                }
                return;
            }
            if (schemaVersion != 1) {
                receivedEvents.put(event.eventId(), envelope);
                isolated.add(event);
                return;
            }
            if (event.kind() != Kind.RESERVATION_REQUESTED
                && event.kind() != Kind.RESERVATION_ACCEPTED
                && event.kind() != Kind.RESERVATION_REJECTED) {
                receivedEvents.put(event.eventId(), envelope);
                return;
            }
            validateProjectionSequence(event);
            TreeMap<Integer, Event> claims = claimedSequences.get(event.reservationId());
            Event claimed = claims == null ? null : claims.get(event.sequence());
            if (claimed != null && !claimed.equals(event)) {
                throw new IllegalArgumentException(
                    "different projection events claim one sequence"
                );
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
                receivedEvents.put(event.eventId(), envelope);
                if (claims == null) {
                    claims = new TreeMap<>();
                    claimedSequences.put(event.reservationId(), claims);
                }
                claims.put(event.sequence(), event);
                buffer.put(event.sequence(), event);
                return;
            }
            if (event.sequence() < expected) {
                if (claimed == null) {
                    throw new IllegalArgumentException(
                        "late event claims an already applied sequence"
                    );
                }
                receivedEvents.put(event.eventId(), envelope);
                return;
            }

            apply(event);
            receivedEvents.put(event.eventId(), envelope);
            if (claims == null) {
                claims = new TreeMap<>();
                claimedSequences.put(event.reservationId(), claims);
            }
            claims.put(event.sequence(), event);
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

        public void rebuild(List<EventEnvelope> history) {
            statuses.clear();
            lastSequence.clear();
            pending.clear();
            claimedSequences.clear();
            receivedEvents.clear();
            isolated.clear();
            for (EventEnvelope envelope : history) {
                consume(envelope);
            }
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

        private static void validateProjectionSequence(Event event) {
            boolean creation = event.kind() == Kind.RESERVATION_REQUESTED
                && event.sequence() == 1;
            boolean terminal = (event.kind() == Kind.RESERVATION_ACCEPTED
                || event.kind() == Kind.RESERVATION_REJECTED)
                && event.sequence() == 2;
            if (!creation && !terminal) {
                throw new IllegalArgumentException(
                    "reservation projection requires REQUESTED sequence 1 and terminal sequence 2"
                );
            }
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
        private final List<ReconciliationRecord> reconciliationRecords = new ArrayList<>();

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
                throw new DeadlineExceeded();
            }
            CommandResult result = reservations.submit(
                operationId,
                correlationId,
                quantity,
                nowMillis
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
            reconcilePending(0L, 1L);
            publishPending(false);
            for (Event event : broker.messages()) {
                query.consume(event);
            }
        }

        public List<ReconciliationRecord> reconcilePending(
            long nowMillis,
            long retryDelayMillis
        ) {
            if (retryDelayMillis <= 0) {
                throw new IllegalArgumentException("retry delay must be positive");
            }
            List<ReconciliationRecord> current = new ArrayList<>();
            for (Reservation reservation : reservations.pendingReservations()) {
                ReconciliationRecord record;
                try {
                    Event result = inventory.findResultByOperation(
                        reservation.operationId()
                    );
                    if (result == null) {
                        reservations.markPending(reservation.reservationId());
                        record = new ReconciliationRecord(
                            reservation.operationId(),
                            reservation.reservationId(),
                            ReconciliationOutcome.PENDING_NOT_FOUND,
                            nowMillis + retryDelayMillis
                        );
                    } else {
                        reservations.applyInventoryResult(result, nowMillis);
                        record = new ReconciliationRecord(
                            reservation.operationId(),
                            reservation.reservationId(),
                            ReconciliationOutcome.APPLIED,
                            0L
                        );
                    }
                } catch (InventoryQueryUnavailable unavailable) {
                    reservations.markUnknown(reservation.reservationId());
                    record = new ReconciliationRecord(
                        reservation.operationId(),
                        reservation.reservationId(),
                        ReconciliationOutcome.PENDING_SOURCE_UNAVAILABLE,
                        nowMillis + retryDelayMillis
                    );
                }
                current.add(record);
                reconciliationRecords.add(record);
            }
            return List.copyOf(current);
        }

        public boolean converged(String reservationId) {
            Status authoritative = reservations.status(reservationId);
            boolean terminal = authoritative == Status.ACCEPTED
                || authoritative == Status.REJECTED;
            return terminal
                && reservations.pendingOutboxCount() == 0
                && authoritative == query.status(reservationId);
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

        public List<ReconciliationRecord> reconciliationRecords() {
            return List.copyOf(reconciliationRecords);
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

    public static final class Dispatcher {
        private final SystemUnderTest system;
        private final int maxRunning;
        private final int maxQueued;
        private final Queue<DispatchTask> queued = new ArrayDeque<>();
        private final Map<DispatchTask, Integer> runningTasks = new HashMap<>();
        private int runningCount;

        public Dispatcher(SystemUnderTest system, int maxRunning, int maxQueued) {
            if (maxRunning <= 0 || maxQueued <= 0) {
                throw new IllegalArgumentException("dispatcher limits must be positive");
            }
            this.system = system;
            this.maxRunning = maxRunning;
            this.maxQueued = maxQueued;
        }

        public void enqueue(DispatchTask task, long nowMillis) {
            if (task == null || nowMillis >= task.deadlineMillis()) {
                throw new DeadlineExceeded();
            }
            if (queued.size() >= maxQueued) {
                throw new Overloaded();
            }
            queued.add(task);
        }

        public DispatchTask beginNext(long nowMillis) {
            if (runningCount >= maxRunning) {
                throw new Overloaded();
            }
            DispatchTask task = queued.poll();
            if (task == null) {
                return null;
            }
            if (nowMillis >= task.deadlineMillis()) {
                throw new DeadlineExceeded();
            }
            runningTasks.merge(task, 1, Integer::sum);
            runningCount++;
            return task;
        }

        public CommandResult execute(DispatchTask task, long nowMillis) {
            if (runningTasks.getOrDefault(task, 0) == 0) {
                throw new IllegalStateException("dispatch task is not running");
            }
            return system.submit(
                task.operationId(),
                task.correlationId(),
                task.quantity(),
                nowMillis,
                task.deadlineMillis()
            );
        }

        public void complete(DispatchTask task) {
            int count = runningTasks.getOrDefault(task, 0);
            if (count == 0) {
                throw new IllegalStateException("dispatch task is not running");
            }
            if (count == 1) {
                runningTasks.remove(task);
            } else {
                runningTasks.put(task, count - 1);
            }
            runningCount--;
        }

        public int queuedCount() {
            return queued.size();
        }

        public int runningCount() {
            return runningCount;
        }
    }

    private ReservationFlow() {
    }
}
