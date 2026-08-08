# Next.js 경로와 렌더링

Next.js App Router에서는 같은 저장소의 component라도 server에서만 실행되거나 browser bundle에 포함될 수 있습니다. 이 경계를 모르면 secret이 client에 노출되거나 browser API가 server에서 실패하고, 첫 HTML과 hydration 결과가 달라질 수 있습니다.

## 목표

- `app/`의 route, layout, dynamic segment와 special file을 구성합니다.
- Server Component와 Client Component의 기본 경계를 설명합니다.
- secret과 browser API를 올바른 실행 위치에 둡니다.
- 첫 HTML과 첫 client render를 일치시킵니다.
- 직접 URL 접근, 새로 고침과 production build를 검증합니다.

## file-system route

```text
app/
├── layout.tsx
├── page.tsx
├── loading.tsx
├── error.tsx
├── not-found.tsx
└── boards/
    └── [id]/
        └── page.tsx
```

`app/page.tsx`는 `/`, `app/boards/[id]/page.tsx`는 동적 `/boards/:id` 경로입니다. client-side link로만 이동해 보지 말고 주소창에서 직접 열고 새로 고침합니다. server가 모든 route를 제공하지 않는 정적 hosting 환경에서는 rewrite 설정이 별도로 필요할 수 있습니다.

## layout과 page

root layout은 html·body와 공통 UI를 제공합니다.

```tsx
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
```

layout에 모든 provider와 client state를 넣어 전체 tree를 client component로 만들지 않습니다. browser interaction이 필요한 작은 provider boundary만 분리합니다.

## Server Component가 기본입니다

App Router component는 기본적으로 server에서 렌더링됩니다. server에서는 database·private environment와 server-only package를 사용할 수 있지만 `window`, `document`, event handler와 client hook을 사용할 수 없습니다.

```tsx
export default async function BoardPage({ params }: Props) {
  const { id } = await params;
  const board = await loadBoard(id);
  return <BoardView initialBoard={board} />;
}
```

server에서 가져온 직렬화 가능한 data를 client component에 props로 전달할 수 있습니다.

## Client Component는 필요한 경계에만

```tsx
"use client";

export function BoardFilter() {
  const [query, setQuery] = useState("");
  return <input value={query} onChange={(event) => setQuery(event.target.value)} />;
}
```

`"use client"`는 “이 file과 그 client import graph가 browser에서 실행될 수 있음”을 뜻합니다. page 전체에 붙이는 대신 event·state·effect가 필요한 가장 작은 경계에 둡니다. server-only module을 client graph에서 import하지 않도록 합니다.

## 직렬화 경계

Server Component에서 Client Component로 전달하는 props는 전송 가능한 값이어야 합니다. DB connection, class instance와 function을 넘기지 않습니다. Date는 명시적인 ISO 문자열처럼 계약을 정하는 편이 안전합니다.

```ts
type BoardInitialData = {
  id: string;
  title: string;
  updatedAt: string;
};
```

## hydration 일치

server가 만든 HTML과 browser의 첫 render가 다르면 hydration warning과 UI 교체가 생깁니다.

피해야 할 첫 render 값:

- `Date.now()`
- `Math.random()`
- browser storage
- viewport 측정
- locale이 다른 server·client formatting

server가 값을 결정해 전달하거나, browser-only 값은 hydration 뒤 effect에서 읽고 초기 fallback을 명시합니다.

## loading, error와 not found

route segment의 비동기 data 경계에 `loading.tsx`, `error.tsx`, `not-found.tsx`를 둘 수 있습니다. 제품 오류를 모두 예외로 던져 framework error boundary에 보내지 않습니다. validation·권한·conflict 같은 예상 가능한 응답은 route 계약으로 처리합니다.

## navigation

내부 이동은 Next.js `Link`를 사용해 browser link 의미와 framework navigation을 함께 유지합니다.

```tsx
<Link href={`/boards/${board.id}`}>{board.title}</Link>
```

button과 programmatic router로 모든 이동을 만들지 않습니다. 사용자가 새 tab, 주소 복사와 기본 link 기능을 사용할 수 있어야 합니다.

## build는 별도 검증입니다

```sh
pnpm typecheck
pnpm build
```

TypeScript가 통과해도 server/client import 경계, route 생성과 build-time data 문제는 production build에서 실패할 수 있습니다. 개발 server만 실행하고 완료로 판단하지 않습니다.

## 실패 조건

- 모든 page에 `"use client"`를 붙입니다.
- client component가 server secret이나 DB module을 import합니다.
- 첫 render에서 시각·random·storage를 읽습니다.
- link 이동만 확인하고 동적 URL 직접 접근을 검사하지 않습니다.
- 개발 server 성공을 production build 성공으로 간주합니다.

## 연결 실습

[`React와 Next.js`](../../exercises/03-react-nextjs/README.md)는 `/profile/[handle]` 직접 접근, client request state와 production build를 검사합니다.

## 완료 기준

- App Router의 route와 dynamic segment를 만들 수 있습니다.
- server/client component를 선택한 이유를 설명합니다.
- browser API와 server secret의 위치를 구분합니다.
- hydration 첫 화면이 결정적입니다.
- 직접 URL 접근과 production build가 통과합니다.

## 다음 단계

화면이 HTTP·cache와 runtime validation 세부 사항에 직접 결합되지 않게 하는 방법은 [`Next.js 데이터 경계와 adapter`](05-nextjs-data-boundaries.md)에서 다룹니다.
