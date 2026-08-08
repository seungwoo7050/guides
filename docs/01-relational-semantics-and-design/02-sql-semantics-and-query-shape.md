# SQL 의미와 질의 모양

## 학습 목표

이 문서를 마치면 다음을 할 수 있어야 한다.

- SQL의 논리 처리 순서로 column alias·filter·grouping의 유효 범위를 설명한다.
- `NULL`과 three-valued logic 때문에 생기는 오답을 식별한다.
- 외부 조인에서 `ON`과 `WHERE`의 조건 위치가 결과를 바꾸는 이유를 설명한다.
- 집계 전후의 “한 행이 무엇을 뜻하는가”를 고정한다.
- 안정적인 pagination에 필요한 전체 정렬 key를 설계한다.
- 실행 계획을 보기 전에 workload의 질의 모양을 기록한다.

## 선행지식

[`관계 모델과 관계 대수`](01-relational-model-and-algebra.md)를 먼저 읽는다.

## SQL은 선언적이지만 의미가 자동으로 명확해지지는 않는다

SQL은 원하는 결과를 선언하고 DBMS가 실행 방법을 선택하게 한다. 그러나 문장이 실행된다는 사실이 질의 의미가 맞다는 뜻은 아니다. SQL은 다음 특성 때문에 교과서의 집합 연산보다 더 많은 경계 조건을 가진다.

- 중복을 기본으로 보존한다.
- `NULL` 때문에 비교 결과가 `TRUE`, `FALSE`, `UNKNOWN`이 된다.
- 외부 조인은 unmatched row를 인위적으로 보존한다.
- `ORDER BY` 없이는 결과 순서가 없다.
- 집계는 행의 의미 단위를 바꾼다.
- `LIMIT`은 전체 결과 의미를 일부만 관찰하게 한다.

성능 문제처럼 보이는 많은 오류가 실제로는 질의 의미가 고정되지 않은 문제다.

## 논리 처리 순서

SQL 문장은 `SELECT`부터 보이지만 다음 순서로 중간 결과를 생각하는 편이 정확하다.

```text
FROM / JOIN / ON
WHERE
GROUP BY
HAVING
SELECT
DISTINCT
ORDER BY
LIMIT / OFFSET
```

이것은 물리 실행 순서가 아니다. 옵티마이저는 의미를 보존하는 범위에서 filter를 밀어 내리고 join 순서를 바꾼다. 논리 순서는 각 절이 어떤 입력을 보는지 이해하기 위한 모델이다.

예를 들어 `SELECT`에서 만든 alias를 같은 level의 `WHERE`에서 바로 사용할 수 없는 이유는 `WHERE`가 먼저 논리 처리되기 때문이다. 반면 `ORDER BY`는 `SELECT` 이후이므로 alias를 사용할 수 있는 DBMS가 많다.

## `NULL`과 three-valued logic

`NULL`은 빈 문자열이나 0이 아니다. 값이 알려지지 않았거나 적용되지 않는 상태를 나타내며, 일반 비교는 `UNKNOWN`을 만들 수 있다.

```sql
WHERE deleted_at = NULL       -- 올바른 null 검사 아님
WHERE deleted_at IS NULL      -- 의도가 명확함
```

`WHERE`는 `TRUE`인 행만 남긴다. `FALSE`와 `UNKNOWN`은 모두 제거된다.

특히 `NOT IN`은 하위 결과에 `NULL`이 있으면 위험하다.

```sql
SELECT id
FROM users
WHERE id NOT IN (SELECT user_id FROM blocked_users);
```

하위 결과가 `(2, NULL)`이면 `id=1`에 대해 “1은 2가 아니고 NULL도 아니다”를 확정할 수 없다. 전체 조건이 `UNKNOWN`이 되어 예상보다 많은 행이 사라질 수 있다. 존재 여부를 표현하려면 다음 형태가 더 직접적이다.

```sql
SELECT u.id
FROM users AS u
WHERE NOT EXISTS (
    SELECT 1
    FROM blocked_users AS b
    WHERE b.user_id = u.id
);
```

중요한 원칙은 문법 선호가 아니다.

> 업무 질문이 “같은 행이 존재하는가”라면 `EXISTS` 계약으로 표현하고, 값 목록 비교가 정말 필요한 경우에만 `IN`을 사용한다.

## 외부 조인의 `ON`과 `WHERE`

다음 질의는 사용자를 보존하려는 것처럼 보이지만 양수 주문이 없는 사용자를 제거한다.

```sql
SELECT u.id, o.id
FROM users AS u
LEFT JOIN orders AS o ON o.user_id = u.id
WHERE o.total_cents > 0;
```

unmatched user에는 `o.total_cents=NULL`이 만들어진다. `WHERE NULL > 0`은 `UNKNOWN`이므로 해당 행이 제거된다. 결과적으로 양수 주문이 있는 사용자만 남아 내부 조인과 비슷해진다.

주문이 없어도 사용자를 보존하고, 결합할 주문만 양수로 제한하려면 조건을 `ON`에 둔다.

```sql
SELECT u.id, o.id
FROM users AS u
LEFT JOIN orders AS o
  ON o.user_id = u.id
 AND o.total_cents > 0;
```

조건 위치를 정할 때 다음을 묻는다.

```text
이 조건은 결합 가능한 오른쪽 행을 제한하는가?
아니면 조인 결과 전체에서 행을 제거하는가?
```

전자는 `ON`, 후자는 `WHERE`에 가깝다.

## 집계는 행의 단위를 바꾼다

집계 전 한 행이 주문 하나를 뜻했다면, `GROUP BY user_id` 뒤 한 행은 사용자별 주문 집합을 뜻한다.

```sql
SELECT user_id, count(*), sum(total_cents)
FROM orders
GROUP BY user_id;
```

이때 select 목록의 비집계 column은 group key에 의해 결정되어야 한다. 그렇지 않으면 “그룹 안의 어느 행 값을 반환하는가”가 모호하다.

외부 조인과 집계를 함께 사용할 때 `count(*)`와 `count(right.id)`를 구분한다.

```sql
SELECT u.id,
       count(*) AS joined_rows,
       count(o.id) AS actual_orders
FROM users AS u
LEFT JOIN orders AS o ON o.user_id = u.id
GROUP BY u.id;
```

주문이 없는 사용자도 외부 조인 결과에는 NULL-extended row 하나가 생기므로 `count(*)`는 1일 수 있다. 실제 주문 수는 `count(o.id)`가 표현한다.

## 중복 제거는 오류 은폐 수단이 아니다

join 뒤 행이 예상보다 많을 때 곧바로 `DISTINCT`를 붙이면 안 된다. 먼저 multiplicity를 확인한다.

- 한쪽 key가 정말 유일한가?
- 다대다 관계를 의도했는가?
- 연결 table의 filter가 빠졌는가?
- temporal row 중 현재 버전만 골라야 하는가?

`DISTINCT`가 업무적으로 필요한 경우도 있다. 그러나 그 이유는 “중복이 보기 싫어서”가 아니라 “결과 단위가 사용자 한 명이기 때문”처럼 명시되어야 한다.

## 안정적인 정렬과 pagination

다음 정렬은 `created_at`이 같은 행 사이의 순서를 정하지 않는다.

```sql
ORDER BY created_at DESC
LIMIT 20;
```

실행 계획이나 concurrent insert에 따라 동률 행의 순서가 달라질 수 있다. 전체 순서를 만드는 unique tie-breaker를 포함한다.

```sql
ORDER BY created_at DESC, id DESC
```

offset pagination은 앞쪽 행이 추가·삭제될 때 중복과 누락을 만들 수 있다.

```sql
OFFSET 100 LIMIT 20
```

연속 피드처럼 변경이 잦은 데이터에는 마지막으로 본 전체 정렬 key를 cursor로 사용하는 keyset pagination이 더 안정적이다.

```sql
WHERE (created_at, id) < (:last_created_at, :last_id)
ORDER BY created_at DESC, id DESC
LIMIT 20
```

정렬 방향과 cursor 비교 방향이 일치해야 한다.

## view는 이름 붙인 질의다

일반 view는 data copy가 아니라 질의 정의다. 읽을 때 원본 관계와 결합되어 plan이 만들어진다. view는 반복되는 의미 계약을 이름 붙이고 권한을 줄이는 데 유용하지만, 내부 join과 aggregation 비용을 숨길 수도 있다.

materialized view는 결과를 저장하므로 다른 계약이 추가된다.

```text
언제 refresh하는가
refresh 중 읽기는 가능한가
얼마나 오래된 결과를 허용하는가
실패 시 어떤 버전을 제공하는가
```

## 질의 모양을 기록한다

대표 질의마다 다음을 작성한다.

```text
업무 결과 단위:
시작 relation:
join key와 multiplicity:
filter:
group key:
반환 column:
정렬과 tie-breaker:
요청당 예상 결과 수:
변경 빈도:
```

예:

```text
업무 결과 단위: 사용자 한 명
시작 relation: users
join: orders.user_id -> users.id, 사용자당 주문 여러 개
filter: 주문 created_at 범위, status='PAID'
group: users.id
return: users.id, sum(total_cents)
order: sum 내림차순, users.id 오름차순
limit: 100
```

이 기록은 뒤의 index 설계와 실행 계획 판단의 입력이 된다.

## 연결 연습

- [`SQL 의미와 질의 모양 exercise`](../../exercises/01-relational-semantics-and-design/01-sql-semantics/README.md): `NOT IN`, 외부 조인 집계와 불안정 정렬을 실제 PostgreSQL 결과로 교정한다.
- 다음 문서인 [`ER·정규화·제약`](03-er-normalization-and-constraints.md)은 질의 의미를 스키마가 어떻게 보존하는지 다룬다.

## 완료 기준

다음 사례를 스스로 설명하고 수정할 수 있어야 한다.

1. nullable 하위 질의를 사용한 `NOT IN`
2. 오른쪽 table 조건을 `WHERE`에 둔 `LEFT JOIN`
3. 주문 없는 사용자를 1건으로 세는 `count(*)`
4. 동률 해소 key가 없는 pagination
5. 잘못된 join multiplicity를 `DISTINCT`로 숨긴 질의
6. 각 질의에서 “한 결과 행이 무엇을 뜻하는가”를 한 문장으로 표현
