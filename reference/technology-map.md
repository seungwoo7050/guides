# 구현 기술 지도

이 표는 제품 추천 순위가 아니다. 설계한 계약을 실제로 관찰하기 위한 **선택적 구현 profile**이다.

| 책임 | 경량 학습 profile | 실제 플랫폼 예시 | 반드시 다시 검증할 계약 |
|---|---|---|---|
| Record/schema | JSON + Python validator | Avro/Protobuf/JSON Schema + registry | reader/writer 방향, semantic change, rollout |
| Batch transform | Python files/SQLite | Spark, Beam, warehouse SQL, dbt | input snapshot, determinism, shuffle/skew, publish |
| Stream | Python event-time simulator | Beam, Flink, Kafka Streams | watermark, trigger, state, checkpoint, sink commit |
| CDC | snapshot + ordered JSON log | Debezium 등 source connector | consistent snapshot, position, transaction, delete, restart |
| Storage | versioned local directories | warehouse/lake + Iceberg/Delta/Hudi | snapshot commit, concurrency, schema/partition evolution |
| Orchestration | manifest + shell/Python | Airflow, Dagster, Prefect 등 | data interval, retry, catchup, backfill, cancellation |
| Quality | Python checks + report | dbt tests, Great Expectations, Soda 등 | grain-aware rule, publish gate, ownership, false signal |
| Lineage | JSON run event | OpenLineage integrations | run/job/dataset identity, snapshot/version, failure event |
| Catalog/governance | Markdown/JSON inventory | data catalog, policy engine | classification, access, retention, deletion propagation |

## 선택 절차

1. 먼저 source, grain, identity, time과 publish 계약을 문서화한다.
2. 필요한 state와 failure를 재현할 수 있는 가장 작은 profile로 검증한다.
3. scale, latency, ecosystem, operations와 team 제약을 기록한다.
4. 후보 플랫폼의 공식 문서에서 정확한 보장 범위를 확인한다.
5. 같은 failure fixture를 실제 플랫폼에서 다시 실행한다.
6. 제품 변경에 종속되지 않는 runbook과 reconciliation을 남긴다.

## 경고

- “exactly-once 지원”이라는 제품 문구만으로 source부터 consumer 업무 효과까지 한 번만 발생한다고 결론 내리지 않는다.
- object storage에서 local filesystem rename과 같은 원자성을 가정하지 않는다.
- scheduler가 task를 성공 처리했다고 output data가 맞다고 결론 내리지 않는다.
- table format이 schema evolution을 지원한다고 semantic compatibility가 자동 보장된다고 결론 내리지 않는다.
