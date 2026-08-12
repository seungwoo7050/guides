package dev.guides.distributed.capstone;

import dev.guides.distributed.testing.Checks;
import java.util.ArrayList;
import java.util.Collections;
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
        dispatcherQueueDeadlineAndRetryAreBounded();
        outboxAgeReconciliationAndReplayAreObservable();
        pendingAgreementIsNotConvergence();
    }

    private static void dispatcherQueueDeadlineAndRetryAreBounded() {
        ReservationFlow.SystemUnderTest system =
            new ReservationFlow.SystemUnderTest(4, 2);
        ReservationFlow.Dispatcher dispatcher =
            new ReservationFlow.Dispatcher(system, 1, 1);
        ReservationFlow.DispatchTask first = new ReservationFlow.DispatchTask(
            "op-dispatch",
            "corr-dispatch",
            1,
            100
        );
        dispatcher.enqueue(first, 10);
        Checks.throwsType(
            ReservationFlow.Overloaded.class,
            () -> dispatcher.enqueue(
                new ReservationFlow.DispatchTask("op-overflow", "corr-overflow", 1, 100),
                10
            ),
            "queue 상한을 넘은 작업은 상태 변경 전에 거절해야 합니다"
        );
        Checks.equals(0, system.reservations().reservationCount(), "queue 거절은 예약을 만들면 안 됩니다");

        ReservationFlow.DispatchTask running = dispatcher.beginNext(20);
        dispatcher.enqueue(
            new ReservationFlow.DispatchTask("op-expired", "corr-expired", 1, 50),
            20
        );
        Checks.throwsType(
            ReservationFlow.Overloaded.class,
            () -> dispatcher.beginNext(20),
            "동시 실행 상한을 넘겨 시작하면 안 됩니다"
        );
        ReservationFlow.CommandResult accepted = dispatcher.execute(running, 20);
        ReservationFlow.CommandResult retry = dispatcher.execute(running, 20);
        Checks.equals(accepted, retry, "dispatch 재시도는 같은 operation ID와 deadline을 사용해야 합니다");
        dispatcher.complete(running);
        Checks.throwsType(
            ReservationFlow.DeadlineExceeded.class,
            () -> dispatcher.beginNext(50),
            "queue에서 deadline이 지난 작업을 실행하면 안 됩니다"
        );
        Checks.equals(1, system.reservations().reservationCount(), "만료된 queue 작업은 상태를 만들면 안 됩니다");
        Checks.equals(0, dispatcher.runningCount(), "완료 뒤 running slot을 반환해야 합니다");
        Checks.equals(0, dispatcher.queuedCount(), "만료된 작업을 queue에서 제거해야 합니다");

        ReservationFlow.Dispatcher duplicateOperations =
            new ReservationFlow.Dispatcher(system, 2, 3);
        ReservationFlow.DispatchTask duplicate = new ReservationFlow.DispatchTask(
            "op-duplicate-running",
            "corr-duplicate-running",
            1,
            100
        );
        duplicateOperations.enqueue(duplicate, 10);
        duplicateOperations.enqueue(duplicate, 10);
        duplicateOperations.enqueue(
            new ReservationFlow.DispatchTask("op-third", "corr-third", 1, 100),
            10
        );
        ReservationFlow.DispatchTask duplicateFirst = duplicateOperations.beginNext(20);
        ReservationFlow.DispatchTask duplicateSecond = duplicateOperations.beginNext(20);
        Checks.equals(2, duplicateOperations.runningCount(), "같은 operation의 실행도 각각 slot을 차지해야 합니다");
        Checks.throwsType(
            ReservationFlow.Overloaded.class,
            () -> duplicateOperations.beginNext(20),
            "같은 operation ID가 running 상한 계산을 우회하면 안 됩니다"
        );
        Checks.equals(1, duplicateOperations.queuedCount(), "상한 거절은 다음 queue 작업을 보존해야 합니다");
        duplicateOperations.complete(duplicateFirst);
        ReservationFlow.DispatchTask third = duplicateOperations.beginNext(20);
        Checks.equals("op-third", third.operationId(), "slot 반환 뒤 보존한 queue 작업을 시작해야 합니다");
        duplicateOperations.complete(duplicateSecond);
        duplicateOperations.complete(third);
        Checks.equals(0, duplicateOperations.runningCount(), "중복 operation 실행의 slot을 모두 반환해야 합니다");
    }

    private static void outboxAgeReconciliationAndReplayAreObservable() {
        ReservationFlow.SystemUnderTest ageSystem =
            new ReservationFlow.SystemUnderTest(3, 2);
        ageSystem.submit("op-newer", "corr-newer", 1, 25, 100);
        ageSystem.submit("op-older", "corr-older", 1, 10, 100);
        Checks.equals(
            30L,
            ageSystem.reservations().oldestPendingOutboxAge(40).orElseThrow(),
            "가장 오래된 Outbox 대기 시간을 모든 pending 레코드에서 계산해야 합니다"
        );
        ageSystem.publishPending(false);
        Checks.isTrue(
            ageSystem.reservations().oldestPendingOutboxAge(40).isEmpty(),
            "발행 완료 뒤 pending Outbox age가 없어야 합니다"
        );

        ReservationFlow.SystemUnderTest system =
            new ReservationFlow.SystemUnderTest(3, 2);
        ReservationFlow.CommandResult command =
            system.submit("op-authoritative", "corr-authoritative", 1, 10, 100);
        system.publishPending(false);
        system.consumeInventoryRequests();

        system.inventory().setLookupAvailable(false);
        List<ReservationFlow.ReconciliationRecord> unavailable =
            system.reconcilePending(50, 25);
        Checks.equals(
            ReservationFlow.ReconciliationOutcome.PENDING_SOURCE_UNAVAILABLE,
            unavailable.get(0).outcome(),
            "정본 조회 실패를 자동 성공이나 보상으로 숨기면 안 됩니다"
        );
        Checks.equals(75L, unavailable.get(0).nextAttemptAtMillis(), "다음 재조정 시각을 남겨야 합니다");
        Checks.equals(
            ReservationFlow.Status.UNKNOWN,
            system.reservations().status(command.reservationId()),
            "확정할 수 없는 결과를 UNKNOWN으로 드러내야 합니다"
        );

        system.inventory().setLookupAvailable(true);
        List<ReservationFlow.ReconciliationRecord> applied =
            system.reconcilePending(75, 25);
        Checks.equals(
            ReservationFlow.ReconciliationOutcome.APPLIED,
            applied.get(0).outcome(),
            "다음 재조정은 inventory 정본 결과를 적용해야 합니다"
        );
        Checks.equals(
            List.of("op-authoritative", "op-authoritative"),
            system.inventory().lookupOperations(),
            "재조정은 처음 operation ID로 정본을 조회해야 합니다"
        );
        system.publishPending(false);

        List<ReservationFlow.EventEnvelope> replay = new ArrayList<>();
        for (ReservationFlow.Event event : system.brokerMessages()) {
            replay.add(new ReservationFlow.EventEnvelope(1, event));
        }
        ReservationFlow.Event replayedUnsupported = new ReservationFlow.Event(
            "rebuild-future-schema",
            ReservationFlow.Kind.RESERVATION_REQUESTED,
            "rebuild-future-reservation",
            1,
            1,
            "rebuild-future-correlation",
            "rebuild-future-operation"
        );
        replay.add(new ReservationFlow.EventEnvelope(2, replayedUnsupported));
        Collections.reverse(replay);
        ReservationFlow.QueryService rebuilt = new ReservationFlow.QueryService();
        ReservationFlow.Event requested = replay.stream()
            .map(ReservationFlow.EventEnvelope::event)
            .filter(event -> event.kind() == ReservationFlow.Kind.RESERVATION_REQUESTED
                && event.reservationId().equals(command.reservationId()))
            .findFirst()
            .orElseThrow();
        rebuilt.consume(requested);
        rebuilt.consume(new ReservationFlow.Event(
            "old-gap",
            ReservationFlow.Kind.RESERVATION_ACCEPTED,
            "old-reservation",
            2,
            1,
            "old-correlation",
            "old-operation"
        ));
        rebuilt.consume(2, new ReservationFlow.Event(
            "old-isolated",
            ReservationFlow.Kind.RESERVATION_REQUESTED,
            "isolated-reservation",
            1,
            1,
            "isolated-correlation",
            "isolated-operation"
        ));
        rebuilt.rebuild(replay);
        Checks.equals(
            ReservationFlow.Status.ACCEPTED,
            rebuilt.status(command.reservationId()),
            "전체 replay가 순서 역전 뒤에도 projection을 재구축해야 합니다"
        );
        Checks.equals(0, rebuilt.pendingCount(command.reservationId()), "replay 뒤 gap이 남으면 안 됩니다");
        Checks.equals(null, rebuilt.status("old-reservation"), "rebuild는 기존 projection 상태를 비워야 합니다");
        Checks.equals(0, rebuilt.pendingCount("old-reservation"), "rebuild는 기존 sequence gap을 비워야 합니다");
        Checks.equals(1, rebuilt.isolatedCount(), "rebuild 이력의 지원하지 않는 schema를 다시 격리해야 합니다");
        Checks.equals(
            null,
            rebuilt.status(replayedUnsupported.reservationId()),
            "rebuild가 schema envelope를 잃고 지원하지 않는 이벤트를 적용하면 안 됩니다"
        );
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> rebuilt.consume(3, replayedUnsupported),
            "rebuild는 격리한 이벤트의 schema-version identity도 복구해야 합니다"
        );
        rebuilt.consume(new ReservationFlow.Event(
            "new-old-sequence",
            ReservationFlow.Kind.RESERVATION_REQUESTED,
            "old-reservation",
            1,
            1,
            "new-correlation",
            "new-operation"
        ));
        Checks.equals(
            ReservationFlow.Status.PENDING,
            rebuilt.status("old-reservation"),
            "rebuild 뒤 과거 sequence claim이 새 replay를 막으면 안 됩니다"
        );

        ReservationFlow.SystemUnderTest notFound =
            new ReservationFlow.SystemUnderTest(1, 1);
        ReservationFlow.CommandResult pending =
            notFound.submit("op-not-found", "corr-not-found", 1, 5, 100);
        notFound.inventory().setLookupAvailable(false);
        notFound.reconcilePending(15, 5);
        Checks.equals(
            ReservationFlow.Status.UNKNOWN,
            notFound.reservations().status(pending.reservationId()),
            "정본 조회 실패는 UNKNOWN을 드러내야 합니다"
        );
        notFound.inventory().setLookupAvailable(true);
        List<ReservationFlow.ReconciliationRecord> absent =
            notFound.reconcilePending(20, 10);
        Checks.equals(
            ReservationFlow.ReconciliationOutcome.PENDING_NOT_FOUND,
            absent.get(0).outcome(),
            "정본에 결과가 없으면 PENDING과 다음 행동을 보존해야 합니다"
        );
        Checks.equals(
            ReservationFlow.Status.PENDING,
            notFound.reservations().status(pending.reservationId()),
            "조회 결과 없음은 자동 성공이나 자동 보상이 아니어야 합니다"
        );
    }

    private static void reconciliationDeadlineAndSchemaIsolationAreVerified() {
        ReservationFlow.SystemUnderTest system =
            new ReservationFlow.SystemUnderTest(2, 1);
        Checks.throwsType(
            ReservationFlow.DeadlineExceeded.class,
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
        ReservationFlow.Event future = new ReservationFlow.Event(
            "future-schema",
            ReservationFlow.Kind.RESERVATION_REQUESTED,
            "reservation-future",
            1,
            1,
            "corr-future",
            "op-future"
        );
        query.consume(2, future);
        query.consume(2, future);
        Checks.equals(1, query.isolatedCount(), "지원하지 않는 schema를 격리해야 합니다");
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> query.consume(2, new ReservationFlow.Event(
                "future-schema",
                ReservationFlow.Kind.RESERVATION_REQUESTED,
                "reservation-future",
                1,
                2,
                "corr-future",
                "op-future"
            )),
            "격리된 event ID의 다른 payload도 충돌로 거절해야 합니다"
        );
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> query.consume(3, future),
            "같은 event ID를 다른 schema envelope로 재사용하면 안 됩니다"
        );
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
        ReservationFlow.Event firstResult = inventory.handle(request);
        ReservationFlow.Event retryResult = inventory.handle(
            new ReservationFlow.Event(
                "request-retry",
                ReservationFlow.Kind.RESERVATION_REQUESTED,
                "reservation-conflict",
                1,
                1,
                "corr-conflict",
                "op-conflict"
            )
        );
        Checks.equals(firstResult, retryResult, "같은 inventory operation 재시도는 기존 결과를 반환해야 합니다");
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> inventory.handle(
                new ReservationFlow.Event(
                    "request-retry",
                    ReservationFlow.Kind.RESERVATION_REQUESTED,
                    "reservation-conflict",
                    1,
                    1,
                    "corr-conflict",
                    "op-alias-conflict"
                )
            ),
            "같은 operation의 alias event ID도 claim해 이후 다른 operation 재사용을 막아야 합니다"
        );
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
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> inventory.handle(
                new ReservationFlow.Event(
                    "request-other",
                    ReservationFlow.Kind.RESERVATION_REQUESTED,
                    "reservation-conflict",
                    1,
                    2,
                    "corr-conflict",
                    "op-conflict"
                )
            ),
            "같은 inventory operation ID의 다른 payload를 새 event로 숨기면 안 됩니다"
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

        ReservationFlow.QueryService applied = new ReservationFlow.QueryService();
        applied.consume(new ReservationFlow.Event(
            "projection-applied",
            ReservationFlow.Kind.RESERVATION_REQUESTED,
            "reservation-applied",
            1,
            1,
            "corr-applied",
            "op-applied"
        ));
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> applied.consume(new ReservationFlow.Event(
                "projection-late-conflict",
                ReservationFlow.Kind.RESERVATION_REQUESTED,
                "reservation-applied",
                1,
                1,
                "corr-applied",
                "op-applied"
            )),
            "이미 적용된 projection sequence를 다른 event가 다시 주장하면 안 됩니다"
        );
        Checks.equals(
            ReservationFlow.Status.PENDING,
            applied.status("reservation-applied"),
            "적용 뒤 sequence 충돌은 기존 projection을 바꾸면 안 됩니다"
        );
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

        ReservationFlow.QueryService query = new ReservationFlow.QueryService();
        query.consume(new ReservationFlow.Event(
            "query-requested",
            ReservationFlow.Kind.RESERVATION_REQUESTED,
            "query-terminal",
            1,
            1,
            "query-correlation",
            "query-operation"
        ));
        query.consume(new ReservationFlow.Event(
            "query-accepted",
            ReservationFlow.Kind.RESERVATION_ACCEPTED,
            "query-terminal",
            2,
            1,
            "query-correlation",
            "query-requested"
        ));
        ReservationFlow.Event contradictory = new ReservationFlow.Event(
            "query-rejected",
            ReservationFlow.Kind.RESERVATION_REJECTED,
            "query-terminal",
            2,
            1,
            "query-correlation",
            "query-accepted"
        );
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> query.consume(contradictory),
            "projection 모순을 event ledger에 기록하기 전에 거절해야 합니다"
        );
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> query.consume(contradictory),
            "같은 모순 projection 재시도도 duplicate로 숨기면 안 됩니다"
        );
        Checks.equals(
            ReservationFlow.Status.ACCEPTED,
            query.status("query-terminal"),
            "모순 projection 재시도가 확정 상태를 바꾸면 안 됩니다"
        );

        ReservationFlow.QueryService outOfOrder = new ReservationFlow.QueryService();
        ReservationFlow.Event impossibleBufferedTerminal = new ReservationFlow.Event(
            "query-impossible-buffered-terminal",
            ReservationFlow.Kind.RESERVATION_REJECTED,
            "query-out-of-order-terminal",
            3,
            1,
            "query-out-of-order-correlation",
            "query-out-of-order-operation"
        );
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> outOfOrder.consume(impossibleBufferedTerminal),
            "순서 역전으로 보이는 잘못된 terminal sequence를 ledger나 buffer에 기록하면 안 됩니다"
        );
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> outOfOrder.consume(impossibleBufferedTerminal),
            "잘못된 terminal sequence 재시도도 duplicate로 숨기면 안 됩니다"
        );
        outOfOrder.consume(new ReservationFlow.Event(
            "query-out-of-order-requested",
            ReservationFlow.Kind.RESERVATION_REQUESTED,
            "query-out-of-order-terminal",
            1,
            1,
            "query-out-of-order-correlation",
            "query-out-of-order-operation"
        ));
        outOfOrder.consume(new ReservationFlow.Event(
            "query-out-of-order-accepted",
            ReservationFlow.Kind.RESERVATION_ACCEPTED,
            "query-out-of-order-terminal",
            2,
            1,
            "query-out-of-order-correlation",
            "query-out-of-order-requested"
        ));
        Checks.equals(
            ReservationFlow.Status.ACCEPTED,
            outOfOrder.status("query-out-of-order-terminal"),
            "거절한 잘못된 buffer 후보가 뒤의 유효한 생성·terminal projection을 막으면 안 됩니다"
        );
        Checks.equals(
            0,
            outOfOrder.pendingCount("query-out-of-order-terminal"),
            "거절한 잘못된 sequence가 pending buffer에 남으면 안 됩니다"
        );
    }

    private static void pendingAgreementIsNotConvergence() {
        ReservationFlow.SystemUnderTest system =
            new ReservationFlow.SystemUnderTest(2, 1);
        ReservationFlow.CommandResult command =
            system.submit("op-pending", "corr-pending", 1);
        system.publishPending(false);
        system.query().consume(system.brokerMessages().get(0));

        Checks.equals(
            ReservationFlow.Status.PENDING,
            system.reservations().status(command.reservationId()),
            "terminal 결과 전에는 reservation 정본이 PENDING이어야 합니다"
        );
        Checks.equals(
            ReservationFlow.Status.PENDING,
            system.query().status(command.reservationId()),
            "생성 event만 투영하면 query도 PENDING이어야 합니다"
        );
        Checks.equals(0, system.reservations().pendingOutboxCount(), "첫 event는 발행 완료 상태여야 합니다");
        Checks.isFalse(
            system.converged(command.reservationId()),
            "정본과 projection이 같은 PENDING이어도 업무가 수렴한 것은 아닙니다"
        );
    }
}
