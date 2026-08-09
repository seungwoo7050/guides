# Backfill, replay와 reconciliation

## 학습 목표

- backfill을 ad-hoc SQL이 아니라 versioned input·transform·publish·검증 작업으로 설계한다.
- live 처리와 historical replay가 충돌하지 않게 범위와 우선순위를 분리한다.
- source와 sink 대사를 count 하나가 아닌 key·aggregate·position·sample로 구성한다.
- 잘못된 backfill을 중단·rollback·재개하는 runbook을 작성한다.

## 핵심 모델

backfill은 과거 interval을 다시 계산하는 운영 작업이다.

```text
why
  누락 복구 / bug 수정 / schema 변경 / 새 dataset 생성 / source correction

what
  interval, entity, partition, source position

with which version
  input snapshot, code, schema, reference data

how publish
  replace, merge, correction journal, new version

how prove
  reconciliation, quality, lineage, consumer sign-off
```

“과거 DAG를 다시 실행한다”만으로는 충분하지 않다.

## backfill과 replay 구분

### replay

기존 raw/event input을 다시 읽어 같은 transform을 수행한다. source position과 event identity를 보존한다.

### backfill

과거 범위의 output을 생성·수정하는 더 넓은 작업이다. 새 source extract, bug-fixed code, new schema를 사용할 수 있다.

### reprocessing

기존 output을 새 algorithm/version으로 다시 계산한다.

### correction

특정 잘못된 record 또는 interval을 수정한다.

용어보다 input과 publish 의미를 명시한다.

## backfill trigger

- source outage로 누락
- transform bug
- late/corrected source data
- schema/metric 정의 변경
- 새 consumer 요구
- data retention/삭제 적용
- table re-clustering 또는 format migration

원인을 먼저 분류해야 같은 잘못이 live path에서 계속 생성되는지 확인할 수 있다. live bug를 고치기 전에 backfill을 시작하지 않는다.

## 범위 고정

```yaml
backfill_id: bf-2026-08-sales-v2
reason: exclude internal accounts
intervals:
  start: 2026-07-01T00:00:00Z
  end: 2026-08-01T00:00:00Z
source_snapshot: raw_orders_snapshot_441
transform_revision: git:abc123
reference_versions:
  account_classification: v9
publish_mode: shadow_then_replace
```

범위가 너무 크면 canary interval 또는 entity subset으로 시작한다.

## live와 backfill 격리

### compute/resource

별도 queue, pool, quota와 priority를 사용한다. live freshness SLO를 침해하지 않는다.

### output

backfill을 production table에 바로 merge하지 않고 shadow table/snapshot에 쓸 수 있다.

### identity

live dedup TTL과 historical replay가 충돌하지 않도록 backfill namespace와 deterministic key를 사용한다.

### source

source DB에 대규모 historical query를 직접 실행해 운영 부하를 만들지 않는다. immutable extract/raw layer를 우선한다.

## publish 전략

### partition replace

영향 interval이 partition과 정렬될 때 적합하다. 전체 partition을 완성·검증한 뒤 snapshot commit한다.

### shadow table + pointer swap

대규모 metric 정의 변경에 적합하다. old/new를 병렬 비교하고 consumer cutover한다.

### merge/upsert

영향 key가 sparse할 때 적합하다. stale version, delete와 unmatched key를 검사한다.

### correction journal

회계 마감처럼 과거 snapshot을 바꾸면 안 될 때 별도 adjustment record를 추가한다.

### new version dataset

의미가 호환되지 않으면 `metric_v2` 같은 새 contract와 migration을 사용한다. 이름만 바꾸는 것으로 끝내지 않고 lineage와 deprecation을 관리한다.

## reconciliation

하나의 count는 충분하지 않다.

### coverage

- source interval/position의 시작과 끝
- expected partitions/files
- watermark/offset coverage

### cardinality

- row count
- distinct key count
- duplicate key count
- unmatched key count

### aggregates

- sum(amount), count by status/date/source
- invariant totals
- null/domain distribution

### fingerprints

key-sorted deterministic digest 또는 partition hash. serialization과 order를 고정한다.

### sample/detail diff

- changed keys
- largest value differences
- missing/extra records
- expected business change와 unexplained change 분리

### temporal consistency

인접 interval boundary, cumulative metric, late correction를 검사한다.

## tolerance

모든 수치가 exact match해야 하는 것은 아니다.

- floating-point rounding
- approximate algorithms
- source가 계속 변하는 경우
- known late data

허용 오차는 이유와 범위, owner 승인을 기록한다. “1% 정도” 같은 임의 tolerance로 bug를 숨기지 않는다.

## canary와 단계 확대

```text
1 interval / 작은 tenant
→ reconciliation
→ 1주
→ consumer shadow 비교
→ 전체 범위
→ publish
```

각 단계의 stop condition을 정한다.

- duplicate key > 0
- aggregate diff > 승인 threshold
- source load 초과
- live SLO 영향
- unknown schema/error 증가

## rollback

- old snapshot/pointer 보존
- merge의 inverse 또는 source-based rebuild
- consumer cache refresh
- downstream derived dataset 재처리 범위
- lineage에 reverted status

backfill output을 publish한 뒤 downstream이 이미 사용했다면 단순 pointer rollback으로 모든 효과가 되돌아가지 않을 수 있다.

## resume

큰 backfill은 중단될 수 있다. interval/partition별 manifest에 상태를 기록한다.

```text
PENDING
RUNNING
STAGED
VALIDATED
PUBLISHED
FAILED
SUPERSEDED
```

worker local file이 아니라 durable control table/manifest를 사용한다. 재개 시 이미 published된 interval을 content/version 확인 없이 skip하지 않는다.

## consumer coordination

- metric change와 영향 기간
- expected row/aggregate diff
- publish/cutover 시각
- dashboard/cache refresh
- downstream backfill 책임
- finality와 correction notice

기술적으로 맞아도 consumer가 old/new를 혼합하면 잘못된 의사결정을 할 수 있다.

## 실패 모드

### direct production write

검증 전 live table을 수정해 중간 상태가 노출된다. shadow/staged publish를 사용한다.

### current dimension used for history

과거 fact를 현재 dimension과 join해 역사 의미가 달라진다. as-of snapshot을 고정한다.

### count-only reconciliation

누락과 중복이 상쇄돼 count가 같다. key set과 aggregate, sample diff를 함께 본다.

### backfill starves live

같은 cluster/warehouse/source를 무제한 사용한다. quota와 stop condition을 둔다.

### rerun after code drift

중단 후 `main` 최신 code로 재개해 한 backfill 안에 다른 transform이 섞인다. artifact revision을 고정한다.

### rollback ignores downstream

upstream table만 되돌리고 이미 materialized된 downstream 결과를 남긴다. lineage impact를 따라 복구한다.

## 검증 질문

1. backfill 이유와 live 원인 수정이 분리돼 있는가?
2. interval·input·code·reference version을 고정했는가?
3. live workload와 source를 보호하는 quota가 있는가?
4. publish 전 shadow 상태에서 대사할 수 있는가?
5. count 외 key·aggregate·position·sample diff를 보는가?
6. 중단·resume·rollback과 downstream propagation이 정의돼 있는가?
7. consumer가 의미 변경과 finality를 알고 있는가?

## 연결 연습

[`backfill plan`](../../exercises/05-orchestration-and-operations/01-backfill-plan/README.md)에서 실제 runbook artifact를 작성한다.

## 완료 기준

- backfill을 versioned data change로 설계한다.
- live와 historical workload를 격리한다.
- reconciliation으로 누락·중복·의미 drift를 증명한다.
- canary, stop, resume, publish, rollback과 consumer communication을 한 runbook에 연결한다.
