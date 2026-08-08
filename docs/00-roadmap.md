# 웹 애플리케이션 개발 로드맵

이 문서는 가이드 전체의 학습 계약입니다. 처음부터 끝까지 모두 외우는 것이 아니라, 현재 프로젝트를 시작하는 데 필요한 최소 모델을 읽고 바로 실습합니다. 각 장은 다음 장에서 실제로 사용하는 개념만 먼저 제공합니다.

## 대상 독자

다음 중 하나에 해당하면 시작할 수 있습니다.

- 프로그래밍을 처음 배우며 브라우저에서 동작하는 첫 애플리케이션을 만들고 싶은 사람
- 다른 언어 경험은 있지만 HTML·CSS·JavaScript와 웹 요청 흐름이 낯선 사람
- 프런트엔드와 백엔드를 따로 배웠지만 API·DB·인증·실시간 상태를 한 시스템으로 연결해 보지 않은 사람

완전 초보자는 Part 01을 순서대로 읽습니다. JavaScript와 브라우저 기초를 이미 안다면 필요한 장의 **완료 기준**을 먼저 보고 통과할 수 있는 장은 건너뛸 수 있습니다.

## 선행지식

필수 선행지식은 다음뿐입니다.

- 파일과 디렉터리를 만들고 수정할 수 있습니다.
- 터미널에서 현재 디렉터리를 확인하고 명령을 실행할 수 있습니다.
- 오류 메시지를 읽고 다시 시도할 의향이 있습니다.

변수, 조건문, 반복문, 함수, HTML, CSS와 JavaScript는 가이드 안에서 시작합니다. Git은 capstone에서 commit을 남길 정도의 기본 사용만 필요합니다.

## 지원 환경

명령 예시는 Linux, macOS 또는 Windows의 WSL처럼 POSIX shell을 기준으로 합니다. 기준 저장소는 다음 계열을 사용합니다.

- Node.js 22.16.0 이상 23 미만 (`.nvmrc` 기준 22.16.0)
- pnpm 10 계열
- TypeScript 5 계열
- React 19와 Next.js 15 계열
- Fastify 5와 Zod 3 계열
- PostgreSQL 16 계열
- Chrome 또는 Chromium
- Docker Compose가 필요한 DB·통합 실습

저장소 루트에서 시작 환경을 확인합니다.

```sh
node --version
corepack --version
corepack enable
pnpm --version
```

Part 01은 Node.js와 Chrome·Chromium만으로 진행할 수 있습니다. PostgreSQL 실습부터는 다음 명령도 성공해야 합니다.

```sh
docker compose version
```

브라우저 검사가 실행 파일을 자동으로 찾지 못하면 `CHROMIUM_PATH`에 경로를 지정합니다. 특정 minor 버전의 API를 외우지 않고, 실제 버전은 lockfile과 각 package manifest를 기준으로 합니다.

도구가 설치되어 있지 않다면 `.nvmrc`와 `package.json`의 범위에 맞는 Node.js 22 배포판과 Chrome·Chromium을 먼저 설치합니다. 임의의 최신 버전으로 바꾸기보다 위 명령의 실제 결과를 기록하고, Part별 설치 범위는 [`시작 전 준비`](../reference/prerequisites.md)에서 확인합니다.

## 종료 능력

이 가이드를 마친 독자는 빈 디렉터리에서 다음 일을 할 수 있어야 합니다.

1. 의미 있는 HTML과 반응형 CSS로 키보드 사용이 가능한 화면을 만듭니다.
2. JavaScript·TypeScript로 상태, 비동기 요청과 외부 입력 검증을 구현합니다.
3. React와 Next.js에서 server·URL·component 상태와 요청 수명을 구분합니다.
4. Fastify API를 route·service·repository로 나누고 안정된 HTTP 오류 계약을 제공합니다.
5. PostgreSQL schema·constraint·migration·transaction으로 업무 불변식을 보호합니다.
6. 비밀번호·세션·cookie·권한·CSRF·CORS 경계를 서버에서 검증합니다.
7. WebSocket snapshot·patch·sequence·재연결로 실시간 상태를 server 정본에 수렴시킵니다.
8. 단위·계약·API·DB·WebSocket·browser 검사와 production build를 독립된 증거로 실행합니다.

완료의 기준은 “코드를 한 번 실행했다”가 아니라 **정상·실패·경계 조건을 자동 검증할 수 있다**는 것입니다.

## 읽는 순서

### Part 01. 웹 기초

| 순서 | 문서 | 핵심 질문 |
|---:|---|---|
| 01 | [웹은 어떻게 동작하는가](01-web-foundations/01-how-the-web-works.md) | 브라우저가 URL을 열 때 어떤 요청·응답·프로세스 경계를 지나는가 |
| 02 | [HTML 폼과 접근성](01-web-foundations/02-html-forms-accessibility.md) | 브라우저의 기본 의미와 키보드 동작을 어떻게 보존하는가 |
| 03 | [CSS 레이아웃과 반응형 화면](01-web-foundations/03-css-layout-responsive.md) | 내용과 viewport가 달라져도 왜 화면이 무너지지 않는가 |
| 04 | [JavaScript 기초](01-web-foundations/04-javascript-foundations.md) | 값·함수·배열·객체와 상태 변경을 어떻게 모델링하는가 |
| 05 | [DOM, 이벤트, URL과 저장소](01-web-foundations/05-dom-events-url-storage.md) | 화면 상태의 정본을 어디에 둘 것인가 |
| 06 | [비동기 작업과 fetch](01-web-foundations/06-async-fetch-errors.md) | 늦은 응답·취소·오류를 어떻게 구분하는가 |
| 07 | [TypeScript와 실행 시점 검증](01-web-foundations/07-typescript-runtime-validation.md) | 정적 형이 사라지는 경계에서 무엇을 검사해야 하는가 |
| 08 | [Node.js, package와 workspace](01-web-foundations/08-node-packages-workspaces.md) | 실행 명령·의존성·package 공개 범위를 어떻게 고정하는가 |

### Part 02. 프런트엔드

| 순서 | 문서 | 핵심 질문 |
|---:|---|---|
| 09 | [React 컴포넌트와 상태](02-frontend/01-react-components-state.md) | 어떤 상태를 어느 component가 소유해야 하는가 |
| 10 | [폼과 목록](02-frontend/02-react-forms-lists.md) | 입력·목록·식별자와 오류 상태를 어떻게 다루는가 |
| 11 | [effect와 비동기 요청](02-frontend/03-react-effects-async.md) | 외부 시스템과 동기화하는 effect의 수명은 무엇인가 |
| 12 | [Next.js 경로와 렌더링](02-frontend/04-nextjs-routing-rendering.md) | server와 client 실행 경계를 어떻게 선택하는가 |
| 13 | [데이터 경계와 adapter](02-frontend/05-nextjs-data-boundaries.md) | 화면이 HTTP와 cache 세부 사항에 얼마나 의존해야 하는가 |

### Part 03. 백엔드

| 순서 | 문서 | 핵심 질문 |
|---:|---|---|
| 14 | [HTTP API 모델](03-backend/01-http-api-model.md) | method·status·header·body로 어떤 계약을 표현하는가 |
| 15 | [Fastify 생명주기](03-backend/02-fastify-lifecycle.md) | app 생성·plugin·hook·listen·close를 어떻게 분리하는가 |
| 16 | [Zod 전송 계약](03-backend/03-zod-contracts.md) | 요청과 응답의 외부 값을 어디서 parse하는가 |
| 17 | [서비스·저장소와 오류](03-backend/04-service-repository-errors.md) | HTTP, 업무 규칙과 저장 책임을 어떻게 분리하는가 |

### Part 04. 데이터와 보안

| 순서 | 문서 | 핵심 질문 |
|---:|---|---|
| 18 | [관계 모델과 SQL](04-data-and-security/01-sql-relational-model.md) | 업무 불변식을 표·키·제약으로 어떻게 표현하는가 |
| 19 | [PostgreSQL과 Kysely](04-data-and-security/02-postgresql-kysely.md) | SQL과 TypeScript 경계를 어떻게 연결하는가 |
| 20 | [migration과 transaction](04-data-and-security/03-migrations-transactions.md) | 함께 성공해야 하는 쓰기와 schema 변화를 어떻게 안전하게 적용하는가 |
| 21 | [비밀번호, 세션과 cookie](04-data-and-security/04-passwords-sessions-cookies.md) | 비밀을 저장하지 않고 사용자 신원을 어떻게 유지하는가 |
| 22 | [권한, CSRF와 CORS](04-data-and-security/05-authorization-csrf-cors.md) | 로그인한 사용자가 할 수 있는 일을 매 요청에서 어떻게 판정하는가 |

### Part 05. 실시간과 품질

| 순서 | 문서 | 핵심 질문 |
|---:|---|---|
| 23 | [WebSocket 프로토콜](05-realtime-and-quality/01-websocket-protocol.md) | 오래 유지되는 연결의 상태와 메시지 계약은 무엇인가 |
| 24 | [실시간 상태와 충돌](05-realtime-and-quality/02-realtime-state-conflicts.md) | 여러 client가 어떻게 같은 정본으로 수렴하는가 |
| 25 | [Canvas 렌더링](05-realtime-and-quality/03-canvas-rendering.md) | imperative drawing을 application state와 어떻게 분리하는가 |
| 26 | [테스트와 품질](05-realtime-and-quality/04-testing-quality.md) | 위험마다 가장 짧은 검증 경계는 어디인가 |

### Part 06. Capstone

| 순서 | 문서 | 통합 범위 |
|---:|---|---|
| 27 | [브라우저 작업 목록](06-capstones/01-browser-task-list.md) | HTML·CSS·JavaScript·URL·저장소 |
| 28 | [메모 API](06-capstones/02-notes-api.md) | TypeScript·Fastify·PostgreSQL |
| 29 | [공유 메모](06-capstones/03-shared-notes.md) | React·API·DB·세션·권한 |
| 30 | [실시간 협업 보드](06-capstones/04-collaboration-board.md) | 전체 과정과 실시간 동기화 |

## 문서와 실습 대응

| 문서 범위 | 실습 | 자동 검증 |
|---|---|---|
| Part 01의 첫 5장 | [`00-first-web-app`](../exercises/00-first-web-app/README.md) | 실제 browser, URL, 저장소, 키보드, 320px |
| 비동기·TypeScript·Node | [`01-runtime`](../exercises/01-runtime/README.md) | typecheck와 실행 결과 |
| HTML·CSS·DOM·URL | [`02-browser`](../exercises/02-browser/README.md) | 실제 browser와 history |
| Part 02 | [`03-react-nextjs`](../exercises/03-react-nextjs/README.md) | typecheck, build, 실제 browser와 요청 순서 역전 |
| Part 03 | [`04-fastify-zod-api`](../exercises/04-fastify-zod-api/README.md) | `app.inject` API 검사 |
| Part 04의 DB | [`05-postgresql-kysely`](../exercises/05-postgresql-kysely/README.md) | 실제 PostgreSQL, 경쟁과 rollback |
| Part 04의 보안 | [`06-security`](../exercises/06-security/README.md) | session·role·ownership·Origin 요청 검사 |
| Part 05의 실시간 | [`07-websocket`](../exercises/07-websocket/README.md) | 두 socket, reconnect와 cleanup |
| Part 05의 테스트 | [`08-testing`](../exercises/08-testing/README.md) | unit·API·browser 비교 |
| 전체 | [`collaboration-board`](../exercises/collaboration-board/README.md) | typecheck·test·build·DB·WS·E2E |

## 학습 방법

모든 실습은 같은 순서를 따릅니다.

```text
문제와 완료 계약 읽기
→ skeleton을 work로 복사
→ 실패하는 검사 실행
→ 한 계약씩 구현
→ 정상·실패·경계 검사 통과
→ 자신의 commit 기록
→ 마지막에만 reference와 비교
```

`reference`는 복사할 정답이 아니라 설계 선택을 비교할 자료입니다. 구현 모양이 달라도 외부 계약과 실패 후 상태를 만족하면 올바른 해결입니다.

## 범위 밖

이 가이드가 의도적으로 깊게 다루지 않는 내용은 다음과 같습니다.

- React·Next.js 대규모 코드베이스 구조와 고급 성능 최적화
- DB 저장 엔진, B+tree, MVCC·WAL 내부구조와 query planner
- Docker·VPS·DNS·공인 TLS·CI/CD·관측 플랫폼·백업 운영
- OAuth/OIDC provider 구축, 암호학 구현과 보안 감사 전체
- 여러 서비스 사이 outbox·saga·재전달·분산 tracing
- Kubernetes, multi-region과 대규모 고가용성

이 항목은 후속 전문 가이드가 소유합니다. 여기서는 작은 풀스택 애플리케이션을 시작하는 데 필요한 경계만 제공합니다.

## 첫 단계

웹 요청 자체가 낯설면 [`웹은 어떻게 동작하는가`](01-web-foundations/01-how-the-web-works.md)로 이동합니다. 이미 브라우저 앱을 만들 수 있다면 각 장의 **완료 기준**을 확인하고 Part 02부터 시작해도 됩니다.
