# 웹 애플리케이션 개발 로드맵

이 문서는 가이드 전체의 학습 범위와 진행 방식을 설명합니다. 모든 내용을 처음부터 외우는 대신, 현재 프로젝트를 시작하는 데 필요한 개념만 익힌 뒤 바로 실습합니다. 각 장에서는 다음 단계에서 실제로 사용할 개념을 우선 다룹니다.

## 대상 독자

다음 중 하나에 해당하면 이 가이드를 시작할 수 있습니다.

- 프로그래밍을 처음 배우며 브라우저에서 동작하는 첫 애플리케이션을 만들고 싶은 사람
- 다른 언어를 사용해 본 경험은 있지만 HTML·CSS·JavaScript와 웹 요청 흐름이 낯선 사람
- 프런트엔드와 백엔드를 따로 배웠지만 API·데이터베이스·인증·실시간 상태를 하나의 시스템으로 연결해 보지 않은 사람

프로그래밍을 처음 접한다면 파트 01부터 순서대로 읽습니다. JavaScript와 브라우저 기초를 이미 알고 있다면 각 장의 **완료 기준**을 먼저 확인하고, 기준을 충족하는 장은 건너뛸 수 있습니다.

## 선행 지식

필수 선행 지식은 다음과 같습니다.

- 파일과 디렉터리를 만들고 수정할 수 있습니다.
- 터미널에서 현재 디렉터리를 확인하고 명령을 실행할 수 있습니다.
- 오류 메시지를 읽고 원인을 확인하며 다시 시도할 수 있습니다.

변수, 조건문, 반복문, 함수, HTML, CSS, JavaScript는 가이드 안에서 기초부터 다룹니다. Git은 종합 실습에서 커밋을 남길 수 있을 정도의 기본 사용법만 알면 됩니다.

## 지원 환경

명령 예시는 Linux, macOS, Windows의 WSL처럼 POSIX 셸을 제공하는 환경을 기준으로 합니다. 이 저장소는 다음 버전 계열을 사용합니다.

- Node.js 24.19.0 이상 25 미만 (`.nvmrc` 기준 24.19.0)
- pnpm 10 계열
- TypeScript 5 계열
- React 19와 Next.js 16 계열
- Fastify 5와 Zod 3 계열
- PostgreSQL 16 계열
- Chrome 또는 Chromium
- 데이터베이스·통합 실습에서 사용할 Docker Compose

저장소 루트에서 기본 실행 환경을 확인합니다.

```sh
node --version
corepack --version
corepack enable
pnpm --version
```

파트 01은 Node.js와 Chrome 또는 Chromium만으로 진행할 수 있습니다. PostgreSQL 실습부터는 다음 명령도 정상적으로 실행되어야 합니다.

```sh
docker compose version
```

브라우저 검사 도구가 실행 파일을 자동으로 찾지 못하면 `CHROMIUM_PATH`에 경로를 지정합니다. 특정 마이너 버전의 API를 외울 필요는 없습니다. 실제 사용 버전은 lockfile과 각 패키지 매니페스트를 기준으로 확인합니다.

도구가 설치되어 있지 않다면 `.nvmrc`와 `package.json`의 버전 범위에 맞는 Node.js 24 LTS 배포판과 Chrome 또는 Chromium을 먼저 설치합니다. 임의로 최신 버전으로 변경하지 말고 위 명령의 실제 출력 결과를 기록합니다. 파트별 설치 범위는 저장소의 `reference/prerequisites.md`에서 확인할 수 있습니다.

## 수료 후 역량

이 가이드의 핵심 과정인 파트 01–06을 마치면 빈 디렉터리에서 다음 작업을 수행할 수 있어야 합니다.

1. 의미 있는 HTML과 반응형 CSS로 키보드 조작이 가능한 화면을 만듭니다.
2. JavaScript·TypeScript로 상태, 비동기 요청, 외부 입력 검증을 구현합니다.
3. React와 Next.js에서 서버 상태, URL 상태, 컴포넌트 상태를 구분하고 요청의 생명주기를 관리합니다.
4. Fastify API를 라우트·서비스·리포지터리 계층으로 나누고 일관된 HTTP 오류 응답 규약을 제공합니다.
5. PostgreSQL 스키마·제약 조건·마이그레이션·트랜잭션으로 도메인 불변식을 보호합니다.
6. 비밀번호·세션·쿠키·권한·CSRF·CORS 경계를 서버에서 검증합니다.
7. WebSocket 스냅샷·패치·시퀀스·재연결을 사용해 클라이언트 상태를 서버의 기준 상태와 일치시킵니다.
8. 단위·계약·API·데이터베이스·WebSocket·브라우저 검사와 프로덕션 빌드를 각각 독립된 검증 수단으로 실행합니다.

선택 과정인 파트 07까지 마치면 다음 역량을 추가로 검증합니다.

9. 금액·가격 스냅샷·재고·주문 상태 전이를 도메인 불변식으로 모델링합니다.
10. 데이터베이스 트랜잭션에 포함할 수 없는 결제 요청을 영속적으로 기록한 명령, 멱등성, 웹훅으로 최종 일관성 있게 처리합니다.
11. 중복·지연·순서 역전·응답 유실·재시도가 발생해도 주문과 재고가 잘못된 상태로 바뀌지 않는지 검사합니다.

완료 기준은 단순히 “코드를 한 번 실행했다”가 아니라 **정상·실패·경계 조건을 자동으로 검증할 수 있다**는 것입니다.

## 읽는 순서

아래 01–33 번호는 문서의 개념 학습 순서를 나타냅니다. 각 파트를 마치면 연계 실습으로 이동합니다. `브라우저 작업 목록`은 파트 01 직후에 수행하고, 선택형 메모 과제는 관련 데이터베이스·보안 문서를 읽은 뒤 수행합니다. `실시간 협업 보드`는 모든 독립 실습을 마친 뒤 진행합니다. 파트 07은 핵심 과정을 마친 뒤 선택적으로 진행하는 도메인 실습이며, 파트 06의 선행 조건은 아닙니다.

### 파트 01. 웹 기초

| 순서 | 문서 | 핵심 질문 |
|---:|---|---|
| 01 | [웹은 어떻게 동작하는가](01-web-foundations/01-how-the-web-works.md) | 브라우저가 URL을 열 때 요청·응답·프로세스의 어떤 경계를 거치는가 |
| 02 | [HTML 폼과 접근성](01-web-foundations/02-html-forms-accessibility.md) | 브라우저가 제공하는 기본 의미와 키보드 동작을 어떻게 보존하는가 |
| 03 | [CSS 레이아웃과 반응형 화면](01-web-foundations/03-css-layout-responsive.md) | 콘텐츠와 뷰포트 크기가 달라도 레이아웃이 무너지지 않게 하려면 어떻게 해야 하는가 |
| 04 | [JavaScript 기초](01-web-foundations/04-javascript-foundations.md) | 값·함수·배열·객체와 상태 변경을 어떻게 모델링하는가 |
| 05 | [DOM, 이벤트, URL과 저장소](01-web-foundations/05-dom-events-url-storage.md) | 화면 상태의 기준을 어디에 둘 것인가 |
| 06 | [비동기 작업과 fetch](01-web-foundations/06-async-fetch-errors.md) | 늦게 도착한 응답·취소·오류를 어떻게 구분하는가 |
| 07 | [TypeScript와 런타임 검증](01-web-foundations/07-typescript-runtime-validation.md) | 정적 타입 정보가 사라지는 경계에서 무엇을 검사해야 하는가 |
| 08 | [Node.js, 패키지와 워크스페이스](01-web-foundations/08-node-packages-workspaces.md) | 실행 명령·의존성·패키지 공개 범위를 어떻게 고정하는가 |

### 파트 02. 프런트엔드

| 순서 | 문서 | 핵심 질문 |
|---:|---|---|
| 09 | [React 컴포넌트와 상태](02-frontend/01-react-components-state.md) | 어떤 상태를 어느 컴포넌트가 소유해야 하는가 |
| 10 | [폼과 목록](02-frontend/02-react-forms-lists.md) | 입력·목록·식별자·오류 상태를 어떻게 다루는가 |
| 11 | [Effect와 비동기 요청](02-frontend/03-react-effects-async.md) | 외부 시스템과 동기화하는 Effect의 생명주기를 어떻게 관리하는가 |
| 12 | [Next.js 라우팅과 렌더링](02-frontend/04-nextjs-routing-rendering.md) | 서버와 클라이언트 실행 경계를 어떻게 선택하는가 |
| 13 | [데이터 경계와 어댑터](02-frontend/05-nextjs-data-boundaries.md) | 화면이 HTTP와 캐시 구현 세부 사항에 얼마나 의존해야 하는가 |

### 파트 03. 백엔드

| 순서 | 문서 | 핵심 질문 |
|---:|---|---|
| 14 | [HTTP API 모델](03-backend/01-http-api-model.md) | 메서드·상태 코드·헤더·본문으로 어떤 계약을 표현하는가 |
| 15 | [Fastify 생명주기](03-backend/02-fastify-lifecycle.md) | 애플리케이션 생성·플러그인·훅·`listen`·`close`를 어떻게 분리하는가 |
| 16 | [Zod 전송 계약](03-backend/03-zod-contracts.md) | 요청과 응답의 외부 값을 어느 경계에서 파싱하고 검증하는가 |
| 17 | [서비스·리포지터리와 오류](03-backend/04-service-repository-errors.md) | HTTP 처리, 도메인 규칙, 저장 책임을 어떻게 분리하는가 |

### 파트 04. 데이터와 보안

| 순서 | 문서 | 핵심 질문 |
|---:|---|---|
| 18 | [관계 모델과 SQL](04-data-and-security/01-sql-relational-model.md) | 도메인 불변식을 테이블·키·제약 조건으로 어떻게 표현하는가 |
| 19 | [PostgreSQL과 Kysely](04-data-and-security/02-postgresql-kysely.md) | SQL과 TypeScript의 경계를 어떻게 연결하는가 |
| 20 | [마이그레이션과 트랜잭션](04-data-and-security/03-migrations-transactions.md) | 원자적으로 처리해야 하는 쓰기와 스키마 변경을 어떻게 안전하게 적용하는가 |
| 21 | [비밀번호, 세션과 쿠키](04-data-and-security/04-passwords-sessions-cookies.md) | 비밀번호 원문을 저장하지 않고 사용자 신원을 어떻게 유지하는가 |
| 22 | [권한, CSRF와 CORS](04-data-and-security/05-authorization-csrf-cors.md) | 로그인한 사용자가 수행할 수 있는 작업을 요청마다 어떻게 판정하는가 |

### 파트 05. 실시간 처리와 품질

| 순서 | 문서 | 핵심 질문 |
|---:|---|---|
| 23 | [WebSocket 프로토콜](05-realtime-and-quality/01-websocket-protocol.md) | 장시간 유지되는 연결의 상태와 메시지 계약을 어떻게 정의하는가 |
| 24 | [실시간 상태와 충돌](05-realtime-and-quality/02-realtime-state-conflicts.md) | 여러 클라이언트의 상태를 어떻게 동일한 기준 상태로 수렴시키는가 |
| 25 | [Canvas 렌더링](05-realtime-and-quality/03-canvas-rendering.md) | 명령형 그리기 코드를 애플리케이션 상태와 어떻게 분리하는가 |
| 26 | [테스트와 품질](05-realtime-and-quality/04-testing-quality.md) | 각 위험을 가장 짧고 정확하게 검증할 수 있는 경계는 어디인가 |

### 파트 06. 종합 실습

| 순서 | 문서 | 통합 범위 | 실제 위치 |
|---:|---|---|---|
| 27 | [브라우저 작업 목록](06-capstones/01-browser-task-list.md) | HTML·CSS·JavaScript·URL·저장소 | 파트 01 뒤 `00-first-web-app`과 같은 계약으로 수행 |
| 28 | [메모 API](06-capstones/02-notes-api.md) | TypeScript·Fastify·PostgreSQL | 데이터베이스 실습 뒤 선택형 검증 과제로 수행 |
| 29 | [공유 메모](06-capstones/03-shared-notes.md) | React·API·데이터베이스·세션·권한 | 보안 실습 뒤 선택형 검증 과제로 수행 |
| 30 | [실시간 협업 보드](06-capstones/04-collaboration-board.md) | 전체 과정과 실시간 동기화 | 모든 독립 실습 뒤 단계 01–08의 최종 과제로 수행 |

### 파트 07. 선택형 도메인 실습

| 순서 | 문서 | 핵심 질문 | 연계 실습 |
|---:|---|---|---|
| 31 | [신뢰할 수 있는 명령과 웹훅](07-domain-practice/01-reliable-commands-and-webhooks.md) | 데이터베이스와 외부 시스템을 하나의 트랜잭션으로 묶을 수 없을 때 중복·응답 유실·재시도를 어떻게 처리하는가 | `commerce-checkout` 단계 03–04 |
| 32 | [커머스 도메인 불변식](07-domain-practice/02-commerce-domain-invariants.md) | 금액·가격 스냅샷·재고·주문 상태를 어떤 기준과 제약 조건으로 보호하는가 | `commerce-checkout` 단계 01–02, 05 |
| 33 | [커머스 체크아웃](07-domain-practice/03-commerce-checkout.md) | 앞서 정의한 계약을 작은 주문·결제 시스템으로 어떻게 결합하고 검증하는가 | [`commerce-checkout`](../exercises/commerce-checkout/README.md) 단계 01–06 |

파트 07은 쇼핑몰 UI를 만드는 과정이 아닙니다. 상품·장바구니 화면보다 금액, 재고 경쟁, 주문 상태 전이, 결제 명령, 웹훅의 실패 처리에 집중합니다. 실제 결제대행사 연동, 배송, 쿠폰, 세금, 다중 판매자 기능은 범위에 포함하지 않습니다.

## 문서와 실습의 대응 관계

별도의 `examples/` 디렉터리는 제공하지 않습니다. 각 독립 실습에서 핵심 동작을 관찰한 뒤 직접 구현합니다. 아래 표에서 수정 대상은 모두 생성된 `work/` 디렉터리입니다.

| 학습 순서 | 문서 범위 | 직접 수행 | 검증 | 완료 후 이동 |
|---:|---|---|---|---|
| 1 | 파트 01의 01–05와 [종합 실습 01 명세](06-capstones/01-browser-task-list.md) | [`00-first-web-app`](../exercises/00-first-web-app/README.md), [`02-browser`](../exercises/02-browser/README.md) | 실제 브라우저·URL·저장소·키보드 조작 | 각 `reference/`와 비교 → 파트 01의 06–08 |
| 2 | 파트 01의 06–08 | [`01-runtime`](../exercises/01-runtime/README.md) | 타입 검사·실행 결과 | `reference/`와 비교 → 파트 02 |
| 3 | 파트 02의 01–05 | [`03-react-nextjs`](../exercises/03-react-nextjs/README.md) | 타입 검사·빌드·실제 브라우저 | `reference/`와 비교 → 파트 03 |
| 4 | 파트 03의 01–04 | [`04-fastify-zod-api`](../exercises/04-fastify-zod-api/README.md) | `app.inject` API 검사 | `reference/`와 비교 → 데이터베이스 |
| 5 | 파트 04의 01–03 | [`05-postgresql-kysely`](../exercises/05-postgresql-kysely/README.md) | 실제 PostgreSQL·경쟁 상태·롤백 | `reference/`와 비교 → 선택형 메모 API 또는 보안 |
| 6 | 종합 실습 02 | [선택형 메모 API 검증 과제](06-capstones/02-notes-api.md) | 수동 검증 기준표 | 저장소 내 정답 구현 없음 → 보안 |
| 7 | 파트 04의 04–05 | [`06-security`](../exercises/06-security/README.md) | 세션·역할·소유권·`Origin` | `reference/`와 비교 → 선택형 공유 메모 또는 파트 05 |
| 8 | 종합 실습 03 | [선택형 공유 메모 검증 과제](06-capstones/03-shared-notes.md) | 수동 검증 기준표 | 저장소 내 정답 구현 없음 → 파트 05 |
| 9 | 파트 05의 01–03 | [`07-websocket`](../exercises/07-websocket/README.md) | 소켓 두 개·재연결·정리 | `reference/`와 비교 → 품질 |
| 10 | 파트 05의 04 | [`08-testing`](../exercises/08-testing/README.md) | 단위·API·브라우저 검사 | `reference/`와 비교 → 최종 과제 |
| 11 | 종합 실습 04 | [`collaboration-board`](../exercises/collaboration-board/README.md) 단계 01–08 | 누적 타입 검사·테스트·빌드·데이터베이스·WebSocket·E2E | 실습 디렉터리의 `reference/`와 비교 → 핵심 과정 종료 |
| 12 | 파트 07의 31–33 | [`commerce-checkout`](../exercises/commerce-checkout/README.md) 단계 01–06 | 도메인 규칙·실제 PostgreSQL·동시 결제·멱등성·HTTP 결제 제공자·서명된 웹훅 | 실습 디렉터리의 `reference/`와 비교 → 선택 과정 종료 |

## 학습 방법

핵심 실습은 모두 같은 순서로 진행합니다.

```text
문제와 완료 조건 읽기
→ 저장소 루트에서 pnpm workspace:create <exercise> 실행
→ 실패하는 검사 실행
→ 생성된 work/에서 계약을 하나씩 구현
→ 정상·실패·경계 조건 검사 통과
→ 커밋 기록
→ 마지막에만 reference와 비교
```

생성기는 기존 `work/` 디렉터리나 심볼릭 링크를 덮어쓰지 않습니다. 각 실습의 `reference/`는 복사할 정답이 아니라 구현을 마친 뒤 설계 선택을 비교하기 위한 자료입니다. 루트의 `reference/`는 언제든 참고할 수 있는 빠른 참조 문서입니다. 구현 방식이 달라도 외부 계약을 지키고 실패 후 상태가 올바르면 유효한 해결입니다.

`commerce-checkout`은 핵심 실습의 허용 목록을 변경하지 않고 추가할 수 있는 선택형 자료이므로, 해당 실습 디렉터리의 생성기를 사용합니다.

```sh
node exercises/commerce-checkout/checks/create-workspace.mjs
node exercises/commerce-checkout/checks/verify-work.mjs 1
```

이 생성기도 기존 `work/` 디렉터리를 덮어쓰지 않으며 심볼릭 링크를 거부합니다.

## 범위 밖

이 가이드에서 의도적으로 깊게 다루지 않는 내용은 다음과 같습니다.

- React·Next.js 대규모 코드베이스 구조와 고급 성능 최적화
- 데이터베이스 저장 엔진, B+ 트리, MVCC·WAL 내부 구조와 쿼리 플래너
- Docker·VPS·DNS·공인 TLS·CI/CD·관측 플랫폼·백업 운영
- OAuth/OIDC 제공자 구축, 암호 알고리즘 구현, 전체 보안 감사
- 여러 서비스 사이의 범용 아웃박스·사가·메시지 브로커 재전달·분산 트레이싱
- 실제 결제대행사 계약, 카드 정보 처리, 회계·세금·배송·쿠폰·정산 시스템
- Kubernetes, 멀티 리전, 대규모 고가용성 구성

파트 07은 단일 애플리케이션 안에서 영속 명령과 멱등한 웹훅을 처리하는 수준까지 다룹니다. 여러 서비스가 각자 데이터베이스를 소유하는 분산 트랜잭션과 범용 사가 운영은 후속 전문 가이드의 범위입니다.

## 첫 단계

웹 요청의 기본 흐름이 낯설다면 [`웹은 어떻게 동작하는가`](01-web-foundations/01-how-the-web-works.md)부터 시작합니다. 이미 브라우저 애플리케이션을 만들 수 있다면 각 장의 **완료 기준**을 확인하고 파트 02부터 시작해도 됩니다. 핵심 과정을 마쳤고 트랜잭션과 외부 시스템 사이의 실패 처리를 연습하려면 [`신뢰할 수 있는 명령과 웹훅`](07-domain-practice/01-reliable-commands-and-webhooks.md)으로 이동합니다.
