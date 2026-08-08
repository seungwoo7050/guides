# HTML 폼과 접근성

HTML 요소는 화면 모양만 만드는 태그가 아닙니다. 링크, 버튼, 입력, 제목과 landmark에는 browser·keyboard·screen reader가 공유하는 동작과 의미가 있습니다. 처음부터 올바른 요소를 사용하면 JavaScript로 다시 구현할 코드가 줄고 자동 검사도 사용자 관점에 가까워집니다.

## 목표

- 문서 landmark와 제목 계층을 구성합니다.
- link, button과 input을 목적에 맞게 선택합니다.
- label과 form submit의 기본 계약을 사용합니다.
- keyboard focus와 비동기 상태를 전달합니다.
- 접근성을 별도 장식이 아니라 기능 계약으로 다룹니다.

## 문서의 큰 구조

최소 문서는 다음과 같이 시작할 수 있습니다.

```html
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>내 작업</title>
</head>
<body>
  <header>
    <nav aria-label="주 메뉴">
      <a aria-current="page" href="/">작업</a>
    </nav>
  </header>
  <main id="main">
    <h1>내 작업</h1>
  </main>
</body>
</html>
```

`lang`은 문서 언어를, `title`은 browser tab과 history의 이름을 제공합니다. `main`은 핵심 본문을, `nav`는 이동 묶음을 표현합니다. 모든 영역에 ARIA role을 추가할 필요는 없습니다. native HTML의 의미를 우선합니다.

## heading은 시각적 크기가 아니라 구조입니다

페이지의 대표 제목은 보통 `h1`, 그 안의 주요 section은 `h2`, 더 작은 하위 주제는 `h3`로 이어집니다.

```html
<h1>보드 설정</h1>
<section>
  <h2>구성원</h2>
  <article>
    <h3>Kim</h3>
  </article>
</section>
```

글자를 크게 만들려고 heading level을 고르지 않습니다. 크기는 CSS가 담당합니다. heading을 건너뛰면 보조 기술 사용자가 문서 구조를 빠르게 탐색하기 어렵습니다.

## 이동은 link, 동작은 button

```html
<a href="/boards/42">보드 열기</a>
<button type="button">메모 추가</button>
```

link는 주소가 바뀌는 이동이며 새 tab 열기, 주소 복사 같은 browser 기능을 가집니다. button은 현재 화면의 상태를 바꾸는 동작입니다. 클릭 가능한 `div`는 Enter·Space keyboard 동작, focus, disabled 상태와 접근 가능한 role을 직접 다시 구현해야 합니다.

form 안의 button은 기본 type이 `submit`일 수 있습니다. 제출 목적이 아니면 `type="button"`을 명시합니다.

## label은 입력 이름의 정본입니다

placeholder는 입력 예시일 뿐 label을 대신하지 않습니다.

```html
<form id="task-form">
  <label for="task-title">새 작업</label>
  <input id="task-title" name="title" autocomplete="off" />
  <button type="submit">추가</button>
</form>
```

`for`와 `id`가 연결되면 label을 클릭해 입력에 focus할 수 있고 screen reader도 이름을 읽습니다. 여러 입력의 오류를 표시할 때는 `aria-describedby`로 해당 설명과 연결할 수 있습니다.

```html
<input id="email" aria-describedby="email-error" />
<p id="email-error">이메일 형식을 확인해 주세요.</p>
```

## form submit을 기본 경로로 사용합니다

button click만 듣는 대신 form의 `submit` event를 처리합니다.

```js
const form = document.querySelector("#task-form");
form.addEventListener("submit", (event) => {
  event.preventDefault();
  // 입력 검증과 저장
});
```

이 경로는 button click뿐 아니라 입력에서 Enter를 누르는 동작도 포함합니다. browser 기본 동작을 이용하면 mouse와 keyboard 경로가 분리되지 않습니다.

## focus는 현재 위치를 보여 줍니다

focus outline을 제거하지 않습니다.

```css
:focus-visible {
  outline: 3px solid #f59e0b;
  outline-offset: 3px;
}
```

페이지 처음에 본문 건너뛰기 link를 둘 수 있습니다.

```html
<a class="skip-link" href="#main">본문으로 건너뛰기</a>
<main id="main" tabindex="-1">...</main>
```

modal을 열면 focus를 modal 안의 의미 있는 위치로 옮기고, 닫으면 열었던 control로 돌려보내야 합니다. 단순히 z-index로 위에 그리는 것은 keyboard 수명을 해결하지 않습니다.

## 비동기 상태와 오류를 알립니다

화면에 새 텍스트가 나타나도 보조 기술이 자동으로 알지 못할 수 있습니다.

```html
<p role="status" aria-live="polite">저장 중입니다.</p>
<p role="alert">저장하지 못했습니다.</p>
```

`status`는 일반적인 진행 상태, `alert`는 즉시 알려야 하는 실패에 사용합니다. 모든 텍스트에 live region을 붙이면 알림이 과도해집니다.

색만으로 성공·오류·역할을 표현하지 않습니다. 텍스트, icon의 접근 가능한 이름과 상태 속성을 함께 사용합니다.

## 접근 가능한 이름으로 검사합니다

사용자 관점의 browser test는 CSS class보다 role과 이름을 사용합니다.

```ts
page.getByRole("button", { name: "메모 추가" });
page.getByLabel("새 작업");
page.getByRole("alert");
```

class 이름이 바뀌어도 사용 계약이 같으면 검사는 유지됩니다. 반대로 label이나 button 이름이 사라지면 실제 사용 회귀로 실패합니다.

## 실패 조건

- link와 button을 모양만 보고 선택합니다.
- placeholder를 label로 사용합니다.
- button click만 처리해 Enter submit이 동작하지 않습니다.
- outline을 지우고 다른 focus 표시를 제공하지 않습니다.
- 화면에서 button을 숨긴 것을 server 권한 검사로 착각합니다.
- ARIA를 native HTML 대신 사용하거나 의미와 다른 role을 붙입니다.

## 연결 실습

[`첫 웹 애플리케이션`](../../exercises/00-first-web-app/README.md)과 [`브라우저 UI`](../../exercises/02-browser/README.md)에서 실제 keyboard와 접근 가능한 이름을 검증합니다.

## 완료 기준

- 문서의 `header`, `nav`, `main`과 heading 구조를 만들 수 있습니다.
- link와 button의 선택 이유를 설명할 수 있습니다.
- label이 연결된 form을 Enter로 제출할 수 있습니다.
- focus와 비동기 오류를 시각·비시각 사용자에게 전달할 수 있습니다.
- 실제 browser test가 role과 이름으로 핵심 control을 찾습니다.

## 다음 단계

의미 있는 문서가 내용과 화면 크기에 따라 무너지지 않도록 [`CSS 레이아웃과 반응형 화면`](03-css-layout-responsive.md)으로 이동합니다.
