# Counter Quality Suite

동일한 counter invariant를 unit, HTTP integration, browser E2E의 서로 다른 verification layer에서 검증하는 작은 full-stack artifact입니다. Test framework 사용법을 나열하는 대신 각 layer가 어떤 failure boundary를 증명하는지 실제 실행 코드로 분리합니다.

## Behavior

Counter는 non-negative integer이며 다음 transition을 지원합니다.

```text
increment: value + 1
decrement: max(0, value - 1)
reset: 0
```

HTTP API:

| Method | Path | Result |
| --- | --- | --- |
| `GET` | `/counter` | 현재 `{ value }` |
| `POST` | `/counter/increment` | 증가된 값 |
| `POST` | `/counter/decrement` | 0 아래로 내려가지 않는 값 |
| `POST` | `/counter/reset` | 0으로 초기화 |
| `GET` | `/` | accessible browser UI |

## Install and verify

```sh
pnpm install
pnpm exec playwright install chromium
pnpm verify
```

개별 layer는 다음처럼 실행합니다.

```sh
pnpm typecheck
pnpm test
pnpm test:e2e
```

개발 server:

```sh
pnpm dev
```

기본 주소는 `http://127.0.0.1:4100`이며 `COUNTER_PORT`로 변경할 수 있습니다.

## Verification architecture

```text
pure transition
├── unit test: invariant and boundary
├── Fastify app: route and serialization
│   └── app.inject integration test
└── real listener and browser UI
    └── Playwright user-flow test
```

Unit test가 통과해도 route wiring과 serialization은 증명되지 않습니다. `app.inject()`가 통과해도 browser event, fetch와 accessible projection은 증명되지 않습니다. 세 layer는 중복이 아니라 서로 다른 failure surface를 소유합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | --- | --- |
| 1 | Pure counter transition | `src/counter.ts` |
| 2 | Unit invariant verification | `src/counter.test.ts` |
| 3 | HTTP and browser composition | `src/app.ts` |
| 4 | HTTP integration verification | `src/app.test.ts` |
| 5 | Network composition root | `src/server.ts` |
| 6 | Isolated browser-test lifecycle | `playwright.config.ts` |
| 7 | Observable browser workflow | `tests/counter.spec.ts` |

## Major design decisions

- Counter state는 app instance가 소유하므로 test case 사이에 공유되지 않습니다.
- Pure reducer는 framework 없이 boundary를 검증합니다.
- Integration test는 실제 port 없이 Fastify route stack을 통과합니다.
- E2E run마다 고유 port와 web server를 사용합니다.
- Browser assertion은 CSS selector보다 role, accessible name과 live status를 사용합니다.
- 모든 layer가 종료 가능한 resource boundary를 명시합니다.

## Scope and limitations

Persistence, authentication, multi-process synchronization과 visual regression은 포함하지 않습니다. 이 project의 목적은 복잡한 counter가 아니라 verification layer가 서로 다른 failure를 어떻게 잡는지 실행 가능한 형태로 보여 주는 것입니다.
