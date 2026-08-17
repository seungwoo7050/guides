# User Directory

React client state와 Next.js App Router의 server route를 결합한 사용자 디렉터리입니다. Search request lifecycle, stale response cancellation, discriminated state와 dynamic profile route를 작은 완성 애플리케이션으로 보여 줍니다.

## Features

- controlled search input
- `loading | success | error` discriminated union
- `AbortController`를 이용한 stale request 취소
- loading, error, empty, success UI 분리
- stable user ID를 React key로 사용
- `/profile/[handle]` dynamic server route
- document metadata와 English language declaration

## Install and run

```sh
npm install
npm run dev
```

Production verification:

```sh
npm run typecheck
npm run build
npm start
```

## Tests

Dependency install 없이 asynchronous adapter의 핵심 contract를 Node.js 22에서 검사할 수 있습니다.

```sh
npm run test:adapter
```

전체 UI와 route는 dependency install 뒤 production build 및 browser에서 확인합니다.

## Architecture

`lib/fake-api.ts`가 delay, failure와 cancellation lifecycle을 소유합니다. `app/page.tsx`는 request state union과 UI projection을 소유합니다. Dynamic segment는 `app/profile/[handle]/page.tsx`의 server component가 해석합니다.

## Major design decisions

- Boolean flag 여러 개 대신 discriminated union을 사용해 모순된 request state를 만들지 않습니다.
- Effect cleanup이 자신이 시작한 request를 abort하므로 늦은 이전 응답이 최신 검색 결과를 덮지 않습니다.
- API adapter를 UI 밖에 두어 delay, failure와 cancellation을 독립적으로 검사합니다.
- Profile route는 client-only state에 의존하지 않아 URL 직접 접근도 동작합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | --- | --- |
| 1 | Root document ownership | `app/layout.tsx` |
| 2 | Abortable search adapter | `lib/fake-api.ts` |
| 3 | Discriminated request state | `app/page.tsx` |
| 4 | Stale-request cancellation | `app/page.tsx` |
| 5 | Mutually exclusive UI projection | `app/page.tsx` |
| 6 | Dynamic profile route | `app/profile/[handle]/page.tsx` |

## Scope and limitations

User data는 in-memory fixture이며 authentication, remote API, pagination, cache와 persistent profile edit는 포함하지 않습니다. 의도적으로 `error` query가 adapter failure를 발생시켜 error UI를 재현합니다.
