# 신뢰할 수 있는 command와 webhook

DB transaction은 DB 안의 상태만 원자적으로 바꿉니다. 주문을 저장한 뒤 결제 API를 호출하거나 외부 시스템이 webhook을 보내는 순간, 애플리케이션은 하나의 transaction으로 묶을 수 없는 경계를 가집니다. 이 경계에서는 요청이 한 번 전달된다고 가정하지 않고 **중복·응답 유실·지연·순서 역전·프로세스 중단 뒤에도 최종 상태가 수렴하는 계약**을 먼저 정의합니다.

## 목표

- HTTP timeout과 성공 여부 불명확성을 구분합니다.
- idempotency key의 scope, request fingerprint, 결과 보존 계약을 설계합니다.
- DB commit과 외부 API 호출 사이의 간격을 durable command로 복구합니다.
- webhook의 서명·중복·순서·재시도 계약을 구현합니다.
- “exactly once delivery” 대신 반복 가능한 처리와 영속 deduplication으로 효과를 한 번만 남깁니다.
- 재시도와 reconciliation이 필요한 실패를 숨기지 않고 관찰 가능한 상태로 남깁니다.

## timeout은 실패가 아니라 결과 불명확일 수 있습니다

다음 흐름에서 결제사는 이미 성공했지만 client는 응답을 받지 못할 수 있습니다.

```text
application ── create payment ──> provider
application <── success ──X network timeout
```

이때 다음 요청이 위험합니다.

```text
timeout
→ 실패라고 단정
→ 새 payment 생성
→ 실제로는 두 번 결제
```

transport 오류는 업무 결과와 같은 값이 아닙니다.

```text
transport result: timeout
business result: unknown
```

client나 worker가 재시도하려면 같은 업무 command를 다시 식별할 수 있어야 합니다.

## Idempotency key는 header 이름이 아니라 수명 계약입니다

위험한 command는 key를 받고 다음 정보를 영속화할 수 있습니다.

```text
scope
key
request_fingerprint
state
response_status
response_body
created_at
expires_at
```

`scope`는 key가 유일한 범위를 정의합니다.

```text
checkout:user-42
refund:order-17
provider-command:create-payment
```

같은 문자열이라도 scope가 다르면 별도 command일 수 있습니다.

### 같은 key와 같은 요청

```text
처음 요청
→ 업무 효과 실행
→ 결과 저장

재시도
→ 저장된 결과 반환
→ 업무 효과 반복 금지
```

### 같은 key와 다른 요청

```text
Idempotency-Key: abc
body: { quantity: 1 }

Idempotency-Key: abc
body: { quantity: 2 }
```

이 경우 기존 결과를 재사용해서는 안 됩니다. canonical request에서 hash를 계산하고 key가 다른 payload에 재사용되면 409 같은 명시적 충돌로 거부합니다.

### 동시에 같은 key가 들어오는 경우

단순한 선행 조회는 경쟁에 안전하지 않습니다.

```text
A: key 없음 확인
B: key 없음 확인
A: 주문 생성
B: 주문 생성
```

DB의 unique constraint와 transaction을 최종 방어선으로 사용합니다. 첫 transaction이 완료되기 전 다른 요청이 대기할지, `request_in_progress`를 반환할지 정책을 정합니다. 무기한 대기는 허용하지 않습니다.

## 응답 snapshot을 보존합니다

idempotent replay는 “이미 처리됨”만 반환하는 것이 아니라 첫 성공 응답의 외부 계약을 재현해야 합니다.

```json
{
  "orderId": "...",
  "status": "pending_payment",
  "total": { "amountMinor": 25000, "currency": "KRW" }
}
```

업무 행을 다시 조회해 응답을 재조립하면 시간이 지난 뒤 상태가 바뀌어 첫 응답과 달라질 수 있습니다. 제품 계약에 따라 최초 응답 snapshot을 저장하거나, replay 응답이 현재 상태를 반환한다는 점을 별도로 문서화합니다. 이 실습은 최초 command 결과를 저장합니다.

## 외부 HTTP를 DB transaction 안에서 기다리지 않습니다

다음 구조는 DB lock을 잡은 채 외부 timeout을 기다립니다.

```text
BEGIN
order insert
inventory lock
HTTP payment call ── 10초 대기
COMMIT
```

문제:

- lock 유지 시간이 외부 latency에 종속됩니다.
- provider 장애가 DB connection 고갈로 전파됩니다.
- 외부 성공 뒤 DB rollback이 발생해도 되돌릴 수 없습니다.
- transaction retry가 외부 호출을 중복 실행할 수 있습니다.

DB transaction에는 DB 불변식만 넣습니다.

## Durable command로 commit 이후 작업을 남깁니다

주문 생성 transaction에서 외부 요청 자체가 아니라 **보내야 할 command**를 함께 저장합니다.

```text
BEGIN
order 생성
재고 차감
payment_command 생성(status=pending)
idempotency 결과 저장
COMMIT
```

그 뒤 worker가 command를 전송합니다.

```text
pending command claim
→ provider 호출
→ 성공 결과 저장
→ sent
```

프로세스가 commit 직후 중단돼도 command 행이 남습니다. 별도 broker가 없는 작은 애플리케이션에서는 DB table을 durable queue로 사용할 수 있습니다.

### Claim 계약

여러 worker가 같은 command를 동시에 보내지 않도록 다음 중 하나를 사용합니다.

- `FOR UPDATE SKIP LOCKED`
- lease owner와 lease expiry
- 상태 조건부 update와 반환 행

이 가이드의 exercise는 짧은 transaction에서 `FOR UPDATE SKIP LOCKED`로 하나를 claim합니다. 각 claim에는 새 token을 발급하고 complete·fail update가 같은 token을 조건으로 사용하게 합니다. lease가 만료돼 다른 worker가 다시 claim한 뒤에는 이전 worker가 새 처리 결과를 덮을 수 없습니다. 외부 HTTP 호출 동안 DB row lock을 유지하지 않고 `processing` 상태와 시도 횟수를 저장합니다.

### 외부 성공 뒤 내부 저장 전 중단

가장 까다로운 간격입니다.

```text
provider 성공
X process crash
DB에는 sent 기록 없음
```

worker는 command를 다시 보냅니다. 따라서 provider 호출에도 안정된 idempotency key를 사용해야 합니다.

```text
provider idempotency key = command.id
```

provider가 같은 key의 효과를 재사용하면 worker 재시도가 안전해집니다. 내부 outbox만 있다고 중복 외부 효과가 자동으로 사라지는 것은 아닙니다.

## 재시도 상태는 숨기지 않습니다

command에는 최소한 다음 상태가 필요합니다.

```text
pending
processing
sent
failed 또는 dead
```

그리고 다음 정보를 관찰할 수 있어야 합니다.

- attempts
- last_error의 안전한 요약
- next_attempt_at
- processing lease
- provider operation ID
- created_at / updated_at

모든 오류를 영원히 재시도하지 않습니다.

```text
retryable: timeout, connection reset, 429, 일부 5xx
permanent: schema 거부, 인증 실패, 잘못된 금액, 존재하지 않는 대상
```

시도 횟수, 전체 deadline과 backoff를 제한합니다. 비밀·card data·전체 provider 응답을 log나 오류 열에 저장하지 않습니다.

## Webhook은 at-least-once 입력으로 취급합니다

외부 provider는 성공 응답을 받지 못하면 같은 event를 다시 보낼 수 있습니다.

```text
evt_42 payment.succeeded
evt_42 payment.succeeded
evt_42 payment.succeeded
```

handler가 매번 재고·상태·감사 기록을 바꾸면 안 됩니다. provider event ID를 영속 저장하고 unique constraint로 중복을 막습니다.

```text
provider_events
- event_id primary key
- event_type
- payload_hash
- outcome
- received_at
```

같은 event ID에 다른 payload가 오면 단순 duplicate로 처리하지 않습니다. provider bug, 공격 또는 canonicalization 오류일 수 있으므로 충돌로 기록하고 상태 변경을 거부합니다.

### Event가 내부 payment identity보다 먼저 도착하는 경우

provider가 operation을 수락한 직후 webhook을 보내고, worker가 `provider_payment_id`를 DB에 기록하기 전에 event가 도착할 수 있습니다. 이 event를 성공 처리된 unknown으로 확정하면 이후 같은 delivery가 영원히 무시됩니다.

이 exercise는 event와 payload hash를 영속화하되 `unknown_payment`에는 retry 가능한 503을 반환합니다. 같은 event가 다시 도착하면 payload hash를 확인한 뒤 payment identity를 다시 조회합니다. command 결과가 저장된 뒤의 delivery는 최초 업무 효과를 적용할 수 있습니다. 실제 provider가 제한 횟수 뒤 재시도를 멈춘다면 reconciliation이 이 inbox를 다시 처리해야 합니다.

## 서명은 parse 전 raw body를 기준으로 검증합니다

JSON object를 다시 stringify하면 공백·key 순서·escape가 달라질 수 있습니다. provider가 정의한 원문 byte를 사용합니다.

```text
signature = HMAC(secret, timestamp + "." + raw_body)
```

검증 순서:

1. 전용 content type으로 raw bytes를 읽습니다.
2. timestamp 형식과 허용 시간창을 검사합니다.
3. raw body의 HMAC을 계산합니다.
4. constant-time 비교를 사용합니다.
5. 서명이 유효한 뒤 JSON을 parse하고 schema를 검증합니다.

오래된 timestamp를 허용하면 탈취한 payload의 replay 시간이 길어집니다. 시간이 맞지 않는 환경에서는 먼저 clock 운영 문제를 해결하지 검증을 끄지 않습니다.

## Event 순서는 계약이 아닐 수 있습니다

다음 순서가 항상 보장된다고 가정하지 않습니다.

```text
payment.created
payment.succeeded
payment.refunded
```

network와 provider 내부 retry 때문에 늦은 event가 뒤늦게 도착할 수 있습니다. handler는 현재 상태와 event를 함께 보고 transition을 결정합니다.

```text
current=refunded, event=payment.succeeded
→ paid로 되돌리지 않음
→ ignored_invalid_transition 기록
```

무시했다고 event를 버리지 않습니다. event ID와 판정 결과를 남겨 reconciliation에서 확인할 수 있게 합니다.

## HTTP 응답과 업무 commit을 분리해 생각합니다

Webhook handler의 성공 응답은 “provider에게 같은 event를 다시 보내지 않아도 된다”는 의미입니다.

- 영속 처리 완료: 2xx
- 일시 DB 장애로 commit 못함: 5xx로 retry 유도
- 서명 실패: 401/400, 상태 변경 없음
- 유효하지만 알 수 없는 payment: 제품 정책에 따라 202/2xx로 격리하거나 404로 재시도 유도

무조건 200을 반환하면 처리하지 못한 event를 잃을 수 있습니다. 반대로 영구적인 schema 오류에 계속 500을 반환하면 retry 폭주가 발생합니다.

## Exactly-once가 아니라 effect-once를 설계합니다

일반 network delivery에서 “정확히 한 번 도착”을 쉽게 보장할 수 없습니다. 현실적인 목표는 다음 조합입니다.

```text
at-least-once delivery
+ stable operation identity
+ durable deduplication
+ idempotent transition
+ transaction
= observable effect once
```

event는 여러 번 도착할 수 있지만 주문 상태 변경과 재고 반환은 한 번만 발생합니다.

## Reconciliation은 예외가 아니라 복구 경로입니다

모든 간격을 synchronous request만으로 없앨 수 없습니다. 다음 상태는 주기적으로 찾아야 할 수 있습니다.

- 오래 `processing`인 command
- provider operation ID 없이 `sent`로 남은 행
- `pending_payment`가 지나치게 오래된 주문
- unknown payment webhook
- 내부 상태와 provider 조회 결과 불일치

이 exercise는 별도 scheduler를 구현하지 않지만 query와 상태를 통해 수동 reconciliation이 가능해야 합니다. 실제 운영에서는 metric, alert, 제한된 retry와 관리자 도구가 필요합니다.

## 실패 행렬

| 실패 지점 | 남아야 하는 상태 | 안전한 다음 행동 |
|---|---|---|
| checkout transaction 전 실패 | 아무 주문도 없음 | 같은 key 재시도 |
| checkout commit 뒤 process 중단 | 주문·재고·pending command 존재 | worker 재개 |
| provider timeout | command identity와 시도 기록 | 같은 provider key로 재시도 |
| provider 성공 뒤 DB 저장 전 중단 | command가 다시 보일 수 있음 | 같은 provider key로 재호출 |
| webhook 중복 | event dedupe 행 존재 | 기존 결과 반환 |
| webhook 처리 transaction 실패 | event commit 없음 | provider retry |
| 늦은 성공 event | 현재 상태 유지 또는 허용 transition | 판정 outcome 기록 |
| 같은 event ID·다른 payload | 상태 변경 없음 | 충돌 기록·조사 |

## 검증

최소 검사는 다음입니다.

- 같은 key·같은 body를 순차·동시에 요청해 하나의 주문만 생성
- 같은 key·다른 body 거부
- 외부 timeout 뒤 같은 command 재전송 시 provider 효과 하나
- command claim을 두 worker가 경쟁해 하나만 처리
- lease 만료 뒤 stale worker가 새 claim 결과를 덮지 못함
- webhook duplicate 세 번 뒤 상태 전이·재고 변경 한 번
- payment identity 기록보다 먼저 온 event가 retry 뒤 적용
- 잘못된 서명과 오래된 timestamp 거부
- 같은 event ID·다른 payload 거부
- 순서가 뒤집힌 event가 terminal 상태를 되돌리지 않음
- DB 오류를 주입한 webhook이 5xx를 반환하고 다음 delivery에서 성공
- 처리 뒤 server·pool·timer가 종료됨

## 실패 조건

- timeout을 업무 실패로 단정합니다.
- idempotency key를 메모리에만 저장합니다.
- 같은 key의 다른 payload를 기존 성공으로 처리합니다.
- 외부 HTTP를 DB transaction 안에서 기다립니다.
- command에 안정된 외부 idempotency identity가 없습니다.
- webhook을 parse한 object를 다시 stringify해 서명합니다.
- 중복 event마다 activity·재고를 다시 바꿉니다.
- 현재 상태를 보지 않고 event 이름만으로 값을 덮습니다.
- 모든 오류를 무한 retry합니다.
- unknown·stuck 상태를 찾을 query나 기록이 없습니다.

## 연결 실습

[`커머스 checkout`](03-commerce-checkout.md)과 [`commerce-checkout exercise`](../../exercises/commerce-checkout/README.md)의 Stage 03–04에서 idempotent checkout, durable payment command, HTTP mock provider와 서명 webhook을 구현합니다.

## 완료 기준

- request와 operation identity의 scope를 정의합니다.
- DB commit과 외부 효과 사이의 실패 간격을 설명합니다.
- durable command를 claim·retry하고 외부 idempotency로 중복 효과를 막습니다.
- raw body 서명, timestamp, event dedupe와 상태 전이를 한 handler에서 검증합니다.
- 중복·지연·순서 역전 뒤에도 observable effect가 한 번만 남음을 자동 검사합니다.

## 다음 단계

외부 command의 전달 계약을 이해했다면 [`커머스 업무 불변식`](02-commerce-domain-invariants.md)에서 금액·재고·주문 상태의 내부 정본을 설계합니다.
