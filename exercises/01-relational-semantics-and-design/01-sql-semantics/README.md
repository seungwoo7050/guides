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
