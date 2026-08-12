# 웹은 어떻게 동작하는가

브라우저 주소창에 URL을 입력하면 HTML 파일 하나가 마법처럼 나타나는 것이 아닙니다. 브라우저는 주소를 해석하고 서버에 HTTP 요청을 보내며, 응답을 받은 뒤 추가 자원을 요청하고 JavaScript를 실행합니다. 첫 웹 앱을 시작하려면 이 전체를 암기할 필요는 없지만, **어느 코드가 어디서 실행되고 실패가 어느 경계에서 발생했는지** 구분할 수 있어야 합니다.

## 목표

- URL, client, server, request와 response를 구분합니다.
- HTML·CSS·JavaScript와 JSON API의 역할을 구분합니다.
- `localhost`와 port가 무엇을 가리키는지 설명합니다.
- browser developer tools에서 요청·상태·응답을 관찰합니다.

## URL은 요청 대상을 표현합니다

다음 URL을 나누어 봅니다.

```text
https://example.com:443/boards/42?view=activity#latest
```

| 부분 | 의미 |
|---|---|
| `https` | 통신 규칙과 TLS 사용 여부를 정하는 scheme |
| `example.com` | 연결할 host 이름 |
| `443` | host 안의 어떤 server process에 연결할지 정하는 port |
| `/boards/42` | 서버가 해석할 path |
| `view=activity` | path 안의 표현 방식을 추가로 정하는 query |
| `latest` | 서버에 보내지 않고 브라우저 문서 안에서 사용하는 fragment |

`localhost`는 “현재 내 컴퓨터”를 뜻합니다. `http://localhost:3000`과 `http://localhost:4000`은 같은 컴퓨터라도 서로 다른 port를 듣는 별도 process일 수 있습니다. frontend 개발 server, API server와 database가 각자 다른 port를 사용하는 이유입니다.

## HTTP 요청과 응답

가장 작은 요청은 method, target과 header를 가집니다.

```http
GET /boards/42 HTTP/1.1
Host: localhost:4000
Accept: application/json
```

서버는 status, header와 선택적인 body로 응답합니다.

```http
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{"id":"42","title":"학습 보드"}
```

`200`은 네트워크 연결만 성공했다는 뜻이 아니라 요청을 정상 처리했다는 애플리케이션 계약입니다. `404`, `409`, `500`도 모두 HTTP 응답일 수 있습니다. 반면 server가 실행되지 않아 연결 자체가 거부된 경우에는 HTTP status가 존재하지 않습니다.

다음 실패를 구분합니다.

| 관찰 | 가능한 경계 |
|---|---|
| `ERR_CONNECTION_REFUSED` | 해당 host·port에 듣는 process가 없음 |
| `404` | server에는 도달했지만 route나 자원을 찾지 못함 |
| `500` | 요청은 도달했지만 server 내부 처리 실패 |
| JSON parse 오류 | body가 예상 형식이 아니거나 중간 proxy가 다른 응답을 보냄 |
| 화면만 오래됨 | 요청 순서, cache 또는 client state 문제일 수 있음 |

## HTML, CSS와 JavaScript

브라우저는 HTML을 문서 구조로 해석하고 CSS를 적용하며 JavaScript를 실행합니다.

```html
<h1>내 보드</h1>
<button type="button">새 보드</button>
```

```css
button { font: inherit; }
```

```js
document.querySelector("button").addEventListener("click", () => {
  console.log("클릭");
});
```

HTML은 “무엇인가”, CSS는 “어떻게 배치하고 표현하는가”, JavaScript는 “상태가 바뀔 때 무엇을 하는가”를 주로 담당합니다. 이 경계가 절대적인 것은 아니지만, 의미 없는 `div`를 JavaScript로 button처럼 만들거나 CSS로 문서 순서를 뒤집으면 브라우저가 이미 제공하는 기능을 다시 구현해야 합니다.

## 정적 자원과 API

브라우저가 처음 받는 HTML과, 화면에서 나중에 가져오는 JSON은 서로 다른 요청입니다.

```text
GET /                    → HTML
GET /style.css           → CSS
GET /app.js              → JavaScript
GET /api/boards          → JSON
POST /api/boards         → 상태 변경 요청
```

Network 탭에서 요청 하나를 선택해 다음을 확인합니다.

- Request URL과 method
- Request headers
- Request payload
- Response status
- Response headers
- Response body
- 요청 시작·대기·다운로드 시간

Console 오류만 보는 습관보다 Network에서 실제 전송 결과를 먼저 보는 편이 정확합니다.

## browser와 server의 신뢰 경계

브라우저 코드는 사용자의 기기에서 실행됩니다. 사용자는 JavaScript를 수정하거나 화면에 없는 HTTP 요청을 직접 보낼 수 있습니다. 따라서 다음은 server가 다시 확인해야 합니다.

- 요청 body와 query의 형식
- 로그인 상태
- 자원 접근 권한
- 가격, 역할, version과 좌표 범위
- 함께 성공해야 하는 database 변경

화면 검사는 사용 경험을 위한 것이고 server 검사는 데이터 계약을 위한 것입니다.

## 작은 관찰

정적 파일 server를 시작합니다.

```sh
node scripts/serve-static.mjs exercises/00-first-web-app/skeleton 8080
```

브라우저에서 `http://127.0.0.1:8080`을 열고 Network 탭에서 HTML 요청을 확인합니다. 이 관찰에는 완성 구현이 필요하지 않으므로 `reference/`를 먼저 실행하지 않습니다. 존재하지 않는 `/missing.html`을 열어 404가 어떻게 보이는지도 확인합니다. server process를 종료한 뒤 다시 열어 연결 실패와 HTTP 404의 차이를 비교합니다.

## 실패 조건

- URL 전체를 하나의 문자열로만 보고 host·port·path 문제를 구분하지 못합니다.
- Network 오류와 HTTP 오류를 같은 것으로 취급합니다.
- browser가 보낸 값은 TypeScript client가 만들었으므로 안전하다고 가정합니다.
- frontend 개발 server와 API server가 같은 process라고 가정합니다.

## 완료 기준

- `http://localhost:3000/boards/1?q=mine`의 각 부분을 설명할 수 있습니다.
- 연결 실패, HTTP 404와 JSON parse 실패의 경계를 구분할 수 있습니다.
- HTML·CSS·JavaScript·JSON 요청이 각각 어떤 역할을 하는지 설명할 수 있습니다.
- 개발자 도구에서 요청 method, status와 response body를 확인할 수 있습니다.

## 다음 단계

브라우저가 이미 제공하는 문서 의미와 폼 동작을 보존하려면 [`HTML 폼과 접근성`](02-html-forms-accessibility.md)으로 이동합니다.
