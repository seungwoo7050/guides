# React effect와 비동기 요청

effect는 “render 뒤 실행할 코드”를 아무거나 넣는 장소가 아닙니다. component를 network, timer, browser event, WebSocket 같은 **React 밖의 시스템과 동기화하는 경계**입니다. 계산 가능한 state를 맞추거나 event에 대한 직접 반응을 effect로 우회하면 수명과 순서가 복잡해집니다.

## 목표

- render 계산, event handler와 effect의 책임을 구분합니다.
- dependency가 의미하는 동기화 입력을 이해합니다.
- 요청, listener, timer와 connection을 cleanup합니다.
- 오래된 closure와 응답 순서 역전을 처리합니다.
- 개발 모드의 재실행에서도 안전한 effect를 만듭니다.

## effect가 필요하지 않은 경우

props와 state에서 계산 가능한 값은 render에서 계산합니다.

```tsx
const visible = tasks.filter((task) => filter === "all" || task.status === filter);
```

이를 effect로 별도 state에 복사하면 render 한 번 늦고 중복 정본이 됩니다.

```tsx
// 피합니다.
useEffect(() => setVisible(filterTasks(tasks, filter)), [tasks, filter]);
```

사용자가 button을 눌렀을 때 바로 일어나야 하는 작업은 event handler에 둡니다. `submitted` state를 true로 바꾸고 effect가 제출하도록 우회하면 중복 요청과 오류 전달이 복잡해집니다.

## 외부 시스템과 동기화

```tsx
useEffect(() => {
  document.title = `${board.title} · 협업 보드`;
}, [board.title]);
```

브라우저 전역 상태를 현재 React 상태와 맞춥니다. effect dependency는 “언제 실행할까”를 임의로 고르는 목록이 아니라 effect가 읽는 reactive 값입니다.

## 요청 수명

```tsx
useEffect(() => {
  const controller = new AbortController();
  setState({ status: "loading" });

  searchUsers(query, controller.signal)
    .then((users) => setState({ status: "ready", users }))
    .catch((error: unknown) => {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setState({ status: "error", message: toMessage(error) });
    });

  return () => controller.abort();
}, [query]);
```

query가 바뀌면 이전 effect cleanup이 실행된 뒤 새 요청이 시작됩니다. component unmount에서도 cleanup됩니다.

## 오래된 closure

callback은 만들어진 render의 값을 기억합니다.

```tsx
useEffect(() => {
  const timer = setInterval(() => console.log(count), 1_000);
  return () => clearInterval(timer);
}, []); // 계속 초기 count를 출력
```

dependency에 count를 넣으면 값마다 timer를 재생성합니다. 실제 요구가 “최신 값만 읽되 timer 수명은 유지”라면 ref나 effect event 패턴을 검토합니다. dependency를 거짓으로 비워 lint만 피하지 않습니다.

## listener cleanup

```tsx
useEffect(() => {
  function onPopState() {
    setFilter(readFilter(location.href));
  }
  window.addEventListener("popstate", onPopState);
  return () => window.removeEventListener("popstate", onPopState);
}, []);
```

등록과 해제가 동일한 function identity를 사용해야 합니다. inline function을 각각 만들면 제거되지 않습니다.

## timer와 WebSocket

```tsx
useEffect(() => {
  const socket = new WebSocket(url);
  const heartbeat = setInterval(() => sendPing(socket), 20_000);

  return () => {
    clearInterval(heartbeat);
    socket.close(1000, "component closed");
  };
}, [url]);
```

실제 connection 관리가 복잡하면 component effect에 모든 protocol을 넣지 않고 별도 client object와 adapter로 분리합니다. effect는 client 수명을 component에 연결합니다.

## Strict Mode와 재실행

개발 환경에서 setup·cleanup이 추가로 실행될 수 있습니다. 올바른 effect는 setup 뒤 cleanup, 다시 setup해도 외부 자원이 중복되지 않습니다. “한 번만 실행되어야 한다”는 가정으로 전역 flag를 두면 실제 route 변경·재연결 계약을 숨길 수 있습니다.

## cache와 framework data boundary

모든 server fetch를 client effect로 시작할 필요는 없습니다. Next.js server component, route handler 또는 data library가 수명·dedupe·cache를 담당할 수 있습니다. effect가 필요한 이유가 browser interaction인지, server rendering으로 옮길 수 있는지 먼저 확인합니다.

## 실패 조건

- props에서 계산 가능한 값을 effect로 state에 복사합니다.
- event action을 flag state와 effect로 우회합니다.
- dependency를 줄이기 위해 실제 읽는 값을 숨깁니다.
- 요청·listener·timer·socket을 cleanup하지 않습니다.
- AbortError와 실제 오류를 모두 무시합니다.
- development 재실행에서 subscription이 중복됩니다.

## 연결 실습

[`React와 Next.js`](../../exercises/03-react-nextjs/README.md)는 느린 이전 검색과 빠른 최신 검색을 실제 browser에서 재현해 cleanup 계약을 확인합니다.

## 완료 기준

- render 계산, event handler와 effect를 구분합니다.
- effect가 읽는 reactive 값을 dependency에 반영합니다.
- 요청·listener·timer와 connection을 cleanup합니다.
- 오래된 closure와 응답 순서 문제를 설명할 수 있습니다.
- setup→cleanup→setup에서 외부 자원이 중복되지 않습니다.

## 다음 단계

React code가 Next.js에서 server와 browser 중 어디서 실행되는지는 [`Next.js 경로와 렌더링`](04-nextjs-routing-rendering.md)에서 다룹니다.
