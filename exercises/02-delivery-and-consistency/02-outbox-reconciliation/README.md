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

## 검증

개별 reference를 검사하려면 저장소 루트에서 실행합니다.

```sh
./scripts/verify-java.sh \
  exercises/02-delivery-and-consistency/02-outbox-reconciliation/reference
```

검사는 전달 횟수가 두 번이어도 소비자 효과가 하나인지, 보상 실패 상태가 복구 가능한지, 보상 재시도 뒤 재고 효과가 하나인지 함께 확인합니다. 저장소 전체의 skeleton 실패까지 확인하려면 `./verify.sh`를 사용합니다.
