# Stage 06: Quality와 종료

## 목표

정상 흐름만 아니라 알려진 잘못된 구현을 실제로 거부하고 모든 외부 resource를 종료합니다.

## 검사 경계

- pure domain unit
- repository와 실제 PostgreSQL integration
- concurrent checkout
- Fastify `inject` API
- child-process mock provider HTTP
- raw-body webhook
- command retry
- full state transition

한 E2E로 모든 실패 원인을 숨기지 않습니다.

## 필수 known-bad

검사가 다음 변형을 잡을 수 있어야 합니다.

- client total 신뢰
- product snapshot 대신 현재 가격 조회
- stock check와 update 분리
- idempotency memory map
- 같은 key·다른 payload 허용
- provider idempotency header 누락
- parsed JSON 재서명
- event dedupe memory map
- duplicate release
- terminal state reversal
- pool·child process 미종료

## 종료 계약

- Fastify app close
- Kysely destroy / pg pool close
- timeout·interval 제거
- provider child process SIGTERM 후 exit 확인
- test가 열린 handle을 숨기기 위해 강제 exit하지 않음

## 전체 명령

```sh
node exercises/commerce-checkout/checks/verify-work.mjs 6
```

Stage 06은 `typecheck`와 모든 baseline test를 실행합니다.

## 완료 기준

- Stage 01–05를 누적 통과합니다.
- known-bad를 허용하지 않습니다.
- clean DB에서 재현됩니다.
- 종료 뒤 test process가 자연스럽게 끝납니다.
