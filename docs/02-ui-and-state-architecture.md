# UI와 상태 구조

React 화면은 컴포넌트 트리만으로 설명되지 않는다. 어떤 상태가 가능하고, 그 상태의 정본이 어디에 있으며, 어떤 event가 상태를 바꾸는지를 함께 설계해야 한다.

## 목표

이 장을 마치면 다음을 수행할 수 있어야 한다.

- UI state, URL state, server state, draft와 파생 값을 구분한다.
- 서로 배타적인 화면 상태를 discriminated union으로 표현한다.
- 외부 응답을 `unknown`으로 받아 runtime contract에서 검증한다.
- Server Component와 Client Component의 책임을 실행 위치로 나눈다.
- component props에 저장 구조보다 허용된 의도와 상태를 표현한다.

연결 실습은 [Stage 02](../exercises/project-catalog/specs/02-ui-state-architecture.md)이다.

## 상태의 종류를 먼저 구분합니다

| 상태 종류 | 예 | 주 소유자 |
| --- | --- | --- |
| URL state | 검색어, status, page, 선택 tab | URL과 browser history |
| server state | 프로젝트 목록, version, 권한 | 서버와 request cache |
| UI state | menu 열림, 편집 mode, focus 대상 | 가장 가까운 Client Component |
| draft | 사용자가 아직 확정하지 않은 제목 | editor component |
| 지속 설정 | 언어, theme, column preference | server profile 또는 browser storage |
| 파생 값 | 필터 결과 수, 제출 가능 여부 | render 중 계산 |

같은 값을 두 소유자에게 복사하면 동기화 경로가 생긴다. URL에 있어야 할 검색 조건을 local state에만 두거나, server project와 edit draft를 같은 변수로 사용하면 navigation과 conflict recovery에서 값이 뒤섞인다.

다음 질문으로 위치를 정한다.

1. 새로 고침 뒤에도 남아야 하는가?
2. link로 공유하거나 뒤로 가기에 포함해야 하는가?
3. 서버가 최종 값을 결정하는가?
4. 사용자가 저장 전까지 자유롭게 편집해야 하는가?
5. 이미 가진 값에서 계산할 수 있는가?

## 모순되는 화면 상태를 제거합니다

다음 상태는 조합 수가 필요 이상으로 많다.

```ts
const [pending, setPending] = useState(false);
const [error, setError] = useState<string | null>(null);
const [projects, setProjects] = useState<Project[]>([]);
```

`pending === true`이고 error가 있으며 projects가 비어 있는 조합이 무엇을 뜻하는지 별도 규칙이 필요하다. 서로 배타적인 상태는 union으로 제한한다.

```ts
type CatalogState =
  | { status: "ready"; result: SearchResult }
  | { status: "empty"; result: SearchResult }
  | { status: "pending"; previous: SearchResult }
  | { status: "error"; message: string; previous: SearchResult };
```

이 모델은 다음 정책을 형에 기록한다.

- 새 검색 중에는 이전 결과를 유지한다.
- 빈 결과는 성공한 응답이며 error가 아니다.
- 실패해도 안전한 이전 결과와 입력을 유지한다.
- component는 `status`를 기준으로 모든 경우를 처리한다.

상태 전이를 순수 함수로 분리하면 DOM 없이 경계를 검사할 수 있다.

```ts
function completeSearch(result: SearchResult): CatalogState {
  return result.projects.length === 0
    ? { status: "empty", result }
    : { status: "ready", result };
}
```

## 외부 데이터는 타입 단언으로 신뢰하지 않습니다

TypeScript는 실행 중 API 응답을 검사하지 않는다.

```ts
const result = (await response.json()) as SearchResult;
```

이 코드는 누락 필드, 잘못된 status, 중복 id와 음수 page를 통과시킨다. 외부 입력은 `unknown`으로 받고 신뢰 경계에서 검사한다.

검증 대상:

- HTTP와 WebSocket 응답
- URL path와 query
- cookie와 browser storage
- `postMessage`
- CMS와 remote configuration
- file upload와 clipboard

```ts
export function parseSearchResult(value: unknown): SearchResult {
  if (!isRecord(value) || !Array.isArray(value.projects)) {
    throw new ContractError("프로젝트 검색 응답 형식이 올바르지 않습니다.");
  }

  const projects = value.projects.map(parseProject);
  const ids = new Set(projects.map((project) => project.id));
  if (ids.size !== projects.length) {
    throw new ContractError("프로젝트 식별자가 중복되었습니다.");
  }

  return {
    projects,
    total: parseNonNegativeInteger(value.total, "total"),
    page: parsePositiveInteger(value.page, "page"),
    pageSize: parsePositiveInteger(value.pageSize, "pageSize"),
  };
}
```

검증 뒤에는 화면에 알맞게 정규화한다. component 곳곳에서 API naming과 optional field를 해석하지 않는다.

```text
외부 응답
→ runtime validation
→ domain model
→ screen model
→ component
```

## Server Component를 기본 표현 경계로 둡니다

서버에 두기 좋은 책임:

- 데이터베이스·파일·비밀값 접근
- authentication과 authorization을 반영한 첫 화면
- 초기 HTML에 필요한 데이터 읽기
- 큰 라이브러리를 사용한 server-only 변환
- 사용자 event 없이 완성되는 표현

브라우저 실행이 필요한 책임:

- click, input, drag와 keyboard event
- focus, selection, scroll와 history
- `localStorage`, Clipboard와 observer API
- client-side request와 실시간 연결
- 사용자의 아직 확정되지 않은 draft

`"use client"`는 한 파일의 표시가 아니라 해당 module graph가 browser boundary에 들어갈 수 있다는 선언이다. page 전체를 client component로 바꾸기보다 상호작용이 필요한 가장 작은 경계에서 시작한다.

서버에서 client로 넘기는 값은 직렬화 가능해야 한다. 함수, database connection, class instance와 secret configuration을 props로 넘기지 않는다.

## 컴포넌트는 변경 이유로 나눕니다

줄 수보다 책임이 바뀌는 이유를 기준으로 분리한다.

- 데이터 읽기와 표현이 서로 다른 이유로 바뀐다.
- browser event와 server rendering 경계가 갈린다.
- 같은 keyboard interaction을 여러 화면에서 재사용한다.
- 접근성 계약을 독립적으로 보장해야 한다.
- 순수 state transition과 DOM 행동의 검사 방식이 다르다.

반대로 한 곳에서만 쓰는 짧은 표현을 모두 파일로 나누거나, props를 그대로 전달하는 wrapper를 여러 겹 만드는 것은 탐색 비용만 높인다.

각 component가 다음 문장을 하나로 답할 수 있는지 본다.

```text
이 컴포넌트가 독립적으로 결정하는 것은 무엇입니까?
```

## Props에는 허용된 의도를 담습니다

여러 boolean prop은 모순되는 조합을 허용한다.

```tsx
<Button primary danger compact />
```

허용된 의미를 union으로 제한한다.

```tsx
<Button tone="danger" size="compact" />
```

도메인 component의 event 이름은 DOM event보다 사용자 의도를 표현한다.

```ts
type ProjectEditorProps = {
  project: Project;
  onSave(command: RenameProjectCommand): Promise<RenameOutcome>;
  onCancel(): void;
};
```

기본 button처럼 DOM 계약 자체를 공개하는 component에는 `onClick`이 자연스럽다. 이름 변경 editor에는 `onSave`, `onCancel`이 더 분명하다.

## Server state와 draft를 분리합니다

사용자가 편집 중인 title은 서버에서 확정된 project title과 다르다.

```text
server project title  서버가 마지막으로 확정한 값
draft title           사용자가 현재 입력 중인 값
```

둘을 하나의 state로 사용하면 실패 복구가 모호해진다.

- 일반 실패: server project는 이전 값으로 되돌리되 draft는 보존한다.
- 409 conflict: server project는 응답의 최신 값으로 바꾸되 draft는 보존한다.
- 성공: server project를 응답 값으로 확정하고 editor를 닫을 수 있다.
- 취소: draft를 현재 server project로 되돌리고 editor를 닫는다.

충돌에서 draft를 버리면 사용자가 입력한 내용을 잃는다. 최신 서버 값과 사용자의 의도를 동시에 보여 주고 다시 판단할 수 있어야 한다.

## 접근성을 상태 계약에 포함합니다

접근성은 마지막 markup 점검이 아니다. 시간에 따른 상태 전이에 포함된다.

- 검색 form은 Enter 제출이 가능하다.
- loading, failure, save 결과는 live region에 전달된다.
- editor를 취소하거나 성공적으로 저장하면 처음의 “제목 수정” button으로 focus가 돌아간다.
- conflict와 일반 실패에서는 editor와 draft가 남고 focus도 입력에 머문다.
- error를 색 하나로만 표현하지 않는다.
- 목록과 article에는 안정적인 accessible name이 있다.

DOM 구조만 맞고 focus 흐름이 깨지면 일부 사용자는 작업을 끝낼 수 없다. 이 계약은 Stage 04의 실제 browser test로 다시 확인한다.

## Stage 02 완료 기준

```sh
pnpm exercise:verify:02
```

다음을 확인한다.

- query parser가 빈 값, 알 수 없는 status와 잘못된 page를 정규화한다.
- search result parser가 malformed payload와 duplicate id를 거절한다.
- UI state가 ready·empty·pending·error를 모순 없이 표현한다.
- pending·error 상태에서 이전 결과를 안전하게 선택할 수 있다.
- reference와 workspace가 production route type을 생성한 뒤 형 검사된다.

## 다음 단계

이제 화면 상태는 분명하지만 시간에 따라 요청과 변경 응답이 뒤섞일 수 있다. [Next.js 데이터·효과·동시성](03-nextjs-data-effects-and-concurrency.md)에서 history, request lifetime과 optimistic recovery를 구현한다.
