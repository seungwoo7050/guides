# 선택형 최종 문제: 커머스 checkout

금액 snapshot, 실제 PostgreSQL 재고 경쟁, idempotent checkout, durable payment command, HTTP mock provider, 서명 webhook, cancel·refund를 하나의 작은 backend에 연결합니다.

이 exercise는 core `workspace:create` allowlist를 수정하지 않고 추가할 수 있도록 자체 workspace 생성기를 가집니다. `skeleton/`에서 직접 구현하고 Stage 01–06 검사를 통과한 뒤에만 `reference/`와 비교합니다.

## 선행 조건

최소한 다음 실습의 완료 기준을 이해해야 합니다.

- `04-fastify-zod-api`
- `05-postgresql-kysely`
- `06-security`의 외부 입력·오류 경계
- `08-testing`

권장:

- `collaboration-board` Stage 01–06
- [`신뢰할 수 있는 command와 webhook`](../../docs/07-domain-practice/01-reliable-commands-and-webhooks.md)
- [`커머스 업무 불변식`](../../docs/07-domain-practice/02-commerce-domain-invariants.md)
- [`커머스 checkout capstone`](../../docs/07-domain-practice/03-commerce-checkout.md)

## 작업 공간 만들기

저장소 루트에서 실행합니다.

```sh
node exercises/commerce-checkout/checks/create-workspace.mjs
```

다음 경로가 생성됩니다.

```text
exercises/commerce-checkout/work/
```

기존 `work/`는 덮어쓰지 않고 skeleton이나 destination에 symbolic link가 있으면 중단합니다.

의존성을 설치합니다.

```sh
corepack enable
pnpm --dir exercises/commerce-checkout/work install --ignore-workspace
```

## PostgreSQL 시작

```sh
POSTGRES_PORT=55433 docker compose \
  -p guide-commerce-checkout \
  -f exercises/commerce-checkout/compose.test.yml \
  up -d --wait

export DATABASE_URL=postgres://postgres:postgres@127.0.0.1:55433/commerce_dev
```

port를 바꾸면 `POSTGRES_PORT`와 `DATABASE_URL`을 함께 바꿉니다.

migration을 적용합니다.

```sh
pnpm --dir exercises/commerce-checkout/work migrate
```

## Stage 실행

```sh
node exercises/commerce-checkout/checks/verify-work.mjs 1
node exercises/commerce-checkout/checks/verify-work.mjs 2
node exercises/commerce-checkout/checks/verify-work.mjs 3
node exercises/commerce-checkout/checks/verify-work.mjs 4
node exercises/commerce-checkout/checks/verify-work.mjs 5
node exercises/commerce-checkout/checks/verify-work.mjs 6
```

checker는 다음을 확인합니다.

- `work/`가 실제 디렉터리이고 exercise 밖으로 탈출하지 않음
- baseline `tests/`가 skeleton과 동일함
- source가 `reference/`를 import하거나 읽지 않음
- symbolic link가 없음
- `package.json`에 해당 `verify:0N` script가 있음
- stage script가 정상 종료함

baseline test는 수정하지 않습니다. 추가 검사는 `tests/extra/`에 둘 수 있습니다.

## Stage 계약

| Stage | 명세 | 핵심 증거 |
|---:|---|---|
| 01 | [`Money와 주문 snapshot`](specs/01-money-and-order.md) | pure domain 계산·상태·snapshot |
| 02 | [`Checkout과 inventory`](specs/02-checkout-inventory.md) | 실제 PostgreSQL lock·경쟁·rollback |
| 03 | [`Idempotent payment command`](specs/03-idempotent-payment.md) | key replay·payload conflict·claim token·durable command |
| 04 | [`Payment webhook`](specs/04-payment-webhook.md) | HTTP provider·raw body HMAC·dedupe·unknown retry·순서 |
| 05 | [`Cancel과 refund`](specs/05-cancel-refund.md) | pending transition·terminal release once |
| 06 | [`Quality`](specs/06-quality.md) | 전체 실패 주입·cleanup·typecheck |

## Mock payment provider

`fixtures/mock-payment-provider/server.mjs`는 외부 시스템 역할을 하는 dependency-free HTTP process입니다. 학습자 application에서 import하지 않습니다. Stage 04 test가 child process로 시작하고 실제 HTTP adapter를 검증합니다.

직접 실행할 수도 있습니다.

```sh
PORT=55991 \
WEBHOOK_URL=http://127.0.0.1:3001/webhooks/payment \
WEBHOOK_SECRET=guide-commerce-secret \
node exercises/commerce-checkout/fixtures/mock-payment-provider/server.mjs
```

Provider API:

```text
POST /operations
GET  /operations
POST /test/emit
POST /test/reset
```

같은 `Idempotency-Key`와 같은 body는 동일 operation을 반환하고, 같은 key와 다른 body는 409입니다.


## 완료 기준

- Stage 01–06 baseline test를 수정하지 않고 통과합니다.
- 실제 PostgreSQL에서 동시 checkout 하나만 성공하고 partial state가 남지 않습니다.
- provider retry와 duplicate webhook 뒤에도 외부·내부 효과가 한 번만 남습니다.
- webhook이 payment identity 저장보다 먼저 도착해도 503 retry 뒤 같은 event가 적용됩니다.
- lease가 만료된 worker는 새 claim의 complete/fail 결과를 덮지 못합니다.
- cancel·refund·late event에서 주문과 재고가 허용된 상태로 수렴합니다.
- typecheck와 모든 test가 끝난 뒤 app, pool과 provider child process가 종료됩니다.

## Reference 검증

학습자 구현을 완료한 뒤 reference를 별도로 설치합니다.

```sh
pnpm --dir exercises/commerce-checkout/reference install --ignore-workspace
pnpm --dir exercises/commerce-checkout/reference migrate
pnpm --dir exercises/commerce-checkout/reference verify
```

`reference/`는 가능한 설계 하나입니다. 파일 배치가 달라도 public HTTP 계약, DB 불변식과 실패 뒤 상태를 만족하면 올바릅니다.

## 정리

```sh
docker compose \
  -p guide-commerce-checkout \
  -f exercises/commerce-checkout/compose.test.yml \
  down -v
```

검사 뒤 Node child process나 DB pool이 남는다면 성공으로 취급하지 않습니다.

## 다음 단계

완료 뒤 실제 제품 요구를 추가할 때는 부분 환불, 예약 만료, 배송·반품, 회계 ledger와 reconciliation을 각각 독립된 상태·실패 계약으로 확장합니다.
