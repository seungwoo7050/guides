# network·session·오류 계약

모바일에서 `connected`는 API 요청이 성공한다는 뜻이 아니다. radio 전환, captive portal, VPN, app background, DNS·TLS 문제와 server timeout이 같은 사용자 동작 중에 바뀔 수 있다.

이 장은 `web-app`의 HTTP·session 기초나 `computer-networks`의 DNS·TLS 장애 분리를 다시 가르치지 않는다. 그 지식을 전제로 **process가 중단되고 연결이 바뀌는 모바일 client에서 request, credential과 outbox를 어떻게 소유하고 복원하는지**만 다룬다. backend 운영은 `web-infra`, 위협 모델과 공격 검증은 `cybersecurity`의 비소유 범위다.

## 목표

- device 연결 상태와 실제 API 도달 가능성을 구분한다.
- 요청·응답·업무 결과의 세 계약을 분리한다.
- credential을 일반 local data와 다른 저장소·수명으로 관리한다.
- retry 가능한 operation과 그렇지 않은 operation을 식별한다.
- cancellation, timeout와 stale response 거절을 함께 사용한다.
- offline·unauthorized·forbidden·conflict·malformed response를 다른 UI 상태로 만든다.
- app foreground 복귀 뒤 session과 remote state를 안전하게 재검증한다.

연결 실습은 [Stage 02](../exercises/field-notes/specs/02-offline-records.md)와 [Stage 04](../exercises/field-notes/specs/04-sync-conflicts.md)다.

## network state는 힌트입니다

network API는 현재 연결 유형이나 인터넷 가능성을 알려 줄 수 있다. 하지만 다음을 보장하지 않는다.

- 특정 hostname의 DNS가 성공한다.
- TLS handshake가 성공한다.
- VPN·proxy·firewall가 endpoint를 허용한다.
- captive portal을 통과했다.
- server가 요청을 처리한다.
- upload가 끝날 때까지 연결이 유지된다.

따라서 `isConnected === true`이면 성공 화면을 미리 확정하지 않는다. 반대로 `offline` 신호는 불필요한 요청을 줄이고 pending 상태를 설명하는 데 사용할 수 있다.

```text
network hint
+ 실제 request 결과
+ local outbox 상태
= 사용자에게 보여 줄 연결·동기화 상태
```

## transport와 application 결과를 나눕니다

한 요청은 적어도 다음 단계를 거친다.

```text
request 준비
→ DNS·연결·TLS
→ HTTP response
→ body decode
→ runtime schema 검증
→ 업무 결과 해석
→ local transaction
```

오류 종류:

| 종류 | 예 | 기본 정책 |
|---|---|---|
| cancellation | 새 검색, app 종료 | 사용자 오류로 표시하지 않음 |
| timeout/transport | 연결 단절 | 안전하면 pending·retry |
| HTTP auth | 401 | refresh 또는 재로그인 |
| HTTP authorization | 403 | 권한 없음, retry 금지 |
| not found | 404 | 삭제·scope 변경 재조정 |
| conflict | 409/업무 conflict | local·remote 둘 다 보존 |
| server failure | 5xx | operation 성격에 따라 retry |
| malformed body | JSON/schema 불일치 | 외부 계약 오류, 기존 안전 상태 보존 |
| stale response | 이전 generation | 조용히 폐기 |

모든 실패를 `네트워크 오류`로 표시하면 사용자는 재시도해도 해결되지 않는 권한·충돌 문제를 알 수 없다.

## 외부 response는 runtime에서 검증합니다

TypeScript type은 network body를 검증하지 않는다.

```ts
const raw: unknown = await response.json();
const result = parseSyncResponse(raw);
```

검증할 것:

- required field와 enum
- id·version 형식
- 배열 item 중복
- timestamp·number 범위
- nullable과 absent의 의미
- 성공 response와 error response의 구분

malformed response를 local database에 일부 저장하지 않는다. parse가 끝난 뒤 transaction을 시작한다.

## session의 수명과 저장소를 분리합니다

일반적인 구분:

```text
access token
- 짧은 수명
- memory 우선
- request authorization

refresh token 또는 장기 credential
- secure storage
- rotation·revocation 고려
- 로그와 일반 database에서 제외

user profile·tenant id
- local cache 가능
- 현재 session과 일치 여부 검증
```

SecureStore 같은 platform-backed 저장소는 작은 credential을 위한 것이다. 큰 record나 image를 넣지 않는다. 반대로 AsyncStorage나 일반 SQLite에 bearer token을 평문으로 저장하지 않는다.

biometric prompt는 server authentication을 대신하지 않는다. local credential 사용 전에 사용자를 확인하는 장치일 수 있지만 token의 서버 유효성·권한을 다시 확인해야 한다.

## session 복원을 상태 기계로 만듭니다

```ts
type SessionState =
  | { kind: "unknown" }
  | { kind: "anonymous" }
  | { kind: "restoring" }
  | { kind: "authenticated"; userId: string; expiresAt: string }
  | { kind: "reauth-required"; reason: string };
```

startup에서 token 문자열이 존재한다는 이유만으로 private route를 확정하지 않는다.

```text
secure credential 읽기
→ local session metadata와 연결
→ 필요하면 refresh
→ response 검증
→ versioned credential envelope 또는 복구 가능한 교체 protocol로 저장
→ authenticated 확정
```

SecureStore의 여러 key 쓰기는 하나의 transaction이 아니다. access token, refresh token과 generation을 각각 덮어쓰며 "원자적 rotation"이라고 부르지 않는다. 한 key의 versioned envelope로 교체하거나, `prepared → active` generation과 startup reconciliation처럼 중단 뒤에도 어느 generation을 쓸지 판정할 수 있는 protocol을 둔다.

refresh 중 app가 종료될 수 있다. 이전 token 삭제와 새 token 저장 순서를 설계하고, 실패 뒤 어떤 credential이 남는지 확인한다. 특히 iOS Keychain-backed 값은 같은 bundle identifier의 app를 삭제·재설치해도 남을 수 있으므로 reinstall을 logout이나 credential 삭제의 증거로 사용하지 않는다.

## 401을 무한 재시도하지 않습니다

여러 request가 동시에 401을 받으면 각자 refresh를 시작할 수 있다. 하나의 refresh coordinator를 두고 결과를 공유한다.

```text
첫 401
→ refresh 시작

추가 401
→ 같은 refresh 결과 대기

refresh 성공
→ 새 credential로 안전한 요청만 재실행

refresh 실패
→ session을 reauth-required로 전환
```

mutation을 자동 재실행할 때는 server가 첫 요청을 처리했을 가능성을 고려한다. command id나 idempotency key가 없으면 중복 업무 변경이 생길 수 있다.

## retry는 operation의 의미가 결정합니다

### 일반적으로 안전한 경우

- 같은 resource의 GET
- idempotent PUT
- 고유 command id로 server가 중복 제거하는 mutation
- resumable upload protocol에서 확인된 chunk

### 자동 retry가 위험한 경우

- 새 payment·order·message 같은 중복 가능한 POST
- server 처리 여부를 모르는 timeout 뒤 새 id로 다시 생성
- destructive operation
- user intent가 이미 바뀐 오래된 mutation

retry policy에는 다음을 포함한다.

```text
최대 attempt
backoff와 jitter
retry 가능한 error set
command identity
app background/cancel 조건
다음 attempt 시각
사용자에게 보이는 pending 상태
```

Field Notes outbox는 mutation마다 안정적인 `commandId`와 `baseVersion`을 가진다.

## request timeout과 cancellation을 별도로 둡니다

`fetch`가 영원히 기다리지 않도록 application timeout을 둔다. 그러나 timeout 뒤 server가 처리하지 않았다는 보장은 없다.

새 화면이나 새 query가 시작되면 이전 요청을 취소할 수 있다. 취소가 불가능하거나 이미 response가 도착하는 race를 위해 generation도 확인한다.

```ts
const request = coordinator.begin();
const response = await api.fetchRecords({ signal: request.signal });
const parsed = parseRecordList(await response.json());

if (!coordinator.isCurrent(request.generation)) {
  return;
}

await repository.replaceRemoteSnapshot(parsed);
```

mutation은 화면 unmount와 함께 무조건 취소할지, application task로 계속할지 별도 결정한다. 업무 save를 component promise에 묶지 않는다.

## upload는 두 상태를 가집니다

사진 첨부는 record metadata와 file bytes가 분리된다.

```text
local attachment row
- local file URI
- checksum·size·mime
- upload state

remote attachment
- remote id·URL·version
```

실패 사례:

- file copy 전에 app 종료
- DB row만 있고 file이 없음
- file은 있으나 row transaction 실패
- upload 완료 response를 받기 전 timeout
- remote upload는 성공했지만 record 연결 실패
- local file이 OS 정리 대상 cache에 있음

app-owned durable directory로 file을 옮긴 뒤 DB transaction에서 참조한다. upload command는 checksum·size와 command identity로 중복을 처리한다. 완료 뒤 local file을 즉시 지울지 offline view를 위해 유지할지 정책을 둔다.

## foreground 복귀는 재검증 trigger입니다

background 동안 다음이 바뀔 수 있다.

- token 만료·revocation
- account 또는 tenant 전환
- permission 철회
- network 유형
- server record version
- OS locale·time zone
- notification으로 알려진 conflict

app가 active가 되면 모든 화면을 재생성하지 않고 필요한 coordinator에 신호를 보낸다.

```text
session validate
→ pending outbox 요청
→ 현재 화면의 stale policy에 따라 remote refresh
→ capability 재조회
```

동시에 여러 resume event가 와도 하나의 작업으로 합칠 수 있어야 한다.

## 사용자에게 다음 행동을 남깁니다

오류 화면은 원인 문자열만 표시하지 않는다.

| 상태 | 다음 행동 |
|---|---|
| offline pending | local 작업 계속, 연결 시 sync, 수동 retry |
| auth expired | 다시 로그인, local unsynced data 처리 설명 |
| forbidden | 다른 계정 확인 또는 뒤로 이동 |
| conflict | server와 local 변경 비교·선택 |
| malformed response | 안전한 이전 data 유지, 재시도·지원 정보 |
| storage full | 불필요 file 정리, 기록 text 보존 |

재시도 button을 모든 오류에 넣지 않는다.

## 관측 정보

request log에 다음을 포함할 수 있다.

- request/command id
- route와 operation kind
- attempt와 duration
- app version·build·runtime
- network hint
- HTTP status와 normalized error kind
- response schema version
- outbox entity id의 비민감 표현

포함하지 않을 것:

- access/refresh token
- authorization header
- 개인 record text와 정밀 위치
- signed upload URL 전체

## Stage 02·04 완료 기준

- 연결 상태와 실제 request 결과를 구분한다.
- 외부 response를 runtime schema로 검증한다.
- credential과 일반 local data의 저장소가 분리돼 있다.
- 동시 401에서 하나의 refresh 작업만 수행한다.
- mutation retry에는 command identity와 최대 attempt가 있다.
- timeout 뒤 server 결과가 UNKNOWN일 수 있음을 UI와 outbox가 표현한다.
- stale response가 최신 화면·database를 덮지 않는다.
- offline·auth·forbidden·conflict·malformed 오류에 서로 다른 다음 행동이 있다.

자동 검사는 normalized error, credential generation과 outbox 전이를 검증한다. 실제 radio 전환, captive portal, OS secure-storage 정책, server의 중복 제거와 backend authorization까지 보장하지는 않는다. 해당 항목은 실제 기기·허가된 test server evidence로 별도 검토한다.

이제 요청 실패를 일시 화면 오류로만 두지 않고 local 업무 상태와 outbox로 수렴시킨다. [local data·offline·sync](05-local-data-offline-and-sync.md)로 이어간다.
