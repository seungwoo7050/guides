# 플랫폼 입력, 접근성, 저장 수명과 release

## 문제

게임은 개발 PC의 editor에서 실행되는 동안보다 실제 플랫폼에서 더 많은 사건을 만납니다.

- user sign-in/sign-out와 controller 재할당
- application focus loss, suspend, resume와 quick resume
- storage quota, cloud conflict와 device removal
- safe area, DPI, HDR, localization와 text input
- platform overlay, invite, entitlement와 network privilege
- patch, DLC, content branch와 rollback
- 접근성 설정이 없는 첫 실행과 기존 save에서의 재실행

플랫폼 integration을 개발 마지막의 체크리스트로 미루면 gameplay·save·UI·input 구조를 다시 바꿔야 합니다. release는 package upload 한 번이 아니라 **정확한 build/content/settings 조합을 사용자에게 전달하고 이후 문제를 조사·복구하는 계약**입니다.

## 핵심 상태

### application lifecycle

```text
Launching
→ ForegroundActive
→ FocusLost
→ Suspending
→ Suspended
→ Resuming
→ ForegroundActive
→ Terminating
```

플랫폼마다 callback과 시간 제한이 다르지만 프로젝트는 다음을 정합니다.

- input을 언제 차단/초기화하는가
- save/checkpoint를 언제 요청하는가
- network session을 유지/재연결/포기하는가
- audio와 vibration을 언제 중단하는가
- renderer와 resource를 언제 축소하는가
- resume 뒤 어떤 state를 검증하는가

### user와 controller 상태

- platform user/account
- local player slot
- controller/device ownership
- online permission/privilege
- save/profile owner
- guest와 signed-in user

controller disconnect를 sign-out으로 해석하지 않고, user switch가 기존 save와 online session에 미치는 영향을 명시합니다.

### accessibility state

접근성은 별도 mode 하나가 아니라 input, UI, visual, audio, timing과 difficulty에 걸친 player option입니다.

- complete input remapping과 conflict resolution
- hold/toggle, repeated press와 simultaneous input 대안
- sensitivity, dead zone, aim/steering 보조의 범위
- subtitle, speaker label, size, contrast와 background
- UI/text scale, screen reader/narration 가능성
- color 외 추가 cue
- camera shake, motion blur, flashing과 motion sickness option
- audio cue의 visual/haptic 대안
- pause, checkpoint와 timing 조절

설정 화면 자체가 첫 cinematic이나 gameplay보다 먼저 접근 가능해야 하는지 제품 요구로 정합니다.

### release identity

```text
source revision
+ engine/toolchain version
+ content manifest
+ platform configuration
+ executable/package id
+ save schema
+ network protocol
+ telemetry schema
+ release channel
```

사용자 bug report와 backend에서 같은 조합을 식별할 수 있어야 합니다.

## 설계 계약

### suspend를 정상 transition으로 다룹니다

suspend callback 안에서 무제한 I/O를 시작하지 않습니다. 미리 checkpoint 가능한 state를 유지하고 platform deadline 내에 필요한 최소 작업만 수행합니다. 작업 완료 여부와 last known-good save generation을 기록합니다.

resume에서는 다음을 재검증합니다.

- active user와 controller
- entitlement/permission
- network connection과 session validity
- wall clock 의존 event
- external content/save conflict
- device/resource availability
- audio focus와 display mode

### 접근성 option을 save와 profile에 versioning합니다

새 option이 추가돼도 기존 profile에 안전한 default를 제공합니다. device-specific binding과 account-wide preference를 구분합니다. “설정을 꺼도 gameplay 정보를 잃지 않는가”를 테스트합니다.

### localization과 UI layout을 data contract로 다룹니다

- localized string key와 fallback
- plural/gender/number formatting
- text expansion과 wrapping
- right-to-left 필요 여부
- font glyph와 fallback
- input glyph가 current device/binding을 반영하는지
- subtitle timing과 speaker metadata

문자열 길이를 고정 pixel layout으로 가정하지 않습니다.

### build와 content channel을 분리합니다

executable, base content, optional DLC와 live data가 서로 다른 cadence로 배포될 수 있습니다. compatibility matrix와 minimum/maximum version, rollback 가능 범위를 정합니다.

### release gate를 evidence로 만듭니다

```text
required build tests
+ target-device smoke
+ save migration matrix
+ input/accessibility checks
+ content validation
+ crash/hang baseline
+ performance budget
+ network compatibility
+ known issues and rollback
```

checkbox만이 아니라 report와 artifact id를 연결합니다.

### staged release와 recovery를 준비합니다

가능한 플랫폼에서는 internal/QA/beta/staged/default channel을 구분하고 telemetry와 crash를 확인한 뒤 확대합니다. 문제가 생기면 executable rollback만으로 save/content/backend compatibility가 복구되는지 검토합니다.

## 대표 실패

### focus loss 뒤 held input이 계속됩니다

keyboard/gamepad release event를 받지 못할 수 있습니다. focus lost에서 input state를 reset하고 resume 시 명시적으로 resample합니다.

### suspend 중 save를 in-place로 씁니다

deadline 종료로 corruption이 생깁니다. atomic generation과 이전 known-good를 유지합니다.

### accessibility를 마지막 QA 항목으로 봅니다

input context, UI layout, camera, audio cue와 timing 구조가 이미 고정돼 수정 비용이 커집니다. 기능 설계에서 requirement를 포함합니다.

### build number만 기록하고 content version을 잃습니다

동일 executable에 다른 content가 배포되면 bug 재현과 save/replay 해석이 불가능합니다.

### rollback이 protocol/save downgrade를 고려하지 않습니다

새 client가 쓴 save와 backend state를 old build가 읽지 못합니다. forward-compatible write, migration gate 또는 downgrade 금지를 정합니다.

### target platform 대신 개발 PC에서 certification 문제를 추측합니다

overlay, user switch, storage, network permission과 suspend behavior는 실제 target 환경에서 검증해야 합니다.

## 관찰과 검증

### lifecycle matrix

| initial | event | expected |
|---|---|---|
| Playing | focus lost | gameplay input reset, audio policy applied |
| Playing | suspend | checkpoint request bounded, session state recorded |
| Suspended | resume same user | state validation then control restored |
| Suspended | resume different user | old profile not exposed, explicit transition |
| Saving | storage full | old generation retained, actionable error |
| Online | permission revoked | protected feature blocked, local state preserved |

### 접근성 test

- keyboard/mouse/gamepad/touch 중 지원 장치에서 모든 필수 action을 수행합니다.
- 주요 action을 rebind하고 conflict를 해소할 수 있습니다.
- subtitles와 중요한 UI가 text scale·safe area·localization에서 잘리지 않습니다.
- color, audio 또는 haptic 하나를 제거해도 중요한 정보가 다른 cue로 전달됩니다.
- camera shake·flash·motion 옵션이 실제 효과를 제어합니다.
- first-run settings와 기존 save migration을 각각 검사합니다.

### release artifact

- package/manifest hash
- included content/depot/chunk list
- symbols와 crash mapping
- test/profile reports
- known issue와 waiver owner/expiry
- rollback/disable procedure
- backend compatibility

## 실습 연결

[release readiness 실습](../exercises/08-release-readiness/README.md)에서 lifecycle, input, accessibility, save와 release artifact evidence를 검토합니다.

## 기존 브랜치와 경계

- 일반 모바일 lifecycle은 `mobile-app`이 소유합니다.
- artifact promotion, deployment와 rollback 원리는 `web-infra`·`platform-engineering`이 소유합니다.
- 현재 문서는 console/PC/mobile game의 user/controller, suspend/save, accessibility, content compatibility와 player-facing release gate를 소유합니다.

## 완료 기준

- focus, suspend/resume, user/controller와 storage event를 explicit state transition으로 설계합니다.
- input·UI·visual·audio·timing 접근성 requirement를 초기 기능 계약에 포함합니다.
- build/content/save/protocol/telemetry version을 하나의 release identity로 연결합니다.
- target platform evidence, staged rollout과 rollback compatibility를 release decision에 포함합니다.
