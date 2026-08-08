package dev.guides.distributed.duplicate;

import java.util.HashMap;
import java.util.Map;

public final class DuplicateDelivery {
    public record Event(String eventId, String accountId, int amount) {
    }

    public static final class SimulatedCrashException extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public SimulatedCrashException() {
            super("crash after commit and before acknowledgement");
        }
    }

    public static final class EffectStore {
        private final Map<String, Integer> balances = new HashMap<>();
        private final Map<String, Integer> appliedEvents = new HashMap<>();
        private final Map<String, Event> appliedInputs = new HashMap<>();

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

    public static final class Handler {
        private final EffectStore store;

        public Handler(EffectStore store) {
            this.store = store;
        }

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
