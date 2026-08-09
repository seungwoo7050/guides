# 테스트·성능·관측성

simulator에서 happy path가 한 번 성공한 것은 모바일 품질 증거가 아니다. process가 죽고, permission이 바뀌고, network가 끊기고, 화면과 글자 크기가 달라져도 같은 업무 계약이 유지되는지 검사해야 한다.

`web-front-react-nextjs`가 소유하는 일반 accessibility·browser 성능 검증과 `web-infra`가 소유하는 운영 관측 체계를 다시 만들지 않는다. 여기서는 설치된 Android/iOS binary, 실제 device 보조기술, mobile lifecycle·native adapter와 local data가 만드는 추가 위험을 검증한다.

## 목표

- domain·repository·native adapter·screen·device test의 책임을 나눈다.
- time·UUID·network·storage·permission·AppState를 통제 가능한 port로 만든다.
- process restart와 schema migration을 fixture로 재현한다.
- TalkBack·VoiceOver·큰 글자·keyboard로 핵심 흐름을 검사한다.
- release build에서 startup·frame·memory·image·network·battery 문제를 측정한다.
- crash·log·trace에 build/runtime/sync context를 남기되 민감정보를 제외한다.
- Android·iOS device matrix를 합격/비합격 근거로 사용한다.

연결 실습은 [Stage 06](../exercises/field-notes/specs/06-quality-release.md)이다.

## 검사층을 업무 계약에 맞춥니다

### 1. 순수 model 검사

대상:

- record validation
- sync state transition
- retry/backoff decision
- conflict resolution
- navigation intent policy
- permission state normalization

장점:

- 빠르고 결정적
- Android/iOS runtime 없이 모든 분기 검사
- stale result·race를 event sequence로 표현

[`examples/sync-model`](../examples/sync-model/README.md)이 이 층의 예다.

### 2. repository·adapter contract 검사

대상:

- SQLite transaction과 migration
- outbox claim/lease
- FileSystem staging·cleanup
- SecureStore error mapping
- HTTP response runtime parsing
- permission native result mapping

실제 implementation과 in-memory fake가 같은 contract suite를 통과하게 할 수 있다. fake가 실제 transaction·error 의미를 지나치게 단순화하지 않게 한다.

### 3. component·screen 검사

대상:

- loading/empty/offline/conflict UI
- form validation과 draft 보존
- accessibility role·state·label
- route parameter에 따른 화면
- optimistic/local save 결과

native module을 mock하더라도 platform state union을 사용한다. 내부 hook 호출 순서보다 사용자 action과 visible/accessible result를 검사한다.

### 4. app integration 검사

대상:

- router + repository + session
- startup migration + deep link
- local save + outbox + sync result
- notification response + current state reconciliation

development build 또는 controlled runtime에서 여러 adapter가 연결되는 경계를 본다.

### 5. E2E·실제 기기 검사

대상:

- install·launch·upgrade
- system permission dialog
- camera/photo picker/location
- process kill·background·notification
- TalkBack·VoiceOver
- release performance와 crash
- signing·deep/universal link

모든 조합을 E2E에 넣지 않는다. 순수 model과 adapter contract로 조합 수를 줄이고, E2E는 OS와 binary 경계를 검증한다.

## 통제할 수 없는 값을 port로 만듭니다

```ts
interface Clock {
  now(): string;
}

interface IdGenerator {
  nextCommandId(): string;
}

interface NetworkPort {
  execute(command: RecordCommand, signal: AbortSignal): Promise<SyncResult>;
}

interface CapabilityPort {
  getPhotoAccess(): Promise<CapabilityAccess>;
}
```

테스트는 time progression, 중복 id, timeout, response 순서와 permission 철회를 직접 만든다. production adapter는 실제 OS/API를 사용한다.

## race를 sleep으로 검사하지 않습니다

나쁜 검사:

```text
request 시작
→ 500ms 기다림
→ 아마 끝났다고 가정
```

controlled promise와 event sequence를 사용한다.

```text
command A 시작
command B 생성
B response 먼저 resolve
A response 나중 resolve
최종 local state 확인
```

background task도 실제 scheduler를 기다리는 테스트와 worker contract 테스트를 분리한다. worker는 fake budget과 repository로 즉시 검사하고, scheduler registration만 device에서 확인한다.

## process restart를 실제로 만듭니다

memory reset 없이 `reload`만 누르면 native process 수명 문제를 놓칠 수 있다.

검사 시나리오:

- local save 뒤 app process 종료·재실행
- outbox in-flight 상태에서 종료
- system picker 중 Activity/process recreation
- DB migration 전 version으로 install한 뒤 upgrade
- notification cold start
- secure credential은 있으나 session metadata 일부 손상
- file은 있으나 DB row 없음, 반대 상태

fixture는 source revision과 schema version을 가진다. 테스트 시작 전 어떤 상태를 설치했는지 기록한다.

## 실제 기기 matrix는 위험 기반으로 고릅니다

모든 OS/device 조합을 소유할 수는 없다. 다음 축에서 위험이 다른 대표를 선택한다.

| 축 | 최소 사례 |
|---|---|
| platform | Android, iOS |
| OS | 지원 최소에 가까운 version, 현재 주력 version |
| hardware | 작은 memory/느린 device 가능 시, 일반 device |
| screen | 작은 phone, 큰 phone 또는 tablet/split view |
| input | touch, software keyboard, screen reader |
| network | offline, 느림/손실, Wi-Fi↔cellular 전환 |
| lifecycle | active, background, process kill, reboot 가능 시 |
| permission | undetermined, granted, denied, limited, revoked |
| build | development, preview/release |

emulator/simulator는 빠른 반복용이고, 실제 기기 결과를 대체하지 않는다.

## 접근성을 별도 마지막 검사로 미루지 않습니다

각 stage에서 component semantics를 검사하고 Stage 06에서 전체 흐름을 실제 보조기술로 수행한다.

필수 흐름:

```text
app 시작
→ record 목록 탐색
→ 새 record 생성
→ validation error 이해·수정
→ 사진 없이 또는 permission 거절로 저장
→ offline/sync 상태 확인
→ conflict 화면에서 선택
→ 뒤로 가기와 modal 닫기
```

확인:

- focus order와 heading
- label·role·state·value
- dynamic announcement
- 큰 글자와 bold text
- 색상 이외의 상태 표현
- gesture의 대체 action
- keyboard와 switch control 가능성

자동 accessibility 검사만으로 screen reader 경험을 증명하지 않는다.

## performance는 release build에서 봅니다

development mode의 warning·debugger·logging 비용은 release와 다르다. 성능 주장은 production-like build와 실제 device에서 측정한다.

### startup

구간을 나눈다.

```text
process launch
→ native runtime ready
→ JavaScript bundle 실행
→ DB open/migration
→ first meaningful screen
→ interactive
```

splash를 오래 보여 수치를 숨기지 않는다. cold/warm start를 구분한다.

### frame과 responsiveness

React Native에는 JavaScript work와 native/UI work가 서로 다른 병목이 될 수 있다.

원인 예:

- render마다 큰 local query·JSON parse
- 모든 list row가 global state 때문에 rerender
- 큰 image decode·resize
- main thread의 native 작업
- 복잡한 gesture/animation과 JS contention
- excessive logging

frame drop가 보이면 추측으로 memoization을 추가하지 말고 profile에서 어느 thread와 component가 시간을 쓰는지 확인한다.

### list와 image

- virtualized list의 window와 key
- stable item component와 selector
- thumbnail size·cache·decode
- original file을 list에서 직접 render하지 않음
- memory warning과 screen unmount 뒤 resource release

### network와 battery

- 같은 data를 foreground/resume마다 무조건 다시 받지 않음
- retry storm와 짧은 polling 금지
- background 작업을 합치고 OS scheduler 사용
- upload compression·chunk·Wi-Fi 정책이 제품 요구와 맞음
- location·camera·sensor가 screen 종료 뒤 멈춤

### storage

- DB query plan/index
- migration duration
- file cache 상한
- cleanup 작업의 I/O budget

## 성능 예산을 사용자 작업으로 정합니다

절대 수치는 제품과 기기에 따라 다르므로 capstone은 다음 작업에 예산과 측정 환경을 기록한다.

- cold start에서 record 목록이 의미 있게 보일 때까지
- 1,000개 local record scroll
- detail open과 edit save
- thumbnail 20개가 보이는 목록
- outbox 100개 처리 중 UI interaction
- app background/foreground 전환

예산을 넘으면 profiler evidence와 원인, 선택한 trade-off를 남긴다. 수치를 감추기 위해 측정 범위를 바꾸지 않는다.

## observability context를 release identity와 연결합니다

오류·trace에 다음 context를 추가한다.

```text
platform·OS·device class
app semantic version
Android versionCode / iOS buildNumber
runtimeVersion·update id/channel
source revision·build profile
현재 route 이름
session 상태 종류(식별자 제외)
DB schema version
sync attempt·command id
network hint
permission normalized state
```

이 정보가 있어야 “업데이트 뒤 특정 iOS build에서만 sync conflict가 증가했다”를 좁힐 수 있다.

## crash와 handled error를 구분합니다

- native crash
- JavaScript fatal error
- unhandled promise rejection
- handled domain error
- expected cancellation

모든 expected offline·permission denial을 error tracker에 exception으로 보내면 signal이 묻힌다. normalized metric과 user outcome으로 관찰한다.

## privacy를 관측성보다 먼저 둡니다

수집하지 않을 기본값:

- record title·notes
- 정확한 coordinate
- image·file URI
- access/refresh token
- authorization header
- notification payload 전체
- signed upload URL

필요한 correlation은 random command/attempt id와 non-sensitive category를 사용한다. data inventory와 telemetry schema를 함께 검토한다.

## 회귀 기준

각 bug 수정에는 가능하면 가장 낮은 결정적 층의 검사를 추가한다.

```text
오래된 sync success가 새 edit를 덮음
→ pure sync model test

SQLite migration에서 outbox index 누락
→ repository migration fixture

permission 거절 뒤 button focus 손실
→ screen/component + device accessibility test

특정 iOS binary에서 module method 없음
→ runtime compatibility/release smoke
```

E2E 하나만 추가해 원인을 멀리 숨기지 않는다.

## Stage 06 완료 기준

- pure model, adapter, screen, integration, device 검사의 책임이 문서화돼 있다.
- time·ID·network·permission·storage를 통제해 race와 실패를 결정적으로 만든다.
- 이전 DB fixture upgrade와 process restart를 검사했다.
- Android·iOS 실제 기기에서 permission·notification·background 흐름을 수행했다.
- TalkBack·VoiceOver·큰 글자에서 capstone 핵심 작업을 완료했다.
- release-like build에서 startup·list·image·sync 성능을 측정했다.
- crash/error context에 build/runtime/schema가 있고 민감정보가 없다.
- 수정한 대표 bug가 가장 낮은 적절한 층의 회귀 검사로 고정돼 있다.

자동 gate가 통과해도 TalkBack·VoiceOver 사용성, 실제 기기 thermal/battery, OS scheduler, release frame profile과 개인정보가 제거된 telemetry를 증명하지 않는다. Stage 06 제출에는 수행자·기기·build identity가 있는 수동 질문과 원본 evidence가 필요하며, 미수행 항목은 `pass`가 아니라 `not-run`으로 남긴다.

마지막으로 source에서 설치 가능한 binary와 update를 만들고 어떤 사용자가 어떤 runtime을 받는지 release 계약을 고정한다. [release·signing·update·store](10-release-signing-updates-and-store-delivery.md)로 이어간다.
