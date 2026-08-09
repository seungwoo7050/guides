# FaaS Event Processing Plan

## Event identity와 schema

producer가 만든 immutable `event_id`, `tenant_id`, `document_id`, `object_version`, `schema_version`, `occurred_at`을 사용한다. 업무 key scope는 `tenant_id + event_id + object_version + operation`이다. provider delivery ID는 attempt마다 달라질 수 있으므로 deduplication 정본으로 사용하지 않는다. event schema는 additive change를 기본으로 하고 consumer가 지원하는 version과 function version을 manifest에 기록한다. 서로 다른 tenant의 같은 event ID는 독립 사건이다.

## 상태 기계와 완료 지점

```text
SOURCE_AVAILABLE → INVOCATION_RUNNING → EFFECT_COMMITTED → ACK_COMMITTED
```

source는 managed queue이며 lease 안에서 명시적 ack가 끝나야 `ACK_COMMITTED`다. `EFFECT_COMMITTED`는 result object, database status와 usage가 같은 logical operation에 연결된 상태다. 한 transaction에 묶을 수 없는 object effect는 deterministic key와 reconciliation으로 판정한다. function return은 완료 evidence 중 하나일 뿐이며 timeout은 effect 취소 증거가 아니다.

## Idempotency와 external effect

result object key는 `tenant/document/object_version/converter_version/event_id`로 결정한다. conditional create 또는 checksum을 사용하고, database에 tenant 범위 event ID별 processing record를 둔다. duplicate attempt는 기존 completed result를 읽어 success로 종료하고 usage를 다시 증가시키지 않는다. output은 존재하지만 status가 없으면 reconciliation이 status와 usage를 복구한 뒤 ack한다.

## Retry classification과 deadline

network timeout, throttle, temporary dependency unavailable은 retryable이다. invalid file, unsupported schema, deleted tenant, unauthorized와 permanent missing object는 terminal이다. source mapping이 retry owner이며 maximum attempt `3`, maximum event age `15분`으로 제한한다. dependency timeout은 invocation deadline보다 짧게 두고 남은 시간 안에 effect reconciliation과 ack가 가능한지 확인한다. backoff와 jitter를 사용하며 retry 전에 idempotency state를 읽는다.

## Batch failure와 ordering

source의 record별 실패 응답을 사용해 성공 record는 ack하고 실패 record만 재전달한다. 반환한 record ID와 source position을 trace로 대조한다. 기능을 비활성화하면 전체 batch가 재시도되므로 성공 record도 duplicate-safe해야 한다. partition key는 tenant+document로 두어 같은 document version의 순서를 유지한다. stale version은 current version과 비교해 거부하거나 ignore event로 기록하고 checkpoint를 이동한다.

## Concurrency, tenant fairness와 quota

function maximum concurrency는 database connection과 converter capacity보다 낮게 제한한다. source mapping의 batch·poller·parallelization과 function concurrency를 함께 제한한다. tenant별 in-flight token을 두고 shared queue에서 fair scheduling 또는 per-tenant rate limit을 적용한다. monthly quota, active-document quota, runtime concurrency와 provider quota는 별도 상태다. quota reservation은 atomic하게 생성하고 terminal failure·expiry 뒤 release한다. tenant flood 중 정상 tenant의 backlog age와 잔존 처리량을 관찰한다.

## Dead-letter와 replay

failure destination record에는 original event, source position, attempts, failure class, first/last time, function version, tenant, data class와 replay eligibility를 포함한다. owner와 alert SLA를 둔다. replay 전에 tenant active, object version, schema compatibility, existing effect, source checkpoint와 current function version을 검사한다. manual replay는 새 audit event와 replay ID를 가지며 원래 record를 덮어쓰지 않는 correction record를 남긴다.

## Observability와 evidence

모든 attempt는 failure ID, event ID, source position, attempt, tenant, function version, deadline, external effect ID, ack/checkpoint, result와 retry decision을 기록한다. metric은 unique event, attempt, duplicate suppressed, output committed, timeout, throttle, terminal failure, oldest age, failure destination, per-tenant backlog, replay outcome과 cost per successful document를 포함한다.

## Cost guard

maximum attempt·event age, per-tenant rate, maximum concurrency와 log payload limit을 둔다. poison event가 무한 retry하지 않게 하고 large payload는 object reference로 전달한다. invocation duration·source read·downstream I/O·log ingestion·failure destination·provisioned warm capacity를 cost model에 포함한다.

## Failure scenario 판정

| ID | 판정 | 필요한 evidence |
|---|---|---|
| `F04-01` | 결과 저장 뒤 timeout은 deterministic output을 재사용하고 missing status·usage만 reconciliation한 뒤 ack | attempt trace, output checksum, processing state와 ack 시각 |
| `F04-02` | 같은 tenant duplicate는 기존 processing record를 읽고 output과 usage를 추가하지 않음 | duplicate-suppressed metric과 단일 effect ID |
| `F04-03` | invalid file은 terminal 분류 후 세 번 이내 failure destination과 customer-visible failure 기록 | receive count, failure class, destination record와 owner |
| `F04-04` | batch 한 건 실패는 성공 record ack와 실패 record만 재전달 | source record ID별 partial result와 checkpoint |
| `F04-05` | tenant flood는 per-tenant token과 fair queue로 다른 tenant 잔존 처리량 보존 | tenant별 in-flight, backlog age, throttle·attempt 비용 |
| `F04-06` | deleted tenant retry는 terminal reject하고 pending output·queue cleanup을 확인 | tenant state, cleanup inventory와 deletion audit |
| `F04-07` | schema v1은 adapter 또는 version failure destination으로 보내며 무한 retry하지 않음 | schema/function version과 bounded attempt |
| `F04-08` | manual replay는 현재 effect·tenant·version과 승인자를 확인하고 correction record로 실행 | replay ID, 선택 version, approver와 linked outcome |
