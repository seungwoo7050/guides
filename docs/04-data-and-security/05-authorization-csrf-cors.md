# 권한, CSRF와 CORS

로그인했다는 사실은 모든 자원을 읽고 수정할 수 있다는 뜻이 아닙니다. 화면에서 버튼을 숨기는 것은 사용자 안내일 뿐이고, HTTP와 WebSocket의 모든 변경 경계에서 서버가 현재 사용자·자원·동작을 다시 판정해야 합니다.

## 목표

- 인증과 권한 판정을 구분합니다.
- 역할과 자원 소유권을 한 정책으로 표현합니다.
- 401, 403과 존재 은닉을 위한 404 정책을 구분합니다.
- cookie 인증에서 CSRF를 방어합니다.
- CORS를 browser 읽기 권한 계약으로 정확히 설정합니다.
- HTTP와 WebSocket에 동일한 업무 권한을 적용합니다.

## 인증과 권한

```text
인증(authentication) → 누구인가
권한(authorization)   → 이 자원에 이 동작을 할 수 있는가
```

예를 들어 `viewer`는 메모를 읽을 수 있지만 수정할 수 없습니다.

| 역할 | 읽기 | 내용 수정 | 구성원 관리 | 삭제 |
|---|---:|---:|---:|---:|
| owner | 가능 | 가능 | 가능 | 가능 |
| editor | 가능 | 가능 | 불가 | 불가 |
| viewer | 가능 | 불가 | 불가 | 불가 |

표는 출발점입니다. 실제 판정에는 계정 상태, 자원 보관 여부, 요청 대상 사용자와 현재 역할도 포함될 수 있습니다.

## 정책을 서버의 한 위치에 둡니다

```ts
function assertCanEditNote(actor: Actor, membership: Membership, note: Note): void {
  if (actor.accountStatus !== "active") throw new Forbidden("account_inactive");
  if (note.archivedAt) throw new Conflict("note_archived");
  if (!(["owner", "editor"] as const).includes(membership.role)) {
    throw new Forbidden("note_write_forbidden");
  }
}
```

HTTP route, service와 WebSocket handler가 서로 다른 role table을 복사하지 않습니다. transport는 actor와 command를 만들고 같은 policy를 호출합니다.

권한 판정에 필요한 데이터를 client가 보낸 role로 믿지 않습니다. membership은 server가 DB나 신뢰할 수 있는 cache에서 조회합니다.

## 자원 범위를 query에 포함합니다

먼저 note를 ID로 읽고 나중에 owner를 확인하는 대신, 보이는 자원만 조회할 수 있습니다.

```sql
select n.id, n.title, m.role
from notes n
join note_members m on m.note_id = n.id
where n.id = $1 and m.user_id = $2;
```

이 방식은 실수로 권한 확인 전 데이터를 사용하거나 로그에 노출하는 위험을 줄입니다. 단, 서비스가 404와 403 중 무엇을 반환할지 제품 정책을 정해야 합니다.

## 401, 403, 404

- **401 Unauthorized**: 유효한 인증 정보가 없습니다.
- **403 Forbidden**: 사용자를 알지만 이 동작은 허용되지 않습니다.
- **404 Not Found**: 자원 없음 또는 존재 자체를 숨기는 정책입니다.

다른 사용자의 private note 존재를 알릴 필요가 없다면 읽기 요청에 404를 사용할 수 있습니다. 관리 화면처럼 권한 부족을 명확히 알려야 하면 403이 적절할 수 있습니다. 같은 API에서 정책을 일관되게 유지합니다.

## IDOR를 막습니다

URL의 식별자를 바꾸어 다른 사용자 자원을 수정할 수 있는 문제를 방지합니다.

```text
PATCH /notes/{noteId}
```

`noteId`가 형식상 유효하다는 것과 actor가 해당 note를 수정할 수 있다는 것은 별개입니다. 목록에 보였는지, UI에 버튼이 있었는지와 관계없이 서버에서 검사합니다.

## 권한 변경 자체의 규칙

구성원 role을 바꾸는 API는 일반 수정 API보다 강한 규칙이 필요합니다.

- owner만 변경 가능
- 마지막 owner를 viewer로 내릴 수 없음
- 자신의 권한 상승 불가
- 정지된 사용자를 초대할 수 없음
- 변경 전후 role과 actor를 감사 기록으로 저장
- membership 변경과 audit event를 한 transaction으로 처리

권한 체계가 자기 자신을 깨뜨리지 않게 불변식을 정의합니다.

## CSRF의 원인

browser는 다른 사이트에서 온 요청에도 대상 domain의 cookie를 자동으로 붙일 수 있습니다. 공격 페이지가 사용자의 cookie를 읽지 못해도 상태 변경 요청을 보낼 수 있습니다.

cookie 기반 인증의 상태 변경 요청에는 여러 방어를 조합합니다.

1. `SameSite=Lax` 또는 더 엄격한 정책
2. HTTPS와 `Secure`
3. `Origin` 또는 필요한 경우 `Referer`의 정확한 검증
4. CSRF token
5. 상태 변경에 GET을 사용하지 않음

`SameSite` 하나만 모든 browser·navigation·subdomain 조건을 해결한다고 가정하지 않습니다.

## Origin 검증

```ts
function requireTrustedOrigin(origin: string | undefined, allowed: Set<string>): void {
  if (!origin || !allowed.has(origin)) throw new Forbidden("untrusted_origin");
}
```

문자열 prefix나 suffix로 검사하면 `https://trusted.example.attacker.test` 같은 값을 허용할 수 있습니다. URL을 정규화하고 정확한 origin 집합과 비교합니다.

non-browser client처럼 `Origin`이 없는 요청을 허용할지는 endpoint와 인증 방식에 따라 별도 정책을 둡니다.

## CSRF token

server session에 연결된 예측 불가능한 token을 form 또는 response로 제공하고 상태 변경 요청 header/body에서 확인할 수 있습니다. double-submit cookie 방식을 사용할 수도 있지만 cookie와 request value의 무결성·same-site 조건을 정확히 이해해야 합니다.

token은 다음을 만족해야 합니다.

- 공격 사이트가 읽을 수 없음
- session과 연결되거나 검증 가능한 서명 포함
- 안전한 비교 사용
- 로그에 원문 미기록
- logout·session 회전 시 함께 갱신 정책

## CORS는 서버 접근 제어 전체가 아닙니다

CORS는 browser가 다른 origin의 response를 JavaScript에 노출할지 결정하는 protocol입니다. curl이나 server-to-server 요청을 차단하지 않으며 권한 검사를 대신하지 않습니다.

credential을 허용할 때는 wildcard origin을 사용할 수 없습니다.

```ts
const allowedOrigins = new Set([
  "https://app.example.com",
  "https://admin.example.com"
]);
```

요청 origin을 무조건 그대로 반사하지 않습니다. preflight에서 method·header를 필요한 범위로 제한하고 `Vary: Origin`이 필요한 cache 동작도 고려합니다.

## WebSocket upgrade

WebSocket도 browser cookie를 보낼 수 있습니다. upgrade 시 다음을 검사합니다.

- 정확한 `Origin`
- session cookie와 만료
- 계정 상태
- 연결 후 `board.join`의 membership

연결 이후 역할이 바뀌거나 계정이 정지될 수 있으므로 각 변경 message에서도 현재 권한을 다시 검사하거나 신뢰 가능한 짧은 cache 정책을 사용합니다.

## 관리자 기능

“admin” boolean 하나로 모든 작업을 허용하기보다 필요한 capability와 감사 요구를 정합니다.

- 대상 사용자와 actor가 같은지
- 자기 자신을 정지할 수 있는지
- 사유가 필요한지
- session 폐기와 audit 기록이 함께 성공하는지
- 민감 조회가 별도 권한인지

관리자 API는 UI 경로가 숨겨졌다는 이유로 공개 route보다 약하게 검사하지 않습니다.

## 검증 행렬

각 변경 API마다 최소한 다음을 검사합니다.

```text
인증 없음               → 401
구성원 아님             → 403 또는 정책상 404
viewer                  → 읽기 성공, 쓰기 거부
editor                  → 내용 쓰기 성공, 역할 변경 거부
owner                   → 허용된 관리 작업 성공
다른 사용자 자원 ID     → 거부
신뢰하지 않은 Origin    → 거부
로그아웃한 session       → 401
정지된 계정의 기존 session → 401 또는 403 정책
```

HTTP와 WebSocket에 같은 행렬을 적용합니다.

## 실패 조건

- UI에서 버튼을 숨긴 것으로 권한 검사를 끝냅니다.
- client가 보낸 role을 신뢰합니다.
- ID 형식 검증을 ownership 검증으로 착각합니다.
- CORS를 인증·권한 방어로 설명합니다.
- credential 요청에서 origin을 그대로 반사합니다.
- cookie 인증 상태 변경에 CSRF 방어가 없습니다.
- WebSocket 연결 때만 권한을 확인하고 이후 message는 모두 허용합니다.

## 연결 실습

[`세션과 권한`](../../exercises/06-security/README.md)에서 401·403, ownership, cookie 삭제와 CORS 취약점을 실제 요청으로 수정합니다.

## 완료 기준

- 인증과 자원별 권한 판정을 분리합니다.
- HTTP·WebSocket이 같은 role·ownership 정책을 사용합니다.
- 401·403·404 선택 근거를 설명합니다.
- cookie 인증의 CSRF 방어와 CORS의 실제 역할을 구분합니다.
- 권한 변경과 관리자 작업의 불변식·감사 기록을 설계합니다.

## 다음 단계

먼저 [`세션과 권한`](../../exercises/06-security/README.md)의 생성된 `work/`에서 session 폐기·role·ownership·Origin 계약을 검증하고 완료 뒤 `reference/`와 비교합니다. 원한다면 이 시점에 자동 verifier나 reference가 없는 선택형 [`공유 메모 expected-evidence brief`](../06-capstones/03-shared-notes.md)를 수행합니다. 기본 경로는 [`WebSocket 프로토콜`](../05-realtime-and-quality/01-websocket-protocol.md)로 이어집니다.
