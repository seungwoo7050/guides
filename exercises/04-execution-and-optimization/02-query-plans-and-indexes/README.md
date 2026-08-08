# 실행 계획과 인덱스

대표 workload에서 필터, 정렬, 반환 열을 함께 보고 인덱스를 설계한다. 인덱스가 존재한다는 사실이 아니라 실제 계획이 목표 접근 경로를 사용하는지를 확인한다.

## workload

1. 한 tenant의 최신 event 20개를 `(created_at DESC, id DESC)` 순서로 조회한다.
2. 실행 가능한 `PENDING` job을 `scheduled_at` 순서로 꺼낸다. 완료된 job은 인덱스에 유지할 필요가 없다.

`reference/indexes.sql`은 다음을 보여 준다.

- equality prefix 뒤의 range/order key
- 동률을 깨는 안정적인 ID 정렬
- 필요한 반환 열의 `INCLUDE`
- 상태가 좁게 고정된 workload의 partial index

검증은 index 정의만 보지 않는다. 두 workload의 실제 정렬 결과, 선택된 index scan, 불필요한 `Sort` 부재를 함께 확인한다.

문서: [`docs/04-execution-and-optimization/02-statistics-cost-model-and-explain.md`](../../../docs/04-execution-and-optimization/02-statistics-cost-model-and-explain.md)

## 목표

대표 질의의 equality, range, order, projection, predicate를 인덱스 정의와 실제 PostgreSQL plan에 연결한다.

## 완료 기준

- event 질의가 복합 인덱스를 사용하고 최신 20개 ID를 안정적인 순서로 반환한다.
- pending job 질의가 partial index scan을 사용하며 별도 `Sort` 없이 기대한 첫 50개 ID를 반환한다.
- index 정의의 key 순서, `INCLUDE` 열과 partial predicate가 catalog 조회에서 정확히 확인된다.

## 자기 설명

1. equality key 뒤에 order/range key를 두는 순서가 이 workload에 맞는 이유는 무엇인가?
2. partial index predicate와 질의 predicate가 논리적으로 맞지 않으면 planner가 사용할 수 없는 이유는 무엇인가?

## 검증

`./prepare.sh` 뒤 `make postgres-check`를 실행해 catalog, `EXPLAIN`, 실제 결과를 모두 확인한다.
