# 실행 예제 지도

이 디렉터리의 예제는 Python 표준 라이브러리만으로 데이터 엔지니어링의 작은 상태·identity·비용 경계를 관찰한다. 제품 SDK의 동작을 흉내 내거나 production 보장을 대신하지 않는다. 각 예제의 축소 가정은 대응 문서와 단계 실습에서 다시 확인한다.

| 예제 | 관찰하는 계약 | 다음 단계 |
|---|---|---|
| [`dataset_identity.py`](dataset_identity.py) | source position, interval, code, config, schema와 reference 판본이 하나의 재현 가능한 dataset identity를 만드는 방식 | [`replay-safe batch`](../exercises/02-batch-processing/01-replay-safe-batch/README.md), [`run ledger`](../exercises/05-orchestration-and-operations/03-run-ledger-backfill/README.md) |
| [`schema_compatibility.py`](schema_compatibility.py) | old/new reader와 writer 방향, default와 type promotion | [`schema evolution`](../exercises/01-contracts-and-records/01-schema-evolution/README.md) |
| [`replay_safe_batch.py`](replay_safe_batch.py) | input manifest, deterministic aggregate와 staged snapshot publish | [`replay-safe batch`](../exercises/02-batch-processing/01-replay-safe-batch/README.md) |
| [`partition_cost.py`](partition_cost.py) | deterministic hash partition과 key skew가 partition load에 미치는 영향 | [`partitioned join`](../exercises/02-batch-processing/02-partitioned-join/README.md) |
| [`compaction_cost.py`](compaction_cost.py) | 작은 file을 묶을 때 줄어드는 file/metadata request와 다시 쓰는 byte의 trade-off | [`compaction planner`](../exercises/04-ingestion-and-storage/02-compaction-planner/README.md) |
| [`windowing_model.py`](windowing_model.py) | event-time fixed window, watermark와 correction version | [`event-time windows`](../exercises/03-stream-processing/01-event-time-windows/README.md) |
| [`cdc_merge.py`](cdc_merge.py) | snapshot position과 change log를 current state로 합치는 경계 | [`CDC snapshot merge`](../exercises/04-ingestion-and-storage/01-cdc-snapshot-merge/README.md) |
| [`quality_report.py`](quality_report.py) | grain key에 묶인 completeness·uniqueness·event-time evidence | [`quality and lineage`](../exercises/05-orchestration-and-operations/02-quality-and-lineage/README.md) |
| [`lineage_model.py`](lineage_model.py) | run, job, input/output snapshot과 code revision을 잇는 lineage event 형태 | [`quality and lineage`](../exercises/05-orchestration-and-operations/02-quality-and-lineage/README.md) |

추가·복원된 결정적 예제 검사는 다음처럼 실행한다.

```bash
python3 -B -m unittest tests.test_preserved_examples -v
```

전체 예제와 단계 계약은 저장소 루트의 `make check`와 `make verify`로 검사한다. 작은 예제가 통과해도 실제 engine의 schema resolution, table commit, checkpoint, object-store 원자성이나 대규모 비용을 증명하지 않는다.
