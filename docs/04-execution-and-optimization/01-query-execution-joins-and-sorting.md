# 질의 실행, join과 sort

## 학습 목표

이 문서를 마치면 다음을 설명할 수 있어야 한다.

- 논리 질의와 물리 실행 plan의 차이
- iterator/pipeline 실행 모델에서 `open`, `next`, `close`가 갖는 수명 계약
- sequential scan과 index scan이 같은 논리 결과를 만드는 방식
- nested-loop, hash, merge join의 전제·비용·메모리 특성
- SQL의 중복 허용 의미와 `NULL`이 join 구현에 주는 제약
- sort와 hash aggregation이 메모리를 넘을 때 필요한 외부 알고리즘
- blocking operator와 streaming operator가 첫 결과 시간에 미치는 영향
- 실행기의 정확성과 성능을 분리해 검증하는 방법

## 선행지식

관계 연산과 SQL 의미는 [`관계 모델`](../01-relational-semantics-and-design/01-relational-model-and-algebra.md), [`SQL 의미`](../01-relational-semantics-and-design/02-sql-semantics-and-query-shape.md)를 참고한다. page와 buffer pool을 알고 있으면 I/O 비용을 더 구체적으로 연결할 수 있다.

## 논리 plan과 물리 plan을 분리한다

다음 질의의 논리 요구는 비교적 단순하다.

```sql
SELECT u.id, count(o.id)
FROM users u
LEFT JOIN orders o ON o.user_id = u.id
WHERE u.active
GROUP BY u.id;
```

논리적으로 필요한 연산은 다음이다.

```text
users에서 active row 선택
→ users와 orders를 left join
→ user별 group
→ count 계산
→ id와 count 사영
```

하지만 실제 실행 방법은 여러 가지다.

```text
users sequential scan + orders hash join
users index scan + orders index nested-loop
두 입력 정렬 + merge join
hash aggregate
sort aggregate
```

논리 결과가 같아야 한다는 계약 안에서 physical operator를 선택한다. 성능 문제를 해결할 때 SQL 문자열만 보지 않고 “각 논리 연산을 어떤 물리 연산자가 수행했는가”를 본다.

## Iterator 모델

축소한 pull 기반 실행기는 다음 interface를 가질 수 있다.

```text
open()
next() -> tuple | EOF
close()
```

상위 operator가 `next()`를 호출하면 하위 operator에서 tuple을 요청한다.

```text
Projection
  └─ Filter
       └─ SequentialScan
```

장점:

- operator를 조합하기 쉽다.
- 필요한 만큼만 tuple을 당겨올 수 있다.
- filter와 projection 같은 연산은 pipeline으로 이어질 수 있다.

주의할 계약:

- `open()` 실패 뒤 어느 자원이 열려 있는가
- `next()`가 EOF를 어떻게 표현하는가
- 중간 오류와 정상 EOF를 구분하는가
- `close()`를 여러 번 호출해도 안전한가
- 상위 operator가 조기 종료할 때 하위 자원을 정리하는가

실제 엔진은 vectorized execution, push model, compiled query를 사용할 수 있지만, operator 수명과 데이터 흐름을 분리하는 원칙은 유지된다.

## Scan operator

### Sequential scan

heap page를 순서대로 읽고 각 tuple의 가시성과 predicate를 검사한다.

비용은 대략 읽는 page 수와 tuple 검사 수에 좌우된다. table 대부분을 읽거나 작은 table이라면 index를 여러 번 따라가는 것보다 효율적일 수 있다.

### Index scan

index에서 조건에 맞는 entry를 찾고 row 위치를 따라간다. 선택도가 높고 필요한 row가 적으면 유리하다. 하지만 다음 비용이 있다.

- index root에서 leaf까지 탐색
- 여러 leaf page
- heap page random access
- MVCC visibility 확인
- index에 없는 column을 읽기 위한 table 접근

Index-only scan도 visibility와 page 상태에 따라 heap 접근이 필요할 수 있다. “인덱스가 있으므로 table을 전혀 읽지 않는다”는 보장은 없다.

## Join의 논리 계약

두 입력에 중복 key가 있을 때 결과 multiplicity를 먼저 고정한다.

```text
left:  key=7 row 2개
right: key=7 row 3개
inner join 결과: 2 × 3 = 6개
```

Hash table에 key당 row 하나만 저장하면 SQL의 bag 의미를 깨뜨린다. key마다 row 목록을 보존해야 한다.

`NULL = NULL`은 SQL에서 `true`가 아니다. 일반 equi-join에서는 양쪽 key가 `NULL`인 row끼리 자동으로 match하지 않는다. 구현 exercise가 Python의 `None == None`을 그대로 사용하면 잘못된 결과를 만들 수 있다.

Outer join은 unmatched row를 보존하고 반대편 column을 `NULL`로 채운다. predicate를 join 전후 어느 위치에서 적용하는지에 따라 결과가 달라진다.

## Nested-loop join

가장 단순한 형태는 왼쪽 row마다 오른쪽 전체를 검사한다.

```text
for left_row in left:
    for right_row in right:
        if matches(left_row, right_row):
            emit
```

대략적인 비교 횟수는 `|L| × |R|`이다. 항상 나쁜 것은 아니다.

- 한쪽 입력이 매우 작다.
- outer input이 강하게 제한된다.
- inner key에 index가 있다.
- 첫 결과를 빨리 내는 것이 중요하다.

Index nested-loop에서는 각 outer row마다 inner index lookup을 한다. outer row가 많으면 random I/O가 누적될 수 있다.

검증 항목:

- 빈 입력
- 중복 key
- unmatched row
- `NULL` key
- predicate 오류
- 조기 종료 시 inner cursor 정리

## Hash join

보통 작은 입력으로 hash table을 만들고 큰 입력을 probe한다.

```text
build: key -> rows
probe: 같은 key bucket을 찾아 equality 재검사
```

평균적으로 선형에 가까운 처리를 기대할 수 있지만 다음 전제가 있다.

- equality join에 적합하다.
- build side가 memory budget 안에 들어간다.
- hash 분포가 심하게 치우치지 않는다.
- collision 뒤 실제 key equality를 확인한다.

메모리를 넘으면 partition을 disk에 spill하고 대응 partition끼리 다시 처리할 수 있다. skewed key 하나에 row가 몰리면 특정 partition이 계속 커질 수 있다.

Hash는 출력 순서를 보장하지 않는다. 논리 계약에 순서가 필요하면 별도 sort가 필요하다.

## Merge join

두 입력이 join key 순서로 정렬되어 있으면 동시에 전진하며 match한다.

```text
left key < right key  → left 전진
left key > right key  → right 전진
같음                  → 같은 key의 run끼리 곱집합 출력
```

범위 조건과 이미 정렬된 입력에 유리할 수 있다. 같은 key가 여러 개면 양쪽 run을 모아 모든 조합을 출력해야 한다.

비용에는 정렬 여부가 중요하다.

- index order를 재사용할 수 있는가
- upstream operator가 이미 정렬을 보장하는가
- 별도 sort가 필요한가
- sort 결과를 이후 `ORDER BY`에도 재사용할 수 있는가

Merge join 자체가 정렬된 출력을 내더라도 SQL 결과 순서를 보장하려면 최종 plan에서 `ORDER BY` 계약이 명시되어야 한다.

## Sort는 blocking operator다

일반적인 sort는 모든 입력을 읽어야 첫 정렬 결과를 낼 수 있다. 따라서 total runtime뿐 아니라 time-to-first-row에 영향을 준다.

메모리 안에 들어가면 in-memory sort를 사용한다. 넘으면 다음과 같은 external merge sort가 필요하다.

```text
입력을 memory 크기의 run으로 나눠 정렬
→ 각 run을 disk에 기록
→ 여러 run을 merge
```

비용은 row 수만이 아니라 tuple 폭, memory budget, 임시 파일 I/O와 merge fan-in에 좌우된다.

Top-N 질의는 전체 sort 대신 제한된 heap으로 상위 N개를 유지할 수 있다. 하지만 filter와 join이 먼저 큰 결과를 만들어야 하면 `LIMIT`만으로 전체 비용이 사라지지 않는다.

## Aggregation

### Hash aggregate

그룹 key별 accumulator를 hash table에 저장한다. group 수가 memory에 들어가면 효율적이다. group cardinality 추정이 틀리면 spill이 발생할 수 있다.

### Sort aggregate

group key로 정렬한 뒤 같은 key run을 순서대로 집계한다. 입력이 이미 정렬되어 있거나 hash memory가 불리할 때 선택될 수 있다.

집계는 row 단위를 바꾼다. 다음을 검증한다.

- `count(*)`와 `count(column)`의 `NULL` 처리 차이
- 빈 입력에서 aggregate 결과
- `sum`·`avg`의 numeric 범위
- group key의 collations
- partial aggregation과 parallel combine의 결합법칙

## Pipeline과 materialization

Filter, projection과 일부 nested-loop는 tuple을 받자마자 다음 단계로 넘길 수 있다. sort, hash build와 전체 aggregate는 일정 입력을 모아야 한다.

Materialization은 중간 결과를 memory나 disk에 저장한다.

장점:

- 반복 scan을 줄인다.
- volatile한 하위 결과를 고정한다.
- rewind가 필요한 operator를 지원한다.

비용:

- memory·disk 공간
- 첫 결과 지연
- snapshot과 임시 자원 수명

실행 계획에서 materialize node를 보면 “불필요하다”고 즉시 단정하지 말고, 어떤 반복 접근이나 rewind 요구를 해결하는지 확인한다.

## Parallel execution

큰 scan, join과 aggregate를 여러 worker로 나눌 수 있다. 병렬화에는 다음 비용이 있다.

- 작업 분할
- worker 시작
- tuple 전달
- partial 결과 merge
- skewed partition
- memory budget의 worker별 증가

작은 query에서는 병렬화 비용이 더 클 수 있다. 병렬 worker 수만 늘리면 DB 전체의 CPU·memory·I/O 경쟁이 커질 수 있다.

## 정확성 검증과 성능 검증을 분리한다

Join 구현의 첫 검증은 결과의 multiset이 맞는지다.

```text
입력 순서를 바꿔도 같은 bag 결과인가?
중복 key의 모든 조합이 있는가?
NULL이 잘못 match하지 않는가?
빈 입력과 한쪽 unmatched를 처리하는가?
```

그 다음 성능 특성을 관찰한다.

```text
비교 횟수
hash build row 수
정렬된 run 수
peak memory
spill bytes
첫 row 시간
전체 시간
```

작은 synthetic input에서 빠른 알고리즘이 실제 workload에서도 빠르다는 보장은 없다. tuple 폭, cache, disk, skew와 병렬 경쟁을 기록해야 한다.

## 연결 연습

먼저 [`Join 알고리즘 예제`](../../examples/join_algorithms.py)로 nested-loop와 hash join이 `NULL`과 중복을 포함한 같은 bag 결과를 만드는지 관찰한다. 더 작은 build side 선택과 sort-merge의 equal-key run 처리는 다음 exercise에서 구현한다.

[`Join algorithms`](../../exercises/04-execution-and-optimization/01-join-algorithms/README.md)에서 같은 equi-join 계약을 다음 세 방식으로 구현한다.

- nested-loop join
- hash join
- merge join

테스트는 중복 key, `NULL`, 빈 입력과 결과 bag을 확인한다. 각 구현이 같은 논리 결과를 만들면서 서로 다른 전제와 비용을 가진다는 점을 비교한다.

## 완료 기준

다음 설명을 코드와 작은 입력으로 재현할 수 있어야 한다.

- 논리 join 하나에 여러 physical join이 가능한 이유
- Hash join에서 key마다 row 목록을 저장해야 하는 이유
- Merge join에서 같은 key run의 곱집합을 만들어야 하는 이유
- Index nested-loop가 유리한 조건과 불리한 조건
- Sort가 첫 결과를 늦추는 이유
- Memory budget을 넘은 hash·sort가 disk spill을 필요로 하는 이유
- 정확한 결과 검증과 성능 측정을 분리해야 하는 이유

다음 문서에서는 옵티마이저가 이 후보들 중 하나를 고르기 위해 사용하는 [`통계, 비용 모델과 EXPLAIN`](02-statistics-cost-model-and-explain.md)을 다룬다.
