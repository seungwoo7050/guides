# Capstone 1: 브라우저 작업 목록

첫 프로젝트는 framework와 server 없이 browser만 사용합니다. HTML·CSS·JavaScript·DOM·URL·저장소를 한 기능으로 연결하며, “화면이 보인다”가 아니라 새로고침·뒤로 가기·잘못된 저장값·키보드·작은 화면까지 자동 검증합니다.

## 목표

다음 사용자 흐름을 구현합니다.

1. 사용자가 작업 제목을 입력해 추가합니다.
2. 작업을 완료·미완료로 전환합니다.
3. 작업을 삭제합니다.
4. `all`, `open`, `done` filter를 URL에 저장합니다.
5. 새로고침 뒤 작업과 filter가 복원됩니다.
6. 뒤로 가기와 앞으로 가기로 이전 filter가 복원됩니다.
7. keyboard와 320px viewport에서도 모든 기능을 사용할 수 있습니다.

연결 실습은 [`첫 브라우저 애플리케이션`](../../exercises/00-first-web-app/README.md)입니다.

## 범위

사용 기술:

- semantic HTML
- responsive CSS
- browser ESM
- DOM event
- `URLSearchParams`와 History API
- `localStorage`
- dependency 없는 실제 Chromium 검증

의도적으로 제외:

- React
- server·API
- database
- 로그인
- build tool

첫 프로젝트에서 framework를 사용하지 않는 이유는 browser가 원래 제공하는 form·URL·storage 계약을 직접 이해하기 위해서입니다.

## 상태 모델

```ts
type Task = {
  id: string;
  title: string;
  completed: boolean;
};

type Filter = "all" | "open" | "done";
```

정본을 나눕니다.

| 상태 | 정본 |
|---|---|
| 작업 배열 | 메모리, 지속 복사본은 `localStorage` |
| filter | URL query |
| 입력 중 제목 | form input |
| 현재 화면 목록 | 위 상태에서 계산한 결과 |

DOM을 읽어 task 배열을 다시 만들지 않습니다. 상태가 바뀔 때 render하고 저장합니다.

## HTML 계약

최소 구조:

```html
<a href="#main" class="skip-link">본문으로 건너뛰기</a>
<header>...</header>
<main id="main" tabindex="-1">
  <h1>작업 목록</h1>
  <form>...</form>
  <nav aria-label="작업 필터">...</nav>
  <p role="status"></p>
  <ul aria-label="작업"></ul>
</main>
```

- 작업 추가는 form submit으로 동작합니다.
- 입력에는 연결된 `label`이 있습니다.
- 완료·삭제는 실제 `button`입니다.
- 완료 상태를 색만으로 표현하지 않습니다.
- 빈 결과와 작업 수를 text로 알립니다.

## CSS 계약

- 모든 요소에 `box-sizing: border-box`
- focus 표시 유지
- 긴 제목 줄바꿈
- 320px에서 가로 overflow 없음
- form과 filter가 좁은 화면에서 재배치
- `prefers-reduced-motion` 사용자의 불필요한 motion 감소

pixel-perfect 복사보다 content가 변해도 무너지지 않는 layout을 우선합니다.

## 저장 계약

`localStorage`는 외부 입력입니다. parse 실패와 잘못된 shape를 처리합니다.

```text
값 없음         → 빈 배열
JSON parse 실패 → 빈 배열 + 저장값 정리 또는 안전한 오류
배열 아님       → 거부
잘못된 task     → 전체 거부 또는 유효 항목만 정책적으로 선택
```

`JSON.parse(...) as Task[]`로 끝내지 않습니다. 비밀값은 저장하지 않습니다.

## URL 계약

```text
/                         → all
/?filter=open             → open
/?filter=done             → done
/?filter=unknown          → all로 정규화
```

filter button을 누르면 `history.pushState`로 URL을 바꾸고, `popstate`에서 URL을 다시 읽어 render합니다. URL과 별도 filter 변수를 각각 임의로 수정하지 않습니다.

## 오류와 경계 조건

- 공백 제목 거부
- 너무 긴 제목 처리
- 같은 제목 허용 여부 명시
- 저장소 quota·쓰기 실패 처리
- 잘못된 URL filter
- 작업 0개
- 모두 완료·모두 미완료
- 여러 번 빠른 클릭
- 새로고침과 back/forward

이 프로젝트는 server가 없으므로 여러 tab 동기화는 필수가 아닙니다. 확장하려면 `storage` event를 사용하되 충돌 정책을 먼저 정의합니다.

## 구현 순서

1. 정적 HTML과 CSS만으로 form·목록·filter를 만듭니다.
2. 메모리 task 배열과 순수 filter 함수를 만듭니다.
3. submit·toggle·delete event를 연결합니다.
4. 상태에서 DOM을 render합니다.
5. localStorage parse·save를 추가합니다.
6. URL filter와 `popstate`를 연결합니다.
7. keyboard·320px·잘못된 저장값 검사를 통과합니다.

각 단계마다 동작을 깨뜨린 뒤 관련 검사가 실패하는지 확인합니다.

## 자동 검증

저장소 루트에서 안전한 학습자 workspace를 한 번 생성한 뒤 검사합니다.

```sh
pnpm workspace:create 00-first-web-app
node exercises/00-first-web-app/tests/verify.mjs exercises/00-first-web-app/work
```

`skeleton/`을 복사한 직후의 `work/`는 실패해야 합니다. 구현을 진행하며 같은 명령의 실패 항목을 하나씩 줄이고, 완료 뒤에는 모두 통과시킵니다.

검증 항목:

- semantic form과 label
- keyboard focus와 submit
- 추가·완료·삭제
- URL filter와 history 복원
- localStorage 복원·잘못된 값 처리
- 320px overflow
- unsafe `innerHTML` 비사용

완료 후에만 reference를 확인합니다.

## 확장 과제

- inline title 편집과 취소
- 완료 작업 일괄 삭제
- `storage` event로 두 tab 동기화
- import/export JSON과 runtime validation
- 접근 가능한 drag 없이 keyboard reorder

확장은 기본 계약 검사를 계속 통과해야 합니다.

## 완료 기준

- framework 없이 browser 상태·DOM·URL·storage를 연결합니다.
- semantic HTML과 responsive CSS로 keyboard 사용이 가능합니다.
- 외부 저장값을 검증하고 실패 후 안전한 상태를 유지합니다.
- 새로고침·뒤로 가기·작은 화면을 실제 browser로 자동 검사합니다.
- 상태 정본과 파생된 DOM을 구분합니다.

## 다음 단계

기본 경로는 [`비동기 작업과 fetch`](../01-web-foundations/06-async-fetch-errors.md)부터 Part 01을 마치고 `01-runtime`으로 이어집니다. DB까지 완료한 뒤 선택형 self-directed 프로젝트가 필요할 때만 [`메모 API`](02-notes-api.md)를 수행합니다.
