# Browser Directory

URL query를 search state의 source of truth로 사용하는 static 문서 검색 애플리케이션입니다. 검색 결과를 안전한 DOM API로 생성하고 browser history, keyboard navigation과 narrow viewport 동작을 함께 보존합니다.

## Features

- 제목과 본문을 대상으로 한 대소문자 비구분 검색
- `?q=` query parameter로 공유 가능한 검색 상태 제공
- submit 시 `history.pushState()` 사용
- 뒤로 가기·앞으로 가기에서 `popstate` 기반 복구
- `textContent`만 사용하는 결과 projection
- live result count, skip link, visible focus
- responsive card grid

## Run

```sh
npm run serve
```

`http://localhost:8080`을 열고 검색어를 입력합니다. 예를 들어 `api`를 검색하면 URL이 `?q=api`로 바뀝니다.

## Tests

```sh
npm test
```

Tests는 semantic structure, URL ownership, unsafe markup insertion 금지와 responsive contract를 검사합니다.

## Architecture

Static corpus와 DOM handles는 `app.js`가 소유합니다. 현재 query는 별도 global state에 복제하지 않고 URL에서 읽습니다. `render()`는 query를 받아 filtered collection을 만들고 결과 DOM을 완전히 교체합니다.

## Major design decisions

- 검색 상태를 URL에 두어 reload, link sharing과 history navigation이 동일한 contract를 사용합니다.
- `popstate`에서 과거 object snapshot을 재사용하지 않고 destination URL을 다시 parse합니다.
- Result card는 `createElement()`와 `textContent`로만 생성합니다.
- Result count는 `role="status"`를 통해 assistive technology에 전달됩니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | --- | --- |
| 1 | Semantic search boundary | `index.html` |
| 2 | Responsive focus-safe layout | `style.css` |
| 3 | Search corpus ownership | `app.js` |
| 4 | URL state derivation | `app.js` |
| 5 | Safe DOM projection | `app.js` |
| 6 | Submitted history transition | `app.js` |
| 7 | History navigation recovery | `app.js` |

## Scope and limitations

검색 corpus는 source에 고정되어 있으며 ranking, highlighting, typo tolerance, remote index와 pagination은 구현하지 않습니다.
