# 비동기 작업과 fetch

비동기 코드의 핵심 문제는 “기다리는 문법”이 아니라 **작업의 시작·완료·실패·취소와 결과가 아직 유효한지** 관리하는 것입니다. 사용자가 검색어를 빠르게 바꾸면 먼저 시작한 요청이 나중에 끝날 수 있습니다. `await`만 사용한다고 이 순서 문제가 사라지지는 않습니다.

## 목표

- Promise, `async`와 `await`의 전달 규칙을 이해합니다.
- HTTP 오류와 network 오류를 구분합니다.
- loading·empty·success·error 상태를 분리합니다.
- `AbortController`로 더 이상 필요 없는 작업을 취소합니다.
- 오래된 응답이 최신 상태를 덮지 않게 합니다.
- timeout과 cleanup의 책임을 정합니다.

## Promise는 미래의 완료 결과입니다

```js
async function loadBoard(id) {
  const response = await fetch(`/api/boards/${id}`);
  return response.json();
}
```

`async` 함수는 항상 Promise를 반환합니다. 호출자가 `await`하거나 반환하지 않으면 실패가 관계없는 시점에 unhandled rejection으로 나타날 수 있습니다.

```js
async function unsafe() {
  saveBoard(); // 완료와 실패를 기다리거나 반환하지 않음
}
```

작업을 의도적으로 background로 보낸다면 실패 관찰과 수명 책임을 따로 둡니다. 단순히 `void saveBoard()`로 경고만 없애는 것은 운영 실패를 처리하지 않습니다.

## event loop의 최소 모델

동기 call stack이 끝나면 microtask queue가 먼저 비워지고 다음 task가 실행됩니다.

```js
console.log("sync");
queueMicrotask(() => console.log("microtask"));
setTimeout(() => console.log("task"), 0);
```

출력은 `sync`, `microtask`, `task`입니다. Promise callback도 microtask에서 이어집니다. 이 순서를 세부적으로 암기하기보다, callback이 현재 함수가 끝난 뒤 실행되어 그 사이 상태가 달라질 수 있음을 기억합니다.

## fetch는 HTTP 404에서 자동으로 reject하지 않습니다

```js
async function requestJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new HttpError(response.status, await safeErrorBody(response));
  }
  return response.json();
}
```

fetch Promise가 reject되는 것은 주로 연결·DNS·취소 같은 전송 실패입니다. server가 400이나 500을 응답해도 `response`는 정상으로 도착합니다. 따라서 `response.ok` 또는 status를 직접 확인합니다.

응답이 JSON이라고 가정하기 전에 `Content-Type`과 parsing 실패도 고려합니다. reverse proxy가 HTML 오류 page를 반환할 수 있습니다.

## 화면 상태를 구분합니다

다음 네 상태는 서로 다릅니다.

```ts
type LoadState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; data: T }
  | { status: "error"; message: string };
```

빈 배열은 “아직 불러오지 않음”과 “정상 응답이지만 결과 없음”을 동시에 표현할 수 없습니다. 여러 boolean으로 상태를 만들면 `loading: true`와 `error: true` 같은 모순 조합이 생깁니다.

## 취소는 작업 수명의 일부입니다

```js
const controller = new AbortController();
fetch(url, { signal: controller.signal });
controller.abort();
```

취소된 fetch는 `AbortError`로 실패합니다. 사용자가 다른 page로 이동하거나 검색어가 바뀌어 결과를 사용할 수 없으면 취소합니다.

```js
try {
  await fetch(url, { signal });
} catch (error) {
  if (error instanceof DOMException && error.name === "AbortError") return;
  throw error;
}
```

취소는 오류 banner를 보여 줄 사용자 실패가 아닐 수 있습니다. 하지만 모든 오류를 취소로 무시해서도 안 됩니다.

## 오래된 응답 차단

취소를 지원하지 않는 API이거나 요청이 이미 완료 직전일 수 있습니다. 결과를 적용할 때 현재 요청인지 확인하는 방법도 있습니다.

```js
let requestVersion = 0;

async function search(query) {
  const version = ++requestVersion;
  const result = await searchUsers(query);
  if (version !== requestVersion) return;
  render(result);
}
```

AbortController와 version check는 대체 관계가 아닐 수 있습니다. 전자는 불필요한 작업을 중단하고, 후자는 결과 적용을 방어합니다.

## timeout을 명시합니다

```js
const signal = AbortSignal.timeout(5_000);
const response = await fetch(url, { signal });
```

사용 환경이 지원하지 않으면 timer와 controller를 조합하되 `finally`에서 timer를 정리합니다. timeout은 server가 요청을 처리하지 않았다는 증거가 아닙니다. 응답만 잃었을 수 있으므로 상태 변경 요청의 재시도에는 idempotency 계약이 필요합니다.

## 독립 작업과 순차 작업

서로 독립적인 요청만 함께 시작합니다.

```js
const [profile, boards] = await Promise.all([
  loadProfile(),
  loadBoards()
]);
```

하나가 실패해 `Promise.all`이 reject되어도 이미 시작한 나머지 작업은 자동 취소되지 않습니다. 공유 signal이나 명시적 cleanup을 설계합니다.

## 오류를 번역하는 위치

network·HTTP·validation 오류를 모든 component에서 제각각 문자열로 만들지 않습니다. adapter 경계에서 안정된 application 오류로 바꾸고 화면은 사용자에게 필요한 메시지를 선택합니다. 내부 stack, SQL 오류와 개인정보를 화면에 노출하지 않습니다.

## 실패 조건

- fetch가 404에서 reject한다고 가정합니다.
- loading을 빈 배열로 표현합니다.
- 이전 요청을 취소하거나 결과 version을 확인하지 않습니다.
- `catch`가 AbortError를 포함한 모든 오류를 무시합니다.
- 고정 timer를 만들고 정리하지 않습니다.
- timeout 뒤 상태 변경 요청을 아무 idempotency 계약 없이 자동 재시도합니다.

## 연결 실습

[`실행 환경과 작업 공간`](../../exercises/01-runtime/README.md)은 task·microtask와 실패 전달을, [`React와 Next.js`](../../exercises/03-react-nextjs/README.md)는 실제 요청 순서 역전을 검증합니다.

## 완료 기준

- Promise 실패가 호출자에게 전달되는 경로를 설명할 수 있습니다.
- network 오류와 HTTP 오류를 구분합니다.
- loading·empty·ready·error를 독립 상태로 표현합니다.
- 더 이상 필요한 요청을 취소하고 AbortError만 구분합니다.
- 느린 이전 응답이 최신 화면을 덮지 않게 검증합니다.

## 다음 단계

정적 형이 외부 응답을 자동으로 안전하게 만들지 않는 이유는 [`TypeScript와 실행 시점 검증`](07-typescript-runtime-validation.md)에서 다룹니다.
