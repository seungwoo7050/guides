# Task List

브라우저만으로 실행되는 작업 목록 애플리케이션입니다. 작업 추가·완료·삭제, URL 기반 필터, `localStorage` 복구, keyboard 접근성과 좁은 viewport 동작을 하나의 작은 static web application으로 묶습니다.

## Features

- 공백만 있는 작업 제목 거부와 최대 길이 제한
- 완료 상태 변경과 삭제
- `all`, `open`, `done` 필터를 URL query에 반영
- 뒤로 가기·앞으로 가기에서 필터 복구
- 손상된 `localStorage` 데이터를 안전하게 무시
- 사용자 입력을 `textContent`로만 출력
- skip link, live status, visible focus와 320px 대응

## Architecture

`index.html`이 semantic DOM과 accessibility contract를 정의합니다. `app.js`의 task array가 작업 상태를 소유하고, URL이 현재 filter의 source of truth입니다. 화면은 `render()`를 통해서만 projection되며 저장 데이터는 로드할 때 다시 검증합니다.

## Run

```sh
npm run serve
```

브라우저에서 `http://localhost:8080`을 엽니다. 별도 build 단계는 없습니다.

## Tests

```sh
npm test
```

Project-local test는 semantic anchor, unsafe DOM insertion 금지, storage/history recovery와 responsive/focus contract를 검사합니다.

## Major design decisions

- URL과 task collection의 소유권을 분리해 filter navigation이 browser history와 일치하도록 했습니다.
- `innerHTML`을 사용하지 않아 저장되거나 입력된 문자열이 markup으로 해석되지 않습니다.
- 저장 데이터를 신뢰하지 않고 shape와 값의 유효성을 다시 확인합니다.
- list-level event delegation으로 동적 item의 listener lifecycle을 단순화합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | --- | --- |
| 1 | Semantic accessibility boundary | `index.html` |
| 2 | Responsive focus-safe presentation | `style.css` |
| 3 | State ownership and initial projection | `app.js` |
| 4 | Submission validation and immutable insertion | `app.js` |
| 5 | Delegated mutation and rendering | `app.js` |
| 6 | Storage and URL recovery | `app.js` |

## Scope and limitations

Data는 현재 browser profile의 `localStorage`에만 저장됩니다. 계정 동기화, server persistence, 공유 목록, drag-and-drop과 due date는 구현하지 않습니다.
