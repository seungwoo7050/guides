# background·notification·lifecycle

모바일 OS는 battery, 사용 패턴, network와 정책에 따라 background 작업의 실행 시점과 시간을 결정한다. 예약했다고 정확한 시각에 실행되는 것도, 사용자가 app를 종료한 뒤 계속 실행되는 것도 아니다.

이 장은 push backend 운영이나 전달 SLA를 소유하지 않는다. client가 OS의 비보장 실행 기회를 받아 durable outbox를 조금씩 전진시키고, 알림을 최신 업무 상태가 아닌 navigation intent로 해석하는 범위만 다룬다.

## 목표

- foreground, background와 terminated 실행의 차이를 설명한다.
- background 작업을 지연·중단·중복에 안전한 bounded step으로 만든다.
- background 실행 없이도 foreground resume에서 결국 수렴하게 한다.
- notification을 업무 정본이 아닌 재참여 신호로 사용한다.
- permission·token·channel/category·response lifecycle을 구분한다.
- notification tap과 deep link를 공통 navigation intent로 처리한다.
- 실제 기기에서 scheduler·notification·force-stop 차이를 검사한다.

연결 실습은 [Stage 05](../exercises/field-notes/specs/05-background-notifications.md)다.

## background 실행은 기회입니다

OS scheduler는 다음 조건을 볼 수 있다.

- battery와 충전 상태
- network availability
- 사용자의 app 사용 패턴
- low power mode
- system quota
- device vendor 정책
- 사용자의 force-stop 또는 app 종료

따라서 정확성 계약을 다음처럼 두면 안 된다.

```text
record save
→ 15분 뒤 background sync가 반드시 실행
→ server에 반드시 있음
```

권장 계약:

```text
record save transaction
→ local record와 outbox는 즉시 durable
→ foreground에서 가능한 즉시 sync 요청
→ background 기회가 오면 같은 worker step 실행
→ 다음 app active에서도 pending outbox 재시도
```

background는 latency를 줄이는 최적화이며 데이터 보존의 유일한 수단이 아니다.

## 작업을 작고 재개 가능하게 만듭니다

하나의 background task가 전체 queue를 비우려고 하지 않는다.

```text
실행 시작
→ lease 만료된 작업 복구
→ 현재 budget·session·network 확인
→ command 한 개 claim
→ bounded request
→ durable 결과 기록
→ 시간이 남으면 다음 command
→ 종료 전에 lease·checkpoint 정리
```

OS expiration 또는 cancellation callback이 오면 새 작업을 시작하지 않고 active 작업의 안전한 중단 지점을 만든다. callback이 오지 않는 crash도 견뎌야 한다.

## task definition과 registration을 구분합니다

background framework는 보통 두 종류의 설정을 가진다.

```text
definition
- 어떤 code가 task name을 처리하는가
- module load 시 등록돼야 할 수 있음

registration
- OS scheduler에 어떤 조건과 interval로 요청하는가
- 사용자가 기능을 켜거나 app 설정이 준비된 뒤 수행
```

component 안에서 task definition을 조건부로 만들면 headless 실행에서 찾지 못할 수 있다. framework의 요구 위치를 따르고, 실제 업무 logic은 platform-independent worker port에 둔다.

## 같은 worker를 foreground와 background에서 사용합니다

```ts
type SyncTrigger = "manual" | "app-active" | "background" | "notification";

async function runSyncStep(trigger: SyncTrigger, budget: TimeBudget) {
  // repository claim, request, checkpoint
}
```

trigger에 따라 정확성 rule이 달라지지 않는다. background에서는 budget이 짧고 UI를 직접 조작할 수 없다는 차이만 있다.

- background worker가 component state를 set하지 않는다.
- 완료는 SQLite state로 기록한다.
- 화면은 focus/active 시 repository를 다시 읽는다.
- foreground와 background 동시 실행은 DB claim/lease로 조정한다.

이 원칙이 곧 모든 sample app이 background network 전송을 기본 활성화해야 한다는 뜻은 아니다. 제공 Field Notes Expo reference는 설정 가능한 endpoint로 local record를 자동 전송하지 않도록 automatic sync를 disabled로 유지하고 manual action만 transport를 실행한다. 같은-worker 불변식은 injected fake에서 검사한다. 실제 제품에서 automatic sync를 켜려면 사용자 opt-in, 허가된 endpoint·session owner, disable/logout 정리와 device evidence를 함께 추가한다. 그 근거가 없으면 app-active/background/notification 제품 경로는 `미검사`다.

## headless 실행에서 사용할 수 없는 것을 압니다

background 또는 terminated 상태에서는 다음 가정이 깨질 수 있다.

- 현재 mounted screen이 있다.
- router가 준비돼 있다.
- modal이나 alert를 표시할 수 있다.
- memory session과 dependency container가 이미 초기화됐다.
- user가 즉시 biometric prompt에 응답할 수 있다.

worker는 필요한 repository와 credential을 독립적으로 초기화하고, user interaction이 필요한 경우 `blocked_auth` 같은 durable 상태를 남긴다.

## notification은 최신 상태가 아닙니다

push payload는 지연·중복·순서 역전될 수 있다. 사용자가 이미 문제를 해결한 뒤 오래된 알림을 누를 수도 있다.

```text
notification payload
→ type·id schema 검증
→ navigation intent
→ local/remote 최신 상태 조회
→ 아직 관련 있으면 화면 표시
→ 이미 해결됐으면 현재 상태 설명 또는 목록 fallback
```

notification body에 민감한 record text를 넣을지 lock screen 노출까지 고려한다. 기본 실습은 non-sensitive summary와 stable id만 사용한다.

## notification permission과 token은 별개입니다

다음 상태를 구분한다.

- OS notification permission
- Android notification channel 설정
- device push token 또는 Expo push token
- backend token registration
- token rotation·invalid 처리
- user/account와 device installation의 연결

permission이 granted라고 backend registration이 성공한 것은 아니다. token이 있다고 사용자에게 알림이 반드시 전달되는 것도 아니다.

Android 13 이상에서는 channel 없이 permission/token 흐름을 시작하면 prompt가 기대한 시점에 나타나지 않거나 token 취득 조건이 어긋날 수 있다. Field Notes의 순서는 다음처럼 고정한다.

```text
stable channel id와 의미 선언
→ channel 생성·현재 설정 확인
→ 사용자가 알림 기능을 켠 문맥에서 permission 요청
→ granted 뒤 device/project token 요청
→ 현재 account/build와 backend registration
```

iOS와 이전 Android version에서는 raw 단계가 달라도 adapter가 `permission`, `channel/config`, `token`, `backend registration`을 별도 상태로 보고한다.

installation record 예:

```ts
type PushInstallation = {
  installationId: string;
  userId: string;
  token: string;
  platform: "android" | "ios";
  appBuild: string;
  enabledAt: string;
};
```

`installationId`는 앱이 생성한 불투명 random id이며 hardware identifier나 fingerprint가 아니다. 로그에는 원문을 남기지 않는다. logout, account switch와 token rotation에서 backend mapping을 정리한다.

## notification 종류를 나눕니다

### local notification

- device 안에서 schedule
- reminder 같은 local 기능
- time zone·clock change·permission 고려

### remote visible notification

- OS가 title/body를 표시
- app 상태에 따라 handler 차이
- tap response로 app 진입

### data/background notification

- UI 없이 data로 작업 trigger 가능
- platform 제한과 delivery 보장 없음
- background entitlement/config와 task manager 필요

서버가 silent push를 주기적으로 보내면 background sync가 보장된다고 설계하지 않는다.

## foreground notification 정책

app가 active일 때 같은 notification을 system banner로 다시 보여 줄지, 화면 안에서 조용히 갱신할지 결정한다.

Field Notes 기본 정책:

- 현재 보고 있는 record의 변경: repository 갱신 후 화면 상태로 알림
- 다른 record conflict: in-app summary와 conflict badge
- 긴급하지 않은 sync 완료: banner 없이 sync state 갱신
- 사용자 action이 필요한 오류: 지속 가능한 message와 Sync 화면 link

notification handler와 screen UI가 중복 announcement를 만들지 않게 한다.

## notification response를 idempotent하게 처리합니다

사용자가 같은 알림을 여러 번 누르거나 startup에서 last response를 다시 읽을 수 있다.

```text
response id 또는 notification id 확인
→ 이미 처리했으면 navigation 중복 방지
→ intent 저장/적용
→ 완료 marker
```

처리 marker가 memory에만 있으면 process restart 때 반복된다. 얼마나 오래 보존할지 정한다.

## Android channel과 iOS category를 제품 계약으로 봅니다

Android channel은 사용자가 소리·중요도·표시를 조정하는 장기 식별자다. 출시 뒤 의미를 쉽게 바꾸지 않는다.

iOS category/action은 notification에서 가능한 작업을 정의한다. destructive action이나 인증이 필요한 action은 app를 열어 최신 상태와 권한을 확인한다.

Field Notes 예:

```text
sync-status channel       낮은 중요도, 완료/대기 요약
record-conflict channel   사용자 조치 필요
```

실제 채널 수는 최소화하고 기본값과 사용자가 바꾼 설정을 존중한다.

## time과 locale을 처리합니다

local reminder를 지원한다면 다음을 정한다.

- absolute instant인지 local calendar time인지
- time zone 변경 시 재계산 여부
- daylight saving 전환
- device reboot 뒤 재등록 여부
- record delete·완료 시 취소
- 같은 reminder 중복 schedule 방지

이 capstone에서는 optional extension으로 둔다. background sync와 reminder를 같은 개념으로 합치지 않는다.

## 실제 기기에서 검사합니다

simulator는 notification·background scheduler·battery·process 관리의 일부만 재현한다. 최소한 Android와 iOS 실제 기기에서 확인한다.

검사 조합:

```text
app active
app background
screen locked
app를 recent에서 제거
OS가 process 종료
device reboot
network 없음/복구
low power mode 가능 시
notification permission denied/granted
notification tap cold start/warm start
```

`최근 앱에서 제거`와 `force stop`의 의미가 platform/vendor마다 다를 수 있으므로 결과를 일반화하지 않고 matrix에 기록한다.

## background 작업 관측

각 실행에 다음을 남긴다.

- task/attempt id
- trigger
- 시작·종료 시각과 duration
- app build/runtime
- command claim 수와 결과
- stop/expiration 여부
- next pending count
- normalized failure

개인 record payload와 credential은 남기지 않는다.

화면에서는 마지막 background 실행 시각을 성공 보장처럼 표시하지 않는다. `마지막 동기화 성공`, `대기 중 변경 수`, `다음 수동 action`을 구분한다.

## Stage 05 실패 주입

- task가 전혀 실행되지 않음
- task 시작 직후 중단
- 같은 task 두 번 겹침
- background에서 credential 만료
- network 연결 신호는 있으나 timeout
- push token rotation
- permission denied
- duplicate notification response
- 오래된 conflict notification
- cold start notification + DB migration 지연
- logout 직전/직후 notification

## Stage 05 완료 기준

- background 실행 없이 foreground resume만으로 outbox가 수렴한다.
- task는 bounded step이며 command마다 durable checkpoint가 있다.
- foreground와 background가 같은 worker contract를 사용한다.
- OS 중단·process 종료 뒤 in-flight lease를 복구한다.
- notification payload를 검증하고 최신 repository 상태를 다시 읽는다.
- permission, token, backend registration과 delivery를 분리한다.
- duplicate/old notification이 중복 변경이나 잘못된 화면을 만들지 않는다.
- Android·iOS 실제 기기에서 cold/warm tap과 background 제한을 기록했다.

worker·intent 자동 검사는 중단, 중복과 오래된 알림의 application 불변식을 보장한다. OS scheduler가 실행한다는 사실, push가 전달되는 시각, vendor force-stop 동작과 backend token 정리가 실제로 됐다는 사실은 보장하지 않으므로 device matrix와 허가된 test backend evidence가 필요하다.

다음은 JavaScript 밖의 binary·configuration·Kotlin·Swift module을 어떻게 읽고, 언제 공통 abstraction을 내려놓아야 하는지 다룬다. [Kotlin·Swift와 native boundary](08-native-boundary-kotlin-swift-and-builds.md)로 이어간다.
