# Reference 구현

이 디렉터리는 `commerce-checkout` 완료 뒤 비교할 수 있는 구현 하나입니다. 학습자 `work/`에서 import하거나 checker 통과에 사용하지 않습니다.

구조:

```text
src/domain.ts             pure 금액 계산과 state machine
src/repository.ts         PostgreSQL transaction·idempotency·claim token·durable command·webhook 적용
src/payment-provider.ts   외부 HTTP adapter
src/service.ts            use case와 command worker
src/webhook.ts            raw body HMAC 검증
src/app.ts                Fastify HTTP 계약
```

실행:

```sh
export DATABASE_URL=postgres://postgres:postgres@127.0.0.1:55433/commerce_dev
pnpm install --ignore-workspace
pnpm migrate
pnpm verify
```

Reference는 단순화를 위해 전량 cancel/refund만 지원하고 `refunded`에서 재고를 전량 반환합니다. 실제 제품에서는 payment refund와 physical restock을 분리할 수 있습니다.

Reference는 unknown payment webhook에 503을 반환하고 같은 event delivery에서 payment identity를 다시 조회합니다. command claim은 token으로 소유권을 확인해 lease 만료 전 worker가 새 처리 결과를 덮지 못하게 합니다.
