package dev.guides.distributed.capstone;

import dev.guides.distributed.testing.Checks;
import java.util.List;

public final class ReservationFlowTest {
    public static void main(String[] args) {
        duplicateCommandReturnsOneReservation();
        overloadDoesNotChangeState();
        brokerFailureAndCrashConvergeThroughRedelivery();
        outOfOrderProjectionEventuallyConverges();
        rejectedInventoryDoesNotAllocate();
        identifiersRemainConnected();
        conflictingEventIdentitiesAreRejectedBeforeMutation();
        contradictoryTerminalTransitionsAreRejected();
        reconciliationDeadlineAndSchemaIsolationAreVerified();
    }

    private static void reconciliationDeadlineAndSchemaIsolationAreVerified() {
        ReservationFlow.SystemUnderTest system =
            new ReservationFlow.SystemUnderTest(2, 1);
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> system.submit("op-late", "corr-late", 1, 50, 50),
            "deadline이 지난 요청을 dispatch하면 안 됩니다"
        );
        Checks.equals(0, system.reservations().reservationCount(), "만료 요청은 상태를 만들면 안 됩니다");

        ReservationFlow.CommandResult command =
            system.submit("op-reconcile", "corr-reconcile", 1, 10, 100);
        system.reconcile();
        Checks.isTrue(
            system.converged(command.reservationId()),
            "재조정은 Outbox와 projection을 정본 상태로 수렴시켜야 합니다"
        );

        ReservationFlow.QueryService query = new ReservationFlow.QueryService();
        query.consume(2, new ReservationFlow.Event(
            "future-schema",
            ReservationFlow.Kind.RESERVATION_REQUESTED,
            "reservation-future",
            1,
            1,
            "corr-future",
            "op-future"
        ));
        Checks.equals(1, query.isolatedCount(), "지원하지 않는 schema를 격리해야 합니다");
        Checks.equals(null, query.status("reservation-future"), "격리 이벤트를 projection에 적용하면 안 됩니다");
    }

    private static void duplicateCommandReturnsOneReservation() {
        ReservationFlow.SystemUnderTest system =
            new ReservationFlow.SystemUnderTest(2, 3);

        ReservationFlow.CommandResult first =
            system.submit("op-1", "corr-1", 1);
        ReservationFlow.CommandResult retry =
            system.submit("op-1", "corr-1", 1);

        Checks.equals(first, retry, "같은 명령은 기존 결과를 반환해야 합니다");
        Checks.equals(
            1,
            system.reservations().reservationCount(),
            "명령 재시도가 예약을 추가하면 안 됩니다"
        );
        Checks.equals(
            1,
            system.reservations().outboxCount(),
            "명령 재시도가 Outbox 이벤트를 추가하면 안 됩니다"
        );
        Checks.equals(
            first,
            system.reservations().findByOperation("op-1"),
            "응답 유실 뒤 operation ID로 결과를 복구할 수 있어야 합니다"
        );

        Checks.throwsType(
            IllegalArgumentException.class,
            () -> system.submit("op-1", "corr-1", 2),
            "같은 operation ID를 다른 입력에 재사용하면 거절해야 합니다"
        );
    }

    private static void overloadDoesNotChangeState() {
        ReservationFlow.SystemUnderTest system =
            new ReservationFlow.SystemUnderTest(1, 3);
        system.submit("op-2", "corr-2", 1);

        Checks.throwsType(
            ReservationFlow.Overloaded.class,
            () -> system.submit("op-3", "corr-3", 1),
            "대기 상태 상한을 넘은 새 명령은 거절해야 합니다"
        );
        Checks.equals(1, system.reservations().reservationCount(), "거절 뒤 예약 수가 같아야 합니다");
        Checks.equals(1, system.reservations().outboxCount(), "거절 뒤 Outbox 수가 같아야 합니다");
    }

    private static void brokerFailureAndCrashConvergeThroughRedelivery() {
        ReservationFlow.SystemUnderTest system =
            new ReservationFlow.SystemUnderTest(2, 1);
        ReservationFlow.CommandResult command =
            system.submit("op-4", "corr-4", 1);

        system.broker().setAvailable(false);
        Checks.throwsType(
            ReservationFlow.BrokerUnavailable.class,
            () -> system.publishPending(false),
            "브로커 장애를 호출자에게 알려야 합니다"
        );
        Checks.equals(
            1,
            system.reservations().pendingOutboxCount(),
            "전송 실패 뒤 Outbox가 대기 상태여야 합니다"
        );

        system.broker().setAvailable(true);
        Checks.throwsType(
            ReservationFlow.SimulatedCrash.class,
            () -> system.publishPending(true),
            "전송 뒤 표시 전 crash를 재현해야 합니다"
        );
        Checks.equals(
            1,
            system.reservations().pendingOutboxCount(),
            "표시 전 crash 뒤 같은 이벤트를 다시 발행할 수 있어야 합니다"
        );

        system.publishPending(false);
        List<ReservationFlow.Event> sent = system.brokerMessages();
        Checks.equals(2, sent.size(), "같은 이벤트가 재전달되어야 합니다");
        Checks.equals(sent.get(0).eventId(), sent.get(1).eventId(), "재전달은 같은 event ID를 사용합니다");

        system.consumeInventoryRequests();
        Checks.equals(
            1,
            system.inventory().allocationEffects(),
            "중복 이벤트는 재고를 한 번만 줄여야 합니다"
        );
        Checks.equals(2, system.inventoryResults().size(), "두 전달 시도를 모두 관찰해야 합니다");

        system.applyInventoryResults();
        Checks.equals(
            ReservationFlow.Status.ACCEPTED,
            system.reservations().status(command.reservationId()),
            "재고 수락 결과가 예약 정본에 반영되어야 합니다"
        );
        Checks.equals(
            2,
            system.reservations().outboxCount(),
            "중복 결과가 상태 이벤트를 여러 개 만들면 안 됩니다"
        );
    }

    private static void outOfOrderProjectionEventuallyConverges() {
        ReservationFlow.SystemUnderTest system =
            new ReservationFlow.SystemUnderTest(2, 1);
        ReservationFlow.CommandResult command =
            system.submit("op-5", "corr-5", 1);
        system.publishPending(false);
        ReservationFlow.Event requested = system.brokerMessages().get(0);

        system.consumeInventoryRequests();
        system.applyInventoryResults();
        system.publishPending(false);

        ReservationFlow.Event accepted = system.brokerMessages().stream()
            .filter(event -> event.kind() == ReservationFlow.Kind.RESERVATION_ACCEPTED)
            .findFirst()
            .orElseThrow();

        system.query().consume(accepted);
        Checks.equals(
            1,
            system.query().pendingCount(command.reservationId()),
            "앞 이벤트가 없으면 상태 이벤트를 보류해야 합니다"
        );
        system.query().consume(requested);

        Checks.equals(
            ReservationFlow.Status.ACCEPTED,
            system.query().status(command.reservationId()),
            "앞 이벤트가 도착하면 연속된 보류 이벤트를 적용해야 합니다"
        );
        Checks.equals(0, system.query().pendingCount(command.reservationId()), "보류 목록이 비어야 합니다");
    }

    private static void rejectedInventoryDoesNotAllocate() {
        ReservationFlow.SystemUnderTest system =
            new ReservationFlow.SystemUnderTest(2, 0);
        ReservationFlow.CommandResult command =
            system.submit("op-6", "corr-6", 1);
        system.publishPending(false);
        system.consumeInventoryRequests();
        system.applyInventoryResults();

        Checks.equals(
            ReservationFlow.Status.REJECTED,
            system.reservations().status(command.reservationId()),
            "재고 부족 결과가 예약 거절로 수렴해야 합니다"
        );
        Checks.equals(0, system.inventory().allocationEffects(), "거절된 요청은 재고 효과가 없어야 합니다");
    }

    private static void identifiersRemainConnected() {
        ReservationFlow.SystemUnderTest system =
            new ReservationFlow.SystemUnderTest(2, 1);
        system.submit("op-7", "corr-7", 1);
        system.publishPending(false);
        ReservationFlow.Event requested = system.brokerMessages().get(0);
        system.consumeInventoryRequests();
        ReservationFlow.Event result = system.inventoryResults().get(0);
        system.applyInventoryResults();
        ReservationFlow.Event status = system.reservations().pendingOutbox().get(0);

        Checks.equals("corr-7", requested.correlationId(), "명령의 correlation ID를 이벤트에 전파해야 합니다");
        Checks.equals("op-7", requested.causationId(), "첫 이벤트는 operation ID를 원인으로 가리켜야 합니다");
        Checks.equals(requested.eventId(), result.causationId(), "재고 결과는 요청 이벤트를 원인으로 가리켜야 합니다");
        Checks.equals(result.eventId(), status.causationId(), "상태 이벤트는 재고 결과를 원인으로 가리켜야 합니다");
        Checks.equals("corr-7", status.correlationId(), "전체 흐름의 correlation ID가 같아야 합니다");
    }

    private static void conflictingEventIdentitiesAreRejectedBeforeMutation() {
        ReservationFlow.InventoryService inventory = new ReservationFlow.InventoryService(5);
        ReservationFlow.Event request = new ReservationFlow.Event(
            "request-conflict",
            ReservationFlow.Kind.RESERVATION_REQUESTED,
            "reservation-conflict",
            1,
            1,
            "corr-conflict",
            "op-conflict"
        );
        inventory.handle(request);
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> inventory.handle(
                new ReservationFlow.Event(
                    "request-conflict",
                    ReservationFlow.Kind.RESERVATION_REQUESTED,
                    "reservation-conflict",
                    1,
                    3,
                    "corr-conflict",
                    "op-conflict"
                )
            ),
            "같은 request event ID의 다른 payload를 중복으로 숨기면 안 됩니다"
        );
        Checks.equals(4, inventory.available(), "충돌 요청은 재고를 더 줄이면 안 됩니다");
        Checks.equals(1, inventory.allocationEffects(), "충돌 요청은 효과를 추가하면 안 됩니다");

        ReservationFlow.QueryService query = new ReservationFlow.QueryService();
        query.consume(new ReservationFlow.Event(
            "projection-2",
            ReservationFlow.Kind.RESERVATION_ACCEPTED,
            "reservation-q",
            2,
            1,
            "corr-q",
            "inventory-q"
        ));
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> query.consume(new ReservationFlow.Event(
                "projection-other",
                ReservationFlow.Kind.RESERVATION_REJECTED,
                "reservation-q",
                2,
                1,
                "corr-q",
                "inventory-other"
            )),
            "같은 projection sequence의 다른 이벤트를 덮어쓰면 안 됩니다"
        );
        Checks.equals(1, query.pendingCount("reservation-q"), "충돌은 기존 보류 이벤트를 보존해야 합니다");
    }

    private static void contradictoryTerminalTransitionsAreRejected() {
        ReservationFlow.ReservationService reservations =
            new ReservationFlow.ReservationService(1);
        ReservationFlow.CommandResult command =
            reservations.submit("op-terminal", "corr-terminal", 1);
        ReservationFlow.Event invalid = new ReservationFlow.Event(
            "inventory-invalid",
            ReservationFlow.Kind.INVENTORY_ACCEPTED,
            command.reservationId(),
            1,
            1,
            "wrong-correlation",
            "reservation-requested-" + command.reservationId()
        );
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> reservations.applyInventoryResult(invalid),
            "검증에 실패한 결과를 consumed로 먼저 기록하면 안 됩니다"
        );

        ReservationFlow.Event accepted = new ReservationFlow.Event(
            "inventory-accepted",
            ReservationFlow.Kind.INVENTORY_ACCEPTED,
            command.reservationId(),
            1,
            1,
            "corr-terminal",
            "reservation-requested-" + command.reservationId()
        );
        reservations.applyInventoryResult(accepted);
        Checks.equals(
            ReservationFlow.Status.ACCEPTED,
            reservations.status(command.reservationId()),
            "유효한 결과는 앞선 잘못된 전달 뒤에도 적용되어야 합니다"
        );

        ReservationFlow.Event rejected = new ReservationFlow.Event(
            "inventory-rejected",
            ReservationFlow.Kind.INVENTORY_REJECTED,
            command.reservationId(),
            1,
            1,
            "corr-terminal",
            "reservation-requested-" + command.reservationId()
        );
        Checks.throwsType(
            IllegalStateException.class,
            () -> reservations.applyInventoryResult(rejected),
            "확정 상태의 모순 terminal transition을 거절해야 합니다"
        );
        Checks.equals(
            ReservationFlow.Status.ACCEPTED,
            reservations.status(command.reservationId()),
            "모순 결과는 확정 상태를 바꾸면 안 됩니다"
        );
    }
}
