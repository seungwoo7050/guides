# 최종 문제: 실시간 협업 보드

로그인, 역할 기반 권한, PostgreSQL transaction, WebSocket 동기화와 실제 브라우저 검사를 하나의 시스템으로 연결합니다. 기본 학습 경로는 patch 적용이나 canonical `skeleton/` 직접 수정이 아니라 생성된 `work/`에서 구현하는 것입니다.

## 선행 조건

다음 실습을 각각 직접 구현하고 검증한 뒤 시작합니다.

- `01-runtime`
- `02-browser`
- `03-react-nextjs`
- `04-fastify-zod-api`
- `05-postgresql-kysely`
- `06-security`
- `07-websocket`
- `08-testing`

전체 요구사항은 [`협업 보드 capstone`](../../docs/06-capstones/04-collaboration-board.md)에 있습니다.

## 작업 공간 만들기

```sh
pnpm workspace:create collaboration-board
corepack enable
pnpm --dir exercises/collaboration-board/work install
git -C exercises/collaboration-board/work init
git -C exercises/collaboration-board/work add .
git -C exercises/collaboration-board/work commit -m 'chore: 협업 보드 시작 상태'
node exercises/collaboration-board/checks/verify-work.mjs exercises/collaboration-board/work 1
```

Stage 01은 복사된 starter의 workspace·package·종료 baseline을 읽고 `verify:01` 통과를 확인하는 단계입니다. Stage 02부터 `specs/` 문서의 계약을 직접 구현하고 `work/package.json`에 `verify:02`~`verify:08` 명령과 검사를 누적한 뒤 자신의 commit으로 끝냅니다. 단계 검사기는 폴더 이름만 확인하지 않고 해당 단계의 검증 명령을 실제로 실행합니다.

| 단계 | 명세 | 핵심 완료 조건 |
|---:|---|---|
| 01 | [`runtime과 workspace`](specs/01-runtime-workspace.md) | 실행 위치, package boundary와 종료 계약 |
| 02 | [`브라우저 기반`](specs/02-browser-foundation.md) | 의미 구조, URL 상태와 반응형 골격 |
| 03 | [`계약과 프런트엔드`](specs/03-contracts-frontend.md) | 공유 schema, Next.js 상태와 요청 수명 |
| 04 | [`HTTP API`](specs/04-http-api.md) | Fastify route·service·repository와 오류 계약 |
| 05 | [`PostgreSQL`](specs/05-postgresql.md) | migration, 제약, transaction과 충돌 |
| 06 | [`인증과 권한`](specs/06-security.md) | 세션·역할·소유권·브라우저 보안 |
| 07 | [`실시간 동기화`](specs/07-realtime.md) | snapshot·patch·sequence·재연결·Canvas |
| 08 | [`품질과 완료`](specs/08-quality.md) | 모든 경계의 자동 검사와 production build |

단계가 끝날 때마다 다음 명령에서 번호만 바꾸어 실행합니다.

```sh
node exercises/collaboration-board/checks/verify-work.mjs exercises/collaboration-board/work 2
node exercises/collaboration-board/checks/verify-work.mjs exercises/collaboration-board/work 3
# ...
node exercises/collaboration-board/checks/verify-work.mjs exercises/collaboration-board/work 8
```

검사기는 `verify:0N` 명령과 단계별 증거를 확인하고, 학습자 script와 별개인 저장소 소유 명령으로 형 검사·기준 test·단계별 test를 실행합니다. `skeleton/`에서 함께 복사된 기준 test는 수정하지 않고 새 test를 별도 파일로 추가합니다. `--structure-only`는 저장소 유지보수자가 검사기 자체를 점검할 때만 사용하며 학습 완료 증거가 아닙니다. 형 검사와 해당 단계까지의 테스트를 통과시키고 commit합니다. 이후 단계의 파일을 미리 복사해 숨은 의존성을 만들지 않습니다.

## 기준 프로젝트와 비교

완성 구현은 [`reference/`](reference/README.md)에서 실행할 수 있습니다. 그러나 이를 `work/`로 복사해서 완료하지 않습니다. 먼저 자신의 구현과 테스트를 끝낸 뒤 다음 세 관점으로 비교합니다.

- 책임이 어느 package와 module에 놓였는가
- 실패 뒤 저장소와 연결 상태가 무엇인가
- 어떤 테스트가 그 계약을 증명하는가

## 기준 구현의 학습용 구성 순서

이 번호의 범위는 `exercises/collaboration-board/reference/` 전체입니다. 파일별 작성 순서나 실제 Git history가 아니라, 완성 구현을 다시 만든다고 가정한 **권장 학습용 구성 순서**입니다. Stage 번호는 검증 checkpoint이고 Implementation 번호는 파일 사이를 오가는 construction order이므로 서로 같은 번호를 뜻하지 않습니다. 아래 표는 source에 있는 exact anchor가 중복되지 않도록 번호를 괄호 없이 적고, 주석을 넣을 수 없는 설정·명령만 이 README가 exact anchor를 소유합니다.

| 순서 | 파일·명령 | 책임과 다음 연결 |
|---:|---|---|
| [Implementation 0] | `corepack enable`, `pnpm install` | 저장소가 선언한 pnpm으로 workspace 의존성을 설치합니다. 일반 디렉터리 생성·복사는 이 단계가 아닙니다. |
| [Implementation 1] | root/package별 `package.json`, `pnpm-workspace.yaml`, `tsconfig*.json`, PostCSS·Tailwind·Vitest 설정 | JSON에 주석을 넣지 않고 workspace package 경계, 공개 명령과 build/typecheck 진입점을 먼저 고정합니다. lockfile은 생성 결과이므로 annotation 대상이 아닙니다. |
| 1-1 | `reference/.env.example` | server secret과 browser 공개 환경 변수의 소유 runtime을 분리합니다. |
| 1-2 | `apps/web/next.config.mjs` | 독립 workspace에서도 Next.js가 올바른 tracing/build root를 사용하게 합니다. |
| 2 | `packages/contracts/src/board.ts` | board 크기, role, item과 snapshot의 정본 schema를 정의합니다. |
| 2-1 | `packages/contracts/src/http.ts` | 인증·HTTP 요청/응답에서 신뢰할 수 없는 값을 parse하는 계약을 추가합니다. |
| 2-2 | `packages/contracts/src/ws.ts` | client/server WebSocket event와 version·sequence 복구 표면을 정의합니다. |
| 2-3 | `packages/contracts/src/index.ts` | 다른 package가 사용할 공개 계약 진입점만 노출합니다. |
| 3 | `compose.dev.yml` | 개발 PostgreSQL resource와 readiness 경계를 준비합니다. |
| 3-1 | `packages/db/migrations/001_initial.sql` | role, ownership, version, sequence와 감사 기록의 DB 불변식을 만듭니다. |
| 3-2 | `packages/db/src/db-types.ts` | SQL schema를 Kysely가 검사하는 application-side table type으로 옮깁니다. |
| 3-3 | `packages/db/src/migrate.ts` | migration version을 transaction으로 한 번만 적용하고 pool을 항상 닫습니다. |
| 3-4 | `packages/db/src/cli.ts`; `pnpm --filter @board/db migrate`, `pnpm --filter @board/db seed` | schema 적용과 학습용 seed를 application startup과 분리한 중간 CLI입니다. |
| 4 | `packages/db/src/index.ts` | HTTP와 realtime이 공유할 repository port와 빠른 memory adapter를 만듭니다. |
| 4-1 | `packages/db/src/postgres.ts`의 factory | pool과 Kysely instance의 resource owner를 정합니다. |
| 4-2 | `packages/db/src/postgres.ts`의 `record` | item, board version, event sequence를 한 transaction에서 확정합니다. |
| 5 | `apps/api/src/app.ts`의 `buildApp` | Fastify plugin, origin 정책, route와 resource cleanup을 한 app factory에 조립합니다. |
| 5-1 | `apps/api/src/app.ts`의 인증 route | server session과 cookie 발급·폐기 수명을 구현합니다. |
| 5-2 | `apps/api/src/app.ts`의 board route | runtime validation 뒤 repository 계약으로 HTTP 상태를 변환합니다. |
| 5-3 | `apps/api/src/app.ts`의 admin route | admin role, 계정 상태와 감사 작업 경계를 연결합니다. |
| 5-4 | `apps/api/src/app.ts`의 `onClose` | hub, socket heartbeat와 repository resource를 app 종료에 귀속합니다. |
| 5-5 | `apps/api/src/index.ts` | memory/PostgreSQL adapter 선택, seed, origin과 listen을 composition root에서 연결합니다. |
| 6 | `apps/web/app/globals.css` | keyboard focus, skip link와 공통 responsive surface를 만듭니다. |
| 6-1 | `apps/web/app/layout.tsx` | document metadata, 언어와 skip-link 경계를 고정합니다. |
| 6-2 | `apps/web/components/AppShell.tsx` | 모든 route가 공유하는 navigation과 main landmark를 만듭니다. |
| 6-3 | `apps/web/lib/api.ts` | cookie 요청과 response runtime parsing을 UI 밖 adapter가 소유합니다. |
| 6-4 | `apps/web/components/LoginForm.tsx` | 입력 draft와 submit failure를 form component가 소유합니다. |
| 6-5 | `apps/web/components/BoardList.tsx` | session, list, create form의 서로 다른 상태를 조립합니다. |
| 6-6 | `apps/web/app/page.tsx` | root route에서 shell과 board feature를 결합합니다. |
| 6-7 | `apps/web/app/activity/page.tsx` | 영속 event와 transient pointer state의 경계를 설명합니다. |
| 6-8 | `apps/web/app/admin/page.tsx` | admin action의 입력·완료 상태와 API adapter를 연결합니다. |
| 7 | `apps/api/src/boardHub.ts` | room snapshot, client lifecycle, heartbeat와 broadcast의 server-side owner를 만듭니다. |
| 7-1 | `apps/web/app/boards/[id]/page.tsx` | socket 연결·재연결과 snapshot/patch 적용 수명을 route가 소유합니다. |
| 7-2 | `apps/web/components/BoardCanvas.tsx` | application state를 pixel로 투영하고 pointer 좌표계를 board 좌표로 변환합니다. |
| 8 | `playwright.config.ts` | 실제 browser 검사를 고유 port의 API·web process와 함께 실행하고 evidence 경계를 분리합니다. |
| 8-1 | `tests/e2e/board.spec.ts` | 접근 가능한 로그인부터 화면 결과까지 핵심 사용자 흐름을 증명합니다. |
| 8-2 | `tests/smoke.mjs` | HTTP session과 WebSocket join을 한 짧은 cross-boundary 검사로 증명합니다. |

`app.test.ts`, `ws.test.ts`, `contracts.test.ts`, DB test와 component test도 Stage 08의 증거이지만, 같은 construction 설명을 반복하지 않도록 위 대표 anchor와 이 표에서 함께 읽습니다. repository-owned checker, `skeleton/`, `specs/`, fixture, patch와 walkthrough 자료에는 이 번호를 붙이지 않습니다.

## patch의 역할

`patches/`는 기본 완료 절차가 아닙니다. curated patch는 `walkthrough-base/`에만 적용되며 새 `skeleton/`과 독립적입니다. 직접 구현을 끝낸 뒤, 기준 프로젝트의 **학습용 권장 구현 순서**를 살펴보는 walkthrough 자료이며 실제 Git history가 아닙니다.

```sh
pnpm check:walkthrough
```

이 명령은 patch가 순서대로 적용되고 내부 import가 해석되는지만 확인합니다. patch 적용 성공은 학습자의 구현 완료를 의미하지 않습니다.

## 전체 검증

기준 프로젝트는 다음 순서로 검증합니다.

```sh
pnpm install --frozen-lockfile
pnpm check
pnpm --dir exercises/collaboration-board/reference typecheck
pnpm --dir exercises/collaboration-board/reference test
pnpm --dir exercises/collaboration-board/reference build
pnpm --dir exercises/collaboration-board/reference exec playwright install chromium
pnpm --dir exercises/collaboration-board/reference test:e2e
```

학습자 구현은 `node exercises/collaboration-board/checks/verify-work.mjs exercises/collaboration-board/work 8`로 누적 검증합니다. PostgreSQL 경로는 프로젝트의 compose와 migration·seed 명령을 사용합니다. 검사 결과는 파일 존재나 정규식이 아니라 실제 HTTP 요청, 데이터베이스 상태, 두 WebSocket 연결과 브라우저 사용자 흐름으로 판정합니다.

## 완료 기준

- 새 checkout에서 문서화된 명령만으로 실행할 수 있습니다.
- 로그인·로그아웃·보드 생성·초대·역할 변경·읽기 전용 참여가 동작합니다.
- 영속 변경과 활동 event가 함께 commit되거나 함께 rollback됩니다.
- 두 client가 같은 sequence의 patch를 받고 재연결 시 snapshot으로 복구합니다.
- 오래된 baseVersion과 읽기 전용 쓰기가 서버에서 거부됩니다.
- 작은 화면, 키보드, 오류 상태와 production build를 검증합니다.
- 모든 서버, pool, timer, socket과 browser가 검사 뒤 종료됩니다.
