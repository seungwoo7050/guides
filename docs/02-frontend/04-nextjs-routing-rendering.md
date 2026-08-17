# Next.js 라우팅과 렌더링

Next.js App Router에서는 같은 저장소에 있는 컴포넌트라도 서버에서만 실행되거나 브라우저 번들에 포함될 수 있습니다. 이 경계를 잘못 이해하면 비밀값이 클라이언트에 노출되거나, 브라우저 API가 서버에서 실행되어 실패하거나, 서버가 만든 첫 HTML과 hydration 결과가 달라질 수 있습니다.

## 목표

- `app/` 디렉터리에 라우트, 레이아웃, 동적 세그먼트, 특수 파일을 구성합니다.
- Server Component와 Client Component의 기본 경계를 설명합니다.
- 비밀값과 브라우저 API를 올바른 실행 위치에 둡니다.
- 서버 HTML과 클라이언트의 첫 렌더링 결과를 일치시킵니다.
- URL 직접 접근, 새로고침, 프로덕션 빌드를 검증합니다.

## 파일 시스템 기반 라우팅

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

`app/page.tsx`는 `/` 경로를, `app/boards/[id]/page.tsx`는 동적 `/boards/:id` 경로를 담당합니다. 클라이언트 링크로 이동하는 경우만 확인하지 말고 주소창에서 경로를 직접 열고 새로고침해야 합니다. 서버가 모든 경로를 처리하지 않는 정적 호스팅 환경에서는 별도의 rewrite 설정이 필요할 수 있습니다.

## 레이아웃과 페이지

루트 레이아웃은 `html`·`body` 요소와 공통 UI를 제공합니다.

```tsx
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
```

레이아웃에 모든 Provider와 클라이언트 상태를 넣어 전체 트리를 Client Component로 만들지 않습니다. 브라우저 상호작용이 필요한 범위만 작은 Provider 경계로 분리합니다.

## 기본값은 Server Component입니다

App Router의 컴포넌트는 기본적으로 서버에서 렌더링됩니다. 서버에서는 데이터베이스, 비공개 환경 변수, 서버 전용 패키지를 사용할 수 있지만 `window`, `document`, 이벤트 처리기, 클라이언트 Hook은 사용할 수 없습니다.

```tsx
export default async function BoardPage({ params }: Props) {
  const { id } = await params;
  const board = await loadBoard(id);
  return <BoardView initialBoard={board} />;
}
```

서버에서 가져온 직렬화 가능한 데이터를 Client Component의 props로 전달할 수 있습니다.

## Client Component 경계는 필요한 곳에만 둡니다

```tsx
"use client";

export function BoardFilter() {
  const [query, setQuery] = useState("");
  return <input value={query} onChange={(event) => setQuery(event.target.value)} />;
}
```

`"use client"`는 해당 파일과 그 파일이 가져오는 클라이언트 의존성 그래프가 브라우저에서 실행될 수 있음을 뜻합니다. 페이지 전체에 붙이지 말고 이벤트·state·Effect가 필요한 가장 작은 경계에 둡니다. 클라이언트 의존성 그래프에서 서버 전용 모듈을 가져오지 않게 합니다.

## 직렬화 경계

Server Component에서 Client Component로 전달하는 props는 전송 가능한 값이어야 합니다. 데이터베이스 연결, 클래스 인스턴스, 함수를 전달해서는 안 됩니다. 날짜와 시각은 ISO 문자열처럼 명시적인 전송 형식을 정해 두는 편이 안전합니다.

```ts
type BoardInitialData = {
  id: string;
  title: string;
  updatedAt: string;
};
```

## hydration 결과를 일치시킵니다

서버가 만든 HTML과 브라우저의 첫 렌더링 결과가 다르면 hydration 경고가 발생하고 UI가 교체될 수 있습니다.

첫 렌더링에서 직접 사용하지 않아야 할 값은 다음과 같습니다.

- `Date.now()`
- `Math.random()`
- 브라우저 저장소 값
- 뷰포트 측정값
- 서버와 클라이언트의 로케일이 다를 수 있는 포맷 결과

서버가 값을 결정해 전달하거나, 브라우저에서만 알 수 있는 값은 hydration 이후 Effect에서 읽고 그전까지 사용할 초기 화면을 명시합니다.

## 로딩, 오류, 찾을 수 없음

라우트 세그먼트의 비동기 데이터 경계에 `loading.tsx`, `error.tsx`, `not-found.tsx`를 둘 수 있습니다. 예상 가능한 모든 제품 오류를 예외로 던져 프레임워크 오류 경계에 보내서는 안 됩니다. 입력 검증 실패, 권한 부족, 충돌처럼 예상 가능한 결과는 해당 라우트의 응답 계약으로 처리합니다.

## 탐색

내부 경로 이동에는 Next.js의 `Link`를 사용해 링크의 기본 의미와 프레임워크 탐색 기능을 함께 유지합니다.

```tsx
<Link href={`/boards/${board.id}`}>{board.title}</Link>
```

모든 이동을 버튼과 프로그래밍 방식의 라우터 호출로 구현하지 않습니다. 사용자가 새 탭에서 열기, 주소 복사 같은 링크의 기본 기능을 사용할 수 있어야 합니다.

## 빌드는 별도의 검증 단계입니다

```sh
pnpm typecheck
pnpm build
```

TypeScript 검사를 통과해도 서버·클라이언트 가져오기 경계, 라우트 생성, 빌드 시점 데이터 문제 때문에 프로덕션 빌드가 실패할 수 있습니다. 개발 서버가 실행된다는 사실만으로 완료를 판단해서는 안 됩니다.

## 흔한 오류

- 모든 페이지에 `"use client"`를 붙입니다.
- Client Component에서 서버 비밀값이나 데이터베이스 모듈을 가져옵니다.
- 첫 렌더링에서 현재 시각·난수·브라우저 저장소 값을 읽습니다.
- 링크를 통한 이동만 확인하고 동적 URL 직접 접근을 검사하지 않습니다.
- 개발 서버 실행 성공을 프로덕션 빌드 성공으로 간주합니다.

## 연결 실습

[`React와 Next.js`](../../exercises/03-react-nextjs/README.md)에서는 `/profile/[handle]` 직접 접근, 클라이언트 요청 상태, 프로덕션 빌드를 검사합니다.

## 완료 기준

- App Router의 라우트와 동적 세그먼트를 만들 수 있습니다.
- Server Component와 Client Component를 선택한 이유를 설명할 수 있습니다.
- 브라우저 API와 서버 비밀값을 서로 다른 실행 경계에 둡니다.
- 서버 HTML과 클라이언트의 첫 렌더링 결과가 일치합니다.
- URL 직접 접근과 프로덕션 빌드 검사를 통과합니다.

## 다음 단계

화면이 HTTP·캐시·런타임 검증의 세부 구현에 직접 결합되지 않게 하는 방법은 [`Next.js 데이터 경계와 어댑터`](05-nextjs-data-boundaries.md)에서 다룹니다.
