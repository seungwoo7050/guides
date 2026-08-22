# Project Catalog

`Project Catalog`는 Next.js App Router 기반의 검색·편집 애플리케이션입니다. URL query로 검색 조건을 공유하고, Server Component가 첫 결과를 렌더링하며, Client Component가 이후 검색과 제목 변경을 처리합니다. 외부 JSON은 runtime contract를 통과한 뒤에만 화면 상태에 반영되고, 제목 변경은 version 기반 optimistic concurrency control로 충돌을 감지합니다.

## 주요 기능

- `q`, `status`, `page` query를 정규화하고 첫 화면과 URL을 같은 조건으로 복원합니다.
- 검색 조건을 browser history에 기록하고 back/forward 탐색에서 입력과 결과를 다시 동기화합니다.
- `AbortController`와 monotonic generation을 함께 사용해 늦은 검색 응답이 최신 결과를 덮지 못하게 합니다.
- 검색 실패 또는 malformed response에서도 마지막으로 검증된 결과를 유지합니다.
- 제목을 먼저 화면에 반영하고, 저장 실패에서는 이전 server value로 rollback합니다.
- `409 Conflict`에서는 최신 server value와 사용자가 입력한 local draft를 동시에 보존합니다.
- keyboard 편집, focus 복구, `aria-live`, `focus-visible`, reduced motion, 좁은 viewport를 지원합니다.
- health endpoint, test-only reset boundary, browser E2E, 성능 예산, production smoke 검증을 포함합니다.

## 구조

```text
project-catalog/
├── app/
│   ├── api/
│   │   ├── health/route.ts
│   │   ├── projects/route.ts
│   │   ├── projects/[id]/route.ts
│   │   └── test/reset/route.ts
│   ├── layout.tsx
│   ├── page.tsx
│   ├── project-catalog.tsx
│   └── styles.css
├── lib/
│   ├── catalog-contract.ts
│   ├── catalog-model.ts
│   ├── project-types.ts
│   ├── projects.ts
│   └── request-coordinator.ts
├── scripts/
│   ├── run-playwright.mjs
│   └── smoke-production.mjs
├── tests/
│   ├── e2e/
│   └── *.test.ts
├── package.json
├── performance-budget.json
├── playwright.config.ts
├── tsconfig.json
└── vitest.config.ts
```

## 구성 요소 책임

- `lib/project-types.ts`는 server, Server Component, client가 공유하는 직렬화 가능한 domain type을 정의합니다.
- `lib/projects.ts`는 process-local store와 검색·version 검사를 소유합니다. 반환값은 clone이므로 caller가 store entry를 직접 변경할 수 없습니다.
- `lib/catalog-contract.ts`는 URL과 `unknown` JSON을 내부 canonical data로 변환하는 신뢰 경계입니다.
- `lib/catalog-model.ts`는 `ready`, `empty`, `pending`, `error` 상태와 마지막 검증 결과 보존 규칙을 정의합니다.
- `app/page.tsx`는 한 URL snapshot에서 초기 query와 결과를 계산합니다.
- `app/project-catalog.tsx`는 browser history, request lifetime, optimistic update, editor focus를 소유합니다.
- Route Handler는 검색, version 기반 수정, health, E2E data reset을 각각 분리합니다.
- `tests/`, Playwright, production smoke script는 state transition부터 실제 production process까지 다른 검증 계층을 담당합니다.

## 요구 환경

- Node.js `24.19.0` 이상
- npm
- Playwright Chromium은 browser test 실행 전에 별도로 설치해야 합니다.

`.nvmrc`를 사용하는 경우 다음과 같이 준비합니다.

```sh
nvm use
npm install
npx playwright install chromium
```

## 실행

개발 server를 시작합니다.

```sh
npm run dev
```

기본 주소는 `http://localhost:3000`입니다. 검색 조건은 URL로 직접 전달할 수 있습니다.

```text
/?q=Storage&status=active&page=1
```

production server는 build 뒤 실행합니다.

```sh
npm run build
APP_RELEASE=local-build npm run start
```

## HTTP API

| Method | Path | 역할 |
| --- | --- | --- |
| `GET` | `/api/projects` | `q`, `status`, `page`를 적용한 project search result를 반환합니다. |
| `PATCH` | `/api/projects/:id` | `{ "title": string, "version": number }`를 받아 현재 version일 때만 제목을 갱신합니다. |
| `GET` | `/api/health` | 정확히 `{ "status", "release" }`만 `no-store`로 반환합니다. |
| `POST` | `/api/test/reset` | 명시적인 test mode와 정확한 token이 모두 있을 때만 in-memory data를 초기화합니다. |

`PATCH`의 version이 오래되면 `409`와 최신 project를 반환합니다. 존재하지 않는 project는 `404`, 잘못된 body는 `400`입니다.

## 환경 변수

| 이름 | 용도 | 기본값 |
| --- | --- | --- |
| `APP_RELEASE` | health response에 노출할 release identifier | `local` |
| `PLAYWRIGHT` | `1`일 때 test reset route를 허용하는 test mode 중 하나 | 없음 |
| `CATALOG_TEST_RESET_TOKEN` | test reset request와 비교할 secret token | 없음 |

`/api/test/reset`은 `NODE_ENV=test` 또는 `PLAYWRIGHT=1`이면서 `x-catalog-test-token` header가 `CATALOG_TEST_RESET_TOKEN`과 일치할 때만 열립니다. 그 외에는 endpoint 존재 여부를 노출하지 않도록 `404`를 반환합니다.

## 검증

TypeScript와 framework route type을 검사합니다.

```sh
npm run typecheck
```

Vitest unit·route test를 실행합니다.

```sh
npm test
```

production build 뒤 Playwright browser test를 실행합니다. runner는 사용 가능한 port를 선택하고 Playwright가 production server를 소유하도록 전달합니다.

```sh
npm run test:e2e
```

production smoke는 실제 `next start` process를 띄워 health, root HTML, project API, 초기 JavaScript artifact와 server-only secret 비노출을 검사한 뒤 process tree를 정리합니다.

```sh
npm run smoke
```

전체 검증을 순서대로 실행합니다.

```sh
npm run verify
```

## 성능 예산

`performance-budget.json`은 browser test가 측정하는 두 한계를 정의합니다.

- 초기 route가 받은 JavaScript response body 합계: `800000` bytes 이하
- 첫 화면 DOM element 수: `180` 이하

예산 파일 자체의 key와 값도 unit test로 고정합니다.

## 주요 설계 결정

### 마지막으로 확인된 결과 보존

`pending`과 `error`가 별도 result를 소유하지 않고 `previous`를 보존합니다. 따라서 재조회 중이거나 응답이 잘못되어도 화면에는 마지막으로 contract를 통과한 결과만 남습니다.

### 취소와 generation의 이중 경계

`AbortController`만으로는 transport가 이미 완료되었거나 abort를 무시한 경우의 state commit을 막을 수 없습니다. 각 요청에 증가하는 generation을 부여하고 commit 직전에 최신 generation인지 다시 검사합니다.

### optimistic value와 local draft 분리

목록에는 optimistic title을 즉시 반영하지만 editor의 `draftTitle`은 별도로 유지합니다. 일반 실패에서는 목록을 이전 server value로 되돌리고, conflict에서는 최신 server project를 반영하면서 input draft를 유지합니다.

### process-local store

이 프로젝트는 별도 database 없이 서버 동작과 concurrency contract를 재현하기 위해 process-local `Map`을 사용합니다. test reset도 같은 owner를 초기화하므로 검증을 위한 두 번째 store가 생기지 않습니다.

## Implementation Order

아래 순서는 파일 배치나 Git history가 아니라, 완성된 시스템을 처음부터 구성할 때의 architecture dependency를 나타냅니다. 번호는 프로젝트 전체에서 한 번만 이어집니다.

| Order | Responsibility | Primary anchor |
| ---: | --- | --- |
| 1 | Project domain model | `lib/project-types.ts` |
| 2 | Process-local catalog store | `lib/projects.ts` |
| 2-1 | Filtered paginated search | `lib/projects.ts` |
| 2-2 | Version-checked rename | `lib/projects.ts` |
| 2-3 | Deterministic store reset | `lib/projects.ts` |
| 3 | External-data contract boundary | `lib/catalog-contract.ts` |
| 3-1 | URL query normalization | `lib/catalog-contract.ts` |
| 3-2 | API response validation | `lib/catalog-contract.ts` |
| 4 | Catalog state machine | `lib/catalog-model.ts` |
| 5 | Application document shell | `app/layout.tsx` |
| 6 | Server-rendered query bootstrap | `app/page.tsx` |
| 7 | Monotonic request coordination | `lib/request-coordinator.ts` |
| 8 | Client catalog state ownership | `app/project-catalog.tsx` |
| 8-1 | History-aware search convergence | `app/project-catalog.tsx` |
| 8-2 | Optimistic rename convergence | `app/project-catalog.tsx` |
| 9 | Editor focus and save lifecycle | `app/project-catalog.tsx` |
| 10 | Search HTTP boundary | `app/api/projects/route.ts` |
| 10-1 | Rename HTTP boundary | `app/api/projects/[id]/route.ts` |
| 11 | Test-only reset boundary | `app/api/test/reset/route.ts` |
| 12 | Production health contract | `app/api/health/route.ts` |
| 12-1 | Framework route type generation | `app/api/health/route.ts` |
| 13 | Responsive accessibility contract | `app/styles.css` |
| 14 | Unit verification configuration | `vitest.config.ts` |
| 14-1 | Query and bootstrap verification | `tests/query-and-bootstrap.test.ts` |
| 14-2 | Runtime contract verification | `tests/catalog-contract.test.ts` |
| 14-3 | Catalog state verification | `tests/catalog-model.test.ts` |
| 14-4 | Request-lifetime verification | `tests/request-coordinator.test.ts` |
| 14-5 | Store and route verification | `tests/projects-api.test.ts` |
| 14-6 | Production-boundary verification | `tests/production-contract.test.ts` |
| 14-7 | Performance-budget verification | `tests/performance-budget.test.ts` |
| 15 | Browser verification runtime | `playwright.config.ts` |
| 15-1 | Isolated Playwright port orchestration | `scripts/run-playwright.mjs` |
| 15-2 | URL and concurrency browser verification | `tests/e2e/catalog-concurrency.spec.ts` |
| 15-3 | Accessibility and performance browser verification | `tests/e2e/accessibility-performance.spec.ts` |
| 16 | Production smoke verification | `scripts/smoke-production.mjs` |

`Implementation 12-1`은 route가 존재한 뒤 `npm run typecheck`가 실행하는 `next typegen` 단계입니다. 생성된 `.next/types`는 build artifact이므로 배포 source에 포함하지 않습니다. 검증된 framework scaffold 생성 기록이 없으므로 `Implementation 0`은 사용하지 않습니다.

## 범위와 제한

- data는 process memory에만 존재하므로 재시작하면 초기 상태로 돌아갑니다.
- 여러 server instance 사이에서 version이나 변경 사항을 공유하지 않습니다.
- 인증과 사용자별 권한은 구현하지 않습니다.
- API는 page query를 지원하지만 UI에는 pagination control이 없습니다. 검색 제출은 항상 page `1`로 돌아갑니다.
- test reset route는 test automation을 위한 내부 경계이며 일반 운영 API가 아닙니다.
- production 실행 전에 같은 project directory에서 `npm run build`가 완료되어야 합니다.
