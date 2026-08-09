# 두 초안의 보존과 통합 결정

이 문서는 `data-engineering` 브랜치를 만들 때 제공된 두 로컬 초안의 유효한 의도를 어디에 보존했고, 무엇을 현재 구조로 통합했는지 기록한다. 초안의 파일 배치를 그대로 복제하는 것이 아니라 정본 `main`의 소유 범위와 현재 세 학습 경로에 맞춰 추적 가능한 결정을 남기는 것이 목적이다.

## 기준 이력

- `data-engineering-2`는 독립 Git 저장소였으며 초기 기준 커밋 `812542d2dbb8c5a7c1e26f963f837903c64c4c26`으로 그대로 기록됐다.
- 기준 커밋과 당시 `data-engineering-2` HEAD의 tree는 모두 `bf5c6d8611d669f6c9c3364ff7d4d2146e2087cf`였다.
- `data-engineering-1`은 Git 저장소가 아니었다. 파일 이력을 새로 꾸며 내지 않고 고유 문서·예제·capstone 의도를 현재 파일에 통합했다.
- 어느 초안도 원본 위치에서 수정하거나 삭제하지 않았다.

## `data-engineering-1` 통합 지도

| 원래 의도 | 현재 근거 | 결정 |
|---|---|---|
| file·API·DB snapshot capture와 completeness | [`CDC snapshot과 log position`](../docs/04-ingestion-and-storage/01-cdc-snapshots-and-log-position.md) | CDC 외 source도 같은 progress identity로 비교하도록 file manifest, API cursor, push/webhook, snapshot chunk와 source 보호를 한 문서로 통합했다. |
| backpressure와 load control | [`state·dedup·delivery`](../docs/03-stream-processing/03-state-deduplication-and-delivery.md) | source→operator→sink 전파, retry storm, backlog recovery와 late-data 전환을 state/recovery 문맥에 통합했다. |
| dependency version과 promotion | [`orchestration·data interval`](../docs/05-orchestration-and-operations/01-orchestration-data-intervals-and-idempotency.md), [`backfill·replay`](../docs/05-orchestration-and-operations/02-backfill-replay-and-reconciliation.md) | code/runtime/config/schema/input/reference/state 판본과 old/new cutover를 실행·재처리 계약에 연결했다. |
| serving model과 consumer contract | [`데이터 제품과 소유권`](../docs/01-contracts-and-records/01-data-products-and-ownership.md), [`warehouse·lake·table format`](../docs/04-ingestion-and-storage/02-warehouse-lake-and-table-formats.md) | consumer inventory·deprecation과 raw/canonical/serving 책임으로 나눴다. 일반 application API serving은 다시 소유하지 않는다. |
| freshness·volume·cost와 data-product 운영 | [`quality·lineage·freshness`](../docs/05-orchestration-and-operations/03-quality-lineage-freshness-and-observability.md), [`시스템 종합 검토`](../docs/90-system-review.md) | source/pipeline delay, unit cost, alert·incident·consumer cutover evidence로 통합했다. |
| 작은 executable state model | [`실행 예제 지도`](../examples/README.md) | 기존 예제를 현재 단계 실습에 연결하고 dataset identity와 compaction 비용 비교를 복원했다. |
| 단계별 schema, batch, partition, stream, CDC, compaction, run ledger, reconciliation | [`exercises/manifest.json`](../exercises/manifest.json) | 대응 실습을 reference/skeleton/known-wrong 계약으로 강화했다. |
| DB snapshot/CDC + file + API를 잇는 commerce capstone | 아래 교차 경로 확장 | 세 기존 capstone을 중복하지 않고 완료 artifact를 같은 source cutoff와 reconciliation로 묶는 선택 확장으로 보존했다. |

## 복원한 작은 관찰 모델

### 재현 가능한 dataset identity

[`dataset_identity.py`](../examples/dataset_identity.py)는 다음 판본을 canonical manifest에 넣고 content digest를 만든다.

```text
product와 data interval
source positions 또는 delivery manifests
code revision
result-affecting config
schema versions
reference data versions
```

Map 입력 순서는 identity를 바꾸지 않지만 어느 고정 판본이든 달라지면 identity가 달라진다. `latest`, `current`, `main` 같은 floating version은 재현 근거로 거부한다. Digest가 실제 source의 존재나 접근 권한을 증명하지는 않는다.

### Compaction의 두 비용

[`compaction_cost.py`](../examples/compaction_cost.py)는 small file 여러 개를 한 output으로 바꿀 때 줄어드는 file/metadata request 수와 다시 써야 하는 byte를 함께 보여 준다. 이는 deterministic local estimate이며 table snapshot commit, concurrent writer, object-store request 가격이나 실제 compression ratio는 [`compaction planner`](../exercises/04-ingestion-and-storage/02-compaction-planner/README.md)와 선택 runtime에서 별도로 검증한다.

## 교차 경로 확장: commerce 데이터 제품

이 확장은 세 capstone의 대체물이나 네 번째 필수 capstone이 아니다. 각 capstone을 완료한 학습자가 서로 다른 source와 처리 모드가 같은 업무 의미를 유지하는지 검토하는 선택 과제다.

```text
orders DB snapshot + CDC
payments file delivery
refund API 또는 webhook
        ↓
raw capture와 공통 source cutoff
        ├── replay-safe batch → daily revenue snapshot
        ├── event-time stream → 5분 집계와 late correction
        └── CDC projection    → canonical current state
        ↓
cross-path quality·freshness·lineage·reconciliation
```

기존 artifact 재사용:

- Batch capstone: input manifest, deterministic transform, staged publish와 backfill
- Stream capstone: event/window policy, state/checkpoint, correction과 batch reconciliation
- CDC capstone: snapshot/log protocol, source position, current-state/table snapshot과 schema change

추가 evidence만 작성한다.

| 단계 | 교차 경로 evidence |
|---|---|
| 1. Contract | 세 output이 공유하는 order/payment/refund identity, event time, correction와 owner |
| 2. Capture | DB position, file manifest와 API cursor를 같은 cutoff/replay 범위로 묶은 capture manifest |
| 3. Processing | 입력 순서·duplicate·restart permutation 뒤 batch/stream/current-state의 논리 결과 |
| 4. Storage·publish | 각 public snapshot과 result version, validation 전후 consumer-visible 상태 |
| 5. Operation | live·backfill·replay quota, pause/resume/abort와 source 보호 기준 |
| 6. Reconciliation | 같은 cutoff의 key set, currency amount, delete/correction와 late distribution diff |
| 7. Evidence·security | run/input/output/code/schema/quality lineage, freshness·cost, access·retention·deletion |
| 8. Evolution | old/new schema와 metric diff, representative consumer cutover, rollback/roll-forward |

최소 실패 trace에는 partial file, API response loss, snapshot/log gap, conflicting event ID, late refund, checkpoint/publish 전후 crash와 live/backfill capacity 충돌을 포함한다. 한 경로가 성공했다는 사실로 다른 두 경로의 completeness를 추정하지 않는다.

## 의도적으로 통합하거나 제외한 것

- 초안의 제품별 설치 순서는 정본이 아니다. 공통 identity·time·state·publish·replay 계약을 먼저 둔다.
- 동일 개념을 문서 수를 맞추기 위해 중복하지 않았다. 예를 들어 backpressure는 별도 장보다 state/recovery 흐름 안에서 다룬다.
- 실제 cloud, broker, warehouse와 table format은 선택 profile이다. 유료 자원이나 production system 변경은 필수 검증에 포함하지 않는다.
- 원본 초안의 간단한 self-test보다 현재 reference/skeleton/known-wrong checker를 우선한다.
- 교차 경로 확장은 root 자동 검사만으로 완료되지 않는다. 선택 runtime의 fixture·trace·result digest와 사람 rubric 검토가 필요하다.
