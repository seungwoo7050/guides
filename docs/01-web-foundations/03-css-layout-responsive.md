# CSS 레이아웃과 반응형 화면

반응형 화면을 만든다는 것은 특정 휴대전화 너비마다 미디어 쿼리를 추가하는 일이 아닙니다. 요소가 사용 가능한 공간에 맞춰 줄어들고, 콘텐츠가 길어져도 넘치지 않으며, 필요한 지점에서만 레이아웃 방식이 바뀌도록 설계하는 일입니다.

## 목표

- 캐스케이드, 박스 모델, 일반 흐름의 역할을 이해합니다.
- Flexbox와 Grid를 용도에 맞게 선택합니다.
- 고정 너비 대신 콘텐츠와 뷰포트에 적응하는 크기를 사용합니다.
- 긴 문자열, 확대된 글자, 너비 320px 화면에서 레이아웃을 검증합니다.
- 모션과 명암비에 관한 사용자 설정을 존중합니다.

## 캐스케이드와 선택자

여러 CSS 규칙이 같은 요소에 적용되면 출처와 중요도, 명시도, 선언 순서에 따라 최종 값이 결정됩니다. 처음부터 명시도가 높은 선택자와 `!important`를 남용하면 이후 컴포넌트에서 스타일을 재정의하기 어렵습니다.

```css
button { font: inherit; }
.primary-action { background: #1d4ed8; color: white; }
```

컴포넌트의 의미를 나타내는 클래스 이름을 사용하고 DOM의 깊은 구조에 지나치게 의존하지 않습니다.

```css
/* 피합니다. */
main > section:nth-child(2) div button { ... }
```

## 박스 모델을 먼저 통일합니다

기본값인 `content-box`에서는 선언한 `width`에 `padding`과 `border`가 더해집니다. 요소의 전체 크기를 예측하기 쉽게 다음 규칙을 적용합니다.

```css
*, *::before, *::after {
  box-sizing: border-box;
}
```

이 규칙은 `width: 100%`인 입력 요소에 패딩이 더해져 뷰포트 너비를 넘는 문제를 줄입니다.

## 일반 흐름을 기본으로 사용합니다

블록 요소는 문서 순서대로 쌓이고 인라인 콘텐츠는 사용 가능한 너비에 맞춰 줄바꿈됩니다. 먼저 일반 흐름만으로 읽을 수 있는 문서를 만든 뒤, 별도의 정렬 관계가 필요한 영역에 Flexbox나 Grid를 적용합니다. 모든 요소를 절대 위치로 배치하면 콘텐츠 길이와 화면 확대에 대응하기 어렵습니다.

## Flexbox와 Grid

Flexbox는 한 축을 기준으로 요소를 배치하고 정렬할 때 적합합니다.

```css
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: .75rem;
}
```

Grid는 행과 열의 관계가 있는 반복 콘텐츠를 배치할 때 적합합니다.

```css
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 18rem), 1fr));
  gap: 1rem;
}
```

`min(100%, 18rem)`은 작은 뷰포트에서 열의 최소 너비가 컨테이너보다 커지는 문제를 방지합니다.

## 요소가 줄어들 수 있게 합니다

Flexbox와 Grid의 자식 요소는 콘텐츠의 최소 크기 때문에 예상보다 줄어들지 않을 수 있습니다.

```css
.card-title {
  min-width: 0;
  overflow-wrap: anywhere;
}
```

사용자가 입력한 긴 제목, URL, 공백 없는 영문 토큰을 넣어 확인합니다. 짧고 보기 좋은 샘플만 사용하면 콘텐츠가 넘치는 문제를 발견하기 어렵습니다.

## 고정값보다 유연한 범위를 사용합니다

```css
main {
  width: min(70rem, calc(100% - 2rem));
  margin-inline: auto;
}
```

읽기 편한 최대 너비는 제한하되, 요소가 뷰포트보다 커지지 않게 합니다. `rem`은 루트 요소의 글자 크기에 비례하므로 사용자의 글자 크기 설정과 확대를 더 잘 반영합니다.

폼은 넓은 화면에서는 한 행으로, 좁은 화면에서는 한 열로 배치할 수 있습니다.

```css
.form-row { display: flex; gap: .5rem; }
.form-row input { min-width: 0; flex: 1; }

@media (max-width: 30rem) {
  .form-row { flex-direction: column; }
}
```

미디어 쿼리의 브레이크포인트는 특정 기기 이름이 아니라 실제 레이아웃이 깨지는 지점을 기준으로 정합니다.

## 뷰포트와 확대 검증

최소한 다음 조건을 확인합니다.

- CSS 픽셀 기준 너비 320px
- 브라우저 확대 200%
- 긴 제목과 비어 있는 콘텐츠
- 시스템 글자 크기 증가
- 키보드 포커스 윤곽선이 잘리지 않는지
- Canvas나 표처럼 가로 스크롤이 필요한 영역이 아닌 곳에서 가로 스크롤이 생기지 않는지

자동 검사에서는 다음 값을 확인할 수 있습니다.

```js
document.documentElement.scrollWidth <= document.documentElement.clientWidth
```

이 조건만으로 전체 디자인의 적절성을 보장할 수는 없지만, 의도하지 않은 페이지 전체의 가로 넘침을 찾는 데 유용합니다.

## 색상과 모션

텍스트와 배경은 충분한 명암비를 가져야 하며, 색상만으로 상태를 구분해서는 안 됩니다. 기능 이해에 꼭 필요하지 않은 애니메이션은 사용자 설정에 따라 줄일 수 있어야 합니다.

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    scroll-behavior: auto !important;
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
  }
}
```

이 전역 규칙을 그대로 복사하기보다는 애플리케이션에서 사용하는 애니메이션의 실제 동작 요구사항에 맞게 조정합니다.

## 흔한 오류

- 모든 너비를 픽셀 단위의 고정값으로 지정합니다.
- `100vw`가 스크롤바 너비까지 포함할 수 있다는 점을 고려하지 않아 가로 넘침을 만듭니다.
- 긴 문자열과 화면 확대를 테스트하지 않습니다.
- CSS `order`로 시각적 순서만 바꾸고 DOM 순서와 키보드 탐색 순서는 그대로 둡니다.
- 컨테이너의 `overflow: hidden` 때문에 포커스 윤곽선이 잘립니다.

## 연결 실습

[`첫 웹 애플리케이션`](../../exercises/00-first-web-app/README.md)과 [`브라우저 UI`](../../exercises/02-browser/README.md)에서는 너비 320px 뷰포트에서 실제 스크롤 너비를 검사합니다.

## 완료 기준

- `content-box`와 `border-box`의 차이를 설명할 수 있습니다.
- Flexbox와 Grid 중 하나를 선택한 이유를 설명할 수 있습니다.
- 긴 콘텐츠와 작은 뷰포트에서도 레이아웃이 사용 가능한 공간에 맞춰 줄어듭니다.
- 키보드 포커스와 화면 확대 때문에 기능이 가려지지 않습니다.
- 기기 이름이 아니라 콘텐츠를 기준으로 필요한 브레이크포인트를 정합니다.

## 다음 단계

화면 상태와 동작을 코드로 표현하려면 [`JavaScript 기초`](04-javascript-foundations.md)로 이동합니다.
