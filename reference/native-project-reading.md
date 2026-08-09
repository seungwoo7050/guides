# native project 읽기

이 문서는 특정 template의 파일 경로를 암기하는 목록이 아니다. generated 또는 직접 소유한 native project에서 build·runtime 계약을 복원하는 순서다.

## 1. source of truth

- `android/`, `ios/`가 commit돼 있는가?
- app config와 config plugin이 있는가?
- clean prebuild 뒤 diff가 재현되는가?
- local native module은 어디에 있는가?

## 2. identity와 version

### Android

- applicationId·namespace
- versionCode·versionName
- build type/flavor
- signing config reference

### iOS

- bundle identifier
- marketing version·build number
- target·scheme·configuration
- development team·provisioning

## 3. dependency graph

- Expo SDK/RN expected versions
- autolinked modules
- Gradle plugin/dependency 또는 Xcode package/pod
- New Architecture 지원
- 최소 OS/SDK
- native library license

## 4. permission와 capability

- Android merged manifest
- iOS built Info.plist와 entitlements
- usage description
- exported components
- background mode/foreground service
- associated domains/deep links
- push capability

source template가 아니라 실제 build variant 결과를 확인한다.

## 5. entry와 lifecycle

- Application/AppDelegate·scene entry
- Activity/view controller
- initial URL과 notification response
- native module registration
- background task registration
- app active/background hook

## 6. build failure 분류

```text
dependency resolution
generation/plugin
compile
resource/config merge
native link/package
signing
install
launch
JavaScript/native runtime call
```

첫 실패 계층과 exact command를 남긴다.

## 7. 선택한 dependency boundary review

- public TypeScript type
- package/autolinking과 config plugin input
- Kotlin/Java와 Swift/Obj-C entry·type mapping
- thread/queue
- cancellation
- error code
- event subscription cleanup
- lifecycle owner
- privacy data
- platform parity와 fallback

아래 표를 제출 evidence로 채운다. source link는 package version/commit까지 식별하고, generated result는 build profile을 함께 적는다.

| 경계 | owner/source | 변경 trigger | 관측 evidence | 보장하지 않는 범위 |
|---|---|---|---|---|
| TypeScript call/result |  |  |  |  |
| package/autolinking/plugin |  |  |  |  |
| Android source/config |  |  |  |  |
| iOS source/config |  |  |  |  |
| thread/lifecycle/error |  |  |  |  |
| build/runtime failure |  |  |  |  |

필수 결과는 이 경계를 읽고 양 플랫폼 계약과 대표 실패를 설명하는 것이다. custom module을 직접 작성하는 일은 선택 확장이고, Kotlin·Swift 전체 학습을 대신하지 않는다.

## 8. 변경 후 검사

- clean generation/build
- 실제 permission/config
- Android/iOS development build
- runtimeVersion/fingerprint
- install/upgrade
- deep link/notification
- release-like smoke

최소 대표 실패는 installed binary에 없는 native API를 같은 `runtimeVersion`의 JS가 호출하려는 상황이다. 실제 production update를 잘못 publish하지 말고 controlled build/test double 또는 preview environment에서 거부 evidence를 만든다.
