# React Effect와 비동기 요청

Effect는 렌더링이 끝난 뒤 실행할 코드를 모두 넣는 장소가 아닙니다. 컴포넌트를 네트워크, 타이머, 브라우저 이벤트, WebSocket처럼 **React 외부의 시스템과 동기화하는 경계**입니다. 계산 가능한 상태를 맞추거나 사용자 이벤트에 직접 반응할 코드를 Effect로 우회하면 생명주기와 실행 순서가 불필요하게 복잡해집니다.

## 목표

- 렌더링 계산, 이벤트 처리기, Effect의 책임을 구분합니다.
- 의존성 배열이 나타내는 동기화 입력을 이해합니다.
- 요청, 이벤트 리스너, 타이머, 연결을 정리합니다.
- 오래된 클로저와 응답 순서 역전을 처리합니다.
- 개발 모드에서 Effect가 다시 실행되어도 안전하게 만듭니다.

## Effect가 필요하지 않은 경우

props와 state에서 계산할 수 있는 값은 렌더링 중에 계산합니다.

```tsx
const visible = tasks.filter((task) => filter === "all" || task.status === filter);
```

이 값을 Effect에서 별도 state로 복사하면 화면 반영이 한 번 늦어지고 같은 값을 두 곳에서 관리하게 됩니다.

```tsx
// 피합니다.
useEffect(() => setVisible(filterTasks(tasks, filter)), [tasks, filter]);
```

사용자가 버튼을 눌렀을 때 즉시 실행해야 하는 작업은 이벤트 처리기에 둡니다. `submitted` state를 `true`로 바꾼 뒤 Effect에서 제출하도록 우회하면 중복 요청과 오류 전달을 다루기 어려워집니다.

## 외부 시스템과 동기화

```tsx
useEffect(() => {
  document.title = `${board.title} · 협업 보드`;
}, [board.title]);
```

이 Effect는 브라우저의 전역 상태를 현재 React 상태와 동기화합니다. 의존성 배열은 실행 시점을 임의로 고르는 목록이 아니라 Effect가 읽는 반응형 값의 목록입니다.

## 요청 생명주기

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

`query`가 바뀌면 이전 Effect의 정리 함수가 실행된 뒤 새 요청을 시작합니다. 컴포넌트가 언마운트될 때도 정리 함수가 실행됩니다.

## 오래된 클로저

콜백은 자신이 만들어진 렌더링 시점의 값을 기억합니다.

```tsx
useEffect(() => {
  const timer = setInterval(() => console.log(count), 1_000);
  return () => clearInterval(timer);
}, []); // 계속 초기 count를 출력
```

의존성 배열에 `count`를 넣으면 값이 바뀔 때마다 타이머를 다시 만듭니다. 요구사항이 “타이머는 유지하되 최신 값만 읽기”라면 ref나 Effect Event 패턴을 검토합니다. 린트 오류를 피하려고 실제로 읽는 값을 의존성 배열에서 숨겨서는 안 됩니다.

## 이벤트 리스너 정리

```tsx
useEffect(() => {
  function onPopState() {
    setFilter(readFilter(location.href));
  }
  window.addEventListener("popstate", onPopState);
  return () => window.removeEventListener("popstate", onPopState);
}, []);
```

등록과 해제에는 같은 함수 객체를 사용해야 합니다. 두 위치에 각각 인라인 함수를 작성하면 등록한 리스너를 제거할 수 없습니다.

## 타이머와 WebSocket

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

연결 관리가 복잡하다면 컴포넌트의 Effect에 프로토콜 전체를 넣지 말고 별도의 클라이언트 객체와 어댑터로 분리합니다. Effect는 해당 클라이언트의 생명주기를 컴포넌트에 연결하는 역할만 담당합니다.

## Strict Mode와 재실행

개발 환경에서는 설정 함수와 정리 함수가 추가로 실행될 수 있습니다. 올바른 Effect는 설정 후 정리하고 다시 설정해도 외부 자원이 중복되지 않습니다. “한 번만 실행해야 한다”는 이유로 전역 플래그를 두면 실제 라우트 변경과 재연결에서 필요한 생명주기를 숨길 수 있습니다.

## 캐시와 프레임워크 데이터 경계

모든 서버 요청을 클라이언트 Effect에서 시작할 필요는 없습니다. Next.js Server Component, Route Handler, 데이터 라이브러리가 생명주기·중복 제거·캐시를 담당할 수 있습니다. 브라우저 상호작용 때문에 Effect가 필요한지, 서버 렌더링 경계로 옮길 수 있는지 먼저 확인합니다.

## 흔한 오류

- props에서 계산할 수 있는 값을 Effect로 state에 복사합니다.
- 사용자 이벤트를 플래그 state와 Effect를 거쳐 처리합니다.
- 의존성을 줄이려고 Effect가 실제로 읽는 값을 숨깁니다.
- 요청·이벤트 리스너·타이머·소켓을 정리하지 않습니다.
- `AbortError`와 실제 오류를 모두 무시합니다.
- 개발 모드에서 Effect가 다시 실행될 때 구독이 중복됩니다.

## 연결 실습

[`React와 Next.js`](../../exercises/03-react-nextjs/README.md)에서는 느린 이전 검색과 빠른 최신 검색의 완료 순서를 실제 브라우저에서 뒤집어 정리 계약을 확인합니다.

## 완료 기준

- 렌더링 계산, 이벤트 처리기, Effect의 역할을 구분합니다.
- Effect가 읽는 반응형 값을 의존성 배열에 반영합니다.
- 요청·이벤트 리스너·타이머·연결을 정리합니다.
- 오래된 클로저와 응답 순서 문제를 설명할 수 있습니다.
- 설정→정리→재설정 과정에서 외부 자원이 중복되지 않습니다.

## 다음 단계

React 코드가 Next.js에서 서버와 브라우저 중 어디에서 실행되는지는 [`Next.js 라우팅과 렌더링`](04-nextjs-routing-rendering.md)에서 설명합니다.
