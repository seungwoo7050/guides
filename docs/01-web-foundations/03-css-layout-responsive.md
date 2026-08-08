# CSS 레이아웃과 반응형 화면

반응형 화면은 특정 휴대전화 폭에 media query를 많이 추가하는 작업이 아닙니다. 요소가 자신의 사용 가능한 공간 안에서 줄어들고, 내용이 길어져도 overflow하지 않으며, 필요한 곳에서만 layout mode가 바뀌도록 만드는 일입니다.

## 목표

- cascade, box model과 normal flow의 역할을 이해합니다.
- Flexbox와 Grid를 목적에 맞게 선택합니다.
- 고정 폭 대신 내용과 viewport에 적응하는 크기를 사용합니다.
- 긴 문자열, 확대된 글자와 320px 화면을 검증합니다.
- motion과 contrast 같은 사용자 환경을 존중합니다.

## cascade와 selector

CSS는 여러 규칙이 같은 요소에 적용될 때 origin, importance, specificity와 선언 순서로 값을 결정합니다. 처음부터 강한 selector와 `!important`를 늘리면 이후 component가 override하기 어렵습니다.

```css
button { font: inherit; }
.primary-action { background: #1d4ed8; color: white; }
```

component의 의미 있는 class를 사용하고 DOM 깊이에 과도하게 의존하지 않습니다.

```css
/* 피합니다. */
main > section:nth-child(2) div button { ... }
```

## box model을 먼저 통일합니다

기본 `content-box`에서는 선언한 width에 padding과 border가 더해집니다. 전체 크기를 예상하기 쉽게 다음을 적용합니다.

```css
*, *::before, *::after {
  box-sizing: border-box;
}
```

`width: 100%`인 입력에 padding이 더해져 viewport를 넘는 문제를 줄입니다.

## normal flow를 기본으로 둡니다

block 요소는 문서 순서대로 쌓이고 inline 내용은 줄바꿈합니다. 먼저 normal flow로 읽을 수 있는 문서를 만든 뒤, 관계가 필요한 영역에 Flexbox나 Grid를 사용합니다. 모든 요소를 absolute positioning으로 배치하면 내용 길이와 확대에 취약합니다.

## Flexbox와 Grid

Flexbox는 한 축의 정렬에 적합합니다.

```css
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: .75rem;
}
```

Grid는 행과 열의 관계가 있는 반복 카드에 적합합니다.

```css
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 18rem), 1fr));
  gap: 1rem;
}
```

`min(100%, 18rem)`은 작은 viewport에서 최소 열 폭이 container보다 커지는 문제를 막습니다.

## 줄어들 수 있는 항목

Flex·Grid child는 content의 최소 크기 때문에 예상보다 줄어들지 않을 수 있습니다.

```css
.card-title {
  min-width: 0;
  overflow-wrap: anywhere;
}
```

사용자 생성 제목, URL과 긴 영문 token을 넣어 테스트합니다. 예쁜 짧은 샘플만으로는 overflow를 발견하기 어렵습니다.

## 고정값보다 유연한 경계

```css
main {
  width: min(70rem, calc(100% - 2rem));
  margin-inline: auto;
}
```

최대 읽기 폭은 제한하되 viewport보다 커지지 않습니다. `rem`은 root 글자 크기에 비례하므로 사용자 확대를 더 잘 반영합니다.

폼은 넓은 화면에서 한 행, 좁은 화면에서 한 열로 바꿀 수 있습니다.

```css
.form-row { display: flex; gap: .5rem; }
.form-row input { min-width: 0; flex: 1; }

@media (max-width: 30rem) {
  .form-row { flex-direction: column; }
}
```

media query는 특정 기기 이름이 아니라 layout이 실제로 깨지는 지점에서 정합니다.

## viewport와 zoom 검증

최소한 다음을 확인합니다.

- 320 CSS pixel 폭
- 200% browser zoom
- 긴 제목과 빈 내용
- system font 크기 증가
- keyboard focus outline이 잘리지 않는지
- horizontal scroll이 실제로 필요한 canvas·table이 아닌 곳에서 생기지 않는지

자동 검증에서는 다음 값을 관찰할 수 있습니다.

```js
document.documentElement.scrollWidth <= document.documentElement.clientWidth
```

이 값만으로 모든 디자인을 증명하지는 못하지만 예상하지 않은 전체 페이지 overflow를 잡는 데 유용합니다.

## 색과 motion

텍스트와 배경은 충분히 구분되어야 하며 색만으로 상태를 표현하지 않습니다. animation은 기능 이해에 필요하지 않다면 줄일 수 있어야 합니다.

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    scroll-behavior: auto !important;
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
  }
}
```

전역 규칙을 그대로 복사하기보다 애플리케이션의 실제 animation contract에 맞춥니다.

## 실패 조건

- 모든 폭을 pixel로 고정합니다.
- `100vw`를 사용해 scrollbar 폭까지 포함한 overflow를 만듭니다.
- 긴 문자열과 확대를 테스트하지 않습니다.
- 시각적 순서만 CSS `order`로 바꾸고 DOM·keyboard 순서는 그대로 둡니다.
- focus outline이 container `overflow: hidden`에 잘립니다.

## 연결 실습

[`첫 웹 애플리케이션`](../../exercises/00-first-web-app/README.md)과 [`브라우저 UI`](../../exercises/02-browser/README.md)는 320px viewport의 실제 scroll width를 검사합니다.

## 완료 기준

- box model과 `border-box`의 차이를 설명할 수 있습니다.
- Flexbox와 Grid를 선택한 이유를 말할 수 있습니다.
- 긴 content와 작은 viewport에서도 layout이 줄어듭니다.
- keyboard focus와 zoom이 기능을 숨기지 않습니다.
- 필요한 breakpoint가 기기 이름이 아니라 content에서 도출됩니다.

## 다음 단계

화면 상태와 동작을 코드로 표현하려면 [`JavaScript 기초`](04-javascript-foundations.md)로 이동합니다.
