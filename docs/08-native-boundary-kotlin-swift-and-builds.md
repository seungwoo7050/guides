# Kotlin·Swift와 native boundary

React Native와 Expo를 사용해도 Android와 iOS가 사라지는 것은 아니다. JavaScript가 호출하는 module, permission configuration, app identifier, signing, build error와 OS lifecycle은 native project가 소유한다.

이 장은 Kotlin·Swift 언어 전체를 가르치지 않는다. **이미 사용하는 native dependency 하나를 JavaScript contract에서 generated configuration, Android·iOS source와 실제 build/runtime까지 추적하고 문제 계층을 좁히는 수준**을 목표로 한다. custom native module 구현은 선택 확장일 뿐 필수 완료 조건이 아니다.

## 목표

- JavaScript package 설치와 native binary 변경을 구분한다.
- CNG/generated native project와 직접 소유하는 native project의 workflow를 선택한다.
- Android와 iOS project에서 identifier·permission·entitlement·entry point를 찾는다.
- config plugin과 native module이 해결하는 문제를 구분한다.
- Kotlin·Swift method가 노출하는 promise/event/cancellation/error contract를 읽는다.
- main/UI thread, background work와 lifecycle 수명을 구분한다.
- native build 실패를 dependency·configuration·compile·signing·runtime 단계로 나눈다.
- 두 플랫폼이 같은 application meaning을 반환하는지 계약과 evidence로 검토한다.

연결 실습은 [Stage 03](../exercises/field-notes/specs/03-media-permissions.md)과 [Stage 06](../exercises/field-notes/specs/06-quality-release.md)이다.

## 먼저 workflow를 선언합니다

### CNG를 사용하는 프로젝트

```text
app config
+ Expo SDK와 package versions
+ config plugins
+ local Expo modules
→ prebuild
→ generated android/ios project
→ compile·sign
```

이 경우 generated directory를 정본으로 보지 않는다. native 변경은 재생성 가능한 입력으로 표현한다.

### native project를 직접 소유하는 프로젝트

```text
android/와 ios/를 source control에서 관리
→ Gradle·Xcode project를 직접 변경
→ package autolinking과 manual setup 관리
```

기존 brownfield app, 복잡한 native target 또는 직접 관리할 이유가 명확한 경우 사용한다.

두 workflow를 섞을 때 가장 위험한 상태는 generated file을 손으로 고친 뒤 다음 clean prebuild에서 변경이 사라지는 경우다. README에 다음을 명시한다.

- `android/`, `ios/`가 commit 대상인가?
- native config의 정본은 어디인가?
- clean generation 명령은 무엇인가?
- 직접 수정이 필요한 파일은 무엇이며 왜 예외인가?

## JavaScript 변경과 binary 변경을 구분합니다

다음은 대체로 새 native build가 필요하다.

- native package 추가·제거·version 변경
- permission, usage description, entitlement 변경
- app icon·splash 등 native asset/config 변경
- local module의 Kotlin·Swift 코드 변경
- Android manifest·Gradle·iOS plist·Xcode 설정 변경
- Expo SDK 또는 React Native native runtime 변경

반대로 순수한 route·component·domain logic은 compatible runtime에 JavaScript update로 전달할 수 있다. 실제 경계는 build fingerprint/runtime policy로 확인한다.

`Metro reload로 동작했다`는 사실은 새 설치 binary가 올바르다는 증거가 아니다.

## Android project를 읽는 기준

파일 경로와 build script 문법은 template/version에 따라 달라질 수 있다. 이름을 암기하기보다 다음 질문으로 찾는다.

### application identity

- `applicationId`와 namespace는 어디서 정하는가?
- debug·preview·production variant가 다른 id를 가지는가?
- versionCode와 versionName은 어디서 생성되는가?

### build graph

- root/settings build가 어떤 module과 plugin을 포함하는가?
- app module의 compile/target/min SDK는 무엇인가?
- native dependency와 autolinking 결과는 무엇인가?
- release signing config는 credential을 어떻게 참조하는가?

### runtime entry와 lifecycle

- Application과 Activity entry는 어디인가?
- intent/deep link와 notification response가 어디서 들어오는가?
- New Architecture와 native loader 설정은 어디인가?

### permission와 component

- generated/merged manifest에 실제 어떤 permission·service·provider가 있는가?
- library manifest가 추가한 항목은 무엇인가?
- foreground service나 exported component가 필요한가?

source manifest 하나만 읽지 말고 build variant의 merged manifest를 확인한다.

## iOS project를 읽는 기준

### application identity와 signing

- bundle identifier는 어디서 정하는가?
- marketing version과 build number는 무엇인가?
- development team, certificate와 provisioning profile은 어떻게 연결되는가?
- capability와 entitlement가 target별로 어떻게 다르는가?

### build graph

- Xcode project/workspace와 target은 무엇인가?
- package/CocoaPods/autolinking dependency는 어디에 연결되는가?
- build configuration과 scheme이 dev·preview·production을 어떻게 구분하는가?

### runtime entry와 configuration

- app delegate/scene lifecycle hook은 어디인가?
- Info.plist의 usage description과 URL type은 어떻게 생성되는가?
- push·background mode·associated domain 같은 capability는 어느 target에 들어가는가?

생성된 plist만 보지 말고 app config/config plugin과의 대응을 추적한다.

## config plugin과 native module은 목적이 다릅니다

### config plugin

build 전에 native project를 변경한다.

- manifest/plist key
- permission 설명
- Gradle·Xcode setting
- native asset 또는 target configuration

runtime에서 JavaScript가 호출하는 기능 자체는 아니다.

### native module

설치된 binary 안에서 JavaScript와 native API를 연결한다.

- device SDK 호출
- platform-only capability
- native view
- 고성능 또는 lifecycle-sensitive 작업

하나의 library가 둘 다 필요할 수 있다. module을 설치했지만 plugin이 적용되지 않으면 compile은 되더라도 permission/config가 빠질 수 있다.

## public contract부터 설계합니다

경계를 읽기 위한 표본으로 app의 build/runtime 환경을 반환하는 가상의 작은 module을 살펴본다. 이것은 attestation이나 device identity가 아니다.

나쁜 interface:

```ts
getDeviceInfo(): any
```

권장 contract:

```ts
type DeviceEnvironment = {
  platform: "android" | "ios";
  appBuild: string;
  runtimeVersion: string | null;
  capability: "available" | "limited" | "unavailable";
};

interface DeviceEnvironmentPort {
  getEnvironment(): Promise<DeviceEnvironment>;
}
```

정한다.

- 왜 이 결과가 device 신원이나 binary 진위를 증명하지 않는가?
- 어떤 추가 값이 개인정보 또는 fingerprint가 될 수 있어 제외됐는가?
- method가 어느 thread에서 실행되는가?
- app background·module teardown 중 취소되는가?
- platform API가 unavailable일 때 어떤 error인가?
- 같은 의미가 두 플랫폼에서 같은 union으로 표현되는가?

## native value를 그대로 노출하지 않습니다

Kotlin enum string과 Swift raw value를 그대로 application에 퍼뜨리면 platform 차이가 상위 계층으로 샌다.

adapter가 의미를 정규화한다.

```text
Android raw status / iOS raw status
→ native module result
→ TypeScript runtime validation
→ application capability union
```

숫자 timestamp 단위, nullable value, 큰 integer, binary buffer와 URI ownership도 명시한다. JavaScript number가 모든 native integer를 정확히 표현한다고 가정하지 않는다.

## 비동기와 thread를 구분합니다

일반적으로 JavaScript promise를 반환한다는 사실만으로 native 작업 thread가 정해지지는 않는다. 다만 Expo Modules API의 현재 `AsyncFunction` body는 기본적으로 JavaScript runtime과 다른 queue에 dispatch된다. 사용 중인 SDK 문서와 source에서 그 기본값과 명시적 `runOnQueue`/main queue 요구를 확인해야 하며, 다른 bridge/library의 규칙으로 일반화하지 않는다.

질문:

- OS API는 main thread를 요구하는가?
- file hashing·image processing이 UI thread를 막는가?
- callback은 어느 queue/thread에서 오는가?
- 결과를 resolve할 때 module/runtime이 아직 살아 있는가?
- 동시에 여러 호출을 허용하는가?

긴 CPU/I/O 작업은 적절한 executor/queue로 이동하고, UI API는 main thread 규칙을 따른다. thread 이동 뒤 공유 mutable state와 cancellation을 다시 검토한다.

## cancellation은 양쪽에서 전달합니다

JavaScript가 screen을 떠나거나 request를 취소해도 native SDK가 계속 작업할 수 있다.

가능한 contract:

```text
start operation → operationId
cancel(operationId)
event/result에는 operationId 포함
```

TypeScript adapter는 `AbortSignal` listener를 등록해 native `cancel(operationId)`를 호출할 수 있다. `AbortSignal` 객체 자체가 Kotlin·Swift로 직접 전달된다고 가정하지 않는다. native API가 자체 취소 token을 제공하면 module 내부에서 operation id와 그 token을 연결한다.

중요한 조건:

- cancel은 여러 번 호출해도 안전하다.
- 완료와 cancel race에서 한 번만 terminal result를 낸다.
- module teardown이 active listener/task를 정리한다.
- cancel 불가능한 작업은 결과 반영 generation을 상위에서 검사한다.

## error를 stable domain으로 바꿉니다

native exception message는 OS version과 library에 따라 바뀔 수 있다.

```ts
type NativeCapabilityError =
  | { code: "permission-denied"; canAskAgain: boolean }
  | { code: "unavailable"; reason: string }
  | { code: "cancelled" }
  | { code: "temporary"; retryable: boolean }
  | { code: "invalid-result" };
```

error에는 stable code, 사용자에게 노출하지 않을 diagnostic detail, cause를 구분한다. Java/Kotlin exception이나 NSError 전체를 telemetry에 무조건 serialize하지 않는다.

## event stream에는 구독 수명이 있습니다

sensor나 native SDK event를 노출할 때:

```text
listener 등록
→ native observation 시작
→ event에 sequence/identity 포함
→ listener 제거
→ 마지막 subscriber면 native observation 중단
```

Fast Refresh, route remount와 background transition에서 listener가 중복되지 않아야 한다. event 순서·누락·buffer 정책을 명시하고, 중요한 업무 상태는 event만 믿지 않고 snapshot/reconciliation API를 둔다.

## Kotlin·Swift를 어디까지 읽어야 하는가

### Kotlin

- class/object, nullability, data class
- suspend/coroutine과 callback의 수명
- sealed class/enum으로 결과 표현
- Android Context·Activity가 필요한 API의 차이
- main/background dispatcher 개념
- Gradle dependency와 manifest 위치

### Swift

- struct/class, optional, enum
- async/await와 completion handler
- actor/main actor 또는 queue 개념
- error/Result
- application/scene와 view controller context
- Xcode target·entitlement·plist 위치

언어 고급 기능을 모두 학습하는 것이 아니라 module public contract와 lifecycle을 리뷰할 정도가 목표다.

## native dependency를 선택할 때

확인할 것:

- 현재 Expo SDK/React Native/New Architecture 지원
- Android·iOS 최소 version
- config plugin 또는 manual setup
- maintenance·release·issue 상태
- permission·privacy 영향
- binary size·startup·thread 영향
- Expo Go/development build 지원 차이
- license
- 제거했을 때 native side effect가 깨끗이 사라지는가?

package README만 보고 선택하지 않고 example app와 실제 clean build를 확인한다.

## build 실패를 단계로 나눕니다

```text
1. dependency resolution
2. native project generation
3. Kotlin/Java 또는 Swift/Obj-C compile
4. resource·manifest·plist·entitlement merge
5. native link/package
6. signing
7. install/launch
8. JavaScript runtime와 module call
```

증거:

- exact command와 profile
- clean/dirty generated project 여부
- Expo/RN/package versions
- Gradle/Xcode error의 첫 원인
- generated manifest/plist
- device OS와 architecture
- app build/runtime version

마지막 수백 줄을 그대로 붙이지 말고 첫 실패와 dependency chain을 좁힌다.

## 필수 native-boundary review evidence

Stage 06에서는 실제 사용 dependency 하나를 골라 다음 경로를 한 표로 추적한다.

```text
TypeScript public call·runtime validation
→ package/autolinking과 config plugin 입력
→ generated Android manifest/Gradle + Kotlin/Java entry
→ generated iOS plist/entitlement + Swift/Obj-C entry
→ thread·lifecycle·error mapping
→ development build의 정상 호출과 대표 binary/runtime 불일치 실패
```

각 행에는 file/setting, owner, 변경 사건, 관측 명령 또는 screenshot/log, 그 evidence가 보장하지 않는 범위를 적는다. 한쪽 platform에서 구현이 없거나 fallback이면 숨기지 않고 application contract가 어떤 상태를 반환하는지 설명한다. custom Kotlin·Swift module 작성은 이 review 이후의 선택 확장이다.

## Stage 03·06 완료 기준

- project가 CNG인지 native directory 직접 소유인지 명시돼 있다.
- permission/config 변경이 clean generation에서 재현된다.
- Android merged manifest와 iOS built configuration에서 실제 capability를 확인했다.
- 선택한 기존 native dependency의 input·output·error·thread·cancellation contract를 source에서 추적했다.
- Kotlin/Java와 Swift/Obj-C 경계가 같은 application union을 반환하는지, 또는 platform fallback이 무엇인지 검토했다.
- native change 뒤 새 development build를 설치해 검사했다.
- build failure를 generation·compile·signing·runtime 계층으로 나눈다.
- JavaScript update가 요구하는 native API와 runtime version 호환성을 확인한다.

이 evidence는 검토한 dependency와 build variant의 경계만 설명한다. Kotlin·Swift 언어 숙련, 모든 transitive module, OS vendor 구현과 store signing을 자동으로 증명하지 않는다.

다음은 pure model부터 실제 기기 release build까지 어떤 검사층을 두고, frame·memory·battery와 crash를 어떤 근거로 판단할지 다룬다. [테스트·성능·관측성](09-testing-performance-and-observability.md)으로 이어간다.
