# 프로젝트 합류와 첫 기능

처음 보는 React/Next.js 저장소에서 가장 먼저 해야 할 일은 파일을 늘리는 것이 아니라 **실행 경계와 검증 경로를 복원하는 일**이다. 첫 변경은 UI, URL, 서버 데이터, 오류와 검사 하나가 이어지는 작은 수직 기능이어야 한다.

## 목표

이 장을 마치면 다음을 수행할 수 있어야 한다.

- 저장소가 요구하는 runtime과 package manager를 그대로 재현한다.
- 개발 서버와 운영 서버의 차이를 확인한다.
- URL 하나가 어느 route, data function, component와 test를 통과하는지 추적한다.
- 기능 이름을 사용자가 확인할 수 있는 결과로 바꾼다.
- 첫 화면을 URL의 `searchParams`에서 복원한다.

연결 실습은 [Stage 01](../exercises/project-catalog/specs/01-project-onboarding.md)이다.

## 실행 계약부터 읽습니다

다음 파일은 단순 설정이 아니라 재현 가능한 실행 계약이다.

| 파일 | 확인할 것 |
| --- | --- |
| `.nvmrc`, `package.json#engines` | Node.js 지원 범위 |
| `packageManager` | package manager와 정확한 major/minor |
| lockfile | 의존성 해석 결과의 정본 |
| scripts | 개발·형 검사·단위 검사·빌드·E2E·smoke 경계 |
| `next.config.*` | output, header, redirect, image와 runtime 설정 |
| `.env.example` | 필요한 설정의 이름과 공개 가능 범위 |
| CI workflow | 저장소가 실제로 통과시키는 명령과 환경 |

저장소가 pnpm lockfile을 사용하면 임의로 npm install을 실행하지 않는다. package manager를 바꾸면 코드와 무관한 dependency graph가 함께 변하고, 실패 원인이 구현인지 환경인지 분리하기 어렵다.

이 저장소의 기준 실행은 다음이다.

```sh
nvm use
corepack enable
pnpm install --frozen-lockfile
pnpm check
pnpm build
pnpm test:e2e
```

개발 서버가 동작해도 production build가 실패할 수 있다. route type, server/client module 경계, 환경 변수 치환과 static optimization은 build 단계에서 다른 제약을 받는다. 첫날부터 `next build`와 실제 `next start` 경로를 한 번 통과한다.

## 실행 위치를 먼저 표시합니다

같은 저장소 안의 코드도 서로 다른 환경에서 실행된다.

```text
브라우저
- event handler
- focus와 history
- localStorage
- client-side fetch

Next.js 서버 runtime
- Server Component
- Route Handler
- 비밀 환경 변수
- 데이터 저장소 접근

빌드 시점
- module graph
- route/type 생성
- 공개 환경 변수 치환
- static/dynamic 판정
```

파일 이름만 보고 실행 위치를 단정하지 않는다. import graph와 사용 API를 함께 본다.

- `"use client"`가 시작하는 module graph는 browser bundle에 포함될 수 있다.
- Server Component가 client component에 넘기는 값은 직렬화할 수 있어야 한다.
- server-only 값은 client graph에서 import하지 않는다.
- `NEXT_PUBLIC_` 계열 값은 browser에 노출된다고 가정한다.
- Route Handler는 화면 route가 아니며 link의 목적지가 될 수 없다.

실행 위치를 잘못 추정하면 비밀값 노출, bundle 증가, hydration 오류와 production-only 실패로 이어진다.

## URL에서 사용자 흐름을 따라갑니다

기존 기능 하나를 다음 순서로 추적한다.

1. 사용자가 여는 URL을 확인한다.
2. 해당 segment의 `page.tsx`, `layout.tsx`, `loading.tsx`, `error.tsx`를 찾는다.
3. Server Component가 읽는 입력과 data function을 찾는다.
4. 외부 응답을 검증하고 화면 모델로 바꾸는 위치를 찾는다.
5. Client Component 경계와 전달 props를 확인한다.
6. 사용자 event가 호출하는 command와 HTTP 요청을 따라간다.
7. 성공·빈 결과·실패가 어디에서 화면 상태로 바뀌는지 찾는다.
8. 이 흐름을 고정하는 unit·integration·browser test를 실행한다.

디렉터리 설명만 읽는 것보다 실제 동작 하나를 끝까지 추적하면 저장소의 책임 배치와 관례가 빠르게 드러난다.

## 기능을 관찰 가능한 결과로 바꿉니다

“검색 추가”, “반응형 수정”, “캐시 적용”은 완료 여부가 불분명하다. 사용자, 조건, 행동과 관찰 결과를 포함한 문장으로 바꾼다.

```text
방문자가 프로젝트 목록에서 "network"를 검색하면
URL에 같은 조건이 기록되고 목록이 갱신됩니다.
새로 고침과 뒤로 이동 뒤에도 조건과 결과가 복원됩니다.
```

좋은 결과 문장은 구현 라이브러리에 의존하지 않는다. router API나 request library를 교체해도 같은 문장으로 동작을 검증할 수 있어야 한다.

### 입력

- URL, form, cookie, API 중 어디에서 값이 들어오는가?
- 빈 값, 알 수 없는 값과 지나치게 긴 값을 어떻게 처리하는가?
- server와 browser가 같은 규칙을 사용하는가?

### 출력

- 화면, URL, server state 가운데 무엇이 바뀌는가?
- 접근 가능한 이름과 status message는 무엇인가?
- 새로 고침과 link 공유 뒤 무엇이 복원되는가?

### 실패

- 빈 결과와 요청 실패를 어떻게 구분하는가?
- 기존 데이터와 사용자 입력을 유지하는가?
- 재시도, 취소, 안전한 이동 중 어떤 행동을 제공하는가?

### 시간

- 응답 순서가 바뀔 수 있는가?
- 같은 command가 반복될 수 있는가?
- 사용자 navigation 뒤 도착한 결과를 버려야 하는가?

## 첫 수직 기능의 크기를 제한합니다

프로젝트 목록의 첫 단계는 다음 정도면 충분하다.

1. `/`의 `searchParams`에서 `q`, `status`, `page`를 읽는다.
2. 알 수 없는 값은 안전한 기본값으로 정규화한다.
3. 서버에서 첫 결과를 읽는다.
4. Client Component에 직렬화 가능한 query와 result를 전달한다.
5. 새로 고침해도 입력과 첫 결과가 같은 조건을 나타낸다.

이 단계에서는 request cancellation, optimistic update와 performance budget을 구현하지 않는다. 먼저 서버 첫 화면과 URL이라는 정본을 확립한다.

```tsx
export default async function Page({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const raw = await searchParams;
  const query = parseProjectQuery(toURLSearchParams(raw));
  const initialResult = searchProjects(query);

  return <ProjectCatalog initialQuery={query} initialResult={initialResult} />;
}
```

구체적인 route signature는 프로젝트가 사용하는 Next.js 버전과 생성된 route type을 따른다. 핵심은 URL 입력을 server boundary에서 정규화하고 같은 값으로 첫 데이터와 입력 UI를 구성하는 것이다.

## 모르는 경계를 하나씩 줄입니다

첫 변경에서 authentication, cache, state library와 design system을 모두 바꾸지 않는다.

| 질문 | 가장 작은 실험 |
| --- | --- |
| 이 page는 server에서 실행되는가? | server와 browser를 구분한 로그를 한 번 확인한다. |
| query 기본값은 어디에서 정해지는가? | 잘못된 URL을 직접 열어 첫 입력과 결과를 본다. |
| client bundle에 무엇이 들어가는가? | 작은 client boundary를 만들고 production build를 비교한다. |
| navigation이 full reload인가? | Network와 component state를 관찰한다. |
| production에서만 실패하는가? | build한 서버를 실제 start 명령으로 실행한다. |

실험 전에 예상 결과를 적고, 실제 결과가 달랐던 지점만 기록한다.

```text
질문: 잘못된 status가 URL에 있으면 첫 화면은 무엇을 보여 줍니까?
예상: any로 정규화하고 전체 결과를 보여 줍니다.
관찰: client에서는 any였지만 server 결과는 빈 목록이었습니다.
결정: query parser를 server/client 공용 계약으로 이동합니다.
```

## 첫 변경의 증거

Stage 01을 완료했다고 판단하려면 다음 증거가 있어야 한다.

- query parser의 경계값 검사가 통과한다.
- `page.tsx`가 실제 `searchParams`를 읽는다.
- 첫 render의 input과 result가 같은 query를 사용한다.
- 형 검사가 production route type까지 생성한 뒤 통과한다.
- 구현 표시를 지우는 것만으로 검사를 우회할 수 없다.

```sh
pnpm exercise:verify:01
```

이 명령은 다음 장의 계약을 요구하지 않는다. 학습 단계의 검사는 현재까지의 책임만 고정해야 한다.

## 다음 단계

첫 화면이 URL에서 복원되면 다음 질문은 “화면에 가능한 상태를 어떻게 모순 없이 표현하고 외부 응답을 언제 신뢰할 것인가?”이다. [UI와 상태 구조](02-ui-and-state-architecture.md)로 이어간다.
