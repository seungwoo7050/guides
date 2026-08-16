# Stage 02: Checkout과 inventory

## 목표

실제 PostgreSQL transaction에서 주문 snapshot과 stock 차감이 함께 성공하거나 함께 rollback되게 합니다. 같은 재고를 경쟁하는 두 checkout에서 oversell이 없어야 합니다.

## Schema 계약

최소 table:

```text
products
orders
order_items
inventory_movements
order_events
```

필수 제약:

- amount·quantity·stock 음수 금지
- order status 허용 목록
- SKU unique
- order item `(order_id, product_id)` unique
- inventory movement `(order_id, product_id, kind)` unique
- FK와 delete 정책

## Transaction 계약

1. 요청 product ID를 정렬합니다.
2. product row를 같은 순서로 `FOR UPDATE`합니다.
3. 존재·active·currency·stock을 검증합니다.
4. order와 item snapshot을 생성합니다.
5. stock을 차감합니다.
6. reserve movement와 order event를 기록합니다.
7. 모두 commit합니다.

외부 payment HTTP는 이 transaction에 들어가지 않습니다.

## 검증 시나리오

- stock=1에서 서로 다른 key의 checkout 두 개를 동시에 실행하면 정확히 하나만 성공
- 실패 뒤 stock은 0이고 주문은 하나
- multi-item 두 번째 상품 부족 시 첫 상품도 차감되지 않음
- 의도적 item insert 오류에서 order·stock·movement 모두 rollback
- stable product lock order

## 완료 기준

```sh
node exercises/commerce-checkout/checks/verify-work.mjs 2
```

실제 `DATABASE_URL`의 PostgreSQL을 사용해야 합니다.
