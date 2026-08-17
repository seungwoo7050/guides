# Collaboration Board

Fastify, Next.js, WebSocket, Zod, Kysely와 PostgreSQL을 하나의 workspace에서 결합하는 실시간 협업 보드입니다.

초기 구성은 browser, API, shared contract와 persistence package의 소유 경계를 먼저 고정하고, 이후 HTTP·database·realtime·browser integration을 같은 package contract 위에 확장합니다.

## 초기 구조

```text
apps/web
apps/api
packages/contracts
packages/db
```

- `apps/web`: browser application
- `apps/api`: HTTP와 WebSocket process boundary
- `packages/contracts`: HTTP·WebSocket·board snapshot의 shared runtime contract
- `packages/db`: persistence contract와 adapter가 위치할 package
- root workspace: package dependency와 실행 경계 소유

## 환경 계약

Server-only 값과 browser에 공개되는 값을 분리합니다.

```text
DATABASE_URL
WEB_ORIGINS
NEXT_PUBLIC_API_BASE_URL
NEXT_PUBLIC_WS_URL
```

API는 환경 값을 startup에서 검증하고, browser는 `NEXT_PUBLIC_*` 값만 사용합니다.

## Shared contracts

초기 contract는 다음을 정본으로 정의합니다.

- `BoardRole`
- `BoardItem`
- `BoardSnapshot`
- login과 board HTTP payload
- client/server WebSocket event

HTTP와 WebSocket은 별도의 유사 type을 만들지 않고 같은 Zod contract를 공유합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | --- | --- |
| 0 | Workspace package ownership | `pnpm-workspace.yaml` |
| 1 | Server and browser configuration ownership | `.env.example` |
| 1-1 | Runtime environment parsing | `apps/api/src/config.ts` |
| 2 | Shared board snapshot contract | `packages/contracts/src/board.ts` |
| 2-1 | Shared HTTP contracts | `packages/contracts/src/http.ts` |
| 2-2 | Shared WebSocket contracts | `packages/contracts/src/ws.ts` |

## 다음 구현 경계

이 foundation 위에 relational persistence, repository adapter, session과 authorization, realtime room lifecycle, browser state projection과 cross-layer verification을 순서대로 추가합니다.
