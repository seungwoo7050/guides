# Commerce Checkout

PostgreSQL, Kysely와 Fastify로 checkout의 금액·재고·주문 불변식을 구현하는 backend 프로젝트입니다.

초기 구현은 외부 payment provider 연동보다 먼저 **주문 시점의 가격 snapshot과 재고 예약을 transaction으로 확정하는 경계**를 완성합니다. 이후 durable payment command와 webhook orchestration을 같은 주문 상태 모델 위에 확장합니다.

## 초기 범위

- 환경 값을 startup에서 runtime validation
- checkout 요청 contract
- minor unit 기반 금액 계산
- 주문 시점 상품명·가격 snapshot
- 명시적인 order state model
- PostgreSQL schema와 Kysely database type
- product row lock과 inventory reservation
- order, order item, payment와 inventory movement의 transaction

## 데이터 일관성

Checkout은 다음 순서를 하나의 database transaction에서 수행합니다.

```text
requested product rows lock
→ product availability와 stock 검사
→ immutable order snapshot 계산
→ order와 order_items 저장
→ inventory 감소와 movement 기록
→ payment 초기 상태 저장
→ commit
```

가격과 상품명은 `order_items`에 복사하므로 catalog가 변경되어도 이미 생성된 주문의 금액은 변하지 않습니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | --- | --- |
| 1 | Runtime configuration contract | `src/config.ts` |
| 2 | External transport contracts | `src/contracts.ts` |
| 3 | Money and order snapshot invariants | `src/domain.ts` |
| 3-1 | Order lifecycle state machine | `src/domain.ts` |
| 4 | Relational consistency model | `migrations/001_initial.sql` |
| 5 | Database types and numeric boundary | `src/db.ts` |
| 6 | Checkout and payment repository | `src/repository.ts` |
| 6-1 | Stock lock and order snapshot transaction | `src/repository.ts` |

## 다음 구현 경계

Database commit과 외부 network 호출을 직접 묶지 않고 durable payment command로 분리합니다. 이후 provider idempotency, retry lease, signed webhook과 cancel/refund state transition을 추가합니다.
