# Capstone C: CDC에서 분석 table까지

## 목적

PostgreSQL과 유사한 source의 주문·결제 table을 consistent snapshot과 change log로 capture하고, raw history, canonical current state와 consumer aggregate를 snapshot table로 publish한다.

실제 PostgreSQL·Debezium·Kafka·Iceberg를 사용할 수 있지만 필수는 아니다. local fixture와 position state machine으로도 계약을 검증할 수 있다.

## 시스템 경계

```text
source database
  ├── consistent snapshot
  └── committed change log
          ↓
CDC ingestion
          ↓
raw immutable change table
          ↓
canonical current-state table
          ↓
consumer daily aggregate
          ↓
quality·lineage·freshness
```

control plane:

```text
connector checkpoint
orchestration/backfill manifest
catalog/table snapshots
retention/deletion policy
incident runbook
```

## 필수 artifact

1. `source-contract.md`
2. `snapshot-stream-protocol.md`
3. `cdc-envelope.md`
4. `table-layout.md`
5. `schema-change-plan.md`
6. `quality-reconciliation.md`
7. `security-retention.md`
8. `failure-matrix.md`
9. `incident-runbook.md`
10. `submission.json` — 구현 profile, 실행·검증 명령과 알려진 한계

템플릿은 [`exercises/06-capstones/03-cdc-analytics-platform`](../../exercises/06-capstones/03-cdc-analytics-platform/README.md)에 있다.

## source 계약

- tables와 primary keys
- captured columns allowlist
- source transaction과 position
- before/after image
- hard/soft delete
- schema change notification
- snapshot load와 log retention
- connector identity와 권한

## snapshot-stream protocol

필수 증명:

- snapshot boundary position `P`
- snapshot과 `P`의 일관성
- `P` 이후 log 시작
- overlap/gap 처리
- snapshot 중 큰 transaction
- restart marker와 completed tables

## raw change table

최소 column:

```text
source_table
business_key
operation
before
after
source_position
transaction_id
transaction_sequence
commit_time
schema_version
snapshot_flag
ingested_at
run_id
```

raw는 무제한 보존을 의미하지 않는다. classification과 retention을 정한다.

## current state

- key별 최신 source position/version
- stale event 거부
- delete 적용
- key change 처리
- schema default/missing 의미
- checkpoint/rebuild

## consumer aggregate

일별 paid/refunded amount를 만든다. raw/current state 중 어떤 것을 source로 사용할지 이유를 설명한다. correction과 event-time 기준을 명시한다.

## table layout

- raw partition와 sort
- current state key/merge 전략
- aggregate partition
- file target와 compaction
- snapshot retention
- catalog recovery
- engine compatibility

## schema change 시나리오

필수:

1. nullable field 추가
2. field rename
3. numeric type 확대
4. primary key 변경 또는 key migration
5. unsupported/large field 추가

각 변화의 producer, connector, raw schema, canonical reader, sink table와 consumer 배포 순서를 작성한다.

## failure 시나리오

1. snapshot 40%에서 connector crash
2. source log retention 임박
3. sink write 성공 뒤 checkpoint 실패
4. delete event 누락
5. stale replay가 최신 row 뒤에 도착
6. catalog commit 전/후 failure
7. compaction과 live merge 충돌
8. connector outage가 retention을 초과
9. source schema change로 decoding 실패
10. 개인정보 삭제 요청이 old snapshot과 derived aggregate에 영향

## reconciliation

- source table snapshot row/key count
- raw CDC position coverage
- transaction/event count
- current-state key set와 deleted keys
- source/current aggregate by status
- consumer aggregate by date/currency
- unmatched/duplicate/stale event
- snapshot ID와 lineage

## incident runbook

최소 두 사건을 작성한다.

### connector lag와 source disk 증가

- retained log bytes 확인
- connector state와 sink throughput 확인
- source 보호를 위한 stop condition
- scale/restart/re-snapshot 결정
- consumer freshness 표시

### checkpoint position loss

- 마지막 검증 position
- live publish freeze
- 새 snapshot plan
- shadow rebuild
- reconciliation
- cutover와 old state cleanup

## 완료 판정

- snapshot과 log 사이 gap/duplicate를 fixture로 검증한다.
- insert·update·delete·key/schema change를 downstream에서 재현한다.
- duplicate/restart 뒤 current state가 source와 같다.
- table snapshot commit과 compaction이 concurrent writer를 잃지 않는다.
- source position, raw/current/aggregate snapshot과 code revision이 lineage로 연결된다.
- retention 초과와 deletion을 runbook으로 복구·증명한다.

## 범위 밖

- source DB 내부 WAL 복구 구현
- broker consensus와 replication 구현
- Kubernetes platform 구축
- ML model training
- 실제 규제 해석을 대신하는 법률 자문

## 후속 확장

- multiple source databases
- schema registry와 compatibility gate
- streaming materialized view
- cross-engine table interoperability
- automated data deletion workflow
- platform self-service connector provisioning
