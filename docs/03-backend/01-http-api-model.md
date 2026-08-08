# HTTP API 모델

HTTP API는 JSON을 주고받는 함수 호출이 아닙니다. method, target, status, header, body와 cache·인증 의미를 가진 공개 계약입니다. 좋은 API는 정상 응답뿐 아니라 잘못된 입력, 권한 부족, 없는 자원, 충돌과 내부 실패를 안정적으로 구분합니다.

## 목표

- resource와 use case에 맞는 method·path를 선택합니다.
- request의 path·query·header·body를 구분합니다.
- status code와 안정된 오류 body를 설계합니다.
- idempotency, pagination과 version conflict의 기본 계약을 이해합니다.
- transport와 domain 책임을 분리합니다.

## resource와 path

```text
GET    /boards
POST   /boards
GET    /boards/:id
PATCH  /boards/:id
DELETE /boards/:id
GET    /boards/:id/activity
```

path에는 자원의 identity와 관계를, query에는 filtering·sorting·pagination을 주로 표현합니다.

```text
GET /boards?role=editor&cursor=abc&limit=20
```

모든 동작을 `/doSomething` POST로 만들면 cache, idempotency와 관찰 가능한 의미가 사라집니다. 반대로 복잡한 업무 command를 억지로 CRUD 한 단어에 맞추지 않습니다.

## method의 기본 의미

| method | 일반적 의미 | 반복 요청 |
|---|---|---|
| GET | 읽기 | 안전하고 idempotent여야 함 |
| POST | collection 생성·command | 자동으로 idempotent하지 않음 |
| PUT | resource 전체 대체 | 같은 요청은 idempotent하도록 설계 |
| PATCH | 부분 변경 | operation에 따라 다름 |
| DELETE | 삭제 | 같은 최종 상태를 목표로 함 |

GET에서 상태를 변경하지 않습니다. browser·proxy·crawler가 미리 요청할 수 있습니다.

## 입력 위치

- path parameter: 어떤 resource인지
- query: 읽기 범위·표현 방식
- header: 인증, 조건부 요청, content negotiation, trace
- body: 생성·변경할 구조화 data

모두 외부 입력입니다. TypeScript client가 만든 요청이라도 server에서 runtime 검증합니다.

## 상태 코드

| 상태 | 계약 |
|---:|---|
| 200 | 성공, 응답 body 있음 |
| 201 | resource 생성, 필요하면 `Location` 제공 |
| 204 | 성공, 응답 body 없음 |
| 400 | 요청 형식·값이 계약에 맞지 않음 |
| 401 | 유효한 인증 정보가 없음 |
| 403 | 신원은 알지만 작업 권한이 없음 |
| 404 | route 또는 보이는 resource가 없음 |
| 409 | 현재 상태·version·uniqueness와 충돌 |
| 429 | 허용된 요청 속도 초과 |
| 500 | 예상하지 못한 server 실패 |
| 503 | 일시적으로 준비되지 않음 |

모든 실패를 200과 `{ success: false }`로 보내면 browser·proxy·monitoring과 client의 표준 의미를 잃습니다.

## 안정된 오류 body

```json
{
  "code": "invalid_request",
  "message": "요청 형식이 올바르지 않습니다.",
  "details": [
    { "path": "title", "reason": "too_long" }
  ],
  "requestId": "req_01..."
}
```

`code`는 client 분기용으로 안정적으로 유지하고, `message`는 사용자에게 보여 줄 수 있는 일반 문장입니다. stack trace, SQL, file path, token과 개인정보를 응답하지 않습니다. validation detail의 공개 범위도 정합니다.

## 자원 존재와 권한

권한 없는 사용자가 resource 존재 여부를 알면 안 되는 제품에서는 403 대신 404를 반환할 수 있습니다. 이는 무조건적인 보안 규칙이 아니라 외부 계약 선택입니다. 내부 log에는 실제 판정 원인을 남깁니다.

## pagination

큰 collection을 무제한 반환하지 않습니다.

```text
GET /activity?cursor=evt_42&limit=50
```

cursor는 정렬 기준과 함께 안정적이어야 합니다. offset pagination은 중간 삽입·삭제에서 중복·누락이 생길 수 있습니다. 작은 관리 화면에서는 offset이 충분할 수 있지만 trade-off를 명시합니다.

## version conflict

client가 읽은 version과 현재 version이 같은 경우에만 갱신할 수 있습니다.

```http
PATCH /boards/42/items/7
If-Match: "12"
```

또는 body에 `baseVersion`을 포함할 수 있습니다. 오래된 요청은 409나 412로 거부하고 현재 값 또는 다시 가져올 방법을 제공합니다. last-write-wins를 선택한다면 사용자 변경 유실을 받아들이는 계약임을 명시합니다.

## idempotency

network timeout 뒤 POST가 처리됐는지 알 수 없는 경우 client가 재시도할 수 있습니다. 중복 효과가 위험한 command는 idempotency key를 받을 수 있습니다.

```http
Idempotency-Key: 3f3c...
```

server는 key의 scope, 보관 기간, 같은 key·다른 body 처리와 결과 재사용을 정의합니다. 단순 header 이름 추가만으로 exactly-once 효과가 생기지 않습니다.

## content type과 body 제한

요청·응답 `Content-Type`을 확인하고 예상하지 않은 큰 body를 제한합니다. JSON parser 실패와 schema 실패를 구분하되 외부 오류 계약은 안정적으로 유지합니다.

## 실패 조건

- GET이 상태를 변경합니다.
- 모든 오류를 200 또는 500으로 반환합니다.
- validation library의 내부 오류를 그대로 노출합니다.
- collection에 limit가 없습니다.
- concurrent update에서 version 계약이 없습니다.
- timeout 뒤 위험한 POST를 무조건 재시도합니다.

## 연결 실습

[`Fastify와 Zod API`](../../exercises/04-fastify-zod-api/README.md)에서 400·404·409와 app error 변환을 실제 요청으로 검사합니다.

## 완료 기준

- resource path, method와 입력 위치를 선택한 이유를 설명합니다.
- 400·401·403·404·409·500을 구분합니다.
- client가 분기할 안정된 오류 code를 제공합니다.
- collection pagination과 concurrent update 계약을 정의합니다.
- 재시도 가능한 command와 그렇지 않은 command를 구분합니다.

## 다음 단계

이 계약을 app 생성·plugin·hook·종료 수명에 연결하려면 [`Fastify 생명주기`](02-fastify-lifecycle.md)로 이동합니다.
