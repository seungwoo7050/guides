# 품질, lineage, freshness와 관측

## 학습 목표

- pipeline health와 data health를 분리한다.
- schema·completeness·uniqueness·validity·consistency·freshness 검사를 grain과 consumer 영향에 연결한다.
- dataset, job, run, input/output snapshot으로 lineage를 모델링한다.
- alert가 실제 조치와 runbook으로 이어지도록 설계한다.

## 핵심 모델

```text
infrastructure health
  worker, CPU, memory, network, scheduler

pipeline health
  task/run state, retry, duration, lag

data health
  schema, keys, values, coverage, freshness, reconciliation

consumer health
  query success, dashboard/feature latency, decision impact
```

한 계층이 정상이어도 다른 계층은 실패할 수 있다.

## quality rule의 구조

좋은 rule은 다음을 포함한다.

- dataset과 grain
- 검사 대상 interval/snapshot
- metric 계산법
- expected range 또는 invariant
- severity
- failure action
- owner와 runbook
- known exception와 expiry

예:

```yaml
rule: order_id_unique
scope: analytics.orders_current@daily_snapshot
metric: duplicate_count(order_id)
expectation: 0
severity: block_publish
owner: data-commerce
```

## 품질 차원

### schema

- expected field/type
- required/nullable
- schema version/compatibility
- unexpected field 처리

### completeness

- source coverage
- expected partitions
- row/key count range
- source position gap
- mandatory entity 포함

### uniqueness

반드시 grain key와 scope를 지정한다.

### validity

- domain/enum
- range
- format
- state transition
- timestamp plausibility

### consistency

- cross-table referential expectation
- source/sink aggregate
- mutually exclusive state
- balance/inventory invariant

### freshness

다음 시각을 구분한다.

- latest event time
- latest source observed time
- latest ingestion time
- latest successful run
- latest published snapshot
- consumer query visibility

`MAX(event_time)`만 보면 미래 timestamp 하나가 freshness를 정상처럼 보이게 할 수 있다.

### volume/distribution

row count, null rate, category distribution, quantile drift. 계절성과 캠페인을 고려하지 않은 고정 threshold는 false alarm을 만든다.

## blocking과 monitoring

### block publish

schema mismatch, duplicate primary key, source coverage gap처럼 consumer가 읽으면 명백히 잘못되는 경우다.

### publish with warning

경미한 distribution drift처럼 결과는 사용 가능하지만 조사해야 하는 경우다.

### quarantine record

일부 malformed record를 격리하고 나머지를 처리할 수 있다. quarantine 비율과 재처리 경로를 운영한다.

### fail open/closed

업무 영향과 잘못된 data 사용 비용을 비교한다. 조용히 default로 대체하지 않는다.

## Sticky quarantine와 repair

같은 stable ID에 서로 다른 payload가 나타나면 도착 순서로 첫 record를 채택하지 않는다. 해당 ID를 evaluation scope 전체에서 conflict로 표시하고, 이후 첫 payload와 같은 record가 다시 와도 자동으로 valid 집합에 재승인하지 않는다. 그렇지 않으면 input permutation에 따라 결과가 달라진다.

Quarantine record에는 다음 control metadata를 남긴다.

- source identity와 input snapshot/position
- record/event ID와 payload checksum
- violated rule ID·version, severity와 observed time
- raw payload의 보호된 위치 또는 redacted evidence
- owner, disposition과 repair run ID
- `OPEN`, `APPROVED_EXCEPTION`, `REPAIRED`, `DISCARDED` 같은 상태와 actor

Rule 수정, source correction 또는 schema migration 뒤에는 original snapshot과 같은 conflict set을 대상으로 repair/reprocess한다. Repaired record는 새 quality result와 lineage로 publish하고 원 quarantine을 덮어쓰지 않는다. Exception에는 scope와 expiry가 필요하다.

Source와 target을 독립적으로 검사한다. Count와 amount가 같아도 missing/extra/changed key가 서로 상쇄될 수 있으므로 key set, aggregate, deterministic fingerprint와 detail sample을 함께 대사한다.

## lineage 모델

최소 entity:

```text
dataset
  namespace + name + version/snapshot

job
  반복 가능한 transform 정의

run
  job의 한 실행, unique run ID

run event
  START/RUNNING/COMPLETE/FAIL 등 상태 전이

input/output facets
  schema, data source, partition, quality, code revision
```

lineage는 정적 화살표만이 아니라 특정 run이 실제로 어떤 input snapshot을 읽고 어떤 output snapshot을 만들었는지 기록해야 한다.

## column-level lineage

유용하지만 모든 표현을 완벽히 해석하기 어렵다.

- SQL projection과 expression
- UDF
- dynamic code
- external API
- implicit filter와 policy

자동 수집 결과의 정확도와 비보장을 기록한다. 중요한 metric은 수동 semantic lineage와 owner를 보완한다.

## observability metadata

run마다 권장:

- run ID, interval, attempt
- code/artifact revision
- input/output snapshot IDs
- source positions
- records/bytes in/out
- rejected/quarantined count
- duplicate/late count
- watermark/lag/freshness
- quality results
- publish status
- duration and resource summary

민감 payload를 log/trace에 넣지 않는다.

## Freshness 지연과 cost evidence

하나의 `MAX(event_time)` 대신 지연을 분해한다.

```text
source delay   = source observed/commit time - event occurred time
pipeline delay = consumer-visible publish time - source observed/commit time
total age      = now - latest trusted event time
oldest backlog = now - oldest unprocessed observed time
```

미래 timestamp와 일부 빠른 partition이 전체 freshness를 정상처럼 보이게 할 수 있다. Source position coverage, partition별 oldest age, watermark, publish time과 plausibility rule을 함께 본다. Alert는 freshness breach만 알리지 않고 source outage, queue/backpressure, transform failure, quality block, publish failure 중 어느 계층에서 지연이 생겼는지 좁힐 근거를 제공한다.

비용도 shared platform 총액이 아니라 dataset/run과 owner에 귀속한다.

- input/output bytes와 rows, shuffle·state·checkpoint volume
- source extraction, compute, storage, catalog/metadata와 query 비용
- live, backfill, replay, compaction과 quality/reconciliation 비용 분리
- `cost per successful interval`, `cost per GiB processed`, `cost per million records` 같은 unit cost
- 실패·retry·quarantine·unused copy가 만든 waste

Freshness를 낮추기 위해 micro-batch를 짧게 하면 small file, metadata와 compaction 비용이 커질 수 있다. 비용 절감이 retention, correction window, recovery capacity와 quality evidence를 훼손하지 않는지 검토한다.

## alert design

좋은 alert는 질문에 답한다.

- 무엇이 잘못됐는가?
- 어떤 dataset/interval/consumer가 영향받는가?
- 마지막 정상 snapshot은 무엇인가?
- 지금 data가 stale, partial, invalid 중 무엇인가?
- 자동 retry가 진행 중인가?
- operator가 처음 확인할 명령과 dashboard는 무엇인가?
- publish를 막아야 하는가?

### symptom과 cause

freshness breach는 source outage, scheduler 지연, transform failure, quality block, catalog publish failure 중 무엇이든 원인일 수 있다. alert를 한 원인으로 단정하지 않는다.

## incident timeline

```text
01:00 run scheduled
01:03 source snapshot ready
01:12 transform completed
01:13 quality duplicate-key failed
01:14 publish blocked; previous snapshot remains current
01:20 source schema change identified
02:05 compatible reader deployed
02:22 rerun validated and published
```

consumer-visible 상태와 operator 조치를 함께 기록한다.

## SLO

data SLO 예:

- freshness: 99% daily partitions by 02:00 UTC
- completeness: 99.99% source keys within correction window
- correctness proxy: blocking rules pass 100%
- recovery: failed daily partition published within 2 hours

SLO는 모든 품질을 완전히 증명하지 않는다. consumer가 중요하게 여기는 observable outcome을 선택한다.

## lineage를 사용하는 작업

- schema change impact analysis
- failed source의 downstream 영향
- backfill propagation 범위
- PII field 위치와 삭제
- unused dataset deprecation
- incident root cause
- reproducible model/report input

lineage graph가 최신인지, runtime 실제 실행을 반영하는지 확인한다.

## 실패 모드

### green DAG, stale data

run은 성공했지만 old input snapshot을 다시 publish한다. snapshot/freshness identity를 검사한다.

### too many noisy rules

action이 없는 threshold alert가 반복돼 무시된다. severity, owner와 expiry를 둔다.

### null rate alert without semantics

optional field의 정상 null을 장애로 본다. field 의미와 segment별 baseline을 사용한다.

### lineage only from code parsing

runtime dynamic input과 actual snapshot이 누락된다. run event와 artifact metadata를 수집한다.

### future timestamp masks freshness

잘못된 미래 event 하나가 max time을 올린다. quantile, source position, publish time과 plausibility rule을 함께 본다.

### quality result not tied to publish

검사는 실패했지만 dataset pointer가 이미 바뀐다. staged output과 quality gate 뒤 commit한다.

## 검증 질문

1. pipeline, data와 consumer health를 분리했는가?
2. 각 rule이 grain, interval, severity와 action을 갖는가?
3. freshness를 어떤 시각과 snapshot으로 정의하는가?
4. lineage가 job 정의뿐 아니라 실제 run input/output을 기록하는가?
5. alert가 영향·마지막 정상 상태·runbook을 제공하는가?
6. quality failure 때 publish와 previous snapshot 상태가 명확한가?

## 연결 연습

[`quality and lineage`](../../exercises/05-orchestration-and-operations/02-quality-and-lineage/README.md)에서 quality report와 run-level lineage event를 생성한다.

## 완료 기준

- task 성공과 data correctness를 구분한다.
- consumer contract에 맞춘 quality/freshness rule을 설계한다.
- run·dataset snapshot·code revision을 연결하는 lineage를 남긴다.
- alert, publish gate, incident와 recovery evidence를 한 흐름으로 운영한다.
- conflict identity를 sticky quarantine으로 유지하고 repair를 새 quality·lineage 결과로 추적한다.
- source/pipeline delay와 dataset/run unit cost를 freshness·capacity 판단에 함께 사용한다.

## 공식 자료 연결

OpenLineage는 dataset, job과 run event를 표현하는 공개 모델의 예다. 최신 specification 링크는 [`reference/official-sources.md`](../../reference/official-sources.md)에 있다.
