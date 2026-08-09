# FaaS Event Processing Plan

## Event identity와 schema

producer가 만든 immutable `event_id`, `tenant_id`, `document_id`, `object_version`, `schema_version`, `occurred_at`을 사용한다. provider delivery ID는 attempt마다 달라질 수 있으므로 deduplication 정본으로 사용하지 않는다. event schema는 additive change를 기본으로 하고 consumer가 지원하는 version을 manifest에 기록한다.

## 상태 기계와 완료 지점

```text
RECEIVED → STARTED → OUTPUT_COMMITTED → STATUS_COMMITTED → USAGE_COMMITTED → COMPLETED
```

business 완료는 result object, database status와 usage가 모두 같은 logical operation에 연결된 상태다. 한 transaction에 묶을 수 없는 object effect는 deterministic key와 reconciliation으로 판정한다. function return은 완료 evidence 중 하나일 뿐이다.

## Idempotency와 external effect

result object key는 `tenant/document/object_version/converter_version`으로 결정한다. conditional create 또는 checksum을 사용하고, database에 event ID별 processing record를 둔다. duplicate attempt는 기존 completed result를 읽어 success로 종료하고 usage를 다시 증가시키지 않는다. output은 존재하지만 status가 없으면 reconciliation이 status와 usage를 복구한다.

## Retry classification과 deadline

network timeout, throttle, temporary dependency unavailable은 retryable이다. invalid file, unsupported schema, deleted tenant, unauthorized와 permanent missing object는 terminal이다. attempt timeout은 end-to-end deadline보다 작게 두고 maximum attempt·event age를 제한한다. backoff와 jitter를 사용하며 retry 전에 idempotency state를 읽는다.

## Batch failure와 ordering

record별 result를 반환할 수 있으면 실패 record만 재시도한다. 불가능하면 성공 record도 다시 실행돼도 안전해야 한다. partition key는 tenant+document로 두어 같은 document version의 순서를 유지한다. stale version은 current version과 비교해 거부하거나 ignore event로 기록한다.

## Concurrency, tenant fairness와 quota

function maximum concurrency는 database connection과 converter capacity보다 낮게 제한한다. tenant별 in-flight token을 두고 shared queue에서 fair scheduling 또는 per-tenant rate limit을 적용한다. monthly quota와 runtime concurrency는 별도 상태다. quota reservation은 atomic하게 생성하고 terminal failure·expiry 뒤 release한다.

## Dead-letter와 replay

dead-letter queue(DLQ) record에는 original event, attempts, failure class, first/last time, function version, tenant, data class와 replay eligibility를 포함한다. owner와 alert SLA를 둔다. replay 전에 tenant active, object version, schema compatibility, existing effect와 current function version을 검사한다. manual replay도 새 audit event와 replay ID를 가진다.

## Observability와 evidence

모든 attempt는 event ID, attempt, tenant, function version, deadline, external effect ID, result와 retry decision을 기록한다. metric은 unique event, attempt, duplicate suppressed, output committed, timeout, throttle, terminal failure, oldest age, DLQ와 cost per successful document를 포함한다.

## Cost guard

maximum attempt·event age, per-tenant rate, maximum concurrency와 log payload limit을 둔다. poison event가 무한 retry하지 않게 하고 large payload는 object reference로 전달한다. retry·DLQ·provisioned warm capacity를 cost model에 포함한다.

## Failure scenario 판정

1. 결과 저장 뒤 timeout: deterministic output을 재사용하고 missing status·usage만 reconciliation한다.
2. duplicate: processed event를 확인해 output과 usage를 추가하지 않는다.
3. invalid file: terminal 분류 후 DLQ와 customer-visible failure를 기록한다.
4. batch 한 건 실패: partial result 또는 전체 duplicate-safe retry를 사용한다.
5. tenant flood: per-tenant limit와 fair queue로 다른 tenant capacity를 보존한다.
6. deleted tenant retry: terminal reject, pending output cleanup와 audit를 수행한다.
7. schema v1: compatibility adapter 또는 unsupported destination으로 보내며 무한 retry하지 않는다.
8. manual replay: 현재 상태·effect·version을 검증하고 새 replay audit로 실행한다.
