# Commerce Checkout

PostgreSQL, Kysely, Fastify로 구성한 checkout 및 payment orchestration 서비스다. 주문 생성 시 상품 가격을 snapshot으로 고정하고, 재고 예약과 주문·결제·payment command 생성을 하나의 transaction으로 처리한다. 외부 payment provider 호출은 durable command와 lease 기반 dispatcher를 통해 수행하며, provider webhook은 raw body HMAC 검증과 event deduplication을 통과한 뒤 주문 상태를 변경한다.

## 주요 기능

- minor unit 정수로 금액을 계산하고 `Number.isSafeInteger` 범위를 강제한다.
- `Idempotency-Key`와 canonical request hash로 checkout, cancel, refund를 replay-safe하게 처리한다.
- product row lock과 조건부 재고 감소로 마지막 재고에 대한 경쟁 checkout을 직렬화한다.
- 주문 생성 transaction 안에서 order snapshot, inventory movement, payment, payment command를 함께 기록한다.
- `FOR UPDATE SKIP LOCKED`, claim token, lease timeout으로 여러 dispatcher가 command를 안전하게 가져간다.
- provider 실패를 retryable/non-retryable로 구분하고 bounded exponential backoff를 적용한다.
- timestamped HMAC, constant-time comparison, raw payload hash로 webhook authenticity와 event ID 재사용을 검증한다.
- cancel/refund/payment event를 명시적인 order state machine으로 제한한다.
- 실패·취소·환불에 따른 inventory release를 unique movement와 order marker로 한 번만 수행한다.

## 구조

```text
commerce-checkout/
├── migrations/             # relational invariants
├── src/
│   ├── domain.ts           # money snapshot and order state machine
│   ├── repository.ts       # transactional persistence and command leasing
│   ├── payment-provider.ts # provider port and HTTP adapter
│   ├── service.ts          # orchestration and retry policy
│   ├── webhook.ts          # raw-body signature verification
│   └── app.ts              # HTTP contract and stable failures
├── fixtures/               # local idempotent payment provider
└── tests/                  # unit and PostgreSQL integration verification
```

## 실행

Node.js 24.19.x와 pnpm 10이 필요하다.

```sh
pnpm install
cp .env.example .env
export $(grep -v '^#' .env | xargs)
docker compose up -d --wait
pnpm migrate
pnpm seed
```

별도 terminal에서 local provider와 API를 실행한다.

```sh
pnpm provider
pnpm dev
```

## API 흐름

상품 목록과 checkout:

```sh
curl http://127.0.0.1:3001/products
curl -X POST http://127.0.0.1:3001/checkouts \
  -H 'content-type: application/json' \
  -H 'idempotency-key: checkout-demo-0001' \
  -d '{"items":[{"productId":"product_keyboard","quantity":1}]}'
```

생성된 command를 provider에 전달한다.

```sh
curl -X POST http://127.0.0.1:3001/internal/payment-commands/dispatch \
  -H 'content-type: application/json' \
  -d '{"limit":10}'
```

Webhook은 `application/vnd.guide-payment+json` raw body, `x-payment-timestamp`, `x-payment-signature`가 필요하다. signature는 다음 byte sequence의 HMAC-SHA256 hex digest다.

```text
<unix timestamp>.<exact raw body>
```

## 테스트

```sh
pnpm typecheck
pnpm test:unit
```

PostgreSQL integration test:

```sh
export TEST_DATABASE_URL="$DATABASE_URL"
pnpm test:integration
```

## 주요 설계 결정

가격과 상품명은 주문 시점의 `order_items`에 복사한다. 이후 catalog 값이 바뀌어도 기존 주문 금액은 변하지 않는다. Provider 호출을 checkout transaction 안에서 직접 수행하지 않는다. Database commit과 외부 network 호출을 원자적으로 묶을 수 없으므로, 먼저 durable command를 기록한 뒤 dispatcher가 lease를 획득해 전달한다. Retry limit를 소진한 command는 `dead`로 남기며 자동으로 재고를 해제하지 않는다. Provider가 실제로 요청을 수신했는지 불명확할 수 있으므로 operator reconciliation 없이 business state를 되돌리지 않는 선택이다. Webhook event가 payment linkage보다 먼저 도착하면 `503`을 반환하고 같은 event ID를 나중에 다시 적용할 수 있게 `unknown_payment` 상태로 남긴다.

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
| 6-2 | Durable payment command lease | `src/repository.ts` |
| 6-3 | Provider event dedup and inventory release | `src/repository.ts` |
| 7 | Payment provider port and HTTP adapter | `src/payment-provider.ts` |
| 7-1 | Idempotent local provider fixture | `fixtures/mock-provider.ts` |
| 8 | Dispatch and retry orchestration | `src/service.ts` |
| 9 | Webhook authenticity and replay boundary | `src/webhook.ts` |
| 10 | HTTP application contract | `src/app.ts` |
| 10-1 | Idempotent checkout and order commands | `src/app.ts` |
| 10-2 | Command dispatch and webhook ingestion | `src/app.ts` |
| 11 | Process composition and shutdown | `src/server.ts` |
| 12 | Domain verification layer | `tests/domain.test.ts` |
| 12-1 | Webhook authenticity verification | `tests/webhook.test.ts` |
| 12-2 | Transactional PostgreSQL verification | `tests/repository.integration.test.ts` |

## 범위와 제한

이 프로젝트는 tax, shipping, promotion, authentication을 다루지 않는다. `/internal/payment-commands/dispatch`는 trusted internal network 뒤에서 호출된다는 전제이며 자체 인증을 제공하지 않는다. `dead` command를 조회·재처리하는 operator UI와 reconciliation worker도 범위 밖이다. Local provider는 같은 idempotency key와 같은 payload를 재사용하고, 같은 key를 다른 payload에 재사용하면 `409`를 반환한다. Webhook은 자동으로 전송하지 않는다. 하나의 주문에는 하나의 currency만 허용한다.
