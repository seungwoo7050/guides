# 웹 애플리케이션 개발

웹을 처음 시작하는 사람이 HTML·CSS·JavaScript부터 React·Next.js, Fastify, PostgreSQL, 인증, WebSocket과 테스트까지 단계적으로 연결하는 가이드입니다. 모든 기술을 먼저 암기하지 않고, 각 단계에서 작은 기능을 직접 만들고 실패를 자동 검증하며 다음 경계로 넘어갑니다.

## 시작점

필요한 선행지식과 도구, 전체 읽기 순서, 문서와 실습의 대응은 [`docs/00-roadmap.md`](docs/00-roadmap.md)에 있습니다. 변수·조건문·반복문도 처음이라면 roadmap의 **Part 01 웹 기초**부터 시작합니다.

첫 구현은 저장소 루트에서 다음처럼 시작합니다. 생성기는 추적된 `skeleton/`을 학습자 전용 `work/`로 한 번만 복사하고, 기존 경로나 symbolic link를 덮어쓰지 않습니다.

```sh
pnpm workspace:create 00-first-web-app
node exercises/00-first-web-app/tests/verify.mjs exercises/00-first-web-app/work
```

검사가 실패하는 초기 상태에서 `exercises/00-first-web-app/work/`의 HTML·CSS·JavaScript만 직접 완성합니다. 모든 검사를 통과한 뒤에만 같은 exercise의 `reference/`와 비교합니다.

## 학습 흐름

```text
웹과 HTTP의 실행 모델
→ HTML·CSS·JavaScript·DOM·비동기·TypeScript·Node.js
→ React와 Next.js
→ HTTP API와 Fastify
→ PostgreSQL과 transaction
→ 비밀번호·세션·권한·CSRF·CORS
→ WebSocket·실시간 충돌·Canvas
→ 테스트와 단계형 capstone
```

문서는 여섯 part로 나뉩니다.

| Part | 내용 | 대표 실습 |
|---|---|---|
| 01 | 웹 기초와 첫 브라우저 애플리케이션 | `00-first-web-app`, `01-runtime`, `02-browser` |
| 02 | React와 Next.js 프런트엔드 | `03-react-nextjs` |
| 03 | HTTP API와 Fastify 백엔드 | `04-fastify-zod-api` |
| 04 | PostgreSQL, 세션과 보안 | `05-postgresql-kysely`, `06-security` |
| 05 | WebSocket, Canvas와 품질 | `07-websocket`, `08-testing` |
| 06 | 선택 통합 brief와 최종 누적 프로젝트 | `collaboration-board` |

## 모든 실습의 공통 순서

```text
연결 문서와 완료 계약 읽기
→ 필요하면 좁은 관찰 예제 실행
→ pnpm workspace:create <exercise>
→ work/의 초기 gate 확인(독립 실습은 의도한 실패, collaboration Stage 01은 starter baseline 통과)
→ work/만 직접 수정
→ 정상·실패·경계 검증 통과
→ 완료 증거 기록
→ 마지막에 exercise-local reference/ 비교
→ 다음 문서·실습 또는 최종 capstone
```

현재 이 브랜치에는 별도 `examples/`가 없습니다. 작은 관찰과 구현을 이미 각 독립 exercise가 함께 제공하므로, 완성 답안을 example로 중복 노출하지 않습니다. 표의 관찰 예제가 `—`인 것은 누락이 아니라 의도한 경계입니다.

## 문서에서 최종 문제까지의 ordered mapping

모든 명령은 저장소 루트 기준입니다. `work/`는 학습자가 수정하는 유일한 위치이며, 검증을 통과하기 전에는 exercise-local `reference/`를 읽거나 실행하지 않습니다.

| 순서 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 뒤 비교·다음 |
|---:|---|---|---|---|---|---|
| 1 | Part 01 [01–05](docs/01-web-foundations/01-how-the-web-works.md)와 [브라우저 작업 목록 brief](docs/06-capstones/01-browser-task-list.md) | — | [`00-first-web-app`](exercises/00-first-web-app/README.md), 이어서 [`02-browser`](exercises/02-browser/README.md) | 각 exercise의 `work/` | 실제 Chromium, URL·storage·keyboard·320px | 각 `reference/` 비교 → Part 01 06–08 |
| 2 | Part 01 [06–08](docs/01-web-foundations/06-async-fetch-errors.md) | — | [`01-runtime`](exercises/01-runtime/README.md) | `exercises/01-runtime/work/` | typecheck·실행 결과 | `reference/` 비교 → Part 02 |
| 3 | Part 02 [01–05](docs/02-frontend/01-react-components-state.md) | — | [`03-react-nextjs`](exercises/03-react-nextjs/README.md) | `exercises/03-react-nextjs/work/` | typecheck·production build·Chromium | `reference/` 비교 → Part 03 |
| 4 | Part 03 [01–04](docs/03-backend/01-http-api-model.md) | — | [`04-fastify-zod-api`](exercises/04-fastify-zod-api/README.md) | `exercises/04-fastify-zod-api/work/` | typecheck·`app.inject` | `reference/` 비교 → Part 04 DB |
| 5 | Part 04 [01–03](docs/04-data-and-security/01-sql-relational-model.md) | — | [`05-postgresql-kysely`](exercises/05-postgresql-kysely/README.md) | `exercises/05-postgresql-kysely/work/` | 실제 PostgreSQL·경쟁·rollback | `reference/` 비교 → 선택 notes API brief 또는 보안 문서 |
| 6 | [메모 API brief](docs/06-capstones/02-notes-api.md) | — | 선택형 self-directed expected evidence | 저장소 밖 학습자 소유 프로젝트 | 문서의 수동 evidence rubric | repo reference 없음 → Part 04 04–05 |
| 7 | Part 04 [04–05](docs/04-data-and-security/04-passwords-sessions-cookies.md) | — | [`06-security`](exercises/06-security/README.md) | `exercises/06-security/work/` | session·role·ownership·Origin | `reference/` 비교 → 선택 shared-notes brief 또는 Part 05 |
| 8 | [공유 메모 brief](docs/06-capstones/03-shared-notes.md) | — | 선택형 self-directed expected evidence | 저장소 밖 학습자 소유 프로젝트 | 문서의 수동 evidence rubric | repo reference 없음 → Part 05 |
| 9 | Part 05 [01–03](docs/05-realtime-and-quality/01-websocket-protocol.md) | — | [`07-websocket`](exercises/07-websocket/README.md) | `exercises/07-websocket/work/` | 두 socket·reconnect·cleanup | `reference/` 비교 → 테스트와 품질 |
| 10 | Part 05 [04](docs/05-realtime-and-quality/04-testing-quality.md) | — | [`08-testing`](exercises/08-testing/README.md) | `exercises/08-testing/work/` | unit·API·browser | `reference/` 비교 → 최종 capstone |
| 11 | [실시간 협업 보드](docs/06-capstones/04-collaboration-board.md) | — | [`collaboration-board` Stage 01 starter 확인 → Stage 02–08 누적 구현](exercises/collaboration-board/README.md) | `exercises/collaboration-board/work/` | 단계별 누적 gate·DB·WS·E2E | `reference/` 비교 → 가이드 종료 |

## reference와 evidence의 역할

- `reference/` 루트는 선행 도구·명령·용어·문제 해결을 담은 **빠른 참조 문서**이므로 언제든 읽을 수 있습니다.
- `exercises/*/reference/`는 학습자가 검증을 통과한 뒤 비교하는 **완성 기준 구현**입니다. 최종 협업 보드도 `exercises/collaboration-board/reference/`에 있습니다.
- 독립 exercise의 `reference.patch`와 협업 보드의 `patches/`는 source에서 파생한 **권장 구현 순서 walkthrough**입니다. 실제 Git 작성 역사를 주장하지 않으며 직접 구현을 대신하지 않습니다.
- 메모 API와 공유 메모는 선택형 분석·설계 brief입니다. 저장소 안에 runnable skeleton·자동 verifier·reference가 없으며, 각 문서의 expected evidence rubric으로만 완료를 판단합니다.

## 검증

문서 구조, 내부 링크, 코드 블록과 실습 계약은 외부 서비스 없이 확인합니다.

```sh
pnpm check:repository
```

초기 브라우저 실습을 실제 Chrome 또는 Chromium으로 확인합니다.

```sh
pnpm verify:foundations
```

runtime, React·Next.js, API, PostgreSQL, 보안, WebSocket, 테스트 실습과 완성 협업 보드를 포함한 전체 검증은 의존성·Docker·브라우저가 필요합니다.

```sh
pnpm install --frozen-lockfile
pnpm --dir exercises/08-testing/reference exec playwright install chromium
pnpm --dir exercises/collaboration-board/reference exec playwright install chromium
pnpm verify
```

`pnpm check`도 구조 검사에 실습 계약·capstone 검사기 자체 검증·known-bad mutation 검출을 더한 공식 품질 게이트이므로 같은 의존성·Docker·브라우저 환경에서 실행합니다.

표준 전체 검증은 `./prepare.sh` 다음 `./verify.sh` 순서로 실행합니다. 전체 로그는 성공·실패와 관계없이 저장소 밖의 실행별 임시 로그 파일에 남고 마지막에 `VERIFY LOG` 경로가 출력됩니다. 다른 위치가 필요하면 현재 worktree 전용의 저장소 밖 절대 경로를 지정하고 그 부모 디렉터리를 먼저 만듭니다.

```sh
./prepare.sh
./verify.sh
```

협업 보드는 생성된 `work/`에서 시작하고 `node exercises/collaboration-board/checks/verify-work.mjs exercises/collaboration-board/work N`으로 단계별 누적 검증을 실행합니다. 누적 patch는 직접 구현을 대신하지 않습니다. 완성 뒤 권장 변화 순서를 비교하는 curated walkthrough이며 별도 명령으로만 검사합니다.

```sh
pnpm check:walkthrough
```

## 빠른 참조

- [`시작 전 준비`](reference/prerequisites.md): Part별로 필요한 도구와 환경
- [`명령 빠른 참조`](reference/command-reference.md): 구조·실습·전체 검증 명령
- [`문제 해결`](reference/troubleshooting.md): 설치, browser, API, DB와 종료 문제의 경계
- [`용어`](reference/glossary.md): 처음 등장하는 웹·상태·보안·실시간 용어

## 다른 가이드와의 경계

- React·Next.js 코드베이스 합류, 고급 상태 구조와 성능 최적화는 `guide-frontend-react-nextjs`가 이어서 다룹니다.
- 관계 의미론, 인덱스, MVCC, WAL과 실행 계획은 `guide-database-systems`가 소유합니다.
- Docker, 공개 호스트, DNS·TLS, CI/CD, 관측성, 백업과 복구는 `guide-web-infrastructure`가 소유합니다.
- Spring Boot 구현은 Java와 Spring 전용 가이드에서 다룹니다.
- 서비스 간 outbox, saga, 재전달과 부분 실패는 `guide-distributed-services`가 다룹니다.

이 저장소는 **한 사람이 작은 풀스택 웹 애플리케이션을 독립적으로 시작하고 검증할 수 있는 지점**에서 끝납니다.
