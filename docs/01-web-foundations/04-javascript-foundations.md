# JavaScript 기초

작은 브라우저 애플리케이션을 만들기 위해 JavaScript 문법 전체를 먼저 외울 필요는 없습니다. 값, 조건문, 반복문, 함수, 배열, 객체, 모듈, 오류 처리의 핵심 개념부터 익히면 됩니다. 이 장의 목표는 코드가 **무엇을 계산하고 상태를 어떻게 변경하는지** 읽고 작성할 수 있는 수준에 도달하는 것입니다.

## 목표

- 값과 변수, 조건문과 반복문을 사용합니다.
- 함수의 입력·반환값·부수 효과를 구분합니다.
- 배열과 객체를 안전하게 변환합니다.
- 객체 참조 공유와 얕은 복사를 구분합니다.
- ESM으로 파일의 공개 범위를 정합니다.
- 실패를 `Error` 객체로 전달합니다.

## 값과 변수

JavaScript에는 문자열, 숫자, 불리언, `null`, `undefined`, 객체 등의 값이 있습니다.

```js
const title = "첫 작업";
const count = 3;
const completed = false;
let selectedId = null;
```

변수는 기본적으로 `const`로 선언하고, 변수 자체에 다른 값을 다시 대입해야 할 때만 `let`을 사용합니다. `const`로 선언해도 객체 내부의 값까지 불변이 되는 것은 아닙니다.

```js
const task = { title: "읽기", completed: false };
task.completed = true; // 가능
```

## 조건문과 반복문

```js
function describeCount(count) {
  if (!Number.isInteger(count) || count < 0) {
    throw new Error("count는 0 이상의 정수여야 합니다.");
  }
  if (count === 0) return "작업 없음";
  return `${count}개 작업`;
}
```

잘못된 입력이나 예외 조건을 먼저 반환하면 중첩을 줄이고 함수의 처리 범위를 분명하게 만들 수 있습니다.

배열을 순회할 때는 목적에 맞는 메서드를 선택합니다.

```js
const openTasks = tasks.filter((task) => !task.completed);
const titles = tasks.map((task) => task.title);
const hasDone = tasks.some((task) => task.completed);
```

각 항목에 부수 효과를 실행할 때는 `forEach`를 사용할 수 있습니다. 새 배열이 필요하면 `map`이나 `filter`를, 하나의 결과값을 계산한다면 `reduce`나 명시적인 반복문을 선택합니다.

## 함수로 문제를 나눕니다

함수 이름과 시그니처만 보고도 입력과 결과를 예상할 수 있어야 합니다.

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

현재 시각이나 무작위 ID처럼 외부에서 결정되는 값은 매개변수로 전달하면 테스트하기 쉬워집니다. DOM 변경, 네트워크 요청, 저장소 쓰기 같은 부수 효과는 순수 계산과 분리합니다.

## 객체와 참조 공유

원시값을 대입하면 값이 복사되지만, 객체와 배열을 대입하면 같은 객체를 가리키는 참조가 복사됩니다.

```js
const current = { version: 1 };
const alias = current;
alias.version = 2;
console.log(current.version); // 2
```

이전 상태를 보존해야 한다면 변경되는 경로에 새 객체나 배열을 만듭니다.

```js
const next = { ...current, version: current.version + 1 };
const nextTasks = tasks.map((task) =>
  task.id === targetId ? { ...task, completed: true } : task
);
```

스프레드 문법은 한 단계만 복사합니다. 중첩된 객체는 여전히 이전 객체와 참조를 공유할 수 있습니다.

## `null`, `undefined`와 참·거짓 평가

`undefined`는 값이나 속성이 제공되지 않았을 때 흔히 나타납니다. `null`은 애플리케이션이 값의 부재를 명시적으로 나타낼 때 사용할 수 있습니다. 둘을 어떻게 구분할지는 애플리케이션 계약에서 정합니다.

빈 문자열, 0, `false`, `null`, `undefined`, `NaN`은 조건식에서 거짓으로 평가됩니다. 문자열 `"false"`는 참으로 평가됩니다.

```js
Boolean("false"); // true
```

환경 변수와 폼 입력 문자열을 단순한 참·거짓 평가만으로 불리언 값으로 변환해서는 안 됩니다.

## 비교와 숫자 변환

암시적 형 변환을 하지 않는 `===`와 `!==`를 기본으로 사용합니다.

```js
"1" === 1; // false
```

숫자 입력은 변환한 뒤 허용 범위까지 검사합니다.

```js
function parseLimit(input) {
  const value = Number(input);
  if (!Number.isInteger(value) || value < 1 || value > 100) {
    throw new Error("limit은 1..100 정수여야 합니다.");
  }
  return value;
}
```

`Number("")`는 0을 반환합니다. 빈 입력을 허용하지 않는다면 숫자로 변환하기 전에 `trim()` 결과가 비어 있는지도 확인해야 합니다.

## 모듈과 공개 범위

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

ESM을 사용하면 파일 사이의 의존성이 명시적으로 드러납니다. 모듈을 가져오는 것만으로 서버를 시작하거나 타이머를 등록하고 전역 상태를 변경하는 큰 부수 효과가 발생하지 않게 합니다.

## 오류를 명시적으로 전달합니다

처리할 수 없는 입력에는 문자열이 아니라 `Error` 객체를 던집니다.

```js
try {
  createTask("", crypto.randomUUID);
} catch (error) {
  const message = error instanceof Error ? error.message : "알 수 없는 오류";
  console.error(message);
}
```

현재 위치에서 오류를 복구할 수 없다면 성공한 것처럼 계속 실행하지 않습니다. 필요하면 원인을 보존한 새 오류를 던질 수 있습니다.

```js
throw new Error("작업 저장 실패", { cause: error });
```

## 흔한 오류

- 모든 입력을 문자열로 취급하고 변환 실패를 확인하지 않습니다.
- 배열과 객체를 직접 변경하면서 이전 상태가 보존된다고 가정합니다.
- 하나의 함수가 입력 검증, DOM 변경, 저장소 쓰기, 네트워크 요청을 모두 담당합니다.
- `==`의 암시적 형 변환에 의존합니다.
- `catch`에서 오류를 무시하고 성공 화면을 계속 표시합니다.

## 연결 실습

[`첫 웹 애플리케이션`](../../exercises/00-first-web-app/README.md)에서 작업 배열의 추가·완료·삭제를 새 값으로 구현하고, 저장소에서 읽은 외부 값을 검사합니다.

## 완료 기준

- 변수·조건문·반복문·함수로 작은 계산을 작성할 수 있습니다.
- `map`·`filter`와 직접 작성한 반복문의 용도를 구분합니다.
- 객체의 참조 공유와 스프레드 문법의 얕은 복사를 설명할 수 있습니다.
- 입력 변환의 실패 여부와 허용 범위를 검사합니다.
- 모듈의 공개 함수와 DOM을 변경하는 부수 효과를 분리할 수 있습니다.

## 다음 단계

JavaScript로 문서와 사용자 입력을 연결하는 방법은 [`DOM, 이벤트, URL과 저장소`](05-dom-events-url-storage.md)에서 다룹니다.
