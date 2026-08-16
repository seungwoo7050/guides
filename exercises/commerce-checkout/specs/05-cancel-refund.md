# Stage 05: Cancel과 refund

## 목표

cancel과 refund를 서로 다른 command와 상태 전이로 구현합니다. Provider event가 확정되기 전에 최종 상태를 표시하지 않습니다.

## 상태 계약

```text
pending_payment --cancel request--> cancel_pending
cancel_pending --payment.canceled--> canceled
cancel_pending --payment.succeeded--> paid
pending_payment --payment.failed--> payment_failed
pending_payment --payment.succeeded--> paid
paid --refund request--> refund_pending
refund_pending --payment.refunded--> refunded
```

Terminal 상태는 `payment_failed`, `canceled`, `refunded`입니다.

## API 계약

```text
POST /orders/:id/cancel
POST /orders/:id/refund
```

각 endpoint는 `Idempotency-Key`를 요구합니다.

- pending_payment이고 create-payment command가 provider에 전달된 뒤에만 cancel 요청 가능
- provider payment identity가 아직 없으면 409 `payment_not_dispatched`
- paid만 refund 요청 가능
- 이미 같은 command가 완료됐으면 최초 응답 replay
- 허용되지 않은 현재 상태는 409
- provider command insert와 pending transition은 한 transaction

## Inventory release 계약

- `payment_failed`, `canceled`, `refunded`에서 전량 반환
- order row의 `inventory_released_at` 조건부 갱신
- release movement unique
- order transition·payment update·stock 반환·event 기록 한 transaction
- duplicate terminal webhook에서 두 번째 반환 없음

## 검증 시나리오

- pending cancel 요청은 즉시 canceled가 아님
- cancel event에서 stock 반환
- cancel_pending 중 success가 오면 paid
- paid refund 요청과 refunded event
- duplicate cancel/refund request replay
- duplicate terminal webhook effect-once
- late success가 canceled/refunded를 되돌리지 않음

## 완료 기준

```sh
node exercises/commerce-checkout/checks/verify-work.mjs 5
```
