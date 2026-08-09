# Stage 06 — 품질·native build·release evidence

## 목적

Field Notes를 development prototype에서 검토 가능한 Android/iOS release candidate로 전환한다. 접근성·performance·migration·native boundary·build/signing·privacy 근거를 source와 artifact identity에 연결한다.

이 단계는 public store 출시나 custom Kotlin/Swift module 구현을 강제하지 않는다. build command 성공을 artifact·install·device·store 성공으로 확대하지 않고, 실행하지 못한 항목은 `미검사`로 남긴다.

먼저 [native boundary](../../../docs/08-native-boundary-kotlin-swift-and-builds.md), [테스트·성능·관측성](../../../docs/09-testing-performance-and-observability.md), [release·signing·update·store](../../../docs/10-release-signing-updates-and-store-delivery.md)를 읽는다.

## 시작 상태와 의도적 미완성

이 절은 Stage 01~05 결과를 가진 learner release candidate의 기준선이다. release contract와 build 검사의 현재 자동 범위는 package scripts와 verify 결과로 확인한다. 해당 파일이 있어도 Stage 06의 실제 Android/iOS build·설치, signing·store 및 사람 품질 검토는 별도 evidence 없이는 완료가 아니다.

시작 상태:

- Stage 01~05의 app, durable data와 공개 behavior 검사
- Android/iOS development build configuration
- development·preview·production profile 초안
- 이전 schema/outbox/conflict fixture
- 실제 device 또는 접근 가능한 검토 환경

skeleton에서 다음은 의도적으로 미완성이다.

- preview/production identity와 runtime compatibility policy
- artifact manifest와 source fingerprint 연결
- upgrade/device/accessibility/performance matrix 결과
- 필수 native-boundary review
- signing/privacy/rollout 사람 판단 evidence

typecheck, Metro bundle 또는 CNG generation만 통과한 skeleton을 release candidate로 표시하지 않는다.

## 판정 상태

모든 자동·수동 gate는 다음 값 중 하나를 사용한다.

```text
통과      — 재현 가능한 기대 결과와 evidence가 있음
실패      — 실행했으며 계약을 만족하지 못함
미검사    — 도구·device·account·시간 제약 등으로 실행하지 않음
비적용    — 제품 계약상 적용되지 않으며 이유와 reviewer가 있음
```

`미검사`와 이유 없는 `비적용`은 통과가 아니다. 자동 필수 검사가 통과해도 실제 device·signing·store·사람 UX gate는 별도 상태다.

## build profile

최소 세 profile을 정의한다.

```text
development
preview
production
```

각 profile에 다음을 표로 기록한다.

- Android `applicationId` / iOS bundle identifier
- app name/icon과 test/prod 구분 표식
- backend environment와 secret 주입 owner
- update channel과 effective `runtimeVersion` policy
- logging/crash environment와 민감정보 제거
- distribution 대상과 install 경로
- signing credential owner, 접근·backup·rotation

production secret과 credential 값을 저장소나 evidence에 넣지 않는다. profile 이름이 같아도 config/backend/signing이 다르면 다른 artifact다.

## CNG·bundle·build·artifact·store를 구분합니다

| 단계 | 관찰 가능한 결과 | 보장하지 않는 것 |
|---|---|---|
| app config resolution | plugin/identifier/permission 입력 | native project에 실제 반영·compile |
| `expo prebuild --clean` / CNG | `android/`, `ios/` generated source | native compile·signing·install |
| Metro Android/iOS bundle | JavaScript/assets가 대상 platform용으로 bundle됨 | native dependency/config와 app binary |
| Android/iOS native compile | compiler/linker가 특정 configuration을 처리 | 올바른 signing·install·upgrade·store accept |
| signed build artifact | 특정 identity/profile의 APK/AAB 또는 app/IPA | 실제 device 동작·store processing·rollout |
| device install/smoke | 그 device/OS에서 install·launch·핵심 흐름 | 다른 vendor/OS와 upgrade 전체 |
| store upload/processing | console이 artifact를 수신·검사 | 심사 승인·사용자 rollout 성공 |

Android AAB는 store가 APK를 생성하기 위한 bundle이며 일반적으로 device에 직접 설치하는 APK와 같지 않다. iOS simulator `.app`, device-signed app/IPA와 App Store 제출 artifact도 같은 근거가 아니다. 어떤 산출물을 만들었는지 정확한 형식과 install 경로를 기록한다.

`eas build` job 성공, Gradle/Xcode archive 생성이나 CNG diff가 각각 다른 gate다. 하나의 screenshot으로 합치지 않는다.

## version과 release evidence schema v2

release candidate마다 최소 다음을 연결한다. 제출하는 `artifact-manifest.json`은 [`release-contract`](../release-contract/README.md)의 schema version 2를 사용한다.

```text
source revision
source/lockfile digest
Expo SDK / React Native / React version
resolved app config summary
native dependency/config fingerprint
application identifier
app semantic version
Android versionCode / Apple buildNumber
effective runtimeVersion
build profile와 toolchain/host
artifact type, path 또는 immutable URL
artifact digest
signing identity의 비밀이 아닌 식별 근거
```

native code가 있는 dependency나 app config/plugin을 바꾸면 binary rebuild가 필요하다. `runtimeVersion`은 별도의 update compatibility policy다. native change마다 문자열을 무조건 손으로 증가시키라는 규칙이 아니라, 선택한 policy가 incompatible update를 이전 binary에 전달하지 않도록 **effective runtime identity와 새 binary**를 함께 검증한다.

같은 source라도 profile/config/toolchain/signing이 다르면 artifact가 다를 수 있다. artifact manifest에 credential·token·secret을 포함하지 않는다.

한 manifest는 같은 `source`·`application`·`build` 후보 아래 고유 ref의 `artifacts[]`를 둔다.

| platform | 필수로 구분할 artifact set | 설치 관찰 허용 범위 |
|---|---|---|
| Android | `android-aab` + `android-apk` 또는 `android-play-split-set` | APK는 physical/emulator, Play split은 physical |
| iOS | `ios-xcarchive` + `ios-ipa` 또는 `ios-testflight-build` | IPA/TestFlight는 physical; simulator `.app`은 simulator evidence만 |

`installation`은 설치한 `artifactRef`, 관찰한 app id/version/build/runtime, build와 같은 runtime fingerprint 또는 policy ref, device class와 launch 결과를 가진다. AAB·xcarchive 직접 설치, IPA의 simulator 설치, simulator `.app`의 physical 설치와 runtime mismatch를 known-wrong으로 거부한다.

`signing[]`은 모든 artifact를 `artifactRef`로 가리키며 `not-run | claimed | manually-reviewed` 중 하나다. `claimed`에는 redacted identity와 방법·시각·evidence를, `manually-reviewed`에는 reviewer/date/review evidence를 추가한다. 후자는 사람 검토 기록일 뿐 signature trust나 credential 소유권을 자동 증명하지 않는다.

store를 실행했다면 `publishingArtifactRef`, immutable `storeBuildRef`, track/status를 분리한다. store-delivered bytes는 `not-run | declared | manually-reviewed` 상태만 사용한다. local AAB/IPA digest를 전달 bytes로 재사용하거나 `declared`를 자동 verified로 올리지 않는다. Play split/TestFlight artifact와 install evidence는 같은 store build identity를 가리켜야 한다.

validator의 `OK`는 schema와 ref/runtime/device matrix가 내부적으로 일관된다는 뜻이다. 실제 file digest 재계산, native build, signature trust, device install, store processing·전달, 교육적 완료나 `stable` 승인을 수행하지 않는다.

## 필수 native-boundary review

Stage 06의 필수 gate는 custom native module 작성이 아니라 **기존 Expo/native dependency 하나의 경계를 읽고 evidence로 연결하는 검토**다. camera, location, notification, background task 등 Field Notes가 실제 사용하는 module 하나를 선택한다.

[`reference/native-project-reading.md`](../../../reference/native-project-reading.md)의 질문을 따라 다음 경로를 추적한다.

```text
JavaScript/TypeScript public API와 반환/error 의미
→ package version과 autolinking
→ app config/config plugin 입력
→ clean CNG가 만든 Android manifest/Gradle·iOS plist/entitlement/project 변화
→ Kotlin/Swift entry point, thread/lifecycle/cancellation 경계
→ device runtime permission/capability와 대표 failure
→ native 변경 뒤 rebuild/update compatibility 판정
```

제출물에는 두 platform에서 다음 질문의 답과 source 위치 또는 generated diff를 포함한다.

- JavaScript call의 입력·성공·cancel·error가 native에서 어떤 의미로 변환되는가?
- permission, manifest/plist/entitlement를 누가 생성하고 source-of-truth는 어디인가?
- main/UI thread와 background work는 어디서 갈리는가?
- app/activity/scene/process 수명 뒤 promise/event가 어떻게 종료되는가?
- native code/config가 binary에 없을 때 build/runtime에서 어떤 실패가 보이는가?
- Android와 iOS raw 차이가 application adapter의 같은 의미로 정규화되는가?

custom native module 구현, 즉 직접 Kotlin/Swift module을 작성하는 일은 선택 확장이다. 작성하지 않았다는 이유로 실패시키지 않으며, 반대로 작은 module을 만들었다고 위 boundary review를 생략할 수 없다.

## clean generation과 native build gate

- clean checkout/known source에서 CNG를 실행하고 generated diff와 tool version을 기록한다.
- Android merged manifest에서 identifier, permission, provider/receiver/service와 exported 값을 확인한다.
- iOS built plist/entitlement와 signing capability에서 같은 config intent를 확인한다.
- development와 preview binary에서 선택한 native module의 정상·cancel·permission failure를 실행한다.
- native dependency/config 변경 전후에 old binary/new bundle, new binary/old bundle 조합의 compatibility 판정을 문서화한다.
- app/universal link와 notification config는 app-side와 외부 association/provider 상태를 구분한다.

full Xcode가 없는 host에서 iOS CNG와 JS bundle만 성공했다면 native compile/signing/install은 `미검사`다. Android SDK가 없으면 Android bundle만으로 APK/AAB gate를 통과시키지 않는다.

## upgrade fixture

최소 다음을 같은 application identity의 이전 version fixture에서 검사한다.

1. fresh install
2. 이전 schema와 local record가 있는 상태에서 upgrade
3. unsynced outbox와 attempted command가 있는 상태에서 upgrade
4. conflict가 있는 상태에서 upgrade
5. attachment staging/orphan이 있는 상태에서 upgrade
6. app delete/reinstall 뒤 DB/file/credential/backup 관찰

migration 실패 시 data를 자동 삭제하거나 빈 DB로 성공 처리하지 않는다. 이전 fixture의 source/build/schema identity, upgrade 명령, final DB/outbox/file/UI를 남긴다. SecureStore/Keychain과 backup/reinstall behavior는 platform/config에 따라 달라질 수 있으므로 실제 결과를 일반화하지 않는다.

## accessibility·layout gate

Android TalkBack과 iOS VoiceOver 실제 device에서 다음을 완료한다.

```text
app launch·목록 탐색
→ record 생성과 validation 오류 수정
→ camera/location permission 거절 상태로 저장
→ attachment 추가 또는 대체 경로
→ offline pending 확인
→ conflict 비교·해결
→ notification 또는 sync 화면 진입
```

추가로 큰 font scale, 작은/좁은 screen, keyboard, color 이외 상태 표현, modal focus 복귀와 dynamic sync announcement를 확인한다.

사람 reviewer는 다음을 판정한다.

- 현재 상태와 다음 action을 보조기술로 이해할 수 있는가?
- permission·offline·conflict 실패에서 draft와 focus를 잃지 않는가?
- visual 상태와 accessibility role/label/state가 같은 source를 반영하는가?
- 알림과 in-app announcement가 과도하게 중복되지 않는가?

component test와 accessibility prop 검사는 실제 TalkBack/VoiceOver 발화·focus 순서를 보장하지 않는다.

## performance·resource gate

release-like build에서 환경과 측정 방법을 먼저 고정한다.

- cold/warm launch와 first meaningful record list
- 1,000 record scroll
- 20 thumbnail list와 image memory behavior
- edit save transaction
- outbox 100 command processing 중 interaction
- app active/background transition
- memory·storage·network·battery의 관찰

목표 수치는 프로젝트가 정하고 근거를 기록한다. sample count, device/OS, build profile, power/thermal/network condition과 측정 도구를 결과 옆에 둔다. development mode 수치나 simulator 한 번의 결과를 release claim으로 사용하지 않는다.

## 누적 failure gate

Stage 01~05의 실패를 release candidate에서 다시 결합한다.

- malformed/stale deep link와 notification cold start
- offline create/edit/delete와 local commit 직후 process kill
- 이전 schema upgrade와 outbox/attachment 복구
- response loss·duplicate·reorder·version regression·conflict
- storage full 또는 missing file fake
- permission deny/revoke와 capability unavailable
- background task not run, duplicate/stale notification
- auth block, malformed response와 permanent failure

각 실패 뒤 DB/outbox/file/session/UI final state와 source/build/runtime identity를 기록한다. 개별 unit test를 다시 나열하는 대신, 앞 단계의 상태가 한 release candidate에서 함께 보존되는지 검토한다.

## privacy·store gate

[`capstone/release-evidence.md`](../../../capstone/release-evidence.md)의 data inventory를 실제 구현과 맞춘다.

- 수집 data, source와 목적
- camera/location/notification permission 사용 이유와 denial 대체 경로
- local/remote 전송과 processor
- retention/delete/backup
- telemetry와 redaction
- 사용자 control
- store privacy/data safety declaration 초안
- reviewer가 핵심 흐름을 재현할 test account/data와 설명

법률 판단은 자동 점수화하지 않고 owner, 질문과 필요한 전문 검토 evidence를 남긴다. declaration 양식 작성은 실제 store 제출/승인을 뜻하지 않는다.

## rollout과 복구

다음을 명시한다.

- preview tester와 production staged rollout 단위
- crash·migration·sync·auth stop threshold와 관측 owner
- rollout 정지·remote update rollback 절차
- 새 binary forward-fix 절차
- backend compatibility window
- signing/credential 사고 시 escalation owner

이미 실행된 local migration이나 remote command는 JavaScript rollback만으로 되돌아가지 않는다. rollback과 data recovery를 같은 말로 쓰지 않는다.

## 자동 검증

자동화하기 적합한 항목:

- 전체 public behavior/unit/contract/integration suite
- reference 통과와 skeleton/known-wrong rejection
- link·structure·license와 source fingerprint
- resolved app config와 profile 정적 계약
- CNG generation, Android/iOS Metro bundle
- 가능한 host의 native compile와 artifact digest
- migration/upgrade fixtures와 Stage 04/05 fault history
- release evidence schema v2와 source/lock/config, `artifacts[]`·installation/signing/store ref 연결

자동 검사는 UI 문자열이나 generated file 존재만으로 통과시키지 않는다. build command가 실행되지 않았거나 tool 부재로 생략됐으면 필수 성공으로 표시하지 않는다.

cloud build는 유일한 필수 구현 수단이 아니다. local native build, EAS 또는 허가된 CI 중 하나를 선택하되 어떤 계층까지 실행했는지 결과에 적는다.

## 사람·실제 기기 검토

[`checks/manual-device-matrix.md`](../checks/manual-device-matrix.md)를 실제 device와 artifact identity로 채운다.

- Android와 iOS 행을 각각 실제 device인지 emulator/simulator인지 표시한다.
- 실제 device에서 실행하지 않은 case는 `미검사`로 둔다.
- Android 결과로 iOS를, simulator 결과로 actual-device 결과를 추정하지 않는다.
- `미검사` platform은 완료/통과 개수에 넣지 않고 필요한 device/account/tool과 reviewer 질문을 적는다.
- screenshot만 제출하지 않고 initial state, event, final DB/UI/artifact, 수행자/date를 연결한다.

현재 host에 full Xcode·signing identity·실제 iPhone이 없을 수 있다. 이때 iOS CNG/bundle evidence는 남길 수 있지만 iOS compile/install/VoiceOver/notification/background/signing은 그대로 `미검사`다. 자동 검사가 green이어도 이 사실은 바뀌지 않는다.

## 제출 증거

```text
stage-06/
├── release-candidate.md
├── artifact-manifest.json
├── native-boundary-review.md
├── cng-and-build-results.md
├── device-matrix.md
├── accessibility-results.md
├── performance-results.md
├── upgrade-results.md
├── privacy-review.md
├── rollout-plan.md
└── known-limits.md
```

각 문서는 [`checks/evidence-template.md`](../checks/evidence-template.md)의 환경·초기 상태·사건·기대 불변식·실제 관측·비보장 범위를 따른다.

## 완료 조건

- development·preview·production profile의 identity, backend, update와 signing owner가 분리돼 있다.
- CNG, JS bundle, native compile, signed artifact, install과 store processing을 서로 다른 gate로 판정한다.
- source·lockfile·config·version·runtime과 고유 ref의 Android AAB+APK/Play split, iOS xcarchive+IPA/TestFlight artifact set이 연결된다.
- installation의 실제 artifact ref·device class·관찰 runtime/policy·launch 결과가 일치하며 known-wrong matrix가 거부된다.
- artifact-linked signing claim/사람 검토와 store delivery declaration/사람 검토가 자동 진위 검증과 구분된다.
- 기존 Expo/native dependency의 필수 boundary review가 Android/iOS 경로와 failure를 추적한다.
- Android와 iOS installable release candidate를 실제 대상에 설치하고 결과를 기록했다. `미검사` platform은 완료로 판정하지 않는다.
- 이전 local data, attachment와 unsynced/conflict 상태를 보존하며 upgrade한다.
- 실제 보조기술과 device에서 핵심 흐름을 완료했다.
- release-like performance와 누적 failure evidence가 있다.
- privacy/store declaration이 실제 data inventory와 일치하고 법률 비보장 범위를 밝힌다.
- rollout 중단 기준과 rollback/forward-fix 차이를 기록했다.

## 비범위와 알려진 한계

- public store release·심사 승인 강제
- custom Kotlin/Swift module 구현 의무
- 모든 Android vendor/Apple device·OS 조합
- 법률·규제 인증
- enterprise MDM, 결제·subscription
- native Android/iOS 전문 최적화 전체

한 Android/iOS device의 통과는 지원 matrix 전체를 보장하지 않는다. local/fault server 결과는 production backend/provider를, signed artifact는 store approval/rollout을, 자동 green은 교육적 완성이나 `stable` 사람 승인을 보장하지 않는다.
