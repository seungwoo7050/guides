# Event delivery, concurrency와 idempotency

FaaS에서 가장 중요한 오류는 function code의 예외 하나가 아니라 **event가 언제 완료된 것으로 인정되며, 같은 event가 다시 왔을 때 외부 상태가 어떻게 되는지**입니다.

이 문서는 `distributed-services`의 일반 원리를 event source와 ephemeral runtime에 적용합니다.

## 1. Delivery state

```text
ACCEPTED
→ AVAILABLE
→ LEASED or DISPATCHED
→ RUNNING
→ SUCCEEDED
→ ACKNOWLEDGED
```

실패 경로:

```text
RUNNING
→ RETRYABLE_FAILURE
→ AVAILABLE

RUNNING
→ TERMINAL_FAILURE
→ DEAD_LETTERED

SUCCEEDED
→ acknowledgment lost
→ AVAILABLE again
```

마지막 경로 때문에 business work가 성공했어도 duplicate delivery가 가능합니다.

## 2. At-most-once, at-least-once, exactly-once

### At-most-once

중복은 피할 수 있지만 처리 전에 message가 사라질 수 있습니다.

### At-least-once

message 손실을 줄이지만 duplicate가 가능합니다. 많은 managed queue와 event mapping이 이 모델을 사용합니다.

### Exactly-once

end-to-end 업무 효과가 정확히 한 번이라는 주장은 source, transport, consumer, database와 external effect 전체를 포함해야 합니다. 특정 service의 deduplication만으로 외부 이메일·결제·파일 생성까지 정확히 한 번이 되지는 않습니다.

실무에서는 다음 목표가 더 명확합니다.

```text
같은 business command를 여러 번 받아도 최종 업무 효과가 하나입니다.
```

## 3. Event identity

idempotency에는 안정적인 key가 필요합니다.

- producer event ID
- business command ID
- object version
- tenant + operation + logical key
- provider delivery ID는 재전송마다 바뀔 수 있으므로 확인 필요

key의 scope와 retention을 정합니다. 너무 일찍 deduplication record를 지우면 늦은 retry가 다시 효과를 만듭니다.

## 4. Idempotency state

대표 상태:

```text
ABSENT
→ STARTED
→ EFFECT_COMMITTED
→ COMPLETED
```

실패 뒤 판정:

- STARTED에서 오래 멈춤
- EFFECT_COMMITTED지만 response 없음
- COMPLETED result cache 만료
- 다른 function version이 같은 key 처리

하나의 database transaction에 business effect와 idempotency record를 함께 저장할 수 있으면 단순해집니다. 외부 service effect는 reconciliation이 필요할 수 있습니다.

## 5. Partial failure

문서 처리 예:

```text
object 읽기 성공
→ thumbnail 저장 성공
→ database status update 실패
→ function timeout
```

retry가 thumbnail을 또 만들 수 있습니다. 해결 방법:

- deterministic output key
- conditional create
- content checksum
- status transition with expected version
- cleanup or reconciliation
- idempotency record

## 6. Batch failure

한 batch에 여러 record가 있을 때 하나가 실패하면 전체 batch가 재시도될 수 있습니다. 공급자에 따라 partial batch response나 split 기능을 제공할 수 있습니다.

설계:

- record별 result
- successful record의 재처리 안전성
- poison record 격리
- batch size와 timeout
- ordering requirement
- checkpoint 또는 offset commit

## 7. Ordering

global ordering은 비싸고 드뭅니다. 필요한 key에 대해서만 순서를 보장하는 편이 일반적입니다.

- tenant
- account
- document
- aggregate
- partition key

순서 역전이 가능하면 event에 version 또는 sequence를 포함하고 stale update를 거부합니다.

```text
current_version = 7
incoming_version = 6
→ ignore or record stale event
```

## 8. Retry policy

재시도 대상:

- transient network failure
- throttle
- temporary dependency unavailable

재시도하지 말아야 할 수 있는 대상:

- invalid schema
- unauthorized
- unsupported version
- deleted tenant
- permanently missing object

정책 필드:

```text
classification
maximum_attempts
backoff
jitter
maximum_age
per-attempt timeout
dead-letter destination
alert threshold
manual replay rule
```

무한 retry는 backlog, 비용과 stale side effect를 만듭니다.

## 9. Dead letter는 종착지가 아니다

dead-letter queue 또는 failure destination에 보냈다고 문제가 해결된 것은 아닙니다.

필요한 상태:

- original event
- failure class
- attempts
- first·last failure time
- function version
- tenant
- data sensitivity
- owner
- replay eligibility
- correction record

replay는 원래 function과 현재 function 중 무엇을 사용할지, 이미 발생한 효과를 어떻게 확인할지 정해야 합니다.

## 10. Concurrency와 원자성

동시에 같은 tenant quota 또는 document를 갱신할 수 있습니다.

나쁜 흐름:

```text
count 읽기: 9
limit: 10
두 invocation 모두 허용
두 개 생성
count: 11
```

필요한 방법:

- database constraint
- conditional update
- compare-and-set
- transaction
- serialized partition
- lease

application-level 사전 검사만으로 quota를 보장하지 않습니다.

## 11. Tenant fairness

하나의 tenant가 event를 대량 생성하면 공유 concurrency를 독점할 수 있습니다.

- per-tenant queue
- fair scheduler
- partitioned limit
- weighted quota
- separate capacity tier
- backlog age alert

상업 plan과 runtime concurrency를 직접 동일시하지 말고 entitlement·quota·capacity를 분리합니다.

## 12. Observability

좋은 trace는 시도와 업무 효과를 구분합니다.

```text
event_id=E1 attempt=1 result=timeout external_effect=unknown
event_id=E1 attempt=2 result=duplicate effect_id=R9 final=success
```

필요한 metric:

- unique event
- attempt count
- duplicate suppressed
- effect committed
- retryable·terminal failure
- dead-letter
- oldest age
- per-tenant backlog
- replay outcome

## 13. Local model의 불변식

이 브랜치의 실행 실습은 다음을 검사합니다.

```text
cross-tenant read는 거부됩니다.
같은 event ID는 usage와 output을 한 번만 만듭니다.
quota 초과는 document를 부분 생성하지 않습니다.
stateful resource는 public으로 노출되지 않습니다.
tenant deletion 뒤 active resource와 queue가 남지 않습니다.
```

실제 provider semantics를 재현하는 것이 아니라 cloud application이 지켜야 하는 외부 불변식을 고정합니다.

## 연결 실습

[04 FaaS event lifecycle](../exercises/04-faas-event-lifecycle/README.md)에서 정책을 작성하고, [07 local cloud model](../exercises/07-local-cloud-model/README.md)에서 같은 event를 반복 실행해 불변식을 검사합니다.
