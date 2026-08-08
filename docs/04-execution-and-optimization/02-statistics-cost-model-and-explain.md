# 통계, 비용 모델과 EXPLAIN

## 학습 목표

이 문서를 마치면 다음을 설명할 수 있어야 한다.

- 옵티마이저가 실제 실행 없이 row 수와 비용을 추정해야 하는 이유
- cardinality와 selectivity 추정 오류가 plan 전체로 증폭되는 방식
- histogram, most-common values와 distinct count가 제공하는 정보
- column correlation과 다중 column 의존성이 단일 column 통계를 깨뜨리는 이유
- 비용 단위가 실제 millisecond와 동일하지 않은 이유
- `EXPLAIN`과 `EXPLAIN ANALYZE`의 차이와 부작용
- scan, join, sort, aggregate plan에서 읽어야 할 핵심 증거
- 인덱스를 추가하기 전에 workload와 검증 기준을 고정하는 방법

## 선행지식

[`질의 실행, join과 sort`](01-query-execution-joins-and-sorting.md)의 물리 operator를 알고 있어야 한다. 인덱스 구조는 [`인덱스 구조`](../02-storage-and-indexes/02-index-structures.md)를 참고한다.

## 옵티마이저는 가능한 plan을 비교한다

같은 SQL을 실행하는 방법은 많다.

```text
sequential scan 또는 index scan
nested-loop 또는 hash join 또는 merge join
join 순서 A-B-C 또는 B-C-A
hash aggregate 또는 sort aggregate
전체 sort 또는 top-N
병렬 또는 단일 worker
```

모든 후보를 실제로 실행해 가장 빠른 것을 고를 수는 없다. 옵티마이저는 통계로 결과 row 수를 추정하고, 각 operator의 CPU·I/O·memory 비용을 계산해 상대적으로 낮은 plan을 선택한다.

따라서 느린 plan을 볼 때 다음 두 실패를 구분한다.

```text
추정이 틀림
→ 실제 row 수를 잘못 예상해 잘못된 plan 선택

비용 모델이 workload와 맞지 않음
→ row 수는 맞지만 I/O·cache·병렬 비용의 상대값이 현실과 다름
```

## Cardinality가 plan 선택을 지배한다

다음 filter가 전체 1,000,000 row 중 몇 row를 남기는지에 따라 유리한 scan이 달라진다.

```sql
WHERE tenant_id = 42
  AND status = 'OPEN'
  AND created_at >= current_date - interval '7 days'
```

결과가 10 row라면 composite index가 유리할 수 있다. 700,000 row라면 sequential scan이 더 나을 수 있다.

Join에서도 추정 row 수가 중요하다.

```text
A filter 추정: 10 row, 실제: 100,000 row
→ inner index lookup을 10번 예상
→ 실제 100,000번 실행
```

하위 node의 오차는 상위 join, sort와 aggregate의 memory 선택까지 전파된다.

## 기본 통계

### Distinct count

column의 서로 다른 값 수를 추정한다. 균등 분포를 가정하면 equality predicate의 선택도를 대략 `1 / distinct_count`로 볼 수 있다.

하지만 tenant별 row 수가 크게 다르면 균등 가정은 틀린다.

### Most-common values

자주 등장하는 값과 빈도를 별도로 저장한다. `status='OPEN'`처럼 특정 값이 매우 흔한 경우 평균 선택도보다 현실적인 추정을 돕는다.

### Histogram

값 범위를 bucket으로 나눠 range predicate의 선택도를 추정한다. 최근 날짜에 데이터가 몰리는 append-only table에서는 stale histogram이 최근 범위를 과소 추정할 수 있다.

### Null fraction과 평균 폭

`NULL` 비율은 `IS NULL`, join과 aggregate 추정에 필요하다. 평균 row·column 폭은 I/O, hash table과 sort memory 비용에 영향을 준다.

## Correlation과 다중 column 통계

두 조건을 독립이라고 가정하면 선택도를 곱할 수 있다.

```text
P(tenant=42 AND status=OPEN)
≈ P(tenant=42) × P(status=OPEN)
```

그러나 tenant마다 status 분포가 다르면 틀린다. 다음 관계도 흔하다.

```text
country와 city
zip_code와 state
created_at과 sequential id
tenant_id와 project_id
```

다중 column 통계나 함수 종속성 정보가 없으면 옵티마이저는 실제 조합 빈도를 놓친다. Composite index를 추가하기 전에 추정 오류의 원인이 index 부재인지 correlation인지 구분한다.

물리 order correlation도 중요하다. index key 순서와 heap 배치가 비슷하면 range scan의 heap 접근이 연속적일 수 있다. correlation이 낮으면 random page 접근이 늘어난다.

## 통계는 자동으로 영원히 정확하지 않다

통계가 오래되면 최근 workload를 반영하지 못한다.

- 대량 insert·delete
- 특정 tenant의 급성장
- 새로운 status 값
- 계절성 분포 변화
- migration으로 값 채우기

`ANALYZE` 시점, sampling 크기와 column별 statistics target을 검토한다. 모든 column의 target을 무조건 크게 올리면 분석 비용과 catalog 크기가 증가한다. plan 오류와 연결된 column에 증거를 두고 조정한다.

## 비용 모델은 상대 단위다

PostgreSQL plan의 `cost=a..b`는 일반적으로 다음을 나타낸다.

```text
startup cost .. total cost
```

이는 측정된 millisecond가 아니다. sequential page, random page, tuple CPU, operator CPU 등의 설정값으로 계산한 상대 비용이다.

Startup cost가 중요한 query:

- `LIMIT`이 있고 첫 row를 빨리 원함
- interactive pagination
- EXISTS처럼 첫 match에서 종료 가능

Total cost가 중요한 query:

- 전체 export
- full aggregation
- batch processing

비용 숫자는 다른 server나 다른 설정과 절대 비교하지 않는다. 같은 환경에서 후보 plan의 선택 근거로 읽는다.

## `EXPLAIN`과 `EXPLAIN ANALYZE`

### `EXPLAIN`

실행하지 않고 추정 plan을 보여 준다. 변경 query를 안전하게 관찰할 수 있지만 실제 row·시간과 buffer는 없다.

### `EXPLAIN ANALYZE`

query를 실제로 실행하고 각 node의 실제 row와 시간을 기록한다. `INSERT`, `UPDATE`, `DELETE`라면 실제 변경이 일어난다. 안전한 transaction에서 rollback하거나 복제된 검증 환경을 사용해야 한다.

권장 형태:

```sql
EXPLAIN (ANALYZE, BUFFERS, VERBOSE, FORMAT JSON)
SELECT ...;
```

- `ANALYZE`: 실제 실행
- `BUFFERS`: shared/local/temp block hit와 read/write
- `VERBOSE`: 출력 column과 내부 세부 정보
- `FORMAT JSON`: 자동 비교와 구조화된 분석

Timing overhead가 큰 환경에서는 `TIMING OFF`를 함께 고려할 수 있다.

## Plan을 아래에서 위로 읽는다

상위 node는 하위 결과를 소비한다. 먼저 가장 안쪽 scan에서 시작한다.

각 node에서 다음을 기록한다.

```text
추정 rows
실제 rows × loops
filter로 제거한 rows
startup/total time
buffer hit/read/temp
sort method와 memory/disk
join condition과 join filter
index condition과 residual filter
```

실제 처리 row 수는 `actual rows × loops`를 봐야 한다. Inner nested-loop node가 한 번에는 3 row를 반환해도 100,000번 실행됐다면 총 작업량은 크다.

## 대표 scan 읽기

### Sequential Scan

항상 나쁜 것이 아니다.

- table이 작다.
- 많은 row를 읽는다.
- 필요한 page가 cache에 있다.
- index random access보다 연속 scan이 싸다.

확인:

- filter가 몇 row를 제거했는가
- table 전체 중 몇 %를 반환하는가
- shared read와 hit 비율
- row width

### Index Scan

확인:

- `Index Cond`가 실제 탐색 범위를 줄이는가
- `Filter`로 많은 row를 다시 버리는가
- heap fetch와 random page read가 많은가
- ordering을 재사용하는가

### Bitmap Scan

여러 index condition이나 중간 선택도에서 page 단위 접근을 묶는다. bitmap이 lossy해지면 heap에서 조건을 다시 확인한다.

### Index Only Scan

필요 column이 index에 있어도 visibility 확인 때문에 heap fetch가 생길 수 있다. `Heap Fetches`를 확인하고 vacuum/visibility map 상태와 연결한다.

## Join plan 읽기

### Nested Loop

- outer 실제 row 수
- inner loops
- inner lookup당 비용
- memoization 여부
- 예상보다 큰 outer input

### Hash Join

- build side
- hash buckets·batches
- memory usage
- spill 여부
- skew
- hash condition과 추가 join filter

### Merge Join

- 양쪽 sort 또는 index order
- sort spill
- merge condition
- 중복 key run 크기

Join algorithm만 바꾸는 hint보다 왜 row 추정과 ordering이 그 선택을 만들었는지 먼저 본다.

## Sort와 aggregate 읽기

Sort node에서는 다음을 확인한다.

```text
Sort Key
Sort Method
Memory
Disk 사용 여부
입력 row 수와 width
```

Aggregate에서는:

```text
HashAggregate 또는 GroupAggregate
실제 group 수
planned partitions와 batches
memory와 disk
입력 ordering
```

work memory를 무조건 크게 올리면 동시 query와 operator 수만큼 memory가 곱해질 수 있다. 한 query의 spill을 없애다가 DB 전체 OOM을 만들 수 있다.

## Plan diff의 단위를 고정한다

인덱스 전후를 비교하려면 다음을 고정한다.

- 같은 schema와 data volume
- 같은 통계 상태
- 같은 query parameter
- 같은 cache 조건 또는 cache 상태 기록
- 같은 DB 설정
- 충분한 반복 횟수
- cold/warm run 구분

다음 표를 남긴다.

| 항목 | 변경 전 | 변경 후 |
|---|---:|---:|
| 실제 반환 row |  |  |
| 총 처리 row |  |  |
| shared read |  |  |
| shared hit |  |  |
| temp read/write |  |  |
| execution time |  |  |
| write amplification |  |  |
| index size |  |  |

읽기 하나가 빨라졌다고 변경이 끝난 것은 아니다. insert/update 비용, vacuum, backup 크기와 migration 시간을 함께 본다.

## Parameter와 plan cache

Prepared statement는 여러 parameter 값에 같은 generic plan을 사용할 수 있다. 분포가 치우친 column에서는 다음 두 값에 유리한 plan이 다를 수 있다.

```text
tenant_id = 작은 tenant
 tenant_id = 전체 row의 절반을 가진 tenant
```

테스트에서 literal 한 값만 사용하면 production의 parameter-sensitive 문제를 놓칠 수 있다. 대표 분포를 여러 구간으로 나누고 custom/generic plan 동작을 관찰한다.

## 성능 주장의 한계

다음 표현은 근거가 부족하다.

```text
인덱스를 추가하니 빨라졌다.
Hash join이 nested loop보다 빠르다.
EXPLAIN cost가 줄었다.
```

더 나은 기록:

```text
PostgreSQL 16, 100만 row, warm cache 환경에서
tenant별 최근 50개 event query의 p95가 120ms에서 18ms로 줄었다.
실제 읽은 block은 8,000에서 140으로 줄었고,
insert p95는 3ms 증가했으며 index 크기는 280MB다.
```

환경과 workload가 바뀌면 결론도 다시 검증해야 한다.

## 연결 연습

[`Query plans and indexes`](../../exercises/04-execution-and-optimization/02-query-plans-and-indexes/README.md)에서 실제 PostgreSQL을 사용해 다음을 검증한다.

- tenant·상태·시간 범위 query
- 부분 index와 composite ordering
- `INCLUDE` column
- `EXPLAIN (ANALYZE, BUFFERS)`
- reference index 적용 전후 plan
- skeleton이 요구된 index·ordering 계약을 충족하지 못하는지

데이터 규모는 plan 차이를 관찰하기 위한 최소 실험 규모다. 결과 시간을 다른 장비에 일반화하지 않는다.

## 완료 기준

다음 분석을 스스로 작성할 수 있어야 한다.

- plan에서 가장 큰 추정 오차가 시작되는 node
- 해당 오차가 상위 join·sort 선택에 미친 영향
- sequential scan이 합리적이거나 불합리한 근거
- index scan이 많은 heap fetch를 일으키는 이유
- `actual rows × loops`가 중요한 이유
- 인덱스 전후 비교에서 고정해야 할 조건
- 읽기 개선과 함께 측정해야 할 쓰기·공간 비용

다음 문서에서는 이 증거를 schema, index와 migration 변경으로 연결하는 [`튜닝 루프`](03-schema-index-and-tuning-loop.md)를 다룬다.
