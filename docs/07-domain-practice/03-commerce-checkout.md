# Capstone: 커머스 checkout

이 선택형 capstone은 상품 UI를 만드는 프로젝트가 아닙니다. 작은 주문·결제 시스템에서 **금액 snapshot, 동시 재고 차감, idempotent command, 외부 결제 adapter, 서명 webhook, cancel·refund와 실패 후 수렴**을 하나의 검증 가능한 경계로 결합합니다.

Core 과정의 `05-postgresql-kysely`, `06-security`, `08-testing`과 `collaboration-board`를 완료했다면 바로 시작할 수 있습니다. WebSocket과 Canvas는 사용하지 않습니다.

기본 작업 공간과 자동 검증은 [`commerce-checkout exercise`](../../exercises/commerce-checkout/README.md)에 있습니다.

## 종료 능력

완료한 독자는 다음을 설명하고 증명할 수 있어야 합니다.

- client cart 입력과 server 가격·재고 정본의 차이
- 현재 product 가격과 order item snapshot의 차이
- product row lock, stable lock order와 oversell 방지
- checkout idempotency key의 scope·request hash·response replay
- order transaction과 외부 payment command의 분리
- provider idempotency와 worker retry의 관계
- raw-body HMAC webhook, timestamp와 event dedupe
- order/payment/inventory transition의 한 transaction 경계
- cancel과 refund의 차이와 늦은 event 처리
- domain·API·실제 PostgreSQL·외부 HTTP adapter 검사의 증거 범위

## 시스템 구조

```text
HTTP client
  ├─ POST /checkouts ──────────────┐
  ├─ POST /orders/:id/cancel ──────┤
  ├─ POST /orders/:id/refund ──────┤
  └─ GET  /orders/:id ─────────────┤
                                    ↓
Fastify application
  ├─ checkout / order service
  ├─ PostgreSQL repository
  ├─ durable payment command worker ─── HTTP ──> mock payment provider
  └─ signed webhook endpoint <────────── event ── mock payment provider
```

외부 provider는 `fixtures/mock-payment-provider/`의 독립 process입니다. 학습자는 provider 내부를 변경하지 않고 application adapter와 실패 계약을 구현합니다.

## 범위

포함:

- 상품 seed와 목록 조회
- checkout request
- 주문·주문 항목 가격 snapshot
- PostgreSQL 재고 경쟁
- 주문 조회
- create/cancel/refund payment command
- command retry와 provider idempotency
- payment succeeded/failed/canceled/refunded webhook
- 전량 cancel/refund와 재고 반환
- domain·DB·API·provider adapter 자동 검사

제외:

- 상품 관리 UI와 장바구니 화면
- 사용자 인증과 다중 상점
- 실제 카드·PG SDK와 PCI 범위
- 할인·쿠폰·세금·배송비
- 부분 취소·부분 환불
- 배송·반품 검수
- message broker와 여러 service
- scheduler·관리자 reconciliation UI

제외 범위의 기능을 임의로 추가하기보다 현재 불변식과 실패 주입을 먼저 통과합니다.

## HTTP 계약

### 상품 목록

```http
GET /products
```

공개 DTO는 현재 가격과 판매 가능 재고를 반환합니다. 교육용 단일 instance에서만 stock 수치를 노출하며 실제 제품에서는 노출 정책이 다를 수 있습니다.

### Checkout

```http
POST /checkouts
Idempotency-Key: 7cf8...
Content-Type: application/json

{
  "items": [
    { "productId": "...", "quantity": 2 }
  ]
}
```

성공:

```text
201 Created
```

응답은 `pending_payment` 주문과 snapshot 금액을 반환합니다. 같은 key·같은 body는 같은 status와 body를 replay하고 `Idempotency-Replayed: true` header를 붙입니다. 같은 key·다른 body는 409입니다.

### 주문 조회

```http
GET /orders/:id
```

현재 상품 table이 아니라 order item snapshot에서 가격을 반환합니다.

### Cancel

```http
POST /orders/:id/cancel
Idempotency-Key: ...
```

`pending_payment`에서 create-payment command가 provider에 전달된 뒤에만 `cancel_pending`을 만들고 durable cancel command를 추가합니다. 아직 provider payment identity가 없으면 409 `payment_not_dispatched`입니다. provider의 `payment.canceled` event 전에는 `canceled`가 아닙니다.

### Refund

```http
POST /orders/:id/refund
Idempotency-Key: ...
```

`paid`에서만 `refund_pending`을 만들고 durable refund command를 추가합니다. provider의 `payment.refunded` event에서 `refunded`와 재고 반환을 commit합니다.

### Command dispatch

```http
POST /internal/payment-commands/dispatch
```

교육용 단일 worker endpoint입니다. 최대 처리 개수를 제한하고 각 command 결과를 반환합니다. production 공개 API가 아니며 실제 운영에서는 scheduler나 worker process가 소유합니다.

### Webhook

```http
POST /webhooks/payment
Content-Type: application/vnd.guide-payment+json
X-Payment-Timestamp: 1730000000
X-Payment-Signature: <hex hmac>
```

서명은 `timestamp + "." + raw_body`를 HMAC-SHA256으로 계산합니다. timestamp window는 기본 5분입니다.

## 데이터 정본

```text
products
  현재 가격·통화·stock

orders
  상태·금액·inventory release 여부

order_items
  SKU·이름·주문 당시 가격·수량 snapshot

payments
  provider payment identity·상태·금액

idempotency_records
  command scope·key·request hash·최초 응답

payment_commands
  외부 create/cancel/refund 작업과 retry 상태

provider_events
  webhook dedupe·payload hash·판정 outcome

inventory_movements
  reserve/release 증거

order_events
  업무 상태 전이와 무시된 event의 감사 기록
```

현재 stock은 `products.stock_on_hand`가 정본입니다. movement는 current stock을 재계산하기 위한 event sourcing log가 아니라 transaction 증거입니다.

## Stage 01. Money와 주문 snapshot

상세 요구사항: [`01-money-and-order.md`](../../exercises/commerce-checkout/specs/01-money-and-order.md)

완료 계약:

- minor unit 정수와 currency
- client total 비신뢰
- order item 가격·SKU·이름 snapshot
- item 합과 order total 일치
- 잘못된 수량·중복 item 정책
- 상품 가격 변경 뒤 과거 주문 불변

## Stage 02. Checkout과 재고 경쟁

상세 요구사항: [`02-checkout-inventory.md`](../../exercises/commerce-checkout/specs/02-checkout-inventory.md)

완료 계약:

- product row stable lock order
- 실제 PostgreSQL transaction
- stock 부족 시 전체 rollback
- stock=1에서 동시 checkout 하나만 성공
- reserve movement와 current stock 동시 변경
- multi-item 중간 실패에서 partial order 없음

## Stage 03. Idempotent checkout과 durable payment command

상세 요구사항: [`03-idempotent-payment.md`](../../exercises/commerce-checkout/specs/03-idempotent-payment.md)

완료 계약:

- checkout key scope와 canonical request hash
- 같은 key·같은 body 결과 replay
- 같은 key·다른 body 409
- order·inventory·idempotency result·create command 한 transaction
- command claim과 제한된 retry
- provider idempotency key로 crash gap 흡수

## Stage 04. Provider adapter와 webhook

상세 요구사항: [`04-payment-webhook.md`](../../exercises/commerce-checkout/specs/04-payment-webhook.md)

완료 계약:

- 실제 HTTP mock provider adapter
- raw body HMAC·timestamp window
- event ID와 payload hash dedupe
- duplicate delivery의 effect-once
- 같은 ID·다른 payload 거부
- out-of-order event가 상태를 역행시키지 않음
- webhook transaction 실패 시 retry 가능 응답

## Stage 05. Cancel과 refund

상세 요구사항: [`05-cancel-refund.md`](../../exercises/commerce-checkout/specs/05-cancel-refund.md)

완료 계약:

- pending payment cancel과 paid refund 분리
- provider 확정 전 pending 상태
- cancel/payment race의 허용 transition
- terminal event에서 inventory release 정확히 한 번
- duplicate cancel/refund command 안전
- late event에서 terminal state 유지

## Stage 06. 품질과 종료

상세 요구사항: [`06-quality.md`](../../exercises/commerce-checkout/specs/06-quality.md)

완료 계약:

- domain unit test
- 실제 PostgreSQL 경쟁·rollback test
- Fastify inject API test
- mock provider HTTP adapter test
- signed webhook failure test
- command retry·duplicate event·state reversal known-bad 검출
- app·DB pool·provider child process cleanup

## 구현 순서

1. Money, status와 외부 DTO schema를 고정합니다.
2. 순수 금액 계산과 state transition을 unit test로 만듭니다.
3. migration과 Kysely DB type을 작성합니다.
4. checkout transaction과 실제 경쟁 검사를 통과합니다.
5. idempotency record와 command outbox를 같은 transaction에 연결합니다.
6. provider port와 HTTP adapter를 구현합니다.
7. raw-body webhook route와 event transaction을 연결합니다.
8. cancel/refund command와 inventory release를 추가합니다.
9. 실패 주입과 전체 cleanup을 검증합니다.

각 stage에서 현재 stage 검사만 통과시킨 뒤 자신의 commit을 남깁니다. 이후 stage의 reference file을 미리 복사하지 않습니다.

## 자동 검증

저장소 루트에서 workspace를 생성합니다.

```sh
node exercises/commerce-checkout/checks/create-workspace.mjs
```

DB를 시작합니다.

```sh
POSTGRES_PORT=55433 docker compose \
  -p guide-commerce-checkout \
  -f exercises/commerce-checkout/compose.test.yml \
  up -d --wait

export DATABASE_URL=postgres://postgres:postgres@127.0.0.1:55433/commerce_dev
```

학습자 package를 설치하고 stage를 실행합니다.

```sh
corepack enable
pnpm --dir exercises/commerce-checkout/work install --ignore-workspace
pnpm --dir exercises/commerce-checkout/work migrate
node exercises/commerce-checkout/checks/verify-work.mjs 1
# ...
node exercises/commerce-checkout/checks/verify-work.mjs 6
```

checker는 skeleton의 baseline test 변경을 거부하고, `reference/` import와 symbolic link를 차단한 뒤 해당 `verify:0N` script를 실행합니다.

완료 뒤 DB를 제거합니다.

```sh
docker compose \
  -p guide-commerce-checkout \
  -f exercises/commerce-checkout/compose.test.yml \
  down -v
```

## 실패 조건

- client total을 저장합니다.
- product 현재 가격으로 과거 주문을 다시 계산합니다.
- stock 확인과 차감을 서로 다른 transaction에서 수행합니다.
- 외부 provider 요청을 stock lock transaction 안에서 기다립니다.
- idempotency key를 메모리에만 저장합니다.
- command가 provider idempotency identity 없이 재시도됩니다.
- webhook 서명을 parse 뒤 object에 대해 계산합니다.
- duplicate event마다 inventory를 반환합니다.
- cancel 요청 직후 provider 확인 없이 canceled로 표시합니다.
- late success가 refunded/canceled 상태를 paid로 되돌립니다.
- baseline test를 지우거나 reference를 import해 verifier를 통과합니다.

## 완료 기준

- Stage 01–06의 baseline test를 변경하지 않고 모두 통과합니다.
- 실제 PostgreSQL에서 경쟁 checkout과 transaction rollback을 증명합니다.
- mock provider HTTP 경계와 서명 webhook을 실행합니다.
- 동일 command·event가 반복돼도 주문·결제·재고 효과가 한 번만 남습니다.
- 종료 뒤 server·pool·child process가 남지 않습니다.

## 다음 단계

이 문서는 선택형 도메인 트랙의 종료점입니다. 이후 실제 커머스 제품으로 확장한다면 인증, 부분 환불, 예약 만료, 배송·반품, 회계 ledger와 provider reconciliation을 각각 별도 요구사항으로 추가합니다. 기능 수를 늘리기 전에 현재 상태 머신과 실패 행렬이 유지되는지 먼저 확인합니다.
