# Stage 03: Idempotent checkout과 durable payment command

## 목표

checkout의 HTTP 재시도와 process 중단을 흡수합니다. 주문 생성 transaction은 외부 결제를 호출하지 않고 보내야 할 create-payment command를 함께 저장합니다.

## Idempotency 계약

```text
scope = checkout
key
request_hash
state
response_status
response_body
```

- 같은 key·같은 body: 첫 `201` body replay
- 같은 key·다른 body: 409 `idempotency_conflict`
- 같은 key 동시 요청: 하나의 주문·하나의 stock 차감
- key 길이와 허용 문자 제한
- response snapshot을 영속 저장

## Payment command 계약

```text
kind=create|cancel|refund
status=pending|processing|sent|dead
attempts
provider_operation_id
last_error
next_attempt_at
```

Stage 03에서는 create command를 완성합니다.

- checkout transaction에 command insert 포함
- `command.id`를 provider idempotency key로 사용
- `FOR UPDATE SKIP LOCKED` 또는 동등한 원자 claim
- claim마다 새 token을 만들고 complete/fail에서 같은 token을 조건으로 사용
- lease가 만료된 이전 worker는 새 claim 결과를 덮을 수 없음
- 외부 호출 동안 DB row lock을 잡지 않음
- retryable failure는 pending으로 복귀하고 attempts 증가
- permanent failure는 dead
- 같은 command 재전송에서 외부 효과 하나

## 검증 시나리오

- 순차 replay
- concurrent replay
- 같은 key·다른 quantity 충돌
- checkout commit 뒤 command 존재
- provider 첫 timeout·두 번째 성공
- provider 성공 응답 뒤 내부 저장이 실패하면 같은 command를 재시도하고 operation 중복 없음
- worker 둘이 경쟁해 같은 command 한 번 claim
- stale worker의 complete/fail 거부

## 완료 기준

```sh
node exercises/commerce-checkout/checks/verify-work.mjs 3
```
