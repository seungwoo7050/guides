# 웹은 어떻게 동작하는가

브라우저 주소창에 URL을 입력한다고 HTML 파일 하나가 바로 나타나는 것은 아닙니다. 브라우저는 URL을 해석해 서버에 HTTP 요청을 보내고, 응답을 받은 뒤 필요한 추가 리소스를 요청하고 JavaScript를 실행합니다. 첫 웹 애플리케이션을 만들기 위해 이 과정을 모두 외울 필요는 없지만, **코드가 어디에서 실행되며 어느 구간에서 오류가 발생했는지**는 구분할 수 있어야 합니다.

## 목표

- URL, 클라이언트, 서버, 요청, 응답을 구분합니다.
- HTML·CSS·JavaScript와 JSON API의 역할을 구분합니다.
- `localhost`와 포트가 무엇을 가리키는지 설명합니다.
- 브라우저 개발자 도구에서 요청과 응답을 확인합니다.

## URL은 요청 대상을 나타냅니다

다음 URL을 구성 요소별로 나눠 봅니다.

```text
https://example.com:443/boards/42?view=activity#latest
```

| 부분 | 의미 |
|---|---|
| `https` | 통신 방식과 TLS 사용 여부를 나타내는 스킴(scheme) |
| `example.com` | 연결할 호스트 이름 |
| `443` | 호스트에서 연결할 네트워크 서비스의 포트 번호 |
| `/boards/42` | 서버가 해석할 경로(path) |
| `view=activity` | 요청 조건을 전달하는 쿼리 문자열(query string) |
| `latest` | 서버에 전송되지 않고 브라우저가 문서 안에서 사용하는 프래그먼트(fragment) |

`localhost`는 현재 컴퓨터 자신을 가리키는 호스트 이름입니다. `http://localhost:3000`과 `http://localhost:4000`은 같은 컴퓨터를 가리키지만 포트가 다르므로 서로 다른 서버 프로세스에 연결될 수 있습니다. 프런트엔드 개발 서버, API 서버, 데이터베이스가 서로 다른 포트를 사용하는 이유도 여기에 있습니다.

## HTTP 요청과 응답

기본적인 HTTP 요청은 메서드, 요청 대상, 헤더로 구성됩니다.

```http
GET /boards/42 HTTP/1.1
Host: localhost:4000
Accept: application/json
```

서버는 상태 줄, 헤더, 선택적인 본문으로 응답합니다.

```http
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{"id":"42","title":"학습 보드"}
```

`200`은 네트워크 연결만 성공했다는 뜻이 아니라 서버가 요청을 정상적으로 처리했음을 나타내는 HTTP 상태 코드입니다. `404`, `409`, `500`도 서버가 반환한 유효한 HTTP 응답입니다. 반면 서버가 실행되지 않아 연결 자체가 거부되면 HTTP 응답과 상태 코드는 존재하지 않습니다.

다음 오류를 서로 구분해야 합니다.

| 관찰 결과 | 가능한 원인 |
|---|---|
| `ERR_CONNECTION_REFUSED` | 해당 호스트와 포트에서 연결을 받는 프로세스가 없음 |
| `404` | 서버에는 도달했지만 요청한 라우트나 리소스를 찾지 못함 |
| `500` | 요청은 서버에 도달했지만 내부 처리 중 오류가 발생함 |
| JSON 파싱 오류 | 응답 본문이 예상한 형식이 아니거나 중간 프록시가 다른 응답을 반환함 |
| 화면의 데이터만 오래됨 | 요청 순서, 캐시, 클라이언트 상태 처리에 문제가 있을 수 있음 |

## HTML, CSS와 JavaScript

브라우저는 HTML을 문서 구조로 해석하고 CSS를 적용한 뒤 JavaScript를 실행합니다.

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

HTML은 주로 콘텐츠의 의미와 구조를, CSS는 배치와 표현을, JavaScript는 상태 변화에 따른 동작을 담당합니다. 이 구분이 절대적인 규칙은 아니지만, 의미 없는 `div`를 JavaScript로 버튼처럼 동작하게 만들거나 CSS로 문서 순서를 뒤집으면 브라우저가 기본으로 제공하는 기능을 직접 다시 구현해야 합니다.

## 정적 리소스와 API

브라우저가 처음 받는 HTML과 화면에서 나중에 가져오는 JSON은 서로 다른 HTTP 요청입니다.

```text
GET /                    → HTML
GET /style.css           → CSS
GET /app.js              → JavaScript
GET /api/boards          → JSON
POST /api/boards         → 상태 변경 요청
```

개발자 도구의 Network 탭에서 요청 하나를 선택하고 다음 항목을 확인합니다.

- Request URL과 HTTP 메서드
- 요청 헤더(Request Headers)
- 요청 본문(Request Payload)
- 응답 상태 코드(Status Code)
- 응답 헤더(Response Headers)
- 응답 본문(Response)
- 요청 시작, 대기, 다운로드에 걸린 시간

Console의 오류 메시지만 보는 것보다 Network 탭에서 실제 전송 결과를 먼저 확인하는 편이 원인을 정확하게 찾는 데 유리합니다.

## 브라우저와 서버 사이의 신뢰 경계

브라우저 코드는 사용자의 기기에서 실행됩니다. 사용자는 JavaScript를 수정하거나 화면에 없는 HTTP 요청을 직접 보낼 수 있습니다. 따라서 서버는 다음 항목을 요청마다 다시 검증해야 합니다.

- 요청 본문과 쿼리의 형식
- 로그인 상태
- 리소스 접근 권한
- 가격, 역할, 버전, 좌표 범위
- 원자적으로 처리해야 하는 데이터베이스 변경

클라이언트 검증은 사용성을 높이기 위한 것이며, 데이터 무결성과 보안을 보장하는 서버 검증을 대신하지 못합니다.

## 직접 확인하기

정적 파일 서버를 시작합니다.

```sh
node scripts/serve-static.mjs exercises/00-first-web-app/skeleton 8080
```

브라우저에서 `http://127.0.0.1:8080`을 열고 Network 탭에서 HTML 요청을 확인합니다. 이 단계에서는 완성된 구현이 필요하지 않으므로 `reference/`를 먼저 실행하지 않습니다. 존재하지 않는 `/missing.html`을 열어 404 응답도 확인합니다. 서버 프로세스를 종료한 뒤 페이지를 다시 열어 연결 실패와 HTTP 404의 차이를 비교합니다.

## 흔한 오류

- URL 전체를 하나의 문자열로만 보고 호스트·포트·경로 문제를 구분하지 못합니다.
- 네트워크 연결 오류와 HTTP 오류 응답을 같은 것으로 취급합니다.
- TypeScript로 작성한 클라이언트가 보낸 값이므로 안전하다고 가정합니다.
- 프런트엔드 개발 서버와 API 서버가 항상 같은 프로세스라고 가정합니다.

## 완료 기준

- `http://localhost:3000/boards/1?q=mine`의 각 구성 요소를 설명할 수 있습니다.
- 연결 실패, HTTP 404, JSON 파싱 실패가 발생하는 구간을 구분할 수 있습니다.
- HTML·CSS·JavaScript·JSON 요청의 역할을 각각 설명할 수 있습니다.
- 개발자 도구에서 요청 메서드, 상태 코드, 응답 본문을 확인할 수 있습니다.

## 다음 단계

브라우저가 기본으로 제공하는 문서 의미와 폼 동작을 활용하려면 [`HTML 폼과 접근성`](02-html-forms-accessibility.md)으로 이동합니다.
