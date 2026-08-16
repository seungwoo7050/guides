# 커머스 업무 불변식

쇼핑몰의 어려움은 상품 목록이나 장바구니 화면이 아닙니다. 가격이 바뀌고 여러 사용자가 같은 재고를 경쟁하며 결제 event가 늦거나 중복되는 동안에도 **과거 주문의 금액, 현재 재고와 허용된 주문 상태가 서로 모순되지 않아야 한다**는 점이 핵심입니다.

이 문서는 특정 결제대행사나 배송사를 설명하지 않습니다. 작은 단일 통화 상점에서 지켜야 할 업무 정본과 실패 후 상태를 정의합니다.

## 목표

- 금액을 minor unit과 currency가 결합된 값으로 다룹니다.
- 현재 상품 가격과 주문 당시 가격 snapshot을 분리합니다.
- cart 입력을 견적이 아닌 외부 요청으로 취급하고 server에서 다시 계산합니다.
- 재고 경쟁을 DB lock·조건부 update·constraint로 보호합니다.
- 주문 상태를 명시적 state machine으로 제한합니다.
- cancel과 refund, reserve와 release를 구분합니다.
- terminal event 중복에서 재고와 activity가 한 번만 바뀌게 합니다.

## Money는 숫자 하나가 아닙니다

금액에는 값과 통화가 함께 있습니다.

```ts
type Money = {
  amountMinor: number;
  currency: "KRW" | "USD";
};
```

`amountMinor`는 가장 작은 통화 단위의 정수입니다.

```text
KRW 12,500원 → 12500
USD 12.50달러 → 1250 cents
```

JavaScript floating point로 세금·할인·합계를 반복 계산하면 반올림 위치에 따라 결과가 달라질 수 있습니다. 이 exercise는 모든 입력을 safe integer 범위의 minor unit으로 제한하고 DB에는 `bigint`로 저장합니다. DB driver가 `bigint`를 `number`로 바꿀 때도 `Number.isSafeInteger`를 검사합니다.

실제 다중 통화 시스템에서는 currency별 exponent, 환율 시점, 회계 반올림과 표시 형식을 별도 모델로 둡니다. 이 과정에서는 한 주문 안의 모든 품목이 같은 통화라는 불변식만 다룹니다.

## Client total을 신뢰하지 않습니다

다음 body의 합계는 server 입력이 아닙니다.

```json
{
  "items": [{ "productId": "p1", "quantity": 2 }],
  "totalMinor": 100
}
```

client는 상품 ID와 수량만 보냅니다. server는 transaction 안에서 현재 판매 가능 상품과 가격을 읽고 다음을 계산합니다.

```text
line_total = unit_price_snapshot × quantity
subtotal = 모든 line_total의 합
```

금액은 매 단계에서 safe integer인지 검사합니다. 음수·NaN·무한대·허용 범위를 넘는 quantity는 schema와 domain 양쪽에서 거부합니다.

## Product price와 OrderItem price는 다른 정본입니다

상품 가격은 바뀔 수 있지만 과거 주문은 바뀌면 안 됩니다.

```text
products.price_minor       = 현재 판매 가격
order_items.unit_price_minor = 주문 생성 당시 가격 snapshot
```

주문 조회에서 현재 product table과 join해 가격을 다시 계산하면 과거 영수증이 변합니다. 주문에는 최소한 다음 snapshot이 필요합니다.

```text
product_id
sku
name
unit_price_minor
currency
quantity
line_total_minor
```

상품 이름이나 SKU를 어느 수준까지 snapshot할지는 영수증·감사·개인정보 정책에 따라 달라집니다. 이 exercise는 주문을 독립적으로 읽을 수 있도록 SKU와 이름도 보존합니다.

## Cart와 Order를 분리합니다

Cart는 사용자의 편집 가능한 의도입니다. Order는 server가 검증하고 확정한 업무 기록입니다.

```text
cart item
→ checkout request
→ product·price·stock 재검증
→ order snapshot
```

Cart에 저장한 가격, 할인 가능 여부와 재고는 checkout 시점에 다시 확인합니다. 오래 열린 화면의 값이 정본이 아닙니다.

이 exercise는 cart table을 만들지 않습니다. checkout body가 cart snapshot 역할을 하며 주문 생성에 필요한 최소 입력만 받습니다. 목표가 cart UI가 아니라 transaction 경계이기 때문입니다.

## 재고 모델을 먼저 선택합니다

재고에는 여러 모델이 있습니다.

### 단순 차감 모델

```text
products.stock_on_hand
```

checkout 성공 시 바로 차감하고 결제 실패·취소·환불에서 반환합니다. 작은 exercise에 적합하지만 결제 대기 시간이 길면 판매 가능한 재고가 오래 묶입니다.

### 예약 모델

```text
on_hand
reserved
available = on_hand - reserved
```

주문 만료와 예약 해제 scheduler가 필요합니다. 실제 서비스에 더 가깝지만 수명 관리가 커집니다.

이 exercise는 **checkout에서 즉시 stock을 차감하고 terminal failure에서 한 번만 반환하는 단순 모델**을 사용합니다. 대신 `inventory_movements`를 남겨 reserve/release가 중복되지 않았음을 검증합니다.

## 사전 조회만으로 oversell을 막을 수 없습니다

잘못된 흐름:

```text
A: stock=1 읽음
B: stock=1 읽음
A: 1 차감
B: 1 차감
```

해결은 업무 불변식에 맞게 선택합니다.

- product row를 안정된 순서로 `FOR UPDATE`
- `UPDATE ... WHERE stock_on_hand >= quantity`
- 별도 reservation row와 unique constraint
- 높은 isolation과 retry

이 exercise는 주문에 포함된 product ID를 정렬한 뒤 row lock을 얻습니다. 여러 품목을 반대 순서로 잠그는 deadlock 가능성을 줄입니다. lock 뒤에도 stock을 다시 확인하고 차감합니다.

```text
stock_on_hand >= 0
```

은 DB check constraint로 최종 방어합니다.

## Inventory movement는 감사 기록이지 현재 수량의 대체물이 아닙니다

```text
reserve  -2
release  +2
```

movement를 남기면 주문별 변화와 중복 release를 확인할 수 있습니다. 그러나 현재 재고 조회마다 모든 movement를 합산하면 성능·정합성 운영이 달라집니다. 이 exercise는:

- `products.stock_on_hand`: 현재 정본
- `inventory_movements`: 변화 증거

로 둡니다. 둘은 한 transaction에서 함께 바뀝니다.

`unique(order_id, product_id, kind)`로 같은 주문의 `release`가 두 번 기록되는 것을 막습니다.

## 주문은 state machine입니다

Boolean을 여러 개 두면 불가능한 조합이 생깁니다.

```text
paid=true
canceled=true
refunded=false
```

하나의 상태와 허용 transition을 정의합니다.

```text
pending_payment
  ├─ payment.succeeded ──> paid
  ├─ payment.failed ─────> payment_failed
  └─ cancel.requested ───> cancel_pending

cancel_pending
  ├─ payment.canceled ───> canceled
  └─ payment.succeeded ──> paid

paid
  └─ refund.requested ───> refund_pending

refund_pending
  └─ payment.refunded ───> refunded
```

`cancel_pending` 중 결제가 먼저 성공하면 `paid`가 됩니다. 취소 요청이 존재했다는 이유만으로 이미 성공한 결제를 `canceled`라고 표시하지 않습니다. 필요하면 이후 refund command를 시작합니다.

Terminal 상태:

```text
payment_failed
canceled
refunded
```

늦은 `payment.succeeded` event가 terminal 상태를 `paid`로 되돌리지 않습니다. event는 기록하되 transition은 거부합니다.

## Cancel과 Refund는 다릅니다

```text
cancel
= 결제 확정 전에 진행 중인 업무를 중단

refund
= 이미 발생한 결제 효과를 반대 방향으로 보상
```

따라서 endpoint와 provider command도 분리합니다.

```text
POST /orders/:id/cancel
POST /orders/:id/refund
```

- `pending_payment`만 cancel 요청 가능
- `paid`만 refund 요청 가능
- 같은 command 재요청은 idempotent
- provider 확정 event 전에는 최종 상태라고 표시하지 않음

실제 배송 뒤 refund가 재고 반환을 뜻하는지는 반품 검수 정책에 따라 달라집니다. 이 exercise는 closed-loop 검증을 위해 `payment.refunded`에서 전량을 재고로 반환하는 단순 정책을 명시합니다. 실제 제품에서는 `refund`와 `restock`을 분리할 수 있습니다.

## 재고 반환은 terminal transition과 같은 transaction입니다

잘못된 순서:

```text
order = canceled commit
→ stock release 실패
```

주문은 취소됐지만 재고가 사라집니다.

다음은 한 transaction이어야 합니다.

```text
order transition
payment state update
inventory release
inventory movement insert
order event insert
provider event outcome update
```

중복 webhook은 provider event unique constraint와 `inventory_released_at` 조건으로 두 번 방어합니다.

## 총액 불변식

주문 생성 뒤 다음이 항상 참이어야 합니다.

```text
order_item.line_total_minor
= order_item.unit_price_minor × quantity

order.subtotal_minor
= sum(order_item.line_total_minor)

order.total_minor
= subtotal_minor
```

이 exercise는 할인·배송비·세금이 없으므로 `total=subtotal`입니다. 실제 시스템에서 각 구성 요소를 숨기지 말고 다음처럼 분리합니다.

```text
subtotal
discount_total
shipping_total
tax_total
grand_total
```

`total` 하나만 저장하고 계산 근거를 잃지 않습니다.

## Database constraint와 application policy를 나눕니다

DB가 직접 보호하기 좋은 규칙:

- quantity > 0
- amount >= 0
- stock_on_hand >= 0
- 허용 status 집합
- order와 payment의 1:1 관계
- provider event ID unique
- command idempotency key unique
- movement 중복 금지

Application service가 transaction 안에서 판단할 규칙:

- 한 주문의 통화가 같은가
- 현재 상태에서 cancel/refund가 가능한가
- 같은 key가 같은 request인가
- provider event가 현재 상태에서 허용되는가
- 어느 오류를 409와 422로 외부에 보여 줄 것인가

DB check에 모든 state machine을 넣을 필요는 없지만, 어떤 writer도 우회하면 안 되는 기본 범위는 제약으로 남깁니다.

## 상태를 숨기는 자동 보상에 주의합니다

외부 결제 성공 뒤 내부 오류가 났다고 즉시 자동 refund를 호출하면 새로운 외부 실패 경계가 생깁니다. 보상 작업도 identity, retry, 상태와 관찰이 필요합니다.

```text
original command
→ partial success
→ compensation command
→ compensation retry
```

이 exercise는 보상을 synchronous catch block에서 임의로 실행하지 않습니다. cancel/refund도 durable command로 남깁니다.

## 검증

필수 검사는 다음입니다.

- 상품 가격 변경 뒤 기존 order item 가격 불변
- client가 보낸 total을 무시하고 server 계산
- 다른 통화 품목 혼합 거부
- 같은 상품 중복 line 정규화 또는 거부 정책
- stock=1에서 두 checkout 경쟁 시 하나만 성공
- 여러 상품 lock 순서가 안정적임
- checkout transaction 중간 실패 시 주문·차감 모두 rollback
- payment failure/cancel/refund에서 stock 정확히 한 번 반환
- duplicate terminal webhook에서 stock 증가 없음
- terminal 상태가 늦은 event로 역행하지 않음
- order total과 item 합계 일치

## 실패 조건

- `number`가 정수·safe range인지 확인하지 않습니다.
- client total이나 product price를 주문 정본으로 사용합니다.
- 주문 조회 때 현재 상품 가격으로 과거 합계를 다시 계산합니다.
- stock 조회와 차감을 서로 다른 transaction으로 처리합니다.
- 주문마다 product lock 순서가 달라집니다.
- cancel과 refund를 같은 상태로 취급합니다.
- provider 응답 전 최종 성공·취소·환불 상태를 표시합니다.
- duplicate event에서 재고를 다시 반환합니다.
- terminal 상태를 늦은 성공 event가 되돌립니다.
- 주문 상태 변경과 activity·재고 변경이 따로 commit됩니다.

## 연결 실습

[`커머스 checkout`](03-commerce-checkout.md)과 [`commerce-checkout exercise`](../../exercises/commerce-checkout/README.md)의 Stage 01–02와 Stage 05에서 금액, 가격 snapshot, 재고 경쟁, cancel·refund 상태 전이를 구현합니다.

## 완료 기준

- Money와 가격 snapshot의 정본을 설명합니다.
- checkout request에서 server가 가격과 합계를 다시 계산합니다.
- 실제 PostgreSQL 경쟁 요청에서 oversell을 막습니다.
- 주문 상태를 허용 transition으로만 변경합니다.
- terminal transition과 재고 반환을 같은 transaction에서 한 번만 수행합니다.

## 다음 단계

금액·재고·상태 전이를 정의했다면 [`커머스 checkout`](03-commerce-checkout.md)과 연결 exercise에서 외부 payment command와 webhook까지 통합합니다.
