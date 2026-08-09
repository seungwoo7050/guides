# 최종 문제: 실시간 협업 보드

로그인, 역할 기반 권한, PostgreSQL transaction, WebSocket 동기화와 실제 브라우저 검사를 하나의 시스템으로 연결합니다. 기본 학습 경로는 patch 적용이 아니라 `skeleton/`에서 직접 구현하는 것입니다.

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
cd exercises/collaboration-board
rm -rf work
cp -R skeleton work
cd work
corepack enable
pnpm install
git init
git add .
git commit -m 'chore: 협업 보드 시작 상태'
cd ..
node checks/verify-work.mjs work 1
```

각 단계는 `specs/` 문서의 계약을 구현하고 `work/package.json`에 누적 `verify:01`~`verify:08` 명령을 만든 뒤 자신의 commit으로 끝냅니다. 단계 검사기는 폴더 이름만 확인하지 않고 해당 단계의 검증 명령을 실제로 실행합니다.

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
node checks/verify-work.mjs work 2
node checks/verify-work.mjs work 3
# ...
node checks/verify-work.mjs work 8
```

검사기는 `verify:0N` 명령과 단계별 증거를 확인하고, 학습자 script와 별개인 저장소 소유 명령으로 형 검사·기준 test·단계별 test를 실행합니다. `skeleton/`에서 함께 복사된 기준 test는 수정하지 않고 새 test를 별도 파일로 추가합니다. `--structure-only`는 저장소 유지보수자가 검사기 자체를 점검할 때만 사용하며 학습 완료 증거가 아닙니다. 형 검사와 해당 단계까지의 테스트를 통과시키고 commit합니다. 이후 단계의 파일을 미리 복사해 숨은 의존성을 만들지 않습니다.

## 기준 프로젝트와 비교

완성 구현은 [`projects/collaboration-board`](../../projects/collaboration-board/README.md)에서 실행할 수 있습니다. 그러나 이를 `work/`로 복사해서 완료하지 않습니다. 먼저 자신의 구현과 테스트를 끝낸 뒤 다음 세 관점으로 비교합니다.

- 책임이 어느 package와 module에 놓였는가
- 실패 뒤 저장소와 연결 상태가 무엇인가
- 어떤 테스트가 그 계약을 증명하는가

## patch의 역할

`patches/`는 더 이상 기본 완료 절차가 아닙니다. 기존 patch는 `walkthrough-base/`에만 적용되며 새 `skeleton/`과 독립적입니다. 직접 구현을 끝낸 뒤, 기준 프로젝트가 어떤 순서로 변화했는지 살펴보는 **walkthrough 자료**입니다.

```sh
pnpm check:walkthrough
```

이 명령은 patch가 순서대로 적용되고 내부 import가 해석되는지만 확인합니다. patch 적용 성공은 학습자의 구현 완료를 의미하지 않습니다.

## 전체 검증

기준 프로젝트는 다음 순서로 검증합니다.

```sh
pnpm install --frozen-lockfile
pnpm check
pnpm --dir projects/collaboration-board typecheck
pnpm --dir projects/collaboration-board test
pnpm --dir projects/collaboration-board build
pnpm --dir projects/collaboration-board exec playwright install chromium
pnpm --dir projects/collaboration-board test:e2e
```

학습자 구현은 `node checks/verify-work.mjs work 8`로 누적 검증합니다. PostgreSQL 경로는 프로젝트의 compose와 migration·seed 명령을 사용합니다. 검사 결과는 파일 존재나 정규식이 아니라 실제 HTTP 요청, 데이터베이스 상태, 두 WebSocket 연결과 브라우저 사용자 흐름으로 판정합니다.

## 완료 기준

- 새 checkout에서 문서화된 명령만으로 실행할 수 있습니다.
- 로그인·로그아웃·보드 생성·초대·역할 변경·읽기 전용 참여가 동작합니다.
- 영속 변경과 활동 event가 함께 commit되거나 함께 rollback됩니다.
- 두 client가 같은 sequence의 patch를 받고 재연결 시 snapshot으로 복구합니다.
- 오래된 baseVersion과 읽기 전용 쓰기가 서버에서 거부됩니다.
- 작은 화면, 키보드, 오류 상태와 production build를 검증합니다.
- 모든 서버, pool, timer, socket과 browser가 검사 뒤 종료됩니다.
