# Collaboration Board

Fastify, Next.js, WebSocket, Zod, Kysely와 PostgreSQL로 구성한 실시간 협업 보드입니다. Session authentication, board membership, owner/editor/viewer authorization, optimistic item version, board별 durable sequence, transient cursor·drag preview, snapshot recovery, admin suspension과 audit trail을 하나의 standalone system으로 제공합니다.

## 구성

```text
apps/web                 Next.js browser application
apps/api                 Fastify HTTP and WebSocket service
packages/contracts       shared Zod domain, HTTP, and socket contracts
packages/db              repository port, memory adapter, PostgreSQL adapter
packages/db/migrations   relational schema
compose.yaml             local PostgreSQL runtime
```

Workspace package는 독립 책임을 갖지만 root 밖의 script나 sibling exercise에 의존하지 않습니다.

## 주요 기능

- Opaque server-side session과 `HttpOnly`, `SameSite=Lax` cookie
- Exact Origin allowlist를 사용하는 authenticated mutation과 WebSocket admission
- Board 생성, 목록, snapshot, member invitation, role 변경, activity 조회와 one-way owner close
- `owner`, `editor`, `viewer` membership authorization과 owner role downgrade 방지
- Item create/update/move의 optimistic `baseVersion` 검사
- PostgreSQL transaction 안의 board row lock, item mutation, board version, event sequence와 event record
- Cursor와 drag preview는 transient, final move만 persistence
- Durable sequence gap이나 stale version 발생 시 full snapshot recovery
- Admin의 suspend/restore, audit action, active session revocation과 connected socket termination
- Memory adapter를 사용한 빠른 local/test 실행과 PostgreSQL adapter를 사용한 durable 실행

## 설치

Node.js 24와 pnpm 10을 기준으로 합니다.

```sh
pnpm install
pnpm typecheck
pnpm test
pnpm build
```

Browser binary가 설치되어 있으면 cross-layer test도 실행할 수 있습니다.

```sh
pnpm exec playwright install chromium
pnpm test:e2e
```

## Memory mode 실행

`DATABASE_URL`을 설정하지 않으면 API는 process-local `MemoryRepository`를 사용하고 시작 시 fixture를 seed합니다.

```sh
export WEB_ORIGINS=http://localhost:3000
export NEXT_PUBLIC_API_BASE_URL=http://localhost:4000
export NEXT_PUBLIC_WS_URL=ws://localhost:4000/ws
pnpm dev
```

- Web: `http://localhost:3000`
- API: `http://localhost:4000`
- Seeded handle: `owner`, `editor`, `viewer`, `admin`

## PostgreSQL mode 실행

```sh
docker compose up -d --wait
export DATABASE_URL=postgres://board:board@127.0.0.1:55434/board
export WEB_ORIGINS=http://localhost:3000
export NEXT_PUBLIC_API_BASE_URL=http://localhost:4000
export NEXT_PUBLIC_WS_URL=ws://localhost:4000/ws
pnpm migrate
pnpm dev
```

종료와 data 제거:

```sh
docker compose down -v
```

## HTTP API

| Method | Path | Responsibility |
| --- | --- | --- |
| `POST` | `/auth/login` | user upsert, session과 cookie 발급 |
| `POST` | `/auth/logout` | server session과 cookie 폐기 |
| `GET` | `/me` | current identity 조회 |
| `GET` | `/boards` | membership 기준 board 목록 |
| `POST` | `/boards` | owner board 생성 |
| `GET` | `/boards/:id` | member-specific snapshot |
| `GET` | `/boards/:id/activity` | durable event history |
| `POST` | `/boards/:id/invitations` | owner member invitation |
| `PATCH` | `/boards/:id/members/:userId/role` | owner role 변경 |
| `POST` | `/boards/:id/close` | owner board close와 socket 종료 |
| `GET` | `/admin/users` | admin user 상태 조회 |
| `PATCH` | `/admin/users/:id/status` | admin suspend/restore |
| `GET` | `/admin/actions` | admin audit trail |

WebSocket endpoint는 `/ws`입니다. 연결 후 첫 domain message는 `board.join`이어야 합니다.

## Data consistency

Persistent item mutation은 다음 순서로 한 transaction에서 처리됩니다.

```text
board row FOR UPDATE
→ active board and writable membership check
→ item optimistic version check and mutation
→ board version increment
→ next per-board sequence allocation
→ durable board_events insert
→ commit
→ WebSocket patch broadcast
```

Repository가 `null`을 반환한 stale mutation은 broadcast하지 않고 요청 client에 최신 snapshot을 보냅니다. Preview는 repository를 호출하지 않으므로 실패나 disconnect 뒤 durable state에 남지 않습니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | --- | --- |
| 0 | Workspace package ownership | `pnpm-workspace.yaml` |
| 1 | Server and browser configuration ownership | `.env.example` |
| 1-1 | Runtime environment parsing | `apps/api/src/config.ts` |
| 2 | Shared board snapshot contract | `packages/contracts/src/board.ts` |
| 2-1 | Shared HTTP contracts | `packages/contracts/src/http.ts` |
| 2-2 | Shared WebSocket contracts | `packages/contracts/src/ws.ts` |
| 3 | Relational persistence invariants | `packages/db/migrations/001_initial.sql` |
| 4 | Repository port and memory adapter | `packages/db/src/repository.ts` |
| 5 | PostgreSQL transactional adapter | `packages/db/src/postgres.ts` |
| 6 | HTTP and WebSocket app composition | `apps/api/src/app.ts` |
| 6-1 | Session lifecycle | `apps/api/src/app.ts` |
| 6-2 | Board HTTP boundary | `apps/api/src/app.ts` |
| 6-3 | Administration boundary | `apps/api/src/app.ts` |
| 6-4 | Application resource teardown | `apps/api/src/app.ts` |
| 7 | Realtime room and connection ownership | `apps/api/src/boardHub.ts` |
| 7-1 | Connection-specific membership and role | `apps/api/src/boardHub.ts` |
| 7-2 | Durable mutation and stale recovery | `apps/api/src/boardHub.ts` |
| 7-3 | Transient delivery and socket lifecycle | `apps/api/src/boardHub.ts` |
| 8 | API executable composition root | `apps/api/src/index.ts` |
| 9 | Browser document and navigation shell | `apps/web/app/layout.tsx` |
| 9-1 | Credentialed runtime-validated API client | `apps/web/lib/api.ts` |
| 9-2 | Session and board-list state | `apps/web/app/page.tsx` |
| 9-3 | Sequenced browser board reducer | `apps/web/lib/boardState.ts` |
| 9-4 | Realtime canvas and pointer lifecycle | `apps/web/components/BoardCanvas.tsx` |
| 9-5 | Activity and admin projections | `apps/web/app/activity/page.tsx` |
| 10 | Cross-layer browser verification | `tests/collaboration.spec.ts` |

## Verification

Project-local tests cover:

- shared runtime contract rejection
- memory repository membership, immutable owner role, defensive event history, optimistic version, one-way close, read-only role and session revocation
- HTTP `401`/`403`, exact Origin policy, cookie issuance, board creation, membership-role revocation, admin suspension and active socket termination
- browser reducer preview behavior and durable sequence-gap recovery
- Playwright login, board creation, WebSocket join and persistent note projection

PostgreSQL behavior requires Docker or an externally provided `DATABASE_URL`. Memory mode does not prove SQL transaction behavior; PostgreSQL mode and its migration are the durability boundary.

## Scope and limitations

Password authentication, file attachments, rich text, offline mutation queue, distributed WebSocket fan-out, Redis presence, event replay buffer and multi-region deployment are not included. A production deployment must terminate TLS, use a durable session policy, apply rate limits and run database migration as a controlled release step.
