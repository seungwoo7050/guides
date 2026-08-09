# 공식 자료와 version 기준

확인일: **2026-08-09**

이 문서는 가이드의 기준선과 변동 가능한 제약을 다시 확인할 정본 링크를 모은다. package patch version은 이 저장소의 lockfile이 소유한다. Expo SDK, OS·Xcode·store 요구, API behavior와 cloud quota는 실제 프로젝트 시작·release 시점에 다시 확인한다.

## 고정한 compatibility 기준

[Expo SDK reference](https://docs.expo.dev/versions/latest/)의 2026-08-09 matrix를 다음처럼 해석한다.

| 항목 | SDK 57 기준 | 이 저장소에서의 사용 |
|---|---|---|
| Expo SDK | 57.0.0 계열 | dependency compatibility 기준 |
| React Native | 0.86 | Expo가 정한 대응 version |
| React | 19.2.3 | Expo가 정한 대응 version |
| 최소 Node.js | 22.13.x | SDK 지원 하한 |
| Android | 7+, compile/target SDK 36 | native build/device 기준 |
| Apple platform | iOS 16.4+, Xcode 26.4+ | native build/device 기준 |

repository의 Node `24.19.0`과 npm `11.17.0`은 이 matrix의 하한을 바꾸는 주장이 아니라 준비·검증 재현을 위한 더 좁은 pin이다. Node는 `.nvmrc`, npm과 dependency graph는 `packageManager`와 `package-lock.json`을 따른다.

SDK 57 API 문서는 가능하면 `latest` alias 대신 아래의 `v57.0.0` URL을 사용한다. 다만 OS·store·EAS 서비스처럼 지속해서 바뀌는 요구는 최신 공식 페이지를 release 시점에 다시 확인한다.

## 프로젝트 생성과 runtime 선택

- [create-expo-app](https://docs.expo.dev/more/create-expo/) — SDK 전환기에는 `--template default@sdk-57`처럼 template을 명시한다.
- [Development builds](https://docs.expo.dev/develop/development-builds/introduction/) — 프로젝트가 선택한 native library와 configuration을 포함한 개발 runtime, local/EAS build 선택
- [Development builds FAQ](https://docs.expo.dev/develop/development-builds/faq/) — Expo Go의 고정 native code, remote push·app/universal link·SDK version 제약
- [Use a development build](https://docs.expo.dev/develop/development-builds/use-development-builds/) — native dependency/config 변경 뒤 rebuild 경계
- [Continuous Native Generation](https://docs.expo.dev/workflow/continuous-native-generation/) — app config·plugins에서 native project 생성

이 브랜치는 **development-build-first**다. 2026-08-09 현재 공식 `create-expo-app` 안내는 SDK 57 transition 중 물리 device에서 Expo Go를 쓰려면 SDK 54 project를 사용하라는 별도 주의를 둔다. 따라서 SDK 57 Field Notes의 기준 evidence를 app store Expo Go에 의존하지 않는다. 이 제한은 시점에 따라 바뀌므로 새 release나 template을 시작할 때 다시 확인한다.

## React Native·navigation·접근성

- [Expo Router introduction](https://docs.expo.dev/router/introduction/) — file-based route, typed route와 deep link
- [React Native AppState](https://reactnative.dev/docs/appstate) — active/background/inactive 상태와 event
- [React Native Linking](https://reactnative.dev/docs/linking) — cold/warm start URL 입력 경계
- [React Native Accessibility](https://reactnative.dev/docs/accessibility) — role·label·state와 TalkBack/VoiceOver
- [React Native Performance](https://reactnative.dev/docs/performance) — development overhead와 release-like 측정 경계

API 문서는 lifecycle event를 설명하지만 route restoration policy나 product invariant를 대신 정하지 않는다. 이 가이드의 navigation intent와 evidence 계약을 함께 사용한다.

## local data·기기 기능

- [Expo SQLite SDK 57](https://docs.expo.dev/versions/v57.0.0/sdk/sqlite/) — restart 뒤 유지되는 SQLite database와 transaction API
- [Expo FileSystem SDK 57](https://docs.expo.dev/versions/v57.0.0/sdk/filesystem/) — app file/directory access
- [Expo SecureStore SDK 57](https://docs.expo.dev/versions/v57.0.0/sdk/securestore/) — 작은 encrypted key-value와 platform별 persistence 제약
- [Expo ImagePicker SDK 57](https://docs.expo.dev/versions/v57.0.0/sdk/imagepicker/) — system photo/camera UI, permission과 pending result
- [Expo Camera SDK 57](https://docs.expo.dev/versions/v57.0.0/sdk/camera/) — camera view/capture와 capability
- [Expo Location SDK 57](https://docs.expo.dev/versions/v57.0.0/sdk/location/) — foreground/background location과 permission
- [Expo Network SDK 57](https://docs.expo.dev/versions/v57.0.0/sdk/network/) — device network state hint

SDK API가 제공하는 성공 값은 Field Notes의 업무 성공과 동일하지 않다. file ownership, transaction, runtime validation, permission degradation와 privacy retention은 application이 별도로 소유한다.

## background·notification

- [Expo BackgroundTask SDK 57](https://docs.expo.dev/versions/v57.0.0/sdk/background-task/) — OS가 결정하는 deferrable background task
- [Expo TaskManager SDK 57](https://docs.expo.dev/versions/v57.0.0/sdk/task-manager/) — location/background/notification task infrastructure
- [Expo Notifications SDK 57](https://docs.expo.dev/versions/v57.0.0/sdk/notifications/) — permission, token, Android channel, receive/respond lifecycle
- [Android background work](https://developer.android.com/develop/background-work) — Android의 scheduling·제한 정본
- [Apple background tasks](https://developer.apple.com/documentation/backgroundtasks) — Apple platform의 background task 정본

등록·예약 API 호출 성공은 정확한 시각의 실행·완료·delivery를 보장하지 않는다. 실제 device, OS version, app/force-stop 상태와 실행 trace를 evidence에 남긴다.

## native module·build

- [Expo Modules API](https://docs.expo.dev/modules/overview/) — Kotlin·Swift module, function/event/view 경계
- [Config plugins](https://docs.expo.dev/config-plugins/introduction/) — native configuration을 CNG source로 관리하는 방법
- [Local app development](https://docs.expo.dev/guides/local-app-development/) — local native compile·install과 host toolchain
- [Expo app config](https://docs.expo.dev/versions/v57.0.0/config/app/) — identifier, permission, plugin과 native config 입력
- [Android build documentation](https://developer.android.com/build) — Gradle, variant와 Android artifact 정본
- [Xcode build documentation](https://developer.apple.com/documentation/xcode/building-and-running-an-app) — Apple build/run 정본

prebuild나 JavaScript bundle 성공은 native compile·signing·install 증거가 아니다. CNG generated file을 읽을 때는 config/plugin/package 중 무엇이 source-of-truth인지 함께 기록한다.

## build·update·submit

- [EAS Build](https://docs.expo.dev/build/introduction/) — hosted native build workflow와 artifact
- [Local EAS builds](https://docs.expo.dev/build-reference/local-builds/) — cloud와 local EAS build의 차이와 제한
- [Runtime versions](https://docs.expo.dev/eas-update/runtime-versions/) — native binary와 update compatibility
- [EAS Update in builds](https://docs.expo.dev/build/updates/) — channel과 runtime compatibility
- [EAS Submit](https://docs.expo.dev/submit/introduction/) — store upload workflow
- [Google Play Console Help](https://support.google.com/googleplay/android-developer/) — Android 제출·정책·계정 요구 최신 정본
- [App Store Connect Help](https://developer.apple.com/help/app-store-connect/) — iOS 제출·TestFlight·권한 요구 최신 정본

EAS는 이 브랜치의 필수 cloud service가 아니다. local build와 fault server로 많은 계약을 검증할 수 있지만, cloud build, signing delegation, store processing과 rollout을 실행했다는 증거는 아니다. store program 비용·정책·target requirement와 EAS quota는 이 문서의 숫자로 고정하지 않고 release 직전에 각 공식 console에서 확인한다.

## 사용 원칙

- 공식 자료는 API와 현재 platform/service 제약의 정본이다.
- 이 브랜치는 상태 owner, 사건, 불변식, 대표 실패와 evidence 계약을 소유한다.
- `latest` 문서가 바뀌었으면 SDK 57 동작을 versioned 문서와 lockfile에서 먼저 확인한다.
- sample이나 API happy path를 production permission·background·signing·store 근거로 확대 해석하지 않는다.
- 실제 device 또는 account가 없어 실행하지 못한 항목은 `미검사`와 필요한 evidence로 남긴다.
- `prepare.sh`·`verify.sh` 통과만으로 교육적 완성이나 `stable`을 선언하지 않는다.
- SDK·OS·Xcode·store requirement가 바뀌면 이 문서의 확인일, 기준 표와 영향을 받는 실습 evidence를 함께 갱신한다.
