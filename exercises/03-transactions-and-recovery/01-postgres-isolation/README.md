# PostgreSQL 동시성 이상 현상

동시에 성공한 두 요청이 함께 보면 불변식을 깨뜨리는 상황을 실제 PostgreSQL session 두 개로 재현한다.

## 구현할 함수

- `reserve_inventory(sku, quantity)`: 재고가 충분할 때만 차감한다. 동시에 7개씩 두 번 요청해도 재고 10개에서 두 요청이 모두 성공해서는 안 된다.
- `take_off_call(doctor_id)`: 최소 한 명은 당직 상태로 남긴다. 두 의사가 동시에 해제해도 둘 다 성공해서는 안 된다.

단순한 `SELECT → 판단 → UPDATE`는 transaction 안에 있어도 안전하지 않다. 어떤 row 또는 명령이 충돌을 직렬화하는지 명시해야 한다.

문서: [`docs/03-transactions-and-recovery/01-transactions-isolation-and-locks.md`](../../../docs/03-transactions-and-recovery/01-transactions-isolation-and-locks.md)

## 시작

```bash
./scripts/new-workspace.sh exercises/03-transactions-and-recovery/01-postgres-isolation
```

직접 수정할 파일은 `workspace/functions.sql`이다. 두 session 검사는 `make prepare`가 준비한 PostgreSQL image를 사용한다.

## 목표

각 업무 불변식을 공유 row 충돌 또는 PostgreSQL isolation 실패와 연결해 동시 요청의 허용 결과를 제한한다.

## 완료 기준

- 재고 10에서 수량 7 예약 두 건을 동시에 실행해 성공 건수가 최대 1임을 확인한다.
- 당직 의사 두 명의 해제 요청을 겹쳐도 최소 한 명이 남는 결과만 허용한다.
- timeout 안에 두 session이 종료되고 deadlock·hang이 정상 결과로 오인되지 않는다.

## 자기 설명

1. 서로 다른 doctor row만 잠그는 방식으로 write skew를 막지 못하는 이유는 무엇인가?
2. retry가 필요한 serialization failure와 업무상 `false` 반환을 호출자는 어떻게 구분해야 하는가?

## 권장 구현 순서

아래 번호 범위는 `reference/functions.sql` 전체다. 실제 과거 순서가 아니라 두 업무 불변식을 안전하게 만드는 권장 construction order이며, workspace 검증 뒤 reference와 비교한다.

| 순서 | 파일·대상 | 책임 |
|---:|---|---|
| 1 | `reserve_inventory` | 조건부 UPDATE로 재고 확인·차감 직렬화 |
| 2 | `take_off_call` | 공유 guard row로 cross-row 불변식 직렬화 |

## 검증

`make prepare` 뒤 workspace의 함수를 실제 PostgreSQL 두 session으로 검사한다.

```bash
./scripts/check-workspace.sh exercises/03-transactions-and-recovery/01-postgres-isolation
```

초기 skeleton은 `GUIDE_SEMANTIC:isolation-lost-update`에서 실패하고, 두 불변식을 모두 동시성 안전하게 만들면 같은 명령이 통과해야 한다.
