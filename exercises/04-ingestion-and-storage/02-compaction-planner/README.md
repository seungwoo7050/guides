# Snapshot-aware compaction planner

Active data file을 partition, schema ID와 partition spec ID 경계를 넘지 않게 묶어 deterministic rewrite plan을 만든다.

문서: [`evolution·compaction·maintenance`](../../../docs/04-ingestion-and-storage/03-evolution-compaction-and-maintenance.md)

## 구현 계약

```python
def plan_compaction(files: list[dict], target_bytes: int, max_group_files: int) -> list[dict]: ...
```

- inactive file과 target 이상 file은 rewrite하지 않는다.
- partition/schema/spec이 다른 file을 섞지 않고 path를 한 번만 사용한다.
- 각 group은 2개 이상, `max_group_files` 이하이며 합계가 target을 넘지 않는다.
- boundary 안에서는 deterministic first-fit-decreasing으로 pair 가능한 file이 path 순서 때문에 고립되는 일을 줄인다.
- output은 identity, 정렬된 inputs, input bytes/rows를 포함한다.

## 완료 기준

- input 순서와 무관하며 `60,60,20,20`/target 80은 두 group으로 계획한다.
- exact-target, inactive, leftover singleton과 boundary 분리를 처리한다.
- 중복 path, bool/negative/fractional metadata와 잘못된 limit를 거부한다.

## 자기 설명

1. partition, schema ID 또는 partition spec ID가 다른 file을 한 rewrite group에 섞으면 어떤 reader·metadata 계약이 깨질 수 있는가?
2. deterministic first-fit-decreasing과 exact input identity가 retry·review·orphan cleanup에 어떤 근거를 제공하는가?
3. 이 local planner만으로는 concurrent writer와 table snapshot commit의 안전성을 증명할 수 없는 이유는 무엇인가?

## 검증

```bash
./scripts/new-workspace.sh exercises/04-ingestion-and-storage/02-compaction-planner
./scripts/check-workspace.sh exercises/04-ingestion-and-storage/02-compaction-planner
```

초기 skeleton은 `GUIDE_SEMANTIC:compaction-planner`로 실패한다.
