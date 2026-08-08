# DOM, 이벤트, URL과 저장소

DOM은 HTML 원문 그 자체가 아니라 browser가 문서를 해석해 만든 객체 모델입니다. JavaScript는 DOM을 읽고 event를 처리해 화면을 바꿉니다. 문제는 화면 상태를 DOM·전역 변수·URL·storage 여러 곳에 중복하면 어느 값이 정본인지 모르게 된다는 점입니다.

## 목표

- DOM 요소를 찾고 안전하게 생성·갱신합니다.
- event의 기본 동작과 bubbling을 구분합니다.
- 화면 상태의 정본을 component memory, URL과 storage 중에서 선택합니다.
- history와 `popstate`로 뒤로 가기를 복원합니다.
- browser storage를 편의 기능으로 사용하되 보안 경계를 이해합니다.

## DOM을 찾고 실패를 드러냅니다

```js
const form = document.querySelector("#task-form");
if (!(form instanceof HTMLFormElement)) {
  throw new Error("task form이 필요합니다.");
}
```

TypeScript를 사용하지 않는 코드에서도 예상한 element가 실제로 존재하는지 확인할 수 있습니다. 무조건 non-null이라고 가정하면 markup 변경이 늦은 runtime 오류가 됩니다.

## 사용자 문자열은 text로 출력합니다

```js
const title = document.createElement("span");
title.textContent = userInput;
```

사용자가 입력한 문자열을 `innerHTML`에 연결하면 markup과 script로 해석될 수 있습니다. 정말 HTML을 받아야 하는 제품 요구가 있다면 제한된 정책과 검증된 sanitizer를 사용하지만, 일반 메모·제목은 text로 렌더링합니다.

여러 child를 교체할 때는 DOM node를 만들어 `replaceChildren`에 전달할 수 있습니다.

```js
list.replaceChildren(...tasks.map(renderTask));
```

## event와 기본 동작

form submit, link 이동, checkbox 변경에는 browser 기본 동작이 있습니다.

```js
form.addEventListener("submit", (event) => {
  event.preventDefault();
  // client-side 저장 또는 요청
});
```

`preventDefault`는 기본 동작만 막고 event 전파를 막지는 않습니다. bubbling을 이용하면 동적으로 생성되는 목록 child마다 listener를 따로 만들지 않고 parent에서 처리할 수 있습니다.

```js
list.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-task-id]");
  if (!button) return;
  removeTask(button.dataset.taskId);
});
```

`target`은 실제 시작 element, `currentTarget`은 listener가 등록된 element입니다.

## 상태의 정본을 선택합니다

| 상태 | 적합한 위치 | 예시 |
|---|---|---|
| 잠깐 열려 있는 UI | 메모리 | modal 열림, 입력 중 문자열 |
| 공유·bookmark·뒤로 가기 필요 | URL | 검색어, filter, 선택한 board |
| 새로 고침 편의, 공개되어도 됨 | localStorage | theme, 임시 draft, 마지막 board 힌트 |
| 권한과 업무 데이터 | server | 계정, role, 결제, board 내용 |

같은 filter를 전역 변수와 URL 양쪽에서 독립적으로 바꾸지 않습니다. URL을 정본으로 정했다면 render할 때 URL에서 다시 읽습니다.

## URL과 history

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

`pushState`는 새 history entry를 만들고 `replaceState`는 현재 entry를 바꿉니다. 사용자에게 의미 있는 상태 전환은 보통 push, 초기 정규화처럼 뒤로 가기 항목을 만들 필요가 없는 변경은 replace가 적합합니다.

뒤로 가기에서는 현재 URL을 다시 읽습니다.

```js
window.addEventListener("popstate", () => {
  render(readFilter());
});
```

`pushState` 자체는 `popstate`를 발생시키지 않습니다. 상태를 쓴 함수가 직접 render하거나 공통 동기화 함수를 호출해야 합니다.

## storage는 외부 입력입니다

사용자가 개발자 도구에서 값을 바꿀 수 있고 이전 버전 형식이 남을 수 있습니다.

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

key에 version을 포함하거나 저장 형식에 schema version을 둡니다. parsing 실패 때문에 전체 page가 시작하지 못하는 대신 안전한 기본값과 migration 정책을 정합니다.

localStorage는 같은 origin의 JavaScript가 읽을 수 있습니다. 다음을 저장하지 않습니다.

- session token
- password
- 장기 API key
- 서버에서만 알아야 할 secret
- 저장 자체가 불필요한 민감 개인정보

## render와 state 변경을 분리합니다

```js
let tasks = readTasks();

function add(title) {
  tasks = [...tasks, createTask(title)];
  persist(tasks);
  render(tasks, readFilter());
}
```

작은 앱에서는 이 구조로 충분합니다. 중요한 것은 DOM에서 다시 업무 상태를 긁어오거나, render 함수가 storage와 network까지 몰래 변경하지 않는 것입니다.

## 실패 조건

- 사용자 문자열을 `innerHTML`에 넣습니다.
- 모든 child마다 listener를 반복 등록하고 제거하지 않습니다.
- URL과 메모리 상태가 각각 filter를 소유합니다.
- `popstate` 없이 URL만 씁니다.
- storage 값을 TypeScript 형이나 이전 저장 코드만 믿고 바로 사용합니다.
- localStorage를 인증 저장소로 사용합니다.

## 연결 실습

[`첫 웹 애플리케이션`](../../exercises/00-first-web-app/README.md)은 task storage와 URL filter를, [`브라우저 UI`](../../exercises/02-browser/README.md)는 검색 history를 실제 browser로 검증합니다.

## 완료 기준

- DOM node를 생성하고 사용자 문자열을 text로 렌더링합니다.
- submit과 bubbling event의 목적을 설명할 수 있습니다.
- 상태별 정본을 URL·memory·storage·server 중에서 선택할 수 있습니다.
- 두 상태 변경 뒤 browser back으로 이전 화면을 복원합니다.
- 잘못된 storage 값에서 안전하게 복구합니다.

## 다음 단계

network 요청처럼 결과가 나중에 도착하는 작업은 [`비동기 작업과 fetch`](06-async-fetch-errors.md)에서 다룹니다.
