# React와 Next.js: 상태, 요청 수명과 경로

제어 입력과 목록을 구현하고 로딩·빈 결과·오류·성공 상태를 구분합니다. 빠르게 바뀌는 검색 요청의 수명을 관리하고, App Router의 동적 경로를 직접 열어도 동작하게 만듭니다.

## 선행 문서

- [`React 컴포넌트와 상태`](../../docs/02-frontend/01-react-components-state.md)
- [`폼과 목록`](../../docs/02-frontend/02-react-forms-lists.md)
- [`effect와 비동기 요청`](../../docs/02-frontend/03-react-effects-async.md)
- [`Next.js 경로와 렌더링`](../../docs/02-frontend/04-nextjs-routing-rendering.md)

## 작업 공간

저장소 루트에서 실행하면 canonical `skeleton/`이 비덮어쓰기 방식으로 `work/`에 복사됩니다.

```sh
pnpm workspace:create 03-react-nextjs
pnpm --dir exercises/03-react-nextjs/work install
```

## 구현 순서

1. 이름 변경 폼을 제어 입력으로 구현하고 빈 이름 제출을 막습니다.
2. 사용자 검색 상태를 `loading | success | error`의 판별 가능한 상태로 표현합니다.
3. effect에서 요청을 시작하고 정리 함수에서 `AbortController.abort()`를 호출합니다.
4. 빈 검색 결과와 오류를 서로 다른 화면으로 표현합니다.
5. 목록 key에는 배열 위치가 아니라 사용자 식별자를 사용합니다.
6. `/profile/[handle]` 동적 경로를 만들고 직접 새로 고침해도 내용을 얻습니다.

## Reference 구현 순서

아래 번호는 역사적 작성 순서가 아니라 하나의 Next.js reference가 공유하는 권장 construction order입니다. JSON config는 직접 주석하지 않고 이 표가 bootstrap 책임을 설명합니다.

| 번호 | 위치 | 책임 |
|---:|---|---|
| [Implementation 0] | `pnpm install`, `package.json`, `tsconfig.json`, `next.config.mjs` | Next.js·React·TypeScript 의존성과 App Router project contract를 준비합니다. |
| 1 | `app/layout.tsx`, `app/style.css` | server root layout과 전역 접근성·반응형 기반을 만듭니다. |
| 2 | `lib/fake-api.ts` | 취소 가능한 검색 경계와 성공·실패·지연을 모델링합니다. |
| 3 | `app/page.tsx` 상태 모델 | UI state owner와 판별 가능한 요청 상태를 정의합니다. |
| 4 | `app/page.tsx` effect | 요청 수명을 AbortController와 effect cleanup에 묶습니다. |
| 5 | `app/page.tsx` render | loading·error·empty·success를 배타적으로 투영합니다. |
| 6 | `app/profile/[handle]/page.tsx` | 직접 접근 가능한 server dynamic route를 완성합니다. |

## 검증

```sh
pnpm --dir exercises/03-react-nextjs/work typecheck
pnpm --dir exercises/03-react-nextjs/work build
node exercises/03-react-nextjs/tests/run.mjs exercises/03-react-nextjs/work
```

마지막 명령은 Next.js 개발 서버와 실제 Chromium을 시작합니다. `a` 검색의 느린 응답보다 `beta` 검색의 빠른 응답이 먼저 도착하는 상황을 만들고, 오래된 응답이 최신 화면을 덮지 않는지 확인합니다. 오류 상태와 동적 경로 직접 접근도 함께 검사합니다.

## 실패 주입

- effect 정리 함수의 `abort()`를 제거합니다.
- 로딩 상태를 빈 배열로 표현합니다.
- 목록 key를 배열 위치로 바꿉니다.
- 렌더링 중 `Date.now()`를 출력합니다.
- 브라우저 이벤트가 필요한 파일에서 `"use client"`를 제거합니다.

## Reference 비교

자동 검증을 모두 통과한 뒤에만 `diff -ru exercises/03-react-nextjs/work exercises/03-react-nextjs/reference`로 구현을 비교합니다. 파일 배치나 표현이 달라도 계약을 만족하면 올바른 구현이며, 차이를 선택한 이유를 설명합니다.

## 완료 기준

형 검사와 production build가 통과하고 실제 브라우저 검사가 요청 순서 역전, 오류 상태, 동적 경로를 통과해야 합니다. 코드에 특정 문자열이 존재하는지만으로 완료를 판정하지 않습니다.
