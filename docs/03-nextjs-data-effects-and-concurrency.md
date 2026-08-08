# Next.js 데이터·효과·동시성

브라우저 화면에는 URL, server render, client request, 사용자 draft와 변경 응답이 서로 다른 시점에 도착한다. 비동기 코드는 동시에 실행되지 않더라도 **완료 순서가 시작 순서와 다를 수 있다.** 각 작업의 수명과 결과 반영 조건을 명시해야 최신 사용자 의도가 화면의 정본으로 남는다.

## 목표

이 장을 마치면 다음을 수행할 수 있어야 한다.

- URL query를 parsing과 serialization의 단일 계약으로 관리한다.
- browser history와 component state를 양방향으로 복원한다.
- request cancellation과 generation guard를 함께 사용한다.
- malformed response와 HTTP failure를 구분하고 이전 결과를 보존한다.
- optimistic update의 success, generic failure, version conflict를 각각 수렴시킨다.
- effect를 외부 시스템과의 동기화에만 사용하고 cleanup을 보장한다.

연결 실습은 [Stage 03](../exercises/project-catalog/specs/03-data-effects-concurrency.md)이다.

## URL을 공유 가능한 정본으로 사용합니다

검색어, status, page처럼 navigation과 함께 복원되어야 하는 값은 URL에 둔다.

URL state의 장점:

- 새로 고침 뒤 복원된다.
- link로 공유할 수 있다.
- browser back/forward와 자연스럽게 연결된다.
- server render와 client navigation이 같은 입력을 사용할 수 있다.

query를 읽는 함수와 쓰는 함수가 다른 기본값을 사용하면 URL이 왕복할 때 값이 달라진다. parsing과 serialization을 같은 module에 둔다.

```ts
const query = parseProjectQuery(new URLSearchParams(location.search));
const params = toProjectSearchParams(query);
```

기본값은 URL에서 생략해도 된다. 단, 다시 parse했을 때 동일한 query가 나와야 한다.

```text
parse(serialize(query)) = normalized query
```

알 수 없는 parameter를 모두 보존할지, 이 화면이 소유한 parameter만 쓸지도 결정한다. 독립 widget들이 URL을 공유한다면 다른 widget의 parameter를 지우지 않도록 현재 query string을 기반으로 갱신한다.

## History 변경 뒤 화면을 다시 동기화합니다

`history.pushState`와 `replaceState`는 URL을 바꾸지만 자동으로 application state를 바꾸지 않는다. 반대로 `popstate`는 사용자가 back/forward를 했다는 신호이므로 URL을 다시 parse하고 데이터 요청을 시작해야 한다.

```ts
useEffect(() => {
  function handlePopState() {
    const next = parseProjectQuery(new URLSearchParams(window.location.search));
    setDraftQuery(next.q);
    setDraftStatus(next.status);
    void runSearch(next, { writeHistory: false });
  }

  window.addEventListener("popstate", handlePopState);
  return () => window.removeEventListener("popstate", handlePopState);
}, []);
```

실제 구현에서는 `runSearch`의 identity와 stale closure를 함께 검토한다. effect dependency를 피하려고 중요한 값을 누락하지 않는다. 외부 system 구독과 cleanup을 같은 effect에서 볼 수 있어야 한다.

## 요청 취소만으로는 충분하지 않습니다

새 검색이 시작되면 이전 `AbortController`를 중단할 수 있다.

```ts
activeController?.abort();
const controller = new AbortController();
```

하지만 취소가 다음을 보장하지는 않는다.

- server가 이미 시작한 작업 전체가 되돌아간다.
- custom promise와 callback이 모두 취소를 지원한다.
- response parsing 직전에 취소된 결과가 절대 도착하지 않는다.
- browser cache나 intermediary가 이미 응답을 전달하지 않는다.

따라서 결과 반영 전에 최신 generation인지도 확인한다.

```ts
const request = coordinator.begin();
const response = await fetch(url, { signal: request.signal });
const result = parseSearchResult(await response.json());

if (coordinator.isCurrent(request.generation)) {
  setState(completeCatalogRequest(result));
}
```

`AbortController`는 불필요한 작업을 줄이고, generation guard는 늦은 callback의 화면 반영을 막는다. 둘은 대체 관계가 아니라 서로 다른 실패 경계를 막는다.

## 요청 생명주기를 독립된 객체로 표현합니다

component 안에 sequence와 controller 조작을 흩어 놓으면 취소·새 요청·unmount 조건이 어긋난다.

```ts
type CoordinatedRequest = {
  generation: number;
  signal: AbortSignal;
};

function createRequestCoordinator() {
  let generation = 0;
  let controller: AbortController | null = null;

  return {
    begin(): CoordinatedRequest {
      controller?.abort();
      controller = new AbortController();
      generation += 1;
      return { generation, signal: controller.signal };
    },
    isCurrent(candidate: number) {
      return candidate === generation;
    },
    cancel() {
      controller?.abort();
      controller = null;
      generation += 1;
    },
  };
}
```

이 coordinator는 React를 모르는 순수한 수명 객체이므로 DOM 없이 검사할 수 있다.

- 두 번째 `begin`이 첫 signal을 abort한다.
- 첫 generation은 더 이상 current가 아니다.
- `cancel` 뒤 기존 generation을 거절한다.
- 다음 `begin`은 새 signal과 generation을 만든다.

## HTTP 성공과 데이터 계약 성공을 구분합니다

`response.ok`가 true여도 body가 application contract와 다를 수 있다.

```ts
const raw: unknown = await response.json();
const result = parseSearchResult(raw);
```

오류 종류를 구분한다.

| 실패 | 예 | 화면 정책 |
| --- | --- | --- |
| 사용자 취소 | 새 검색이 이전 요청 중단 | 오류 메시지 없음 |
| HTTP 실패 | 503, 401, 403 | 이전 안전 데이터와 다음 행동 유지 |
| JSON parsing 실패 | 잘린 응답 | 외부 계약 오류로 처리 |
| runtime contract 실패 | field 누락, 중복 id | 잘못된 응답을 화면에 반영하지 않음 |
| stale result | 이전 generation 결과 | 조용히 폐기 |

malformed payload를 TypeScript assertion으로 통과시키면 화면 state가 깨지고 더 먼 component에서 원인을 잃는다. 신뢰 경계에서 즉시 오류로 바꾼다.

## Optimistic update의 확정 시점을 정합니다

제목 변경은 되돌릴 수 있고 결과가 명확하므로 화면에 먼저 반영할 수 있다.

```text
현재 server project와 draft 보관
→ 예상 제목을 목록에 표시
→ version을 포함해 PATCH
→ 응답 종류에 따라 확정 또는 복구
```

### 성공

- 응답의 project를 runtime validation한다.
- server가 보정한 title과 새 version을 최종 값으로 사용한다.
- editor를 닫고 edit button으로 focus를 복원한다.
- live region에 성공을 알린다.

### 일반 실패

- optimistic project를 이전 server project로 되돌린다.
- 사용자가 입력한 draft는 유지한다.
- editor를 열어 두고 입력 focus를 유지한다.
- 재시도 가능 여부를 설명한다.

### 409 Conflict

- 응답의 최신 server project를 목록에 반영한다.
- 사용자 draft는 유지한다.
- editor를 열어 두고 최신 값과 draft의 차이를 다시 판단하게 한다.
- conflict를 일반 network failure와 다른 문장으로 설명한다.

```text
서버 최신 제목: 배포 흐름 분석
내가 입력한 제목: 릴리스 흐름 분석
```

충돌 응답에서 이전 server value로 단순 rollback하면 이미 다른 사용자가 저장한 최신 값을 다시 숨기게 된다.

## 연속 변경의 경쟁도 고려합니다

한 항목에 save 요청을 여러 개 보낼 수 있다면 다음을 정한다.

- 저장 중 입력을 잠그는가?
- 새 save가 이전 save를 취소할 수 있는가?
- server command가 idempotent한가?
- 각 요청의 optimistic patch를 어떤 순서로 되돌리는가?
- 성공 응답이 현재 draft보다 오래된 의도인지 어떻게 판단하는가?

실습은 한 editor에서 저장 중 추가 제출을 막아 문제 범위를 제한한다. 더 복잡한 editor에서는 mutation별 command id와 base version을 관리해야 한다.

## Effect는 외부 시스템 동기화에만 사용합니다

다음 값은 effect로 다시 저장하지 않는다.

```tsx
const visibleProjects = projects.filter((project) => matches(project, query));
```

props와 state에서 render 중 계산할 수 있는 값을 effect로 복사하면 한 render 늦게 동기화되고 source가 둘이 된다.

Effect가 필요한 대상:

- browser history event 구독
- request abort on unmount
- WebSocket과 observer 연결
- imperative widget 생성·정리
- document title 같은 외부 상태

각 effect에서 세 가지가 보여야 한다.

```text
무엇과 연결하는가?
언제 다시 연결하는가?
어떻게 정리하는가?
```

개발 환경에서 setup → cleanup → setup이 반복돼도 안전해야 한다.

## 실시간 데이터로 확장할 때

이 실습은 HTTP 요청만 사용하지만 같은 원리가 WebSocket에도 적용된다.

```text
연결
→ 현재 version의 snapshot
→ 이후 event 적용
→ sequence 누락 또는 reconnect 감지
→ 새 snapshot으로 수렴
```

event만 무한히 이어 붙이면 연결이 끊긴 동안 놓친 상태를 알 수 없다. snapshot, event sequence와 현재 local draft를 별도로 관리한다.

## Stage 03 완료 기준

```sh
pnpm exercise:verify:03
```

다음을 확인한다.

- 제출한 query가 URL에 기록되고 reload·back 뒤 복원된다.
- 새 request가 이전 signal을 abort한다.
- 늦게 풀린 이전 response가 화면을 덮지 않는다.
- malformed response는 이전 결과를 유지한 error state로 바뀐다.
- optimistic success는 server response로 확정된다.
- 일반 실패는 server state를 rollback하지만 draft를 보존한다.
- 409 conflict는 최신 server value와 local draft를 함께 보존한다.
- production build 뒤 실제 browser에서 결정적으로 재현된다.

## 다음 단계

기능이 시간 차이에도 수렴하면 이제 이 계약이 keyboard, focus, viewport와 performance budget에서도 유지되는지 확인해야 한다. [테스트·접근성·성능](04-testing-accessibility-and-performance.md)으로 이어간다.
