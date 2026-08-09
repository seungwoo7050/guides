# navigation·link·상태 복원

모바일 route는 화면 전환용 문자열만이 아니다. launcher, 외부 link, notification, OS 복원과 사용자의 back action이 모두 같은 화면 계약에 들어온다.

## 목표

- route parameter를 신뢰 경계의 입력으로 검증한다.
- 현재 화면, selected entity와 편집 draft의 소유자를 분리한다.
- deep link와 내부 navigation이 같은 route contract를 사용하게 한다.
- session·database 준비 전 도착한 navigation intent를 안전하게 보류한다.
- 존재하지 않거나 권한이 없는 target에 deterministic fallback을 제공한다.
- Android system back, iOS gesture와 modal dismiss를 업무 취소와 구분한다.
- cold start·warm start·process restoration에서 적용할 intent와 버릴 일시 상태를 결정한다.

연결 실습은 [Stage 01](../exercises/field-notes/specs/01-runtime-navigation.md)이다.

## 이 장의 책임 경계

일반적인 URL, React state와 인증·인가 기초는 [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app)에 맡기고, 브라우저 URL/UI 상태와 비동기 race 심화는 [`web-front-react-nextjs`](https://github.com/seungwoo7050/guides/tree/web-front-react-nextjs)에 맡긴다. 이 장은 OS와 외부 앱이 process가 없거나 준비되지 않은 순간에도 intent를 전달할 수 있다는 모바일 고유 실패를 다룬다. link를 열 권한과 record를 볼 권한은 별개이며, 보안 정책 자체의 정본은 [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity)에 있다.

| 상태·자원 | 소유자 | 바꾸는 사건 | 불변식 |
|---|---|---|---|
| raw link·notification response·restoration input | OS·외부 source | cold/warm delivery, process restoration | 신뢰하지 않고 schema와 freshness를 검증한다. |
| normalized navigation intent | startup/navigation coordinator | raw input 수신·정규화 | 같은 입력과 readiness에서 같은 route decision을 낸다. |
| 현재 route·back stack | router | intent 적용, back, modal dismiss | route와 별도 selected entity를 이중 정본으로 만들지 않는다. |
| record·authorization·draft | repository/session/draft owner | sync, account change, edit/save | navigation 실패가 업무 data를 rollback하거나 반쯤 변경하지 않는다. |

정상 경로는 준비된 app의 내부 navigation이다. 대표 경계는 private deep link cold start이고, 대표 실패는 malformed·stale intent가 migration/session 복원보다 먼저 도착하는 경우다.

## route를 화면 정본으로 사용합니다

Field Notes의 핵심 route 예:

```text
/records
/records/new
/records/:recordId
/records/:recordId/edit
/sync
/settings
```

`selectedRecordId`를 별도 global state에 복제하면 route와 값이 어긋날 수 있다. 공유·복원되어야 하는 화면 선택은 route가 소유하고, 현재 record는 repository가 id로 조회한다.

```text
route id
→ 형식 검증
→ local record 조회
→ authorization·visibility 확인
→ screen state 결정
```

component가 navigation 직전에 record object 전체를 넘겨도 cold start나 deep link에는 그 object가 없다. route에는 안정적인 identity와 화면 의도만 둔다.

## route parameter는 외부 입력입니다

file-based route가 type을 생성해도 실제 link 문자열은 외부에서 들어온다.

검증할 것:

- id 문법과 길이
- 허용된 query key와 enum
- 중복 parameter와 decoding error
- 오래된 app version의 route
- 삭제되거나 아직 local에 없는 record
- 인증 또는 tenant가 다른 record

잘못된 id를 assertion으로 넘기지 않는다.

```ts
type RecordRouteResult =
  | { kind: "ready"; recordId: string }
  | { kind: "invalid-link" }
  | { kind: "not-found" }
  | { kind: "forbidden" }
  | { kind: "needs-sync"; recordId: string };
```

`not-found`와 `forbidden`을 사용자에게 어느 정도 구분해 보여 줄지는 보안·제품 정책이 정한다. 내부 로그에는 raw secret이 아닌 정규화된 failure kind를 남긴다.

## navigation intent를 정규화합니다

앱을 여는 경로는 여러 개다.

```text
launcher icon
custom scheme 또는 universal/app link
push notification response
OS state restoration
internal navigation
```

각 source가 직접 router를 조작하면 startup race가 생긴다. 먼저 공통 intent로 변환한다.

```ts
type NavigationIntent =
  | { kind: "home" }
  | { kind: "open-record"; recordId: string; source: "link" | "notification" }
  | { kind: "open-sync"; source: "notification" }
  | { kind: "invalid"; reason: string };
```

그 뒤 application readiness와 policy가 실제 route를 결정한다.

```text
intent 도착
→ syntax normalization
→ DB/session 준비 대기
→ target 조회와 권한 검사
→ 현재 navigation state와 중복 여부 확인
→ route 적용 또는 fallback
```

## cold·warm·restoration을 구분합니다

같은 record intent도 process 상태에 따라 전제가 다르다.

```text
cold start
process와 JS memory 없음
→ DB migration·session 복원 뒤 initial intent 적용

warm delivery
process와 현재 route/draft가 있음
→ 현재 작업을 덮지 않는지 확인한 뒤 intent 적용 또는 보류

restoration
이전 route 후보가 있음
→ 현재 app version·session·record로 재검증한 뒤 제한적으로 복원
```

Field Notes의 기본 우선순위는 명시적인 최신 사용자 진입 intent를 유효한 restoration 후보보다 먼저 평가하고, 둘 다 없으면 `/records`로 간다. link와 notification이 동시에 발견되면 OS callback 완료 순서로 추측하지 않는다. 각 source의 stable response identity와 수신 시각을 기록하고, 하나만 active intent로 claim한다. 신뢰할 수 있는 순서를 정할 수 없으면 현재 안전 route를 유지하면서 사용자가 선택할 수 있는 pending intent를 남긴다.

이 우선순위는 제품 정책이므로 다른 앱이 바꿀 수 있다. 중요한 불변식은 같은 초기 상태와 사건 순서가 같은 결정을 내리고, 보류된 intent가 다른 process에서 무한히 재적용되지 않는다는 것이다.

## startup race를 명시합니다

cold start에서 다음 작업이 동시에 일어날 수 있다.

- initial link 조회
- notification response 조회
- local DB migration
- secure session 복원
- auth refresh
- app update 또는 configuration load

첫 promise가 완료되는 순서대로 navigate하면 같은 입력에서도 다른 화면이 열린다.

startup coordinator는 최소한 다음 상태를 가진다.

```ts
type StartupState =
  | { kind: "booting"; pendingIntent: NavigationIntent | null }
  | { kind: "public-ready"; pendingIntent: NavigationIntent | null }
  | { kind: "private-ready"; sessionId: string; pendingIntent: NavigationIntent | null }
  | { kind: "failed"; reason: string };
```

public screen은 DB가 없어도 표시할 수 있는지, private intent는 session 확인 전 보류할지 결정한다. loading screen이 오래 지속되면 retry·sign-out·local-only 진입 같은 다음 행동을 제공한다. pending queue는 크기와 수명이 제한돼야 하며, malformed input을 readiness 대기열에 넣지 않는다.

## deep link는 navigation과 authorization을 분리합니다

link를 열 수 있다는 사실은 record를 볼 권한이 있다는 뜻이 아니다.

```text
https://example.invalid/records/abc
```

이 link는 화면 의도를 전달할 뿐이다. app은 local/remote authorization과 tenant context를 다시 확인한다.

고려할 상태:

- app가 설치되지 않음
- 오래된 version이 route를 모름
- 로그인 필요
- 다른 계정으로 로그인됨
- record가 local에는 없지만 remote에는 있음
- record가 삭제됨
- offline이라 권한 또는 존재를 확인할 수 없음

오프라인 정책을 명시한다.

```text
이전에 승인·동기화된 local record
→ local 표시 가능, stale 표시

처음 보는 remote record
→ 연결 필요 화면, 존재를 확정하지 않음
```

production universal/app link는 app-side configuration 외에도 도메인 association 파일과 운영 상태가 필요하다. 이 브랜치에서는 custom scheme 또는 허가된 test domain으로 app의 intent·fallback을 검증할 수 있지만, 그것이 production DNS·TLS·association hosting을 보장하지는 않는다.

## notification은 route가 아니라 메시지입니다

notification payload의 title/body를 업무 정본으로 사용하지 않는다. 가능한 한 stable identifier와 intent type을 전달하고 app가 최신 상태를 조회한다.

```json
{
  "type": "record-conflict",
  "recordId": "rec-123"
}
```

payload는 외부 입력이므로 schema를 검증한다. notification tap이 여러 번 전달되거나 이미 같은 record를 보고 있을 수 있다. intent identity를 사용해 중복 navigation을 피한다.

notification permission이 없거나 delivery가 누락돼도 app 안의 conflict 목록에서 같은 상태를 찾을 수 있어야 한다.

## back은 데이터 rollback이 아닙니다

사용자가 edit 화면에서 back을 누르면 다음 정책 중 하나가 필요하다.

- draft가 없으면 이전 화면으로 이동
- unsaved draft가 있으면 discard 확인
- draft checkpoint가 있다면 “임시 저장됨”을 설명하고 이동
- 이미 local save transaction이 끝났다면 단순 화면 이동; outbox는 유지

system back event에서 DB transaction을 되돌리지 않는다. 화면 수명과 업무 commit을 구분한다.

Android hardware/system back, gesture navigation, iOS interactive back gesture, header button, modal dismiss가 같은 정책을 사용해야 한다. platform callback마다 다른 confirm 로직을 복사하지 않는다.

## modal과 route의 선택 기준

modal은 일시적인 하위 작업에 적합하다.

- 사진 source 선택
- 짧은 filter
- discard 확인
- conflict의 한 단계 선택

다음은 route가 더 적합할 수 있다.

- 공유 가능한 record detail
- 여러 단계 편집
- notification이나 외부 link로 직접 열어야 하는 화면
- 독립된 back stack과 복원이 필요한 작업

modal을 URL/route 없이 global boolean로만 관리하면 deep link와 재시작에 복원할 수 없다. 복원이 필요한 modal은 route 표현을 고려한다.

## route state 복원 범위를 제한합니다

OS가 navigation state 복원을 지원하거나 router가 이전 state를 저장해도 모든 screen stack을 그대로 되살리는 것이 항상 맞지는 않다.

검사:

- app version이 바뀌어 route schema가 달라졌는가?
- session이 만료됐는가?
- target record가 삭제됐는가?
- edit draft가 실제로 저장됐는가?
- 이전 modal이 현재 의미가 있는가?

권장 방식:

```text
안정적인 최상위 route와 entity id 복원
→ 현재 data·session·capability로 재검증
→ 일시 modal·loading·in-flight action은 새로 계산
```

복원 payload에는 schema/version을 두고 모르는 version은 폐기한다. stale restoration을 적용하지 않는 것은 실패가 아니라 현재 정본으로 수렴하는 정상 정책이다.

## tab과 stack의 상태 소유권

여러 tab을 사용할 때 tab마다 stack을 유지할지, tab 변경 시 초기화할지 정한다. 무조건 유지하면 오래된 detail과 memory가 쌓이고, 무조건 초기화하면 사용자가 작업 맥락을 잃는다.

Field Notes 예:

```text
Records tab          list/detail stack 유지
Sync tab             현재 filter만 route query로 유지
Settings tab         일시 form draft는 화면 수명
```

record가 삭제되면 다른 tab stack에 남은 detail route도 다음 focus 시 재검증한다.

## navigation event를 관찰합니다

오류 분석을 위해 다음을 남길 수 있다.

- app version·build·runtime version
- source: internal/link/notification/restoration
- normalized intent kind
- route before/after
- target id의 hash 또는 비민감 식별자
- fallback reason
- session readiness와 local existence
- response identity와 accepted/ignored 결과

raw link에 token이나 개인정보가 있을 수 있으므로 전체 URL을 무조건 기록하지 않는다.

## navigation 실패를 상태로 남깁니다

navigation 실패를 예외 하나로 뭉치지 않는다. 같은 target을 열지 못해도 복구 행동은 원인에 따라 다르다.

| 실패 상태 | 예 | 제품 행동 |
|---|---|---|
| malformed | route parameter 형식이 잘못됨 | 안전한 목록으로 이동하고 입력을 반영하지 않음 |
| missing | local·remote 모두 target이 없음 | 삭제·오래된 link 가능성을 설명 |
| forbidden | session은 있으나 접근 권한 없음 | 존재 여부를 과도하게 노출하지 않고 이전 안전 route 유지 |
| offline-unavailable | local copy가 없고 network가 없음 | 연결 뒤 재시도할 intent를 보존 |
| not-ready | DB 또는 session 복원이 끝나지 않음 | fallback으로 확정하지 않고 bounded queue에서 대기 |
| stale-restoration | process restart 뒤 복원된 route가 현재 데이터와 모순됨 | 현재 정본으로 재검증하고 목록 또는 최신 route로 수렴 |
| duplicate | 같은 link/notification response가 다시 전달됨 | 이미 적용한 업무·route 결과를 반복하지 않음 |

중요한 불변식은 잘못된 intent가 화면을 반쯤 바꾸지 않고, 실패 뒤에도 사용자가 다음 행동을 선택할 수 있다는 것이다.

## 결정적 검사

router 자체의 E2E만으로 모든 조합을 검사하기 어렵다. intent normalization과 policy를 순수 함수로 분리한다.

```ts
function resolveIntent(
  intent: NavigationIntent,
  context: {
    session: "unknown" | "anonymous" | "authenticated";
    localRecord: "unknown" | "missing" | "present";
    network: "offline" | "online";
  },
): RouteDecision {
  // framework-independent policy
}
```

검사 사례:

- malformed record id와 decoding error
- private link + anonymous session
- local record + offline
- missing local record + offline
- link와 notification이 함께 도착한 cold start
- notification duplicate
- deleted record after restored route
- stale restoration schema/version
- warm intent + unsaved edit draft
- draft edit + Android back/iOS gesture

## 검증 범위와 한계

pure policy 검사는 malformed input, readiness와 event ordering에 대한 결정성을 보장할 수 있다. integration 검사는 실제 router·repository·session 연결을 확인하고, development build의 cold/warm link·notification 실험은 OS entry point와 native configuration을 확인한다.

다음은 별도 evidence가 필요하다.

- type-safe route 생성은 외부 문자열의 runtime 유효성·권한을 보장하지 않는다.
- custom scheme 성공은 production universal/app link의 도메인 association을 보장하지 않는다.
- simulator URL open은 실제 notification delivery, process restoration과 store-installed binary를 보장하지 않는다.
- 한 계정의 성공은 account switch·tenant mismatch를 보장하지 않는다.
- screenshot은 back gesture, modal dismiss와 focus 복귀의 업무 결과를 보장하지 않는다.

Android와 iOS에서 cold start, warm delivery와 stale restoration을 각각 기록하고, 실제로 검사하지 못한 link source와 OS version을 known limits에 남긴다.

## Stage 01 완료 기준

- 모든 public route와 parameter schema가 문서화돼 있다.
- deep link·notification·internal navigation이 공통 intent를 사용한다.
- cold·warm·restoration의 state owner와 intent 우선순위가 정해져 있다.
- DB/session 준비 전 intent를 보류하고 결정적으로 적용한다.
- invalid·missing·forbidden·offline·stale target에 fallback이 있다.
- edit draft와 local save의 back 정책이 분리돼 있다.
- process restart와 오래된 restored route를 검사했다.
- Android system back과 iOS back gesture에서 같은 업무 결과를 확인했다.
- pure policy, simulator와 실제 기기 evidence가 보장하지 않는 범위를 기록했다.

다음은 route가 준비돼도 mobile network와 session이 불안정할 때 데이터를 어떻게 읽고 변경할지 다룬다. [network·session·오류 계약](04-networking-session-and-error-contracts.md)으로 이어간다.
