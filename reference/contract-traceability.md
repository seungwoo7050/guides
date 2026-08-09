# Data Engineering contract traceability

이 문서는 `main`의 `data-engineering` 계약이 개념, 단계 연습, 대표 실패, capstone과 종료 근거로 이어지는 위치를 고정한다. 링크가 존재한다는 사실만으로 학습 결과가 증명되지는 않는다. 실제 구현·실행 evidence와 사람 검토가 필요하다.

## 정본 계약

- kind: `specialization`
- requires: `python`, `database-systems`
- recommends: `distributed-services`, `distributed-systems`
- connects: `machine-learning`, `platform-engineering`
- continues to: `platform-engineering`

```text
데이터 계약과 schema evolution
batch·stream 처리
event time·window·late data
CDC·warehouse·lake
orchestration·quality·lineage·backfill
```

종료 능력은 다음 세 가지다.

```text
재실행 가능한 데이터 파이프라인을 설계한다
late event와 backfill을 처리한다
품질·freshness·lineage를 운영 근거로 남긴다
```

## Owns 1: 데이터 계약과 schema evolution

- 개념: [`데이터 제품과 소유권`](../docs/01-contracts-and-records/01-data-products-and-ownership.md), [`schema evolution과 호환성`](../docs/01-contracts-and-records/02-schema-evolution-and-compatibility.md), [`identity·시간·correction`](../docs/01-contracts-and-records/03-identity-time-and-corrections.md), [`분석 모델과 역사`](../docs/01-contracts-and-records/04-analytical-modeling-and-history.md)
- 단계 evidence: [`schema evolution`](../exercises/01-contracts-and-records/01-schema-evolution/README.md)에서 old/new reader 방향, key와 semantic change를 구분한다.
- 대표 실패: physical schema는 통과하지만 unit/time 의미가 바뀜, default가 거짓 사실을 만듦, grain mismatch, old/new reader 혼합과 consumer shadow dependency.
- 누적 evidence: Batch capstone의 `data-contract.md`, Stream capstone의 `event-contract.md`, CDC capstone의 `source-contract.md`와 `schema-change-plan.md`; 각 capstone의 `evidence.json`이 같은 run/input/code/output identity와 scenario 관측 파일을 연결한다.
- 연결되는 종료 능력: 모든 input/output identity와 판본을 재현 가능하게 만들고, late correction의 의미와 quality/freshness owner를 고정한다.

## Owns 2: batch·stream 처리

- 개념: [`replay-safe batch`](../docs/02-batch-processing/01-bounded-data-and-replay-safe-batch.md), [`partition·shuffle·join`](../docs/02-batch-processing/02-partition-shuffle-join-and-aggregation.md), [`columnar layout`](../docs/02-batch-processing/03-columnar-files-and-table-layout.md), [`unbounded data와 event time`](../docs/03-stream-processing/01-unbounded-data-and-event-time.md), [`window·watermark·trigger`](../docs/03-stream-processing/02-windows-watermarks-and-triggers.md), [`state·dedup·delivery`](../docs/03-stream-processing/03-state-deduplication-and-delivery.md)
- 단계 evidence: [`replay-safe batch`](../exercises/02-batch-processing/01-replay-safe-batch/README.md), [`partitioned join`](../exercises/02-batch-processing/02-partitioned-join/README.md), [`event-time windows`](../exercises/03-stream-processing/01-event-time-windows/README.md), [`stateful dedup`](../exercises/03-stream-processing/02-stateful-dedup/README.md).
- 대표 실패: duplicate/conflicting event, input permutation, partial publish, many-to-many fan-out와 hot key, checkpoint/sink failure, retry storm과 backlog가 allowed lateness를 넘김.
- 누적 evidence: [`Batch 데이터 제품`](../docs/06-capstones/01-batch-data-product.md)의 manifest·staged publish·backfill과 [`Event-time pipeline`](../docs/06-capstones/02-event-time-pipeline.md)의 state·sink·batch reconciliation. 두 capstone은 각 문서의 정상·순서 변경·duplicate/conflict·restart/publish·reconciliation 경계를 rubric과 `evidence.json`의 같은 ID로 고정한다.
- 연결되는 종료 능력: 동일 input/version의 재실행이 같은 logical output으로 수렴하고, late/duplicate/restart를 정상 입력으로 처리한다.

## Owns 3: event time·window·late data

- 개념: [`identity·시간·correction`](../docs/01-contracts-and-records/03-identity-time-and-corrections.md), [`unbounded data와 event time`](../docs/03-stream-processing/01-unbounded-data-and-event-time.md), [`window·watermark·trigger`](../docs/03-stream-processing/02-windows-watermarks-and-triggers.md), [`state·dedup·delivery`](../docs/03-stream-processing/03-state-deduplication-and-delivery.md).
- 단계 evidence: [`event-time windows`](../exercises/03-stream-processing/01-event-time-windows/README.md)와 [`stateful dedup`](../exercises/03-stream-processing/02-stateful-dedup/README.md)에서 boundary, watermark, allowed lateness, dedup TTL, stale/delete/conflict를 검사한다.
- 대표 실패: processing-time 집계, watermark를 완전성 보장으로 오해, late drop 무기록, idle partition, TTL 이후 duplicate, late update가 새 state를 덮음.
- 누적 evidence: Stream capstone의 `window-policy.md`, `state-and-checkpoint.md`, `sink-contract.md`, `quality-and-lateness.md`, `reconciliation.md`와 `evidence.json`의 고유 failure trace.
- 연결되는 종료 능력: late event를 correction/quarantine/batch replay 중 명시한 경로로 처리하고 backfill 결과와 key/window별로 대사한다.

## Owns 4: CDC·warehouse·lake

- 개념: [`CDC snapshot과 log position`](../docs/04-ingestion-and-storage/01-cdc-snapshots-and-log-position.md), [`warehouse·lake·table format`](../docs/04-ingestion-and-storage/02-warehouse-lake-and-table-formats.md), [`evolution·compaction·maintenance`](../docs/04-ingestion-and-storage/03-evolution-compaction-and-maintenance.md).
- 단계 evidence: [`CDC snapshot merge`](../exercises/04-ingestion-and-storage/01-cdc-snapshot-merge/README.md)와 [`compaction planner`](../exercises/04-ingestion-and-storage/02-compaction-planner/README.md).
- 대표 실패: snapshot/log gap, equal position/key conflict, stale replay after delete, retention loss, file write without table commit, compaction/live writer conflict, expiration이 reader/backfill을 깨뜨림.
- 누적 evidence: [`CDC analytics platform`](../docs/06-capstones/03-cdc-to-analytics-platform.md)의 snapshot-stream protocol, envelope, table layout, schema change, reconciliation, security-retention, incident runbook과 같은 identity를 공유하는 `evidence.json`.
- 연결되는 종료 능력: snapshot/position/version을 고정해 CDC projection을 재구축하고, table snapshot과 source/current/aggregate 대사로 결과를 증명한다.

## Owns 5: orchestration·quality·lineage·backfill

- 개념: [`orchestration·data interval`](../docs/05-orchestration-and-operations/01-orchestration-data-intervals-and-idempotency.md), [`backfill·replay·reconciliation`](../docs/05-orchestration-and-operations/02-backfill-replay-and-reconciliation.md), [`quality·lineage·freshness`](../docs/05-orchestration-and-operations/03-quality-lineage-freshness-and-observability.md), [`security·governance·retention`](../docs/05-orchestration-and-operations/04-security-governance-and-retention.md).
- 단계 evidence: [`backfill plan`](../exercises/05-orchestration-and-operations/01-backfill-plan/README.md), [`quality and lineage`](../exercises/05-orchestration-and-operations/02-quality-and-lineage/README.md), [`run ledger`](../exercises/05-orchestration-and-operations/03-run-ledger-backfill/README.md), [`quality reconciliation`](../exercises/05-orchestration-and-operations/04-quality-reconciliation/README.md).
- 대표 실패: task success/data failure 혼동, active run 중복, invalid state transition, live/backfill conflict, count-only reconciliation, conflicting ID 재승인, quality failure 뒤 publish, stale lineage와 freshness.
- 누적 evidence: 세 capstone의 failure matrix, reconciliation, runbook, submission metadata와 scenario evidence manifest를 [`시스템 종합 검토`](../docs/90-system-review.md)에서 함께 검사한다.
- 연결되는 종료 능력: run/input/output/code/schema/quality identity를 연결하고, canary·stop·resume·rollback·consumer cutover와 freshness/lineage evidence를 운영한다.

## Exit capability evidence

| Exit capability | 최소 단계 evidence | 누적·운영 evidence |
|---|---|---|
| 재실행 가능한 데이터 파이프라인을 설계한다 | replay-safe batch, CDC merge, run ledger/backfill에서 input permutation·duplicate·restart 뒤 같은 logical state | Batch의 same-manifest snapshot, Stream의 checkpoint/sink recovery, CDC의 rebootstrap/table snapshot; input·code·config·schema·reference와 output lineage |
| late event와 backfill을 처리한다 | event-time window/stateful dedup의 allowed-lateness·TTL 경계와 versioned backfill plan | Stream의 correction/quarantine/batch reconciliation, Batch의 late refund, CDC의 stale replay/re-snapshot; live quota·canary·stop·resume·rollback |
| 품질·freshness·lineage를 운영 근거로 남긴다 | quality-lineage와 quality-reconciliation의 publish gate, sticky quarantine, source/target diff | 세 capstone의 quality/reconciliation/runbook/submission; source/pipeline delay, oldest backlog, unit cost, secure repair/deletion과 consumer sign-off |

## Ownership boundaries

- 모델 학습·평가와 model artifact는 `machine-learning`이 소유한다. 이 가이드는 재현 가능한 input dataset과 lineage까지만 다룬다.
- MVCC·WAL·query optimizer 등 DBMS 내부구조 전체는 `database-systems`가 소유한다. 이 가이드는 source snapshot/position과 downstream CDC 의미를 사용한다.
- 애플리케이션 command, Outbox, Saga와 업무 보상은 `distributed-services`가 소유한다. 이 가이드는 전달된 record의 replay·dedup·data reconciliation을 다룬다.
- cluster, Kubernetes, IaC와 multi-team self-service provisioning 전체는 `platform-engineering`이 소유한다. 이 가이드는 pipeline workload가 요구하는 resource·quota·evidence contract까지만 다룬다.

## Human review

자동 검사는 reference의 공개 행동, skeleton/known-wrong 거부, link, capstone 필수 section, identity와 scenario evidence의 정적 연결을 검증할 수 있다. evidence가 실제 runtime 실행에서 생성됐는지와 다음 판단은 사람과 선택 runtime의 검토가 필요하다.

- 설명이 실제 source·engine·table format의 semantics와 일치하는가?
- failure injection이 consumer-visible state, cleanup과 recovery를 실제로 증명하는가?
- capstone artifact가 서로 같은 grain·identity·time·version을 사용하는가?
- canary가 실제 consumer와 workload를 대표하고 semantic change를 승인했는가?
- quarantine, access, retention과 deletion propagation이 조직 정책에서 실행 가능한가?
- 대규모 data, 장기 backfill과 비용 압력에서 아직 보장하지 않는 범위를 공개했는가?

`make check`와 `make verify` 통과만으로 이 검토를 완료했다고 주장하지 않는다.
