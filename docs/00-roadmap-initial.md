# 웹 애플리케이션 개발 로드맵

이 문서는 저장소 전체의 초기 학습 순서를 정의합니다. 세부 문서와 프로젝트가 추가되더라도 큰 흐름은 브라우저에서 시작해 서버·데이터·보안·실시간 통합으로 확장합니다.

## Part 01. 웹 기초

다음 주제를 먼저 다룹니다.

- 웹 요청과 응답의 기본 흐름
- 의미 있는 HTML과 접근성
- 반응형 CSS
- JavaScript 값·함수·상태
- DOM event, URL과 browser storage
- 비동기 작업과 오류
- TypeScript의 정적 형과 runtime validation
- Node.js package와 workspace

이 단계에서는 브라우저 애플리케이션과 Node.js workspace를 작은 독립 프로젝트로 구현합니다.

## Part 02. 프런트엔드

- React component와 state ownership
- form과 list
- effect와 비동기 요청 수명
- Next.js route와 server/client 경계
- HTTP adapter와 화면 상태의 분리

## Part 03. 백엔드

- HTTP API contract
- Fastify application lifecycle
- Zod runtime contract
- route, service, repository 책임 분리
- 안정된 오류 응답

## Part 04. 데이터와 보안

- 관계 모델과 SQL constraint
- PostgreSQL과 Kysely
- migration과 transaction
- session과 cookie
- ownership과 role authorization
- Origin, CORS와 CSRF 경계

## Part 05. 실시간과 품질

- WebSocket protocol
- snapshot, patch와 sequence
- optimistic conflict 처리
- connection, timer와 socket lifecycle
- unit, API, integration, browser test

## Part 06. 통합 프로젝트

앞선 경계를 하나의 실시간 협업 시스템으로 연결합니다. 최종 프로젝트는 browser application, API, shared contract, persistence와 realtime transport를 독립 package로 분리하는 workspace 구조를 사용합니다.

## 후속 확장

Core 통합 이후에는 transaction 밖의 외부 시스템 호출을 다루는 commerce checkout 사례를 추가합니다. 이 단계에서는 금액 snapshot, inventory 경쟁, idempotency, durable command와 webhook을 다룹니다.

## 완료 기준

저장소의 최종 상태에서는 각 `exercises/<project>/`가 parent repository의 script나 sibling project 없이 독립적으로 설치·실행·검증될 수 있어야 합니다.
