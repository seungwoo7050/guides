# Event delivery, concurrency와 idempotency

FaaS에서 가장 중요한 오류는 function code의 예외 하나가 아니라 **event source가 언제 진행 지점을 이동시키고, invocation timeout 뒤 외부 효과와 재전달이 어떻게 수렴하는지**입니다.

일반적인 전달·멱등성·재시도 원리는 [`distributed-services`의 idempotency와 single effect](https://github.com/seungwoo7050/guides/blob/distributed-services/docs/02-delivery-and-consistency/01-idempotency-and-single-effects.md), [`timeout·retry·DLQ`](https://github.com/seungwoo7050/guides/blob/distributed-services/docs/03-resilience-and-load/01-timeouts-retries-circuit-breakers-and-dlq.md), [`contract version과 ordering`](https://github.com/seungwoo7050/guides/blob/distributed-services/docs/02-delivery-and-consistency/03-contracts-versioning-and-order.md)이 소유합니다. 이 문서는 그 계약을 다시 가르치지 않고 **managed event source와 ephemeral invocation의 ack/checkpoint, batch, concurrency, version, replay와 비용 제약**에 적용합니다.

## 1. Source와 완료 경계를 먼저 식별하기

`event source`라는 한 단어로 완료 의미를 통일하면 안 됩니다.

| source 형태 | 진행 상태 | 성공 뒤 이동 | 실패·timeout 뒤 확인할 것 |
|---|---|---|---|
| managed queue | visible message, lease/visibility deadline, receive count | delete 또는 ack | lease 만료 시 재등장하는지, ack 권한과 DLQ redrive 정책 |
| ordered stream | partition, offset 또는 sequence, consumer checkpoint | checkpoint commit | batch 중 어디까지 checkpoint되는지, shard/partition concurrency |
| object notification·event bus | immutable source object/version, delivery attempt | source별 success disposition | provider delivery ID가 재전달에도 안정적인지, 보존·replay window |
| scheduler·HTTP | schedule occurrence 또는 request ID | response/dispatch 기록 | caller가 timeout 뒤 재호출하는지, 응답 유실을 누가 관찰하는지 |

공급자 문서에서 최소한 delivery claim, ack/checkpoint 시점, retry owner, event retention, maximum age, batch 의미와 failure destination을 확인합니다. 확인하지 못한 항목은 `unknown`으로 남기며 “exactly once”로 보강해 쓰지 않습니다.

## 2. FaaS invocation 상태

이 가이드와 실습은 다음 provider-neutral 상태 이름을 사용합니다.

```text
SOURCE_AVAILABLE
→ INVOCATION_RUNNING
→ EFFECT_COMMITTED
→ ACK_COMMITTED
```

대표 분기:

```text
INVOCATION_RUNNING → RETRYABLE_FAILURE → SOURCE_AVAILABLE
INVOCATION_RUNNING → TERMINAL_FAILURE → FAILURE_DESTINATION
EFFECT_COMMITTED → invocation timeout or ack lost → SOURCE_AVAILABLE
```

`EFFECT_COMMITTED`와 `ACK_COMMITTED` 사이가 핵심 불확실성 구간입니다. function의 성공 응답, source ack, database commit과 object write는 서로 다른 사건입니다.

## 3. Timeout은 취소 증거가 아니다

invocation timeout은 실행 시간이 끝났다는 관측이지 외부 효과가 없다는 증거가 아닙니다. client·runtime·dependency 중 어느 timeout인지와 마지막 확인 가능한 commit을 분리합니다.

```text
event_id=E1 attempt=1
output write=committed
status update=unknown
invocation=timeout
source ack=not committed
```

retry는 먼저 deterministic output key, conditional write, event processing record와 reconciliation을 조회합니다. 일반 멱등성 구현은 위 소유 문서를 따르고, 여기서는 **invocation deadline보다 짧은 dependency timeout**, 남은 시간 예산, ack 이전에 완료해야 하는 최소 상태를 정합니다.

## 4. Event identity와 version scope

안정적인 업무 key는 최소 `tenant_id + event_id + object_version + operation` 범위를 가집니다. provider delivery ID가 attempt마다 바뀔 수 있으므로 source 계약에서 안정성을 확인하지 않고 정본 key로 쓰지 않습니다.

- schema version과 지원 consumer version을 기록합니다.
- function version, converter version과 output version을 연결합니다.
- stale object version은 최신 결과를 덮어쓰지 않습니다.
- deduplication retention은 source의 최대 replay age보다 짧지 않아야 합니다.
- tenant가 다르면 같은 문자열 event ID를 독립적으로 처리합니다.

## 5. Partial batch와 checkpoint

batch 한 건의 실패가 성공한 record까지 재전달하는지, record별 실패 응답을 지원하는지, checkpoint가 batch 앞·뒤 어디에서 이동하는지를 문서화합니다.

| 결정 | 필요한 근거 |
|---|---|
| record별 결과 | 성공 record의 ack와 실패 record의 재전달을 trace로 구분 |
| 전체 batch 실패 | 모든 성공 record가 duplicate-safe함을 같은 검사로 증명 |
| ordered stream | 실패 record 뒤 checkpoint 정지·skip·격리 중 하나를 명시 |
| poison record | retry 횟수·event age bound와 failure destination owner |

partial batch 응답을 활성화했다는 설정만으로 안전하지 않습니다. handler가 반환한 record ID가 source record와 정확히 연결되고, 처리한 record를 누락하지 않는지 검증합니다.

## 6. Source별 retry와 failure destination

retry owner가 source mapping인지 function platform인지 application scheduler인지 구분합니다. 정책에는 `classification`, maximum attempts, maximum event age, backoff·jitter, per-attempt deadline, failure destination, alert threshold와 replay rule이 함께 있어야 합니다.

- throttle·temporary dependency failure는 bounded retry 후보입니다.
- invalid schema·unsupported version·deleted tenant·permanent missing object는 무한 retry하지 않습니다.
- DLQ나 failure destination 기록에는 original event, source position, attempts, function version, tenant, failure class, first/last time, data class와 replay eligibility를 남깁니다.
- replay 전 tenant 상태, schema·function version, 기존 external effect와 현재 source checkpoint를 확인합니다.

failure destination은 종착지가 아니라 운영 대기열입니다. owner·처리 SLA·수정 기록·재실행 결과가 없으면 실패를 저장했을 뿐 복구하지 않은 상태입니다.

## 7. Concurrency, throttle과 backpressure

일반적인 부하 통제는 [`distributed-services`의 backpressure·bulkhead·load shedding](https://github.com/seungwoo7050/guides/blob/distributed-services/docs/03-resilience-and-load/02-backpressure-bulkheads-and-load-shedding.md)이 소유합니다. FaaS에서는 다음 provider 제어와 함께 적용합니다.

- account·region·function·alias별 concurrency 한도
- source mapping의 batch size·poller·parallelization
- downstream database connection·object I/O·third-party quota
- reserved 또는 provisioned concurrency와 cold-start 비용
- throttle 시 source가 즉시 재시도하는지, backoff하는지
- 한 tenant flood가 shared concurrency와 retry budget을 독점하는지

maximum concurrency는 downstream의 지속 가능한 처리량보다 낮아야 합니다. queue age가 계속 증가하면 자동 확장은 해결이 아니라 비용 증폭일 수 있습니다.

## 8. Tenant fairness와 retry 비용

tenant별 in-flight token, fair scheduling, partitioned limit, weighted quota 또는 별도 capacity tier를 선택합니다. 상업 plan의 monthly quota, runtime concurrency, retry budget과 provider account quota는 서로 다른 상태입니다.

retry 비용식은 성공 invocation만 세지 않습니다.

```text
attempt cost
= invocation duration + request + source read
 + downstream I/O + log ingestion + failure destination
```

poison event의 maximum attempt·age, per-tenant backlog와 log payload 제한이 cost guard입니다. 특정 tenant가 정상 tenant의 latency와 budget을 소진하면 격리 계약 실패입니다.

## 9. Replay와 변경 관리

수동 replay는 단순 재전송이 아닙니다. 원래 event와 새 replay ID, 선택한 function version, schema adapter, 이미 발생한 effect, current tenant state와 승인자를 기록합니다.

다음 중 어느 동작인지 명시합니다.

- 당시 function version으로 재현
- 현재 version으로 migrate 후 처리
- effect가 이미 있으면 reconcile만 수행
- 삭제·보존 만료·법적 제한으로 replay 거부

replay 결과는 원래 failure record를 덮어쓰지 않고 연결된 correction record로 남깁니다.

## 10. Concurrency와 quota 원자성

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

## 11. Observability와 실패 ID

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

개념·실습·Capstone에서 같은 대표 실패 ID를 사용합니다.

| ID | 관찰해야 할 FaaS 상태 |
|---|---|
| `F04-01` | `EFFECT_COMMITTED` 뒤 timeout, ack 미완료와 reconciliation |
| `F04-02` | 같은 tenant·event의 duplicate suppression |
| `F04-03` | poison event의 bounded retry와 failure destination |
| `F04-04` | partial batch의 record별 결과와 checkpoint |
| `F04-05` | tenant flood가 shared concurrency·cost를 고갈시키지 않는 fairness |
| `F04-06` | 삭제된 tenant로 온 늦은 retry의 terminal 처리와 cleanup |
| `F04-07` | 지원하지 않는 schema/function version의 격리 |
| `F04-08` | replay version·effect·승인·correction record |

## 12. Local model의 불변식

이 브랜치의 실행 실습은 다음을 검사합니다.

```text
cross-tenant read는 거부됩니다.
같은 tenant의 같은 event ID는 usage와 output을 한 번만 만듭니다.
서로 다른 tenant의 같은 event ID는 독립적으로 처리됩니다.
quota 초과는 document를 부분 생성하지 않습니다.
stateful resource는 public으로 노출되지 않습니다.
tenant deletion 뒤 active resource와 queue가 남지 않습니다.
```

실제 provider semantics를 재현하는 것이 아니라 cloud application이 지켜야 하는 외부 불변식을 고정합니다.

## 연결 실습

[04 FaaS event lifecycle](../exercises/04-faas-event-lifecycle/README.md)에서 정책을 작성하고, [07 local cloud model](../exercises/07-local-cloud-model/README.md)에서 같은 event를 반복 실행해 불변식을 검사합니다.
