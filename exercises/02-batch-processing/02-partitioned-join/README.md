# Partitioned join과 skew report

Stable hash로 양쪽 record를 execution partition에 배치하고 many-to-many join cardinality, partition load와 hot key를 함께 보고한다.

문서: [`partition·shuffle·join·aggregation`](../../../docs/02-batch-processing/02-partition-shuffle-join-and-aggregation.md)

## 구현 계약

```python
def partition_for(key: str, partition_count: int) -> int: ...
def join_and_report(left, right, partition_count, hot_key_threshold, broadcast_threshold) -> dict: ...
```

- `key`를 UTF-8로 encode해 SHA-256 digest를 만들고, 첫 8 byte를 unsigned big-endian integer로 해석한 뒤 `partition_count`로 나눈 나머지를 partition 번호로 사용한다. Python process마다 달라지는 `hash()`는 사용하지 않는다.
- `partition_loads`와 `hot_keys`는 left와 right record를 합친 load를 기준으로 한다.
- 같은 key의 모든 left/right 조합을 보존하고 deterministic하게 정렬한다.
- right row 수가 `broadcast_threshold` 이하일 때만 `broadcast-right`를 선택한다.
- partition 수와 threshold는 빈 input에서도 검증하며 input record를 수정하지 않는다.

`joined`의 각 row는 정확히 `{"key": key, "left": <원본 left row의 copy>, "right": <원본 right row의 copy>}` 형태다. 결과는 `key`, key 정렬 JSON으로 표현한 `left`, 같은 방식의 `right` 순서로 정렬한다. 필드 충돌을 평평하게 합치거나 한쪽 row를 생략하지 않는다.

## 완료 기준

- process hash seed와 input 순서가 달라도 같은 partition/report를 만든다.
- many-to-many Cartesian row의 정확한 encoding, unmatched key, partition별 load 배치, hot-key 경계와 broadcast 경계를 보존한다.
- 잘못된 partition/threshold와 record key를 거부한다.

## 자기 설명

1. Python process와 replay가 달라도 같은 key가 같은 partition으로 가야 하는 이유와 이를 증명할 evidence는 무엇인가?
2. many-to-many join에서 row count뿐 아니라 정확한 left/right 조합과 partition별 load를 함께 검증해야 하는 이유는 무엇인가?
3. right row 수가 threshold 안이어도 broadcast가 위험할 수 있는 data size·skew 조건은 무엇인가?

## 검증

```bash
./scripts/new-workspace.sh exercises/02-batch-processing/02-partitioned-join
./scripts/check-workspace.sh exercises/02-batch-processing/02-partitioned-join
```

초기 skeleton은 `GUIDE_SEMANTIC:partitioned-join`으로 실패한다.
