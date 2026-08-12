# Outbox, Saga와 재조정

## 목표

업무 상태와 발행할 이벤트를 함께 저장해 broker 장애와 전송 뒤 중단을 복구하고, Saga 보상이 끝나지 않은 상태를 명시적으로 남겨 재조정할 수 있게 합니다.

## 구현할 계약

### Outbox

- 업무 상태와 Outbox는 같은 로컬 commit에 존재합니다.
- 실제 broker 전송이 성공하기 전에는 Outbox를 완료로 표시하지 않습니다.
- broker 장애에서는 Outbox가 `PENDING`으로 남습니다.
- 전송 성공 뒤 표시 전에 중단되면 같은 `eventId`가 다시 전달될 수 있습니다.
- 소비자는 중복 이벤트에도 업무 효과를 한 번만 적용합니다.
- 재조정은 대기 Outbox를 끝까지 발행합니다.

### Saga

- 재고 예약 뒤 결제가 거절되면 재고 해제를 시도합니다.
- 재고 해제가 성공한 뒤에만 Saga를 `CANCELLED`로 확정합니다.
- 보상이 실패하면 `COMPENSATING`에 머물러야 합니다.
- 재조정은 남아 있는 보상을 다시 실행합니다.
- 같은 보상 명령을 여러 번 실행해도 재고 효과는 한 번만 남습니다.

## 실패 조건

skeleton은 broker에 보내기 전에 Outbox를 완료로 표시합니다. 전송이 실패하면 재조정이 해당 이벤트를 찾지 못합니다.

또한 보상이 실패해도 Saga를 먼저 `CANCELLED`로 표시하고 오류를 숨깁니다. 이 상태에서는 운영자가 완료된 취소와 미완료 보상을 구분할 수 없습니다.

## 작업

1. `Publisher.publishNext`를 `send → markPublished` 순서로 수정합니다.
2. 전송 뒤 표시 전 중단에서는 같은 이벤트를 재전송할 수 있게 둡니다.
3. `OrderSaga`가 보상 시작 전에 `COMPENSATING`을 기록하게 합니다.
4. 보상 성공 뒤에만 `CANCELLED`로 전이합니다.
5. `reconcile`이 남은 보상을 반복 가능하게 처리하도록 만듭니다.

## 권장 구현 순서

Outbox와 Saga는 이 실습의 한 `reference` 프로젝트를 이루므로 아래 번호를 프로젝트
전체에서 공유합니다. 이 번호는 학습을 위한 권장 구성 순서이고 실제 Git 이력이나
과거 작성 순서를 뜻하지 않습니다.

| 순서 | 구현 위치 | 책임과 연결 |
| --- | --- | --- |
| Implementation 1 | `DomainEvent` | Outbox와 소비자가 공유할 이벤트 식별 계약을 정의합니다. |
| Implementation 2 | `OutboxRow` | 발행 완료 여부와 시도 횟수의 lifecycle을 소유합니다. |
| Implementation 3 | `Database` | 업무 상태와 발행 근거를 같은 로컬 자원 경계에 둡니다. |
| Implementation 3-1 | `Database.createOrder` | 주문과 이벤트 ID를 검증하고 업무 상태와 Outbox를 함께 생성합니다. |
| Implementation 4 | `Consumer` | 처리한 이벤트 지문과 투영 효과를 함께 소유합니다. |
| Implementation 4-1 | `Consumer.onEvent` | 중복 전달을 이전 효과로 수렴시키고 payload 충돌을 거절합니다. |
| Implementation 5 | `Broker` | 가용성과 실제 전달 횟수라는 외부 전송 경계를 재현합니다. |
| Implementation 6 | `Publisher` | 미발행 행의 전송과 완료 기록 순서를 조정합니다. |
| Implementation 6-1 | `Publisher.publishNext` | `send` 뒤에만 완료로 표시하고 중간 중단을 드러냅니다. |
| Implementation 6-2 | `Publisher.reconcile` | broker 장애에서는 근거를 보존하며 남은 행을 다음 실행으로 넘깁니다. |
| Implementation 7 | `SagaState` | 정방향 완료와 진행 중인 보상을 구분합니다. |
| Implementation 8 | `InventoryParticipant` | 재고 예약·해제 효과와 주문별 지문을 소유합니다. |
| Implementation 8-1 | `InventoryParticipant.reserve` | 예약 중복을 막고 자원 부족 시 실패 지문을 되돌립니다. |
| Implementation 8-2 | `InventoryParticipant.release` | 실제 예약을 한 번만 해제하고 장애 시 재조정 근거를 남깁니다. |
| Implementation 9 | `PaymentParticipant` | 결제 승인 여부라는 원격 실패 경계를 제공합니다. |
| Implementation 10 | `OrderSaga` | 두 participant와 주문 상태 전이의 순서를 소유합니다. |
| Implementation 10-1 | `OrderSaga.execute` | 정방향 처리와 결제 거절 뒤 보상 진입을 실행합니다. |
| Implementation 10-2 | `OrderSaga.reconcile` | `COMPENSATING` 상태의 미완료 책임만 다시 실행합니다. |
| Implementation 10-3 | `OrderSaga.compensate` | 재고 해제 성공 뒤에만 `CANCELLED`로 확정합니다. |

## 완료 기준

- 전송 실패 뒤 Outbox 행이 `PENDING`으로 남아 재조정 대상이 됩니다.
- 전송 뒤 표시 전 중단으로 두 번 전달되어도 소비자 효과는 하나입니다.
- 보상 실패는 `COMPENSATING`에 남고 재조정 성공 뒤에만 `CANCELLED`가 됩니다.

## 자기 설명

- Outbox 상태를 `send`보다 먼저 완료하면 어떤 복구 근거가 사라집니까?
- Saga가 보상 성공 전 `CANCELLED`가 되어서는 안 되는 이유는 무엇입니까?

## 검증

처음 한 번 저장소 루트에서 추적된 skeleton을 안전한 workspace로 복사합니다. 기존
destination은 덮어쓰지 않습니다.

```sh
./scripts/new-workspace.sh outbox-reconciliation
```

학습자 복사본은 다음 정본 명령으로 검사합니다.

```sh
./scripts/verify-java.sh .workspace/outbox-reconciliation
```

학습자 workspace 검증을 통과하고 위 자기 설명에 답한 뒤에만 reference와 비교합니다.
개별 reference를 검사하려면 저장소 루트에서 실행합니다.

```sh
./scripts/verify-java.sh \
  exercises/02-delivery-and-consistency/02-outbox-reconciliation/reference
```

검사는 전달 횟수가 두 번이어도 소비자 효과가 하나인지, 보상 실패 상태가 복구 가능한지, 보상 재시도 뒤 재고 효과가 하나인지 함께 확인합니다. 저장소 전체의 skeleton 실패까지 확인하려면 `./verify.sh`를 사용합니다.
