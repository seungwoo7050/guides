# Stage 04: Payment provider와 webhook

## 목표

실제 HTTP mock provider adapter를 연결하고 raw body 서명, timestamp와 event dedupe를 구현합니다.

## Provider adapter 계약

`PaymentProvider` port는 application 내부 command를 provider request로 변환합니다. HTTP status, timeout과 body parse 오류를 domain 오류로 번역합니다.

- operation idempotency key header 전달
- request timeout
- non-2xx 오류 분류
- response runtime schema 검증
- secret과 전체 body log 금지

## Webhook wire 계약

Content-Type:

```text
application/vnd.guide-payment+json
```

Headers:

```text
X-Payment-Timestamp
X-Payment-Signature
```

Signature:

```text
hex(HMAC-SHA256(secret, timestamp + "." + raw_body))
```

허용 시간창 기본값은 300초입니다.

## Event 계약

```text
payment.succeeded
payment.failed
payment.canceled
payment.refunded
```

body:

```json
{
  "id": "evt_...",
  "type": "payment.succeeded",
  "providerPaymentId": "pay_...",
  "occurredAt": "2026-01-01T00:00:00.000Z"
}
```

## Deduplication 계약

- event ID unique
- raw payload hash 저장
- 같은 ID·같은 payload: 기존 outcome 반환
- 같은 ID·다른 payload: 409, 상태 변경 없음
- unknown payment: event와 outcome을 기록하고 503으로 retry 요청
- 같은 unknown event가 재전달되면 payment identity를 다시 조회해 적용 가능
- DB commit 실패: provider가 retry할 수 있는 5xx

## 검증 시나리오

- fixture child process와 HTTP adapter
- provider operation idempotency
- 올바른 signature 성공
- 잘못된 signature·오래된 timestamp 거부
- duplicate event 세 번 뒤 상태·activity 한 번
- 같은 ID·다른 payload 거부
- provider event가 command 결과 저장보다 먼저 도착해도 retry 뒤 적용
- out-of-order event가 terminal state를 역행시키지 않음
- child process와 response body cleanup

## 완료 기준

```sh
node exercises/commerce-checkout/checks/verify-work.mjs 4
```
