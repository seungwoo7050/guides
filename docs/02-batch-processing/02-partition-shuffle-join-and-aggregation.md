# Partition, shuffle, join과 aggregation

## 학습 목표

- logical partition과 physical execution partition을 구분한다.
- shuffle가 왜 발생하고 network·disk·memory 비용을 만드는지 설명한다.
- join 전략을 data size, key 분포, ordering과 memory 조건으로 선택한다.
- skew와 fan-out을 평균이 아닌 key별 분포로 진단한다.

## 핵심 모델

분산 batch 처리의 비용은 보통 record별 함수보다 **데이터를 어디에 모아야 하는가**에서 발생한다.

```text
map/local transform
  현재 partition 안에서 처리 가능

shuffle
  같은 key 또는 정렬 순서를 만들기 위해 record를 worker 사이에 재배치

reduce/stateful transform
  재배치된 key group 또는 partition을 집계·join·sort
```

engine 이름이 달라도 key grouping과 data movement 문제는 유지된다.

## 네 가지 partition

### source partition

파일, Kafka partition, DB split처럼 source가 제공하는 병렬 읽기 단위다.

### execution partition

worker task가 한 번에 처리하는 record 집합이다. source partition과 같을 수도 있고 split/merge될 수 있다.

### dataset partition

consumer-visible physical layout이다. 예: `event_date=2026-08-08` directory.

### business grouping key

집계와 state가 필요한 논리 key다. 예: `customer_id`.

같은 단어를 사용해도 역할이 다르다. `event_date`로 저장 partition을 나눴다고 customer별 aggregation shuffle가 사라지는 것은 아니다.

## partition 수와 크기

너무 적으면:

- 병렬성이 부족하다.
- 한 task가 큰 memory·spill을 가진다.
- straggler 영향이 커진다.

너무 많으면:

- scheduling overhead가 커진다.
- 작은 file과 metadata가 늘어난다.
- open/close와 commit 비용이 커진다.

고정된 “최적 partition 수”는 없다. input size, record size, operator, cluster, file target, downstream query를 측정한다.

## shuffle

다음 연산은 흔히 shuffle를 만든다.

- `group by key`
- repartition
- global sort
- non-co-located join
- distinct
- windowed aggregation

shuffle 단계에서 관찰할 것:

- input/output bytes와 records
- key cardinality와 상위 hot key
- task duration 분포
- spill bytes와 disk usage
- network throughput와 retry
- partition별 record/byte histogram

평균 task duration만 보면 hot partition을 놓친다.

## join cardinality

join 전에 기대 행 수를 계산한다.

```text
1:1    최대 한 쪽 key당 한 행
1:N    dimension 또는 parent와 여러 fact
N:M    양쪽에 중복 key가 있어 곱집합 가능
```

의도하지 않은 N:M은 data correctness와 성능을 동시에 깨뜨린다.

검사:

- 각 side key uniqueness
- unmatched key 수
- input/output row count ratio
- key별 max multiplicity
- null key 처리

## join 전략

### broadcast/hash join

작은 side를 각 worker memory에 복제하고 큰 side를 local lookup한다.

적합 조건:

- 작은 side가 실제로 각 worker memory에 들어감
- snapshot/version이 모든 worker에서 같음
- size 추정이 신뢰 가능

위험:

- “작다”는 평균 또는 compressed disk size만 보고 결정
- skewed nested value로 memory 폭증
- 여러 동시 task가 같은 side를 복제

### partitioned hash join

양쪽을 join key로 shuffle한 뒤 partition별 hash join을 수행한다. 큰 dataset끼리 일반적이지만 network와 spill 비용이 크다.

### sort-merge join

양쪽을 key로 partition·sort하고 merge한다. 이미 정렬돼 있거나 range scan이 유리할 수 있다. sort와 spill 비용을 고려한다.

### bucket/co-partitioned join

동일 partitioning과 bucket contract를 유지하면 shuffle를 줄일 수 있다. writer 수, hash function, bucket count와 schema 변경을 장기간 관리해야 한다.

### lookup join

외부 key-value/DB를 record마다 조회하면 latency, rate limit과 일관성 문제가 생긴다. batch snapshot을 materialize하거나 async/batched access와 version contract를 둔다.

## aggregation

### combinable aggregation

sum, count, min, max처럼 부분 결과를 다시 합칠 수 있으면 local pre-aggregation으로 shuffle volume을 줄인다.

### non-associative logic

순서나 전체 record가 필요한 계산은 병렬 reduction 결과가 달라질 수 있다. floating-point 합, percentile, custom list mutation의 정확성과 결정성을 검토한다.

### distinct

distinct는 중복 원인을 해결하지 않고 결과에서 숨길 수 있다. grain과 join multiplicity를 먼저 조사한다. 정확 distinct가 필요한지 approximate cardinality로 충분한지도 구분한다.

## skew

### 원인

- 매우 인기 있는 customer/product
- `null` 또는 default key에 모든 record 집중
- 날짜·지역 분포 불균형
- celebrity/tenant hot key
- join side의 duplicate explosion

### 완화

- hot key를 별도 경로로 분리
- key salting 후 두 단계 aggregation
- null/default를 의미별로 분리
- broadcast 가능한 side 사용
- adaptive execution 또는 skew-aware split
- upstream grain 수정

salting은 결과 key를 다시 합치는 추가 contract를 만든다. 단순히 partition 수만 늘려 hot key 하나를 나눌 수는 없다.

## sorting과 top-N

global sort는 전체 범위의 ordering과 range partition이 필요하다. consumer가 정말 전역 순서를 요구하는지 확인한다.

대안:

- partition 내부 sort
- key별 order
- local top-N 후 global merge
- approximate quantile로 range boundary 생성

동점 tie-break를 명시하지 않으면 재실행 결과 순서가 달라질 수 있다.

## 실패 모드

### hidden fan-out

양쪽 key가 중복인데 join 후 `distinct`로 숨긴다. 합계가 이미 부풀었을 수 있다. join 전 uniqueness와 multiplicity를 검사한다.

### compressed size로 broadcast 결정

disk에서는 작지만 deserialized object가 훨씬 크다. runtime memory와 concurrent task를 기준으로 판단한다.

### partition count copied from another pipeline

데이터 shape와 operator가 달라 효과가 없다. target task size와 actual metrics로 조정한다.

### null hot key

missing key가 한 partition으로 몰린다. missing 의미를 분류하거나 별도 처리한다.

### average hides straggler

평균은 양호하지만 p99 task가 전체 stage를 지연시킨다. duration과 bytes histogram, top key를 본다.

## 검증 질문

1. source, execution, dataset partition과 grouping key를 구분했는가?
2. 어떤 operator가 shuffle를 만들며 몇 byte를 이동하는가?
3. join cardinality와 output row 수를 예상했는가?
4. top key가 전체 record의 몇 %를 차지하는가?
5. broadcast side의 실제 in-memory size와 concurrency를 확인했는가?
6. 결과 ordering과 tie-break가 deterministic한가?

## 연결 연습

- [`examples/partition_cost.py`](../../examples/partition_cost.py)로 key 분포와 partition imbalance를 관찰한다.
- replay-safe batch exercise에 skewed fixture를 추가하고 output correctness와 partition histogram을 함께 확인한다.

## 완료 기준

- data movement를 기준으로 batch plan의 비용을 설명한다.
- join 전략과 aggregation을 cardinality·memory·ordering 조건으로 선택한다.
- skew를 평균이 아닌 key/partition 분포로 진단한다.
- 성능 변경이 결과 grain과 correctness를 깨뜨리지 않는지 검사한다.
