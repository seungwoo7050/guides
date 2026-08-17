# DOM, 이벤트, URL과 저장소

DOM은 HTML 원문이 아니라 브라우저가 문서를 해석해 만든 객체 모델입니다. JavaScript는 DOM을 읽고 이벤트를 처리해 화면을 변경합니다. 화면 상태를 DOM·전역 변수·URL·브라우저 저장소에 중복해서 보관하면 어떤 값이 기준인지 판단하기 어려워집니다.

## 목표

- DOM 요소를 찾고 안전하게 생성·변경합니다.
- 이벤트의 기본 동작과 버블링을 구분합니다.
- 화면 상태의 기준을 메모리, URL, 브라우저 저장소 중에서 선택합니다.
- History API와 `popstate`로 뒤로 가기 동작을 복원합니다.
- 브라우저 저장소를 편의 기능으로 사용하되 보안 한계를 이해합니다.

## DOM 요소를 확인하고 오류를 즉시 드러냅니다

```js
const form = document.querySelector("#task-form");
if (!(form instanceof HTMLFormElement)) {
  throw new Error("task form이 필요합니다.");
}
```

TypeScript를 사용하지 않아도 찾은 요소가 예상한 타입인지 확인할 수 있습니다. 요소가 항상 존재한다고 가정하면 마크업이 변경되었을 때 관련 없는 위치에서 런타임 오류가 발생할 수 있습니다.

## 사용자 문자열은 텍스트로 출력합니다

```js
const title = document.createElement("span");
title.textContent = userInput;
```

사용자가 입력한 문자열을 `innerHTML`에 대입하면 문자열이 HTML 마크업이나 스크립트로 해석될 수 있습니다. 제품 요구사항상 HTML 입력을 허용해야 한다면 제한된 허용 정책과 검증된 새니타이저를 사용해야 합니다. 일반적인 메모와 제목은 텍스트로 렌더링합니다.

여러 자식 요소를 한 번에 교체할 때는 DOM 노드를 만든 뒤 `replaceChildren`에 전달할 수 있습니다.

```js
list.replaceChildren(...tasks.map(renderTask));
```

## 이벤트와 기본 동작

폼 제출, 링크 이동, 체크박스 변경에는 브라우저가 제공하는 기본 동작이 있습니다.

```js
form.addEventListener("submit", (event) => {
  event.preventDefault();
  // 클라이언트 저장 또는 요청
});
```

`preventDefault`는 기본 동작만 막으며 이벤트 전파는 막지 않습니다. 이벤트 버블링을 활용하면 동적으로 생성되는 목록의 각 자식 요소에 리스너를 따로 등록하지 않고 부모 요소에서 처리할 수 있습니다.

```js
list.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-task-id]");
  if (!button) return;
  removeTask(button.dataset.taskId);
});
```

`target`은 이벤트가 실제로 시작된 요소이고, `currentTarget`은 현재 리스너가 등록된 요소입니다.

## 상태의 기준 위치를 선택합니다

| 상태 | 적합한 위치 | 예시 |
|---|---|---|
| 일시적인 UI 상태 | 메모리 | 모달 열림 여부, 입력 중인 문자열 |
| 공유·북마크·뒤로 가기가 필요한 상태 | URL | 검색어, 필터, 선택한 보드 |
| 새로 고침 후 복원할 편의 정보이며 공개되어도 되는 상태 | `localStorage` | 테마, 임시 초안, 마지막 보드 힌트 |
| 권한과 도메인 데이터 | 서버 | 계정, 역할, 결제, 보드 내용 |

같은 필터 값을 전역 변수와 URL 양쪽에서 독립적으로 변경해서는 안 됩니다. URL을 기준으로 정했다면 화면을 렌더링할 때도 URL에서 값을 다시 읽습니다.

## URL과 History API

```js
function readFilter() {
  const value = new URL(location.href).searchParams.get("filter");
  return value === "done" ? "done" : "all";
}

function writeFilter(filter) {
  const url = new URL(location.href);
  if (filter === "all") url.searchParams.delete("filter");
  else url.searchParams.set("filter", filter);
  history.pushState(null, "", url);
  render(readFilter());
}
```

`pushState`는 방문 기록에 새 항목을 추가하고, `replaceState`는 현재 항목을 교체합니다. 사용자가 되돌아갈 필요가 있는 상태 전환에는 일반적으로 `pushState`를 사용합니다. 초기 URL 정규화처럼 별도 기록을 남길 필요가 없는 변경에는 `replaceState`가 적합합니다.

뒤로 가기나 앞으로 가기가 실행되면 현재 URL을 다시 읽습니다.

```js
window.addEventListener("popstate", () => {
  render(readFilter());
});
```

`pushState`를 호출하는 것만으로는 `popstate` 이벤트가 발생하지 않습니다. 상태를 기록한 함수가 직접 화면을 렌더링하거나 공통 동기화 함수를 호출해야 합니다.

## 브라우저 저장소의 값도 외부 입력입니다

사용자는 개발자 도구에서 저장된 값을 바꿀 수 있고, 이전 버전의 저장 형식이 남아 있을 수도 있습니다.

```js
function readTasks() {
  try {
    const value = JSON.parse(localStorage.getItem("tasks.v1") ?? "[]");
    return Array.isArray(value) ? value.filter(isTask) : [];
  } catch {
    return [];
  }
}
```

키 이름에 버전을 포함하거나 저장 데이터 안에 스키마 버전을 둡니다. 파싱에 실패했을 때 페이지 전체가 시작되지 않는 대신 안전한 기본값과 마이그레이션 정책을 적용합니다.

`localStorage`는 같은 출처(origin)에서 실행되는 JavaScript가 읽을 수 있습니다. 다음 값은 저장하지 않습니다.

- 세션 토큰
- 비밀번호
- 장기 API 키
- 서버만 알아야 하는 비밀값
- 저장할 필요가 없는 민감한 개인정보

## 렌더링과 상태 변경을 분리합니다

```js
let tasks = readTasks();

function add(title) {
  tasks = [...tasks, createTask(title)];
  persist(tasks);
  render(tasks, readFilter());
}
```

작은 애플리케이션에서는 이 정도 구조로도 충분합니다. 중요한 점은 DOM에서 도메인 상태를 다시 추출하지 않고, `render` 함수가 브라우저 저장소나 네트워크 상태까지 암묵적으로 변경하지 않게 하는 것입니다.

## 흔한 오류

- 사용자 문자열을 `innerHTML`에 직접 넣습니다.
- 각 자식 요소마다 리스너를 반복해서 등록하고 정리하지 않습니다.
- URL과 메모리가 같은 필터 상태를 각각 소유합니다.
- `popstate` 처리를 구현하지 않고 URL만 변경합니다.
- TypeScript 타입이나 과거의 저장 코드만 믿고 저장소 값을 바로 사용합니다.
- `localStorage`를 인증 정보 저장소로 사용합니다.

## 연결 실습

[`첫 웹 애플리케이션`](../../exercises/00-first-web-app/README.md)에서는 작업 저장과 URL 필터를, [`브라우저 UI`](../../exercises/02-browser/README.md)에서는 검색 방문 기록을 실제 브라우저에서 검증합니다.

## 완료 기준

- DOM 노드를 생성하고 사용자 문자열을 텍스트로 렌더링합니다.
- 폼 제출 이벤트와 이벤트 버블링의 용도를 설명할 수 있습니다.
- 상태별 기준 위치를 URL·메모리·브라우저 저장소·서버 중에서 선택할 수 있습니다.
- 상태를 두 번 변경한 뒤 브라우저의 뒤로 가기로 이전 화면을 복원합니다.
- 잘못된 저장소 값이 있어도 안전하게 복구합니다.

## 다음 단계

먼저 [`첫 웹 애플리케이션`](../../exercises/00-first-web-app/README.md)과 [`브라우저 UI`](../../exercises/02-browser/README.md)의 `work/`에서 DOM·URL·저장소 계약을 구현하고 검증합니다. 두 실습의 `reference/`와 비교를 마친 뒤, 완료 순서를 예측할 수 없는 작업을 [`비동기 작업과 fetch`](06-async-fetch-errors.md)에서 다룹니다.
