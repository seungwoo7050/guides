# CDC snapshot과 change log 병합

consistent snapshot의 기준 position과 이후 change event를 연결해 현재 상태를 materialize한다.

문서: [`CDC snapshot과 log position`](../../../docs/04-ingestion-and-storage/01-cdc-snapshots-and-log-position.md)

## 입력 계약

```python
snapshot_rows = [
    {"key": "o1", "position": 10, "value": {"status": "NEW"}},
]
changes = [
    {"key": "o1", "position": 12, "operation": "UPDATE", "after": {"status": "PAID"}},
    {"key": "o1", "position": 11, "operation": "UPDATE", "after": {"status": "CANCELLED"}},
]
```

`materialize(snapshot_rows, changes)`는 key별 최신 현재 상태를 dictionary로 반환한다.

## 구현 계약

- snapshot row와 change는 key별 position으로 비교한다.
- arrival order가 아니라 source position 순서를 사용한다.
- snapshot position 이하의 stale change는 무시한다.
- `DELETE`는 row를 지우지만 마지막 position tombstone은 유지한다.
- delete보다 오래된 update가 나중에 도착해도 row가 부활하지 않는다.
- delete 뒤 더 새로운 `INSERT`는 허용한다.
- 같은 position의 중복 change는 한 번만 반영한다.
- 같은 key/position에 서로 다른 change나 snapshot payload가 있으면 임의로 하나를 고르지 않고 거부한다.

이 모델의 정수 position은 한 source의 total order를 축소 표현한다. 실제 source에서는 partition, transaction, LSN/binlog offset과 connector resume token의 보장 범위를 별도로 확인해야 한다.

## 완료 기준

- unordered change 입력이 같은 결과를 만든다.
- stale update가 최신 값을 덮지 않는다.
- delete tombstone이 stale resurrection을 막는다.
- 더 새로운 insert가 삭제된 key를 다시 만든다.

## 자기 설명

1. snapshot을 읽은 시각만 기록하고 log position을 기록하지 않으면 어떤 gap 또는 duplicate가 생기는가?
2. tombstone을 즉시 버리면 오래 지연된 update가 row를 부활시킬 수 있는 이유는 무엇인가?
3. 여러 table transaction을 row 단위 event로 분해할 때 소비자가 잃을 수 있는 원자성은 무엇인가?

## 검증

```bash
./scripts/new-workspace.sh exercises/04-ingestion-and-storage/01-cdc-snapshot-merge
./scripts/check-workspace.sh exercises/04-ingestion-and-storage/01-cdc-snapshot-merge
```

초기 skeleton은 `GUIDE_SEMANTIC:cdc-snapshot-merge`로 실패한다.
