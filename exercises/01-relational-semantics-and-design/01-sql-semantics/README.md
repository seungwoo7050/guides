# SQL 의미와 질의 모양

`NULL`, 외부 조인, 중복, 집계 단위와 안정적인 정렬을 실제 PostgreSQL 결과로 검증한다.

## 구현할 view

- `q01_users_without_orders`: 주문이 한 건도 없는 사용자
- `q02_unblocked_users`: 차단 목록에 없는 사용자. 차단 목록의 `NULL` 때문에 전체가 사라지면 안 된다.
- `q03_user_totals`: 모든 사용자를 보존하고 주문 수와 합계를 계산한다.
- `q04_ranked_spenders`: 합계 내림차순, 사용자 ID 오름차순으로 상위 3명을 정하고 `position`으로 순서를 계약에 포함한다.

`skeleton/answers.sql`을 작업 공간으로 복사해 네 view를 완성한다.

```bash
./scripts/new-workspace.sh exercises/01-relational-semantics-and-design/01-sql-semantics
```

문서: [`docs/01-relational-semantics-and-design/02-sql-semantics-and-query-shape.md`](../../../docs/01-relational-semantics-and-design/02-sql-semantics-and-query-shape.md)

## 목표

`NULL`, outer join, 집계의 행 단위와 tie-breaker가 결과 집합에 미치는 영향을 네 view로 설명한다.

## 완료 기준

- 주문이 없는 사용자와 차단되지 않은 사용자가 seed의 기대 ID 집합과 정확히 일치한다.
- 주문이 없는 사용자도 합계 view에 남고 count와 amount가 각각 `0`으로 관찰된다.
- 동일 합계가 생겨도 `position` 1~3의 순서가 사용자 ID tie-breaker로 고정된다.

## 자기 설명

1. `NOT IN` 후보 집합에 `NULL`이 있을 때 `NOT EXISTS`와 결과가 달라지는 이유는 무엇인가?
2. `COUNT(*)`와 nullable 오른쪽 열의 `COUNT(column)` 중 outer join 집계에 맞는 것은 무엇인가?

## 검증

`make prepare` 뒤 학습자 workspace를 공용 PostgreSQL fixture에서 검사한다.

```bash
./scripts/check-workspace.sh exercises/01-relational-semantics-and-design/01-sql-semantics
```

처음 복사한 skeleton은 `GUIDE_SEMANTIC:sql-three-valued-logic`에서 실패하고, 네 view를 완성한 뒤 같은 명령이 통과해야 한다. `make postgres-check`는 배포된 reference/skeleton 계약을 검사하는 가이드 무결성 명령이다.
