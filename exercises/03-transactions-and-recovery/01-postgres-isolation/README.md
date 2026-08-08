# PostgreSQL 동시성 이상 현상

동시에 성공한 두 요청이 함께 보면 불변식을 깨뜨리는 상황을 실제 PostgreSQL session 두 개로 재현한다.

## 구현할 함수

- `reserve_inventory(sku, quantity)`: 재고가 충분할 때만 차감한다. 동시에 7개씩 두 번 요청해도 재고 10개에서 두 요청이 모두 성공해서는 안 된다.
- `take_off_call(doctor_id)`: 최소 한 명은 당직 상태로 남긴다. 두 의사가 동시에 해제해도 둘 다 성공해서는 안 된다.

단순한 `SELECT → 판단 → UPDATE`는 transaction 안에 있어도 안전하지 않다. 어떤 row 또는 명령이 충돌을 직렬화하는지 명시해야 한다.

문서: [`docs/03-transactions-and-recovery/01-transactions-isolation-and-locks.md`](../../../docs/03-transactions-and-recovery/01-transactions-isolation-and-locks.md)
