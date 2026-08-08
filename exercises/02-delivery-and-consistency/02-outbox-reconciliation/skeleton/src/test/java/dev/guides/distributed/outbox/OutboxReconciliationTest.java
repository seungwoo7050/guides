package dev.guides.distributed.outbox;

import dev.guides.distributed.testing.Checks;

public final class OutboxReconciliationTest {
    public static void main(String[] args) {
        stateAndOutboxAreCreatedTogether();
        brokerFailureLeavesPendingWork();
        crashAfterPublishCanBeReconciledWithoutDuplicateEffect();
        failedPaymentCompensatesInventory();
        failedCompensationRemainsRecoverable();
        conflictingIdentifiersAreRejected();
    }

    private static void conflictingIdentifiersAreRejected() {
        OutboxReconciliation.Database database = new OutboxReconciliation.Database();
        database.createOrder("order-conflict", "event-original");
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> database.createOrder("order-conflict", "event-other"),
            "같은 주문을 다른 이벤트 ID로 조용히 재사용하면 안 됩니다"
        );

        OutboxReconciliation.Consumer consumer = new OutboxReconciliation.Consumer();
        consumer.onEvent(new OutboxReconciliation.DomainEvent("event-c", "order-a"));
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> consumer.onEvent(
                new OutboxReconciliation.DomainEvent("event-c", "order-b")
            ),
            "같은 event ID의 다른 payload는 중복으로 숨기면 안 됩니다"
        );
        Checks.equals(1, consumer.effectCount(), "충돌 이벤트는 효과를 추가하면 안 됩니다");
    }


    private static void failedPaymentCompensatesInventory() {
        OutboxReconciliation.InventoryParticipant inventory =
            new OutboxReconciliation.InventoryParticipant(1);
        OutboxReconciliation.PaymentParticipant payment =
            new OutboxReconciliation.PaymentParticipant(false);
        OutboxReconciliation.OrderSaga saga =
            new OutboxReconciliation.OrderSaga("order-saga-1", inventory, payment);

        saga.execute();

        Checks.equals(
            OutboxReconciliation.SagaState.CANCELLED,
            saga.state(),
            "보상이 완료된 뒤에만 Saga를 취소 상태로 표시해야 합니다"
        );
        Checks.equals(1, inventory.available(), "실패한 주문의 재고를 복구해야 합니다");
        Checks.equals(1, inventory.releaseEffects(), "보상 효과는 한 번이어야 합니다");
    }

    private static void failedCompensationRemainsRecoverable() {
        OutboxReconciliation.InventoryParticipant inventory =
            new OutboxReconciliation.InventoryParticipant(1);
        inventory.setReleaseAvailable(false);
        OutboxReconciliation.PaymentParticipant payment =
            new OutboxReconciliation.PaymentParticipant(false);
        OutboxReconciliation.OrderSaga saga =
            new OutboxReconciliation.OrderSaga("order-saga-2", inventory, payment);

        Checks.throwsType(
            OutboxReconciliation.CompensationUnavailableException.class,
            saga::execute,
            "보상 실패를 완료 상태로 숨기면 안 됩니다"
        );
        Checks.equals(
            OutboxReconciliation.SagaState.COMPENSATING,
            saga.state(),
            "미완료 보상을 명시적인 중간 상태로 남겨야 합니다"
        );
        Checks.equals(0, inventory.available(), "보상 전에는 예약 재고가 유지됩니다");

        inventory.setReleaseAvailable(true);
        saga.reconcile();
        saga.reconcile();

        Checks.equals(
            OutboxReconciliation.SagaState.CANCELLED,
            saga.state(),
            "재조정이 보상을 완료해야 합니다"
        );
        Checks.equals(1, inventory.available(), "재조정 뒤 재고가 복구되어야 합니다");
        Checks.equals(1, inventory.releaseEffects(), "보상 재시도도 단일 효과여야 합니다");
    }

    private static void stateAndOutboxAreCreatedTogether() {
        OutboxReconciliation.Database database = new OutboxReconciliation.Database();

        database.createOrder("order-1", "event-1");

        Checks.equals(1, database.orderCount(), "업무 상태가 저장되어야 합니다");
        Checks.equals(1, database.outboxCount(), "같은 commit에 Outbox가 있어야 합니다");
        Checks.equals(1, database.pending().size(), "새 Outbox는 발행 대기 상태입니다");
    }

    private static void brokerFailureLeavesPendingWork() {
        OutboxReconciliation.Database database = new OutboxReconciliation.Database();
        OutboxReconciliation.Consumer consumer = new OutboxReconciliation.Consumer();
        OutboxReconciliation.Broker broker = new OutboxReconciliation.Broker(consumer);
        OutboxReconciliation.Publisher publisher =
            new OutboxReconciliation.Publisher(database, broker);

        database.createOrder("order-2", "event-2");
        broker.setAvailable(false);

        Checks.throwsType(
            OutboxReconciliation.BrokerUnavailableException.class,
            () -> publisher.publishNext(false),
            "broker 장애를 재현해야 합니다"
        );
        Checks.equals(1, database.pending().size(), "실패한 Outbox는 대기 상태로 남아야 합니다");
        Checks.equals(0, consumer.effectCount(), "전달되지 않은 이벤트는 효과를 만들면 안 됩니다");
    }

    private static void crashAfterPublishCanBeReconciledWithoutDuplicateEffect() {
        OutboxReconciliation.Database database = new OutboxReconciliation.Database();
        OutboxReconciliation.Consumer consumer = new OutboxReconciliation.Consumer();
        OutboxReconciliation.Broker broker = new OutboxReconciliation.Broker(consumer);
        OutboxReconciliation.Publisher publisher =
            new OutboxReconciliation.Publisher(database, broker);

        database.createOrder("order-3", "event-3");

        Checks.throwsType(
            OutboxReconciliation.SimulatedCrashException.class,
            () -> publisher.publishNext(true),
            "publish 뒤 표시 전 중단을 재현해야 합니다"
        );
        Checks.equals(1, database.pending().size(), "ACK되지 않은 Outbox는 다시 처리되어야 합니다");
        Checks.equals(1, consumer.effectCount(), "첫 전달 효과는 적용되어 있습니다");

        publisher.reconcile();

        Checks.equals(0, database.pending().size(), "재조정 뒤 Outbox가 완료되어야 합니다");
        Checks.equals(2, broker.deliveryCount(), "같은 이벤트가 재전달되어야 합니다");
        Checks.equals(1, consumer.effectCount(), "재전달 뒤에도 업무 효과는 하나여야 합니다");
    }
}
