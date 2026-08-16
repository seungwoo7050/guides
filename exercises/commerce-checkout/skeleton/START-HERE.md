# 구현 시작점

baseline `tests/`는 수정하지 않습니다. Stage별 주요 구현 위치:

| Stage | 우선 파일 |
|---:|---|
| 01 | `src/domain.ts`, 필요하면 `src/contracts.ts` |
| 02 | `migrations/001_initial.sql`, `src/repository.ts#createCheckout` |
| 03 | `src/repository.ts` idempotency·claim token·command, `src/service.ts#dispatchPending` |
| 04 | `src/payment-provider.ts`, `src/webhook.ts`, `src/repository.ts#applyProviderEvent`와 unknown retry |
| 05 | `src/domain.ts` transition, `src/repository.ts#requestOrderCommand`·inventory release |
| 06 | `src/app.ts`, 오류·resource cleanup, 추가 test |

각 TODO를 코드 모양 그대로 reference와 맞추는 것이 목표가 아닙니다. public HTTP 계약과 DB 실패 후 상태를 만족시키면 됩니다.
