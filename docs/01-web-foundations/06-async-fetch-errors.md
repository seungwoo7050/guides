# 비동기 작업과 `fetch`

비동기 코드의 핵심은 기다리는 문법이 아니라 **작업의 시작·완료·실패·취소를 관리하고, 도착한 결과가 여전히 유효한지 판단하는 것**입니다. 사용자가 검색어를 빠르게 바꾸면 먼저 시작한 요청이 나중에 완료될 수 있습니다. `await`를 사용한다고 이러한 순서 문제가 자동으로 해결되지는 않습니다.

## 목표

- Promise와 `async`·`await`의 결과 전달 방식을 이해합니다.
- HTTP 오류 응답과 네트워크 오류를 구분합니다.
- 대기·빈 결과·성공·오류 상태를 분리합니다.
- `AbortController`로 더 이상 필요하지 않은 작업을 취소합니다.
- 오래된 응답이 최신 상태를 덮어쓰지 않게 합니다.
- 타임아웃과 자원 정리의 책임을 정합니다.

## Promise는 나중에 완료될 작업을 나타냅니다

```js
async function loadBoard(id) {
  const response = await fetch(`/api/boards/${id}`);
  return response.json();
}
```

`async` 함수는 항상 Promise를 반환합니다. 호출자가 Promise를 `await`하거나 반환하지 않으면 실패가 호출 흐름에서 분리되어 나중에 처리되지 않은 거부(unhandled rejection)로 나타날 수 있습니다.

```js
async function unsafe() {
  saveBoard(); // 완료와 실패를 기다리거나 반환하지 않음
}
```

작업을 의도적으로 백그라운드에서 실행한다면 실패를 관찰할 위치와 작업의 생명주기를 별도로 정해야 합니다. `void saveBoard()`로 정적 검사 경고만 없애는 것은 실제 오류를 처리하는 방법이 아닙니다.

## 이벤트 루프의 최소 모델

현재 동기 호출 스택이 끝나면 마이크로태스크 큐를 처리한 뒤 다음 태스크를 실행합니다.

```js
console.log("sync");
queueMicrotask(() => console.log("microtask"));
setTimeout(() => console.log("task"), 0);
```

출력 순서는 `sync`, `microtask`, `task`입니다. Promise의 후속 콜백도 마이크로태스크로 실행됩니다. 세부 규칙을 모두 외우기보다는 콜백이 현재 함수가 끝난 뒤 실행되며, 그 사이에 상태가 달라질 수 있다는 점을 기억해야 합니다.

## `fetch`는 HTTP 404 응답 때문에 거부되지 않습니다

```js
async function requestJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new HttpError(response.status, await safeErrorBody(response));
  }
  return response.json();
}
```

`fetch` Promise가 거부되는 주된 원인은 연결 실패, DNS 오류, 요청 취소 같은 전송 문제입니다. 서버가 400이나 500 상태 코드로 응답해도 `Response` 객체는 정상적으로 도착합니다. 따라서 `response.ok`나 `response.status`를 직접 확인해야 합니다.

응답이 항상 JSON이라고 가정해서도 안 됩니다. `Content-Type`과 파싱 실패를 고려해야 하며, 리버스 프록시가 HTML 오류 페이지를 반환할 가능성도 있습니다.

## 화면 상태를 명확하게 구분합니다

다음 상태는 서로 다른 의미를 가집니다.

```ts
type LoadState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "empty" }
  | { status: "ready"; data: T }
  | { status: "error"; message: string };
```

빈 배열 하나로 “아직 불러오지 않음”과 “정상적으로 불러왔지만 결과가 없음”을 동시에 표현할 수는 없습니다. 여러 불리언 변수로 상태를 표현하면 `loading: true`와 `error: true`가 동시에 설정되는 모순된 조합도 만들 수 있습니다.

## 취소도 작업 생명주기의 일부입니다

```js
const controller = new AbortController();
fetch(url, { signal: controller.signal });
controller.abort();
```

취소된 `fetch`는 `AbortError`로 실패합니다. 사용자가 다른 페이지로 이동하거나 검색어를 바꿔 결과가 더 이상 필요하지 않다면 요청을 취소합니다.

```js
try {
  await fetch(url, { signal });
} catch (error) {
  if (error instanceof DOMException && error.name === "AbortError") return;
  throw error;
}
```

취소는 사용자에게 오류 배너를 보여 줘야 하는 실패가 아닐 수 있습니다. 그렇다고 모든 오류를 취소로 간주해 무시해서는 안 됩니다.

## 오래된 응답이 상태를 덮어쓰지 않게 합니다

취소를 지원하지 않는 API가 있을 수 있고, 취소 시점에 요청이 이미 완료 직전일 수도 있습니다. 결과를 적용하기 전에 현재 요청의 결과인지 확인하면 이를 방어할 수 있습니다.

```js
let requestVersion = 0;

async function search(query) {
  const version = ++requestVersion;
  const result = await searchUsers(query);
  if (version !== requestVersion) return;
  render(result);
}
```

`AbortController`와 버전 검사는 반드시 둘 중 하나만 선택해야 하는 방식이 아닙니다. 전자는 불필요한 작업을 중단하고, 후자는 오래된 결과가 적용되는 것을 막습니다.

## 타임아웃을 명시합니다

```js
const signal = AbortSignal.timeout(5_000);
const response = await fetch(url, { signal });
```

실행 환경이 `AbortSignal.timeout`을 지원하지 않으면 타이머와 `AbortController`를 조합하고 `finally`에서 타이머를 정리합니다. 타임아웃은 서버가 요청을 처리하지 않았다는 증거가 아닙니다. 서버는 처리했지만 응답만 유실되었을 수 있으므로, 상태 변경 요청을 재시도하려면 멱등성 계약이 필요합니다.

## 독립 작업과 순차 작업을 구분합니다

서로 의존하지 않는 요청만 동시에 시작합니다.

```js
const [profile, boards] = await Promise.all([
  loadProfile(),
  loadBoards()
]);
```

하나가 실패해 `Promise.all`이 거부되더라도 이미 시작된 나머지 작업이 자동으로 취소되지는 않습니다. 공유 `AbortSignal`이나 명시적인 자원 정리 방식을 설계해야 합니다.

## 오류를 변환할 위치를 정합니다

네트워크·HTTP·검증 오류를 모든 컴포넌트에서 제각각 문자열로 바꾸지 않습니다. 어댑터 경계에서 애플리케이션이 이해하는 일관된 오류로 변환하고, 화면에서는 사용자에게 필요한 메시지만 선택해 표시합니다. 내부 스택 추적, SQL 오류, 개인정보를 화면에 노출해서는 안 됩니다.

## 흔한 오류

- `fetch`가 404 응답에서 Promise를 거부한다고 가정합니다.
- 대기 상태를 빈 배열로 표현합니다.
- 이전 요청을 취소하지 않고 결과의 버전도 확인하지 않습니다.
- `catch`에서 `AbortError`를 포함한 모든 오류를 무시합니다.
- 타이머를 만들고 정리하지 않습니다.
- 타임아웃 후 상태 변경 요청을 멱등성 계약 없이 자동으로 재시도합니다.

## 연결 실습

[`실행 환경과 워크스페이스`](../../exercises/01-runtime/README.md)에서는 태스크·마이크로태스크와 오류 전달을, [`React와 Next.js`](../../exercises/03-react-nextjs/README.md)에서는 실제 요청의 완료 순서가 뒤바뀌는 상황을 검증합니다.

## 완료 기준

- Promise의 실패가 호출자에게 전달되는 경로를 설명할 수 있습니다.
- 네트워크 오류와 HTTP 오류 응답을 구분합니다.
- 대기·빈 결과·성공·오류를 서로 다른 상태로 표현합니다.
- 더 이상 필요하지 않은 요청을 취소하고 `AbortError`만 별도로 처리합니다.
- 느린 이전 응답이 최신 화면 상태를 덮어쓰지 않는지 검증합니다.

## 다음 단계

정적 타입이 외부 응답의 안전성을 보장하지 못하는 이유는 [`TypeScript와 런타임 검증`](07-typescript-runtime-validation.md)에서 다룹니다.
