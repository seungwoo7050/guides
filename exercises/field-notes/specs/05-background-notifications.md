# Stage 05 — background 작업과 notification

## 목적

Stage 04의 bounded sync worker를 OS가 제공하는 background 실행 기회와 연결하고, notification을 최신 업무 상태로 다시 진입하는 신호로 사용한다. background task가 한 번도 실행되지 않거나 notification이 중복·지연·누락돼도 local data와 foreground sync가 정확해야 한다.

이 단계는 production push provider나 delivery SLA를 만들지 않는다. scheduler와 notification lifecycle의 모바일 client 경계만 소유한다.

먼저 [background·notification·lifecycle](../../../docs/07-background-work-notifications-and-lifecycle.md)을 읽고 Stage 01의 navigation intent와 Stage 04 worker 계약을 함께 사용한다.

## 시작 상태와 의도적 미완성

이 절은 Stage 04 공개 계약을 완료한 learner 작업 복사본의 Stage 05 기준선이다. 누적 reference의 lifecycle core/package 또는 adapter 존재는 구현 근거일 수 있지만, 실제 scheduler·notification·cold-start device evidence나 Stage 완료를 자동으로 뜻하지 않는다. 자동 범위는 현재 package scripts와 verify 결과로 확인한다.

시작 상태:

- Stage 04의 durable outbox, claim/lease와 bounded sync worker
- development build와 CNG app configuration
- 공용 `BackgroundScheduler`, `NotificationPort`, `NavigationIntentPort`
- notification payload/parser와 scheduler를 대체할 deterministic adapter

skeleton에서 다음은 의도적으로 비어 있다.

- background task definition/registration과 budget 전달
- manual·app-active·background trigger를 하나의 worker에 연결하는 coordinator
- Android notification channel·permission·token 순서
- notification runtime parsing, duplicate/stale/account 판정
- cold/warm start navigation intent 조정

등록 함수나 파일의 존재만으로 완료하지 않는다. task가 미실행·중단·중복돼도 repository snapshot과 foreground 결과가 같은지를 공개 행동 검사로 확인한다.

## 관찰할 상태와 불변식

| 상태·자원 | 소유자 | 바꾸는 사건 | 보존할 불변식 |
|---|---|---|---|
| outbox와 lease | Stage 04 repository | 모든 sync trigger와 result | trigger 종류가 command 의미나 terminal transition을 바꾸지 않는다. |
| scheduler registration | OS scheduler + app config | install/update/register/unregister | 등록 성공을 실행·완료로 표시하지 않는다. |
| task budget/checkpoint | worker coordinator | start, expiration, cancellation, process death | 중단 뒤 같은 durable state에서 재개할 수 있다. |
| notification permission/channel/token | OS·native config·installation registry | user decision, reinstall, rotation, account change | permission·token·backend mapping·delivery를 하나의 boolean으로 합치지 않는다. |
| notification response identity | notification intent adapter | cold/warm delivery, duplicate tap | 같은 response를 한 번만 claim하고 업무 payload를 정본으로 쓰지 않는다. |
| route decision | startup/navigation coordinator | intent + repository readiness | 최신 DB/session 상태를 읽은 뒤 deterministic route/fallback을 선택한다. |

정상 경로는 foreground app-active가 pending outbox를 처리하는 경우다. 대표 경계는 background task와 foreground resume가 동시에 worker를 여는 경우다. 대표 실패는 scheduler가 끝내 실행되지 않은 상태에서 오래된 conflict notification을 두 번 누르는 경우다.

## 모든 trigger는 같은 bounded worker를 사용합니다

```ts
type SyncTrigger = "manual" | "app-active" | "background" | "notification";
```

trigger는 관측 context일 뿐 업무 결과를 바꾸지 않는다.

```text
manual/app-active/background/notification
→ 같은 worker.run({ itemBudget, timeBudget, cancellation })
→ 같은 repository claim/lease
→ 같은 SyncTransport와 result transaction
```

- background 전용 queue나 별도 sync state machine을 만들지 않는다.
- background callback은 component, toast나 router를 직접 조작하지 않는다.
- worker 결과는 SQLite/outbox/conflict에 durable하게 기록하고 UI는 다음 foreground에서 읽는다.
- foreground와 background가 겹치면 repository의 atomic claim/lease가 한 command의 중복 시도를 조정한다.
- trigger별 budget은 달라도 command ID, attempted snapshot과 terminal 의미는 같다.

같은 initial repository와 fault schedule에서 trigger만 바꾼 contract test의 final durable state가 같아야 한다.

## scheduler registration은 실행 보장이 아닙니다

다음을 구현과 evidence에 기록한다.

- task definition 파일과 application load 시점
- registration 조건, identifier와 minimum interval의 의미
- unregister·logout·account switch·app update 정책
- Android/iOS capability와 OS 제한
- development build와 실제 device 요구
- scheduler 조회 결과와 마지막 실제 start/finish/checkpoint trace

`scheduled`, `registered` 또는 요청한 interval을 UI에서 “동기화 완료”나 “정확히 N분 뒤 실행”으로 표현하지 않는다.

### task가 실행되지 않을 때

```text
outbox pending
→ scheduler가 실행되지 않음
→ pending/next opportunity가 durable하게 유지됨
→ app active
→ 같은 bounded worker가 재개
```

이 경로는 필수 acceptance case다. background task가 없어도 foreground에서 eventually sync될 수 있어야 한다. app가 다시 열리지 않고 scheduler도 실행되지 않으면 remote 수렴을 보장하지 않는다는 한계를 명시한다.

### expiration·cancellation·process death

- budget이 작아지면 새 command claim을 중단한다.
- 가능하면 active request에 cancellation을 전달하지만 UNKNOWN 결과는 Stage 04 규칙으로 처리한다.
- 완료한 result transaction과 마지막 checkpoint만 성공 근거로 사용한다.
- active lease는 즉시 release하거나 expiry 뒤 복구한다.
- 종료 callback 없이 process가 사라져도 command snapshot은 durable하게 남는다.

## notification lifecycle을 분리합니다

```text
native configuration/channel
→ OS permission
→ device/push token 획득
→ installation-account mapping 등록
→ provider accept
→ OS delivery
→ 표시/사용자 interaction
→ app response parsing·claim
→ 최신 repository 기반 route
```

각 단계는 owner와 실패가 다르다. token이 있다는 사실은 permission·delivery·사용자 표시·tap 처리를 보장하지 않는다.

### Android 13 이상 순서

Android 13(API 33)+의 기준 순서는 다음과 같다.

```text
1. notification channel 생성/확인
2. 사용자 맥락에서 POST_NOTIFICATIONS 상태 확인·요청
3. granted 뒤 device/push token 획득
4. installation/account mapping upsert
```

- channel을 만들기 전에 token API가 permission prompt를 대신 띄울 것이라고 가정하지 않는다.
- permission이 denied/restricted면 token·backend mapping을 “알림 가능”으로 표시하지 않는다.
- channel importance 변경과 runtime permission은 별도 상태다.
- Android 12 이하와 iOS에는 이 channel 순서를 일반화하지 않고 platform adapter에 차이를 남긴다.

실제 순서는 SDK/OS 변경 영향을 받을 수 있으므로 release 시 SDK 57 Notifications와 Android 공식 문서를 다시 확인하고 device trace를 제출한다.

## notification message는 업무 정본이 아닙니다

최소 normalized input:

```ts
type NotificationMessage =
  | { type: "record-conflict"; recordId: string; messageId: string; accountId: string }
  | { type: "sync-blocked"; messageId: string; accountId: string }
  | { type: "record-updated"; recordId: string; messageId: string; accountId: string };
```

- raw payload는 `unknown`에서 runtime parse한다.
- title/body/record snapshot은 업무 정본으로 저장하지 않는다.
- `messageId` 또는 stable response identity를 durable하게 claim해 duplicate tap을 무효화한다.
- account/tenant가 현재 session과 다르면 route에 사용하지 않는다.
- record/content/conflict는 tap 시 repository에서 최신 상태를 읽는다.
- permission이나 delivery가 없어도 app의 Sync/Conflict 화면에서 같은 상태를 찾을 수 있다.

payload에 account ID를 넣을 수 없는 제품이라면 installation/session binding에서 같은 판정을 제공하고 schema 문서에 근거를 남긴다. token·credential·민감 record content를 trace에 기록하지 않는다.

## duplicate·stale·malformed 판정

| 입력 | 기대 관측 결과 |
|---|---|
| 같은 `messageId` 두 번 | 첫 response만 claim; 두 번째는 duplicate trace, 추가 navigation·업무 효과 없음 |
| 이미 해결된 conflict message | repository에 current conflict가 없으면 conflict UI를 만들지 않음; record가 있으면 detail/상태 안내, 없으면 records fallback |
| 삭제되거나 권한 없는 record | content 존재를 단정하지 않는 안전 fallback |
| malformed/unknown type | invalid trace 후 navigation 없음; app가 crash하지 않음 |
| logout 전 account message | 현재 session과 불일치해 drop; 이전 user data를 열지 않음 |
| notification payload version이 오래됨 | payload snapshot을 무시하고 current repository/version으로 decision |

stale 여부를 notification 수신 시각 하나로 추측하지 않는다. 현재 conflict/record/session을 정본으로 사용한다.

## cold/warm start

### cold start

```text
raw notification response
→ runtime parse와 duplicate/account 사전 판정
→ pending NavigationIntent
→ DB migration·session 복원
→ current record/conflict 조회
→ route 또는 fallback
→ response claim 완료
```

startup 중 crash가 나도 response가 무한 재적용되지 않도록 claim 시점과 recovery를 문서화한다.

### warm start

- 이미 같은 destination인지 확인한다.
- 열린 edit draft나 modal을 무조건 덮지 않고 보류/확인 정책을 따른다.
- 같은 response identity는 다시 navigate하지 않는다.
- background result가 UI를 직접 바꾸지 않고 current repository observation을 유발한다.

deep link, restoration과 notification은 Stage 01의 공통 `NavigationIntent`와 startup coordinator를 사용한다.

## token·installation·account 수명

- installation identity와 user/account identity를 분리한다.
- login/session 확정 뒤 mapping을 upsert한다.
- token rotation은 새 token을 upsert하고 이전 token을 무효화한다.
- logout/account switch에서는 mapping을 제거하거나 server에서 inactive로 만든다.
- provider의 invalid-token result를 cleanup event로 처리한다.
- reinstall·backup 뒤 installation identity가 유지된다고 가정하지 않는다.

실제 backend가 없다면 deterministic registry fake와 state-machine test를 제공하고 production delivery를 보장하지 않는다고 기록한다.

## 필수 failure matrix

1. scheduler가 한 번도 실행되지 않음
2. task start 직후 expiration/cancellation
3. foreground/background 동시 trigger
4. callback 없는 process 종료와 lease expiry
5. background 중 401 또는 response loss
6. Android channel 생성 전/후 permission 상태
7. notification permission denied·granted·revoked
8. token 등록 실패·rotation·logout cleanup
9. duplicate message/response identity
10. 이미 해결된 conflict의 stale notification
11. notification payload malformed/unknown type
12. cold start + migration/session 지연
13. warm start + unsaved edit draft
14. logout 뒤 이전 account notification

## 자동 검증

자동화하기 적합한 항목:

- trigger만 다른 worker 실행이 같은 final durable state를 만든다.
- task budget 종료·cancellation·lease expiry 뒤 재개된다.
- task 미실행 뒤 app-active가 같은 pending command를 처리한다.
- Android adapter가 channel→permission→token 순서를 지키고 denied에서 token 등록을 하지 않는다.
- payload parser가 malformed/account mismatch를 거절한다.
- duplicate/stale notification이 repository current state를 기준으로 한 deterministic decision을 낸다.
- installation token rotation/logout lifecycle이 fake registry에서 수렴한다.
- skeleton/known-wrong adapter가 같은 public 검사에서 거부된다.

자동 fake는 OS scheduler가 실제로 callback을 주거나 vendor별 background 제한, notification provider/OS delivery가 동작함을 보장하지 않는다.

## 사람·실제 기기 검토

Android와 iOS 각각에서 다음을 `checks/manual-device-matrix.md`에 기록한다.

- foreground notification과 in-app 상태 중복 여부
- background tap과 cold-start tap
- permission deny/grant/revoke와 Settings 복귀
- network 없음에서 tap한 뒤 최신 local fallback
- recent 제거, force-stop/사용자 종료, reboot 전후 관찰
- scheduler test trigger와 OS가 실제로 지연 실행한 trace의 구분
- TalkBack/VoiceOver가 conflict·sync 상태와 다음 action을 설명하는지

simulator/emulator 결과는 별도 행에 기록할 수 있지만 실제 device 결과로 바꾸지 않는다. 실행하지 않은 platform은 `미검사`이며 Stage 완료나 exit capability 통과가 아니다.

## 제출 증거

```text
stage-05/
├── background-contract.md
├── registration-and-platform-config.md
├── notification-schema.md
├── installation-lifecycle.md
├── automated-contract-output.txt
├── android-device-results.md
├── ios-device-results.md
└── task-and-intent-traces/
```

trace에는 source/build/runtime identity, trigger, attempt/message ID, normalized result와 repository decision만 남긴다. token, credential, full payload와 사용자 record content는 제거한다.

## 완료 조건

- manual·app-active·background·notification이 같은 bounded worker와 result contract를 사용한다.
- background task가 없어도 다음 foreground 기회에서 sync가 재개된다.
- task는 중단·중복·동시 실행과 process death에 안전하다.
- Android 13+에서 channel→permission→token 상태가 분리되고 순서가 evidence로 남는다.
- notification payload와 최신 record/conflict/session 상태를 분리한다.
- duplicate·stale·malformed·이전 account notification이 잘못된 route나 업무 효과를 만들지 않는다.
- cold/warm start가 공통 `NavigationIntent`를 사용한다.
- 자동 contract와 Android/iOS 실제 device evidence의 보장 범위를 구분했다.

## 비범위와 알려진 한계

- 정확한 background 주기, 실행 횟수 또는 완료 보장
- notification delivery SLA와 production provider 운영
- background location
- marketing campaign/segmentation system
- notification action에서 destructive 업무 변경 직접 실행
- 모든 Android vendor battery policy 조합

app가 다시 foreground로 오지 않고 OS도 task를 실행하지 않으면 sync 수렴을 보장하지 않는다. local/deterministic notification 검사는 remote provider accept, APNs/FCM, OS delivery와 사용자 interaction을 보장하지 않는다.
