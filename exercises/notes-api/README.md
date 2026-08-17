# Notes API

Fastify, Zod와 repository port를 사용한 in-memory memo HTTP API입니다. Runtime validation, service-level uniqueness, stable HTTP error contract와 `app.inject()` 기반 test isolation을 완성된 backend artifact로 제공합니다.

## HTTP API

| Method | Path | Behavior |
| --- | --- | --- |
| `GET` | `/memos` | 모든 memo 조회 |
| `GET` | `/memos/:id` | 단일 memo 조회, 없으면 `404` |
| `POST` | `/memos` | memo 생성, invalid body `400`, duplicate title `409` |

Create body:

```json
{
  "title": "release notes",
  "body": "ship after verification"
}
```

`title`은 trim 이후 1–80자, `body`는 trim 이후 최대 500자입니다.

## Install and run

```sh
npm install
npm run typecheck
npm test
npm run dev
```

Server는 `0.0.0.0:4000`에서 요청을 받습니다.

## Architecture

```text
HTTP route
→ Zod runtime schema
→ use-case service
→ MemoRepository port
→ MemoryMemoRepository
```

`buildApp()`은 repository instance를 주입받습니다. 따라서 test마다 독립적인 state와 lifecycle을 가질 수 있고 실제 port를 열지 않고 `app.inject()`로 API contract를 검증할 수 있습니다.

## Major design decisions

- TypeScript type만으로 HTTP body를 신뢰하지 않고 Zod schema에서 type을 파생합니다.
- Duplicate title은 route가 아니라 service invariant로 표현합니다.
- 예상하지 못한 exception message를 response에 노출하지 않습니다.
- Repository instance가 자신의 in-memory row lifetime을 소유합니다.
- Test는 성공·실패 모두 `app.close()`를 호출합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | --- | --- |
| 1 | Runtime request contract | `src/contracts.ts` |
| 2 | Persistence port and row ownership | `src/repository.ts` |
| 3 | Duplicate-title invariant | `src/service.ts` |
| 4 | App factory and failure boundary | `src/app.ts` |
| 5 | Read-route translation | `src/app.ts` |
| 6 | Write-route orchestration | `src/app.ts` |
| 7 | Executable composition root | `src/server.ts` |

## Scope and limitations

Data는 process memory에만 저장됩니다. Database transaction, authentication, pagination, update/delete와 distributed uniqueness는 포함하지 않습니다. Process 재시작 시 memo가 사라집니다.
