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

문서: [`docs/04-execution-and-optimization/02-statistics-cost-model-and-explain.md`](../../../docs/04-execution-and-optimization/02-statistics-cost-model-and-explain.md)
