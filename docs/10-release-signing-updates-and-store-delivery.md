# release·signing·update·store 전달

모바일 배포는 server에 새 artifact를 올리는 것으로 끝나지 않는다. app identifier, signing identity, store record, binary version, native runtime, JavaScript update와 rollout이 함께 맞아야 한다.

이 브랜치는 mobile client의 build·signing·submission artifact를 읽고 검증하는 데까지 소유한다. 공개 backend, DNS/TLS, CI/CD host와 incident 운영은 `web-infra`에 맡기며 store 정책 자체를 이 저장소가 고정한다고 주장하지 않는다.

## 목표

- application id/bundle id, semantic version, build number와 runtime version을 구분한다.
- development·preview·production build profile의 목적과 backend를 분리한다.
- signing credential의 소유·backup·rotation·접근 정책을 정한다.
- source revision에서 installable artifact까지 provenance를 남긴다.
- native change와 JavaScript update의 compatibility를 판정한다.
- staged rollout·update rollback·store rollback의 차이를 설명한다.
- privacy·permission·metadata·review evidence를 release gate에 포함한다.
- Android와 iOS install·upgrade·deep link·notification smoke를 수행한다.

연결 실습은 [Stage 06](../exercises/field-notes/specs/06-quality-release.md)과 [capstone release evidence](../capstone/release-evidence.md)다.

## 여러 identity를 구분합니다

| identity/version | 역할 |
|---|---|
| Android applicationId | 설치·store에서 app를 식별 |
| iOS bundle identifier | target·signing·store에서 app를 식별 |
| Expo/EAS project id | Expo service project 연결 |
| app version | 사용자에게 보이는 release version |
| Android versionCode | store가 비교하는 증가 정수 |
| iOS buildNumber | 같은 app version의 build 식별 |
| runtimeVersion | native binary와 JS update 호환성 경계 |
| update id/channel | 배포된 JS/assets 집합과 대상 |
| source revision | 어떤 source에서 만들었는지 |

서로 대체하지 않는다. app version이 같아도 build number와 native artifact가 다를 수 있고, source revision이 같아도 profile/environment가 다르면 다른 binary가 된다.

## app identifier를 초기에 고정합니다

identifier 변경은 새 app로 취급될 수 있고 signing·deep link·push·store record를 모두 바꾼다.

profile별로 동시에 설치해야 한다면 suffix를 계획한다.

```text
production    com.example.fieldnotes
preview       com.example.fieldnotes.preview
development   com.example.fieldnotes.dev
```

각 variant는 다음도 분리해야 한다.

- app display name/icon
- backend base URL
- push credential와 token registry
- deep/universal link domain·scheme
- analytics/error environment
- update channel
- local data migration 기대

preview가 production API와 실제 사용자 data를 무심코 사용하지 않게 한다.

## build profile을 목적별로 나눕니다

### development

- development client와 debug capability
- 빠른 native 반복
- 내부 developer device
- production signing/telemetry와 분리

### preview

- release-like optimization
- 내부·외부 tester 배포
- production과 유사한 runtime·feature flag
- 별도 backend 또는 안전한 test account
- store 제출 전 upgrade·notification·deep link 검사

### production

- store 배포용 signing
- production identifier·environment
- release logging·privacy 정책
- 승인된 runtime/update channel

profile 이름만 다르고 실제 environment가 섞이지 않도록 generated config를 artifact evidence에 저장한다. secret 값 자체는 저장하지 않는다.

## signing credential은 조직 자산입니다

질문:

- 누가 Android keystore와 iOS certificate/profile을 소유하는가?
- cloud service가 관리하는가, 자체 vault에 보관하는가?
- 최소 권한과 감사 기록은 있는가?
- 담당자가 떠나도 release 가능한가?
- 손실·만료·폐기·rotation 절차는 무엇인가?
- CI가 credential을 어떻게 가져오고 정리하는가?

credential을 개인 노트북 하나에만 두지 않는다. 저장소에 commit하지 않는다. 자동 관리 서비스를 사용해도 recovery와 접근 정책을 이해한다.

## 재현 가능한 build 입력을 기록합니다

release evidence:

```text
source commit
clean/dirty state
Node/package manager와 lockfile digest
Expo SDK·React Native versions
app config 결과
native dependency fingerprint
build profile·environment name
Android/iOS toolchain image/version
application id·bundle id
app/build/runtime versions
artifact digest
signing identity의 비밀이 아닌 식별 정보
```

같은 source revision을 다른 환경에서 만들 수 있으므로 commit hash만으로 충분하지 않다.

## native runtime과 update를 연결합니다

remote JavaScript/assets update는 설치된 binary가 제공하는 native API와 호환돼야 한다.

native runtime이 바뀌는 대표 사건:

- native package 추가·제거·upgrade
- Expo SDK/React Native upgrade
- local Kotlin·Swift module 변경
- app config가 native project를 바꾸는 경우
- permission·entitlement·native resource 변경

위 변경에는 모두 새 binary가 필요하다. 그러나 모든 native resource·usage-description 변경이 JavaScript와 native API 호환성 집합까지 바꾸는 것은 아니다. `runtimeVersion`을 바꿀지는 프로젝트의 fingerprint/runtime policy로 판정한다. native package API, Expo/RN runtime, local module 또는 config plugin 결과가 JS 호환 경계를 바꾸면 반드시 새 runtime을 사용한다. 단순 icon처럼 binary만 바뀌고 JS/native contract가 같은 변경도 새 store binary는 필요하지만 runtime policy 결과는 같을 수 있다.

호환성 사고 예:

```text
기존 binary runtime R1
→ 새 JS update도 R1로 publish
→ update가 새 camera module method 호출
→ R1 binary에는 method 없음
```

runtimeVersion policy와 build fingerprint를 사용하고 preview channel에서 같은 runtime의 update를 먼저 검사한다.

## update와 store release의 rollback이 다릅니다

### remote update rollback

- compatible runtime 안에서 이전 update로 되돌리거나 새 수정 update publish
- rollout 취소 가능
- 이미 실행한 local migration·업무 side effect는 자동 복구되지 않음

### store binary 문제

- 새 binary를 만들어 store review/rollout
- 일부 store는 rollout 중단 가능
- 사용자 device에 이전 binary를 강제로 되돌리기 어려움
- DB migration과 server compatibility를 forward-fix 관점으로 설계

따라서 destructive local migration을 JS update와 함께 무계획으로 실행하지 않는다.

## migration compatibility window를 둡니다

동시에 여러 app version이 사용된다.

- 오래된 client와 새 server
- 새 client와 아직 rollout 중인 server
- 새 binary + 이전 JS update
- 이전 binary + compatible 새 update

API와 local schema 변경은 지원 window를 정한다.

예:

```text
server가 새 field를 optional로 먼저 지원
→ 새 app가 field 사용
→ adoption 확인
→ 오래된 client 지원 종료 뒤 required 전환
```

mobile store rollout 속도를 backend deploy와 같다고 가정하지 않는다.

## release 실패를 artifact와 rollout 상태로 분리합니다

release 실패는 "build가 안 됐다" 하나가 아니다. 다음 상태를 구분해야 rollback과 사용자 안내가 달라진다.

| 실패 위치 | 예 | 복구 기준 |
| --- | --- | --- |
| source gate | type·test·migration fixture 실패 | artifact를 만들지 않고 source 수정 뒤 전체 gate 재실행 |
| native build | signing·entitlement·manifest·dependency 실패 | credential과 generated/owned native 입력을 분리해 새 build 생성 |
| install/launch | 특정 OS에서 설치 또는 cold start 실패 | 해당 binary의 rollout 중단, 재현 device와 crash evidence 보존 |
| runtime update | 잘못된 bundle 또는 runtime 불일치 | compatible update로 되돌리거나 해당 runtime 배포 비활성화 |
| store review | metadata·privacy·permission 설명 불일치 | binary와 store record 중 실제 계약을 기준으로 수정 |
| staged rollout | crash·migration·sync 지표 악화 | stop threshold에 따라 rollout 정지 또는 이전 artifact로 복귀 |

실패 뒤에는 어떤 사용자가 어떤 binary/runtimeVersion/data schema를 받았는지 추적할 수 있어야 한다.

## release gate

### source와 자동 검사

- clean checkout
- lockfile 기반 install
- type/lint/unit/integration 검사
- sync·migration fixture
- dependency/license/security 검사

### binary 검사

- Android와 iOS production-like build 성공
- Android publishing artifact(AAB), 설치 가능한 APK/Play-generated split APK와 실제 설치 결과를 구분
- iOS archive, export/provision된 IPA 또는 TestFlight 설치 build와 실제 설치 결과를 구분
- identifier·version·runtime·permission 확인
- app install·cold start·upgrade
- deep/universal link
- notification registration/tap
- offline save·restart·sync
- crash reporting environment

### 사용자 품질

- TalkBack·VoiceOver
- 큰 글자·작은 화면
- permission deny/limited/revoke
- privacy data inventory
- store screenshot·description·review note와 실제 기능 일치

### 운영 준비

- staged rollout과 monitor
- error/performance dashboard
- support·incident owner
- update rollback/disable 절차
- signing·credential recovery

## store submission과 공개 release를 구분합니다

binary upload가 자동으로 모든 사용자에게 공개된다는 뜻은 아니다. test track/TestFlight, review, production rollout 단계가 있다.

각 platform에서 확인한다.

- store record와 identifier 일치
- build가 올바른 track에 들어감
- metadata·privacy·age/content 질문
- permission 사용 이유
- reviewer가 기능을 재현할 test account·절차
- subscription/payment가 있다면 별도 정책
- export/compliance 질문

현재 store 요구사항은 자주 바뀌므로 release 시점에 공식 console과 문서를 다시 확인한다.

AAB는 store가 device별 APK를 생성하는 publishing format이며 기기에 직접 설치하는 artifact가 아니다. iOS archive도 그 자체가 임의 device 설치 증거가 아니다. source build에서 얻은 AAB/archive digest는 그 입력 artifact를 식별하지만 store가 처리·재서명해 사용자에게 전달한 bytes와 동일함을 증명하지 않는다. release evidence에는 publishing artifact digest, store build/track identity와 실제 device install evidence를 별도 행으로 남긴다.

## staged rollout과 관측

전체 공개 전에 작은 집단에서 본다.

관측 지표 예:

- crash-free launch/session
- startup와 screen responsiveness
- login/refresh failure
- DB migration failure
- pending outbox·conflict 비율
- upload failure와 storage error
- notification registration/tap failure
- runtime/update별 오류

사용자 행동 지표만 보고 데이터 손실·privacy 문제를 놓치지 않는다. stop/rollback threshold와 판단 owner를 미리 정한다.

## release 중 변경을 동결합니다

release candidate를 검증하는 동안 source·config·credential·backend가 계속 바뀌면 evidence가 artifact와 달라진다.

```text
release candidate revision 고정
→ build
→ device/store preflight
→ 승인
→ submit/rollout
→ 같은 artifact digest 추적
```

수정이 필요하면 새 build/update identity를 만들고 관련 검사를 다시 수행한다.

## 첫 설치·upgrade·재설치를 구분합니다

- fresh install
- 이전 production version에서 upgrade
- app delete 후 reinstall
- device backup/restore 가능 시
- account logout/login
- 다른 account 전환

local data와 secure credential이 platform별로 어떻게 남거나 삭제되는지 실제로 확인한다. uninstall이 모든 secure data를 반드시 지운다고 추측하지 않는다.

## release note와 내부 변경 기록

사용자 release note는 사용자 결과와 필요한 action을 설명한다. 내부 release record는 더 구체적이다.

```text
포함 기능과 bug fix
DB/API/native runtime 변경
permission/privacy 변경
known issue
rollout plan과 threshold
rollback/forward-fix 절차
support owner
artifact·source·test evidence link
```

## Stage 06 완료 기준

- dev·preview·production identifier와 backend/update channel이 분리돼 있다.
- app version, build number/code와 runtimeVersion을 독립적으로 기록한다.
- signing credential의 owner·recovery·rotation이 문서화돼 있다.
- source revision부터 Android/iOS artifact digest까지 evidence가 있다.
- 이전 app/DB fixture에서 upgrade를 검사했다.
- native 변경이 incompatible JS update로 배포되지 않게 runtime policy가 있다.
- preview에서 deep link·notification·offline·migration·접근성·성능 smoke를 완료했다.
- store metadata·permission·privacy declaration이 data inventory와 일치한다.
- staged rollout의 관측 지표, stop 기준과 책임자가 있다.

local 자동 검사는 config, lockfile, JS bundle과 artifact metadata의 일부만 확인한다. signing credential 소유권, cloud builder, store review, store가 전달한 bytes, 실제 iOS/Android 설치와 공개 rollout은 사람이 해당 계정·기기에서 확인해야 한다.

이 기준을 충족하면 Field Notes capstone은 모바일 프로젝트의 시작·개발·기기 검증·배포 경계를 한 번 연결한 것이다. 이후 실제 저장소에서 작은 native dependency, offline bug, accessibility 또는 release 문제에 반복 기여하며 깊이를 만든다.
