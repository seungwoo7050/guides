# 웹 애플리케이션 개발

웹을 처음 시작하는 사람이 HTML·CSS·JavaScript부터 React·Next.js, Fastify, PostgreSQL, 인증, WebSocket과 테스트까지 단계적으로 연결하는 가이드입니다. 모든 기술을 먼저 암기하지 않고, 각 단계에서 작은 기능을 직접 만들고 실패를 자동 검증하며 다음 경계로 넘어갑니다.

## 시작점

필요한 선행지식과 도구, 전체 읽기 순서, 문서와 실습의 대응은 [`docs/00-roadmap.md`](docs/00-roadmap.md)에 있습니다. 변수·조건문·반복문도 처음이라면 roadmap의 **Part 01 웹 기초**부터 시작합니다.

첫 구현은 다음 문제입니다.

```sh
cd exercises/00-first-web-app
cp -R skeleton work
node tests/verify.mjs work
```

검사가 실패하는 초기 상태에서 HTML·CSS·JavaScript를 직접 완성합니다. 모든 검사를 통과한 뒤에만 `reference/`와 비교합니다.

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
| 06 | 브라우저 앱에서 협업 보드까지 누적 프로젝트 | `collaboration-board` |

## 검증

문서 구조, 내부 링크, 코드 블록과 실습 계약은 외부 서비스 없이 확인합니다.

```sh
pnpm check
```

초기 브라우저 실습을 실제 Chrome 또는 Chromium으로 확인합니다.

```sh
pnpm verify:foundations
```

runtime, React·Next.js, API, PostgreSQL, 보안, WebSocket, 테스트 실습과 완성 협업 보드를 포함한 전체 검증은 의존성·Docker·브라우저가 필요합니다.

```sh
pnpm install --frozen-lockfile
pnpm --dir exercises/08-testing/reference exec playwright install chromium
pnpm --dir projects/collaboration-board exec playwright install chromium
pnpm verify
```

협업 보드는 `skeleton/`의 실제 workspace에서 시작하고 `node exercises/collaboration-board/checks/verify-work.mjs work N`으로 단계별 누적 검증을 실행합니다. 누적 patch는 직접 구현을 대신하지 않습니다. 완성 뒤 변화 순서를 비교하는 walkthrough 자료이며 별도 명령으로만 검사합니다.

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
