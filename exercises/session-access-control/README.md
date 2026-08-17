# Session Access Control

Fastify 기반의 작은 session authentication·authorization API입니다. Opaque server-side session, credential cookie, exact Origin allowlist, owner/admin authorization과 logout revocation을 하나의 독립 실행 artifact로 제공합니다.

## HTTP API

| Method | Path | Contract |
| --- | --- | --- |
| `POST` | `/auth/login` | `alpha` 또는 `admin` identity로 session 발급 |
| `POST` | `/auth/logout` | server session 폐기와 cookie 제거 |
| `GET` | `/me` | 현재 authenticated user 조회 |
| `PATCH` | `/profiles/:id` | owner 또는 admin만 display name 변경 |
| `GET` | `/admin/users` | admin role 전용 목록 조회 |

Browser가 `Origin`을 보낸 state-changing request는 exact allowlist를 통과해야 합니다. Session cookie가 있는 mutation은 `Origin` 누락도 거부하므로 suffix match, malicious login Origin과 credentialed non-browser mutation을 같은 boundary에서 차단합니다.

## Install and run

```sh
pnpm install
pnpm typecheck
pnpm test
pnpm dev
```

기본 server 주소는 `http://localhost:4000`입니다. 설정 가능한 environment variable은 다음과 같습니다.

```text
PORT=4000
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
NODE_ENV=production
```

## Architecture

```text
HTTP request
→ cookie and CORS boundary
→ exact Origin guard
→ server-side session resolution
→ ownership or role authorization
→ app-owned SecurityStore
```

`buildApp()`은 `SecurityStore` instance를 주입받습니다. 따라서 app instance마다 user/session lifetime이 분리되고 test가 다른 process-global state에 오염되지 않습니다.

## Security decisions

- Browser에는 opaque token만 저장하고 identity와 role은 server state에서 복원합니다.
- Cookie는 `HttpOnly`, `SameSite=Lax`, `Path=/`를 사용하며 production에서는 `Secure`를 활성화합니다.
- 인증 실패 `401`, 권한 실패 `403`, resource 부재 `404`를 구분합니다.
- State mutation은 authenticated request에서 exact Origin을 필수로 검사합니다.
- Store가 token과 `maxAgeSeconds`를 함께 발급하므로 browser cookie와 server token이 같은 lifetime을 사용합니다.
- Logout은 cookie만 지우지 않고 server token도 폐기합니다.
- URL parameter는 actor identity로 취급하지 않습니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | --- | --- |
| 1 | Identity and input contracts | `src/contracts.ts` |
| 2 | App-owned user and session state | `src/store.ts` |
| 3 | Cookie, CORS, and dependency composition | `src/app.ts` |
| 4 | Exact Origin mutation guard | `src/app.ts` |
| 5 | Session identity restoration | `src/app.ts` |
| 6 | Session issuance | `src/app.ts` |
| 7 | Session revocation | `src/app.ts` |
| 8 | Ownership authorization | `src/app.ts` |
| 9 | Role authorization | `src/app.ts` |
| 10 | Executable composition root | `src/server.ts` |

## Verification

`src/app.test.ts`는 다음을 검사합니다.

- `401`과 `403`의 구분
- Cookie security attribute
- owner/admin authorization
- malicious·deceptive·missing Origin과 untrusted browser login 거부
- mutation 거부 뒤 state 보존
- logout 뒤 token revocation
- cookie와 server token의 동일 expiry
- app instance 간 session isolation

## Scope and limitations

Password verification, password hash, persistent session store, sliding expiration, session rotation, rate limit, TLS termination과 multi-instance revocation은 범위 밖입니다. 제공된 identity 두 개는 authorization boundary를 재현하기 위한 고정 fixture입니다.
