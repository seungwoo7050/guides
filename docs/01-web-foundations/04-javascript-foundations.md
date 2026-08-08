# JavaScript 기초

JavaScript 문법 전체를 먼저 외울 필요는 없습니다. 작은 브라우저 애플리케이션을 만들기 위해 값, 조건, 반복, 함수, 배열, 객체, module과 오류를 다루는 최소 모델이 필요합니다. 이 장은 코드가 “무엇을 계산하고 어떤 상태를 새 값으로 만드는지” 읽을 수 있는 수준을 목표로 합니다.

## 목표

- 값과 변수, 조건과 반복을 사용합니다.
- 함수를 입력·결과·부수 효과로 나눕니다.
- 배열과 객체를 안전하게 변환합니다.
- 참조 공유와 얕은 복사를 구분합니다.
- ESM으로 파일의 공개 범위를 정합니다.
- 실패를 `Error`로 전달합니다.

## 값과 변수

JavaScript에는 문자열, 숫자, 불리언, `null`, `undefined`, 객체 등의 값이 있습니다.

```js
const title = "첫 작업";
const count = 3;
const completed = false;
let selectedId = null;
```

기본은 `const`로 시작하고 변수 자체를 다시 대입해야 할 때만 `let`을 사용합니다. `const`는 객체 내부까지 불변으로 만들지는 않습니다.

```js
const task = { title: "읽기", completed: false };
task.completed = true; // 가능
```

## 조건과 반복

```js
function describeCount(count) {
  if (!Number.isInteger(count) || count < 0) {
    throw new Error("count는 0 이상의 정수여야 합니다.");
  }
  if (count === 0) return "작업 없음";
  return `${count}개 작업`;
}
```

빠르게 반환하면 중첩을 줄이고 실패 조건을 먼저 드러낼 수 있습니다.

배열 반복은 목적에 맞는 도구를 고릅니다.

```js
const openTasks = tasks.filter((task) => !task.completed);
const titles = tasks.map((task) => task.title);
const hasDone = tasks.some((task) => task.completed);
```

단순히 각 항목에 부수 효과를 수행할 때만 `forEach`를 사용합니다. 새 배열이 필요하면 `map`·`filter`, 한 값을 계산하면 `reduce` 또는 명시적인 loop를 선택합니다.

## 함수로 문제를 나눕니다

좋은 함수는 이름만으로 입력과 결과를 예상할 수 있습니다.

```js
function normalizeTitle(input) {
  return input.trim();
}

function createTask(title, createId) {
  const normalized = normalizeTitle(title);
  if (!normalized) throw new Error("제목이 필요합니다.");
  return { id: createId(), title: normalized, completed: false };
}
```

현재 시각이나 무작위 id처럼 외부 값은 매개변수로 전달하면 검사하기 쉬워집니다. DOM 변경, network 요청, storage 쓰기 같은 부수 효과와 순수 계산을 분리합니다.

## 객체와 참조 공유

원시값은 대입 시 값이 복사되지만 객체와 배열은 같은 객체를 가리키는 참조가 복사됩니다.

```js
const current = { version: 1 };
const alias = current;
alias.version = 2;
console.log(current.version); // 2
```

이전 상태를 보존하려면 변경 경로에 새 값을 만듭니다.

```js
const next = { ...current, version: current.version + 1 };
const nextTasks = tasks.map((task) =>
  task.id === targetId ? { ...task, completed: true } : task
);
```

spread는 한 단계만 복사합니다. 중첩 객체는 여전히 공유될 수 있습니다.

## `null`, `undefined`와 truthiness

`undefined`는 값이나 속성이 제공되지 않은 경우에 흔히 나타나고, `null`은 애플리케이션이 “없음”을 명시하는 값으로 사용할 수 있습니다. 계약에서 둘의 의미를 정합니다.

빈 문자열, 0, `false`, `null`, `undefined`, `NaN`은 조건에서 false로 취급됩니다. 문자열 `"false"`는 true입니다.

```js
Boolean("false"); // true
```

환경 변수와 form 문자열을 단순 truthiness로 boolean 변환하지 않습니다.

## 비교와 숫자 변환

형 변환을 하지 않는 `===`, `!==`를 기본으로 사용합니다.

```js
"1" === 1; // false
```

숫자 입력은 변환 뒤 전체 범위를 검사합니다.

```js
function parseLimit(input) {
  const value = Number(input);
  if (!Number.isInteger(value) || value < 1 || value > 100) {
    throw new Error("limit은 1..100 정수여야 합니다.");
  }
  return value;
}
```

`Number("")`는 0이므로 빈 입력을 허용하지 않는다면 변환 전에 trim 결과도 확인합니다.

## module과 공개 범위

```js
// tasks.js
export function addTask(tasks, task) {
  return [...tasks, task];
}
```

```js
// app.js
import { addTask } from "./tasks.js";
```

ESM은 파일 사이 의존성을 드러냅니다. import만으로 server 시작, timer 등록이나 전역 상태 변경 같은 큰 부수 효과를 만들지 않습니다.

## 오류를 값처럼 구분합니다

복구할 수 없는 입력에는 문자열이 아니라 `Error`를 던집니다.

```js
try {
  createTask("", crypto.randomUUID);
} catch (error) {
  const message = error instanceof Error ? error.message : "알 수 없는 오류";
  console.error(message);
}
```

현재 위치에서 복구할 수 없다면 오류를 기록하고 성공한 것처럼 계속하지 않습니다. 원인을 보존해 다시 던질 수 있습니다.

```js
throw new Error("작업 저장 실패", { cause: error });
```

## 실패 조건

- 모든 값을 문자열로 취급하고 변환 실패를 확인하지 않습니다.
- 배열과 객체를 직접 변경하면서 이전 상태가 보존된다고 가정합니다.
- 한 함수가 입력 검증, DOM, storage와 network를 모두 담당합니다.
- `==`의 암시적 변환에 의존합니다.
- `catch`에서 오류를 비우고 성공 화면을 계속 보여 줍니다.

## 연결 실습

[`첫 웹 애플리케이션`](../../exercises/00-first-web-app/README.md)에서 작업 배열의 추가·완료·삭제를 새 값으로 구현하고 storage 외부 값을 검사합니다.

## 완료 기준

- 변수·조건·반복·함수로 작은 계산을 작성할 수 있습니다.
- `map`·`filter`와 직접 loop의 목적을 구분합니다.
- 객체 참조 공유와 spread의 얕은 복사를 설명할 수 있습니다.
- 입력 변환의 실패와 범위를 검사합니다.
- module 공개 함수와 DOM 부수 효과를 분리할 수 있습니다.

## 다음 단계

JavaScript가 실제 문서와 사용자 입력을 연결하는 방법은 [`DOM, 이벤트, URL과 저장소`](05-dom-events-url-storage.md)에서 다룹니다.
