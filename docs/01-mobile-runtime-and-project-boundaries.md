# 모바일 runtime과 프로젝트 경계

모바일 앱은 하나의 JavaScript process가 계속 실행되는 프로그램이 아니다. 사용자가 화면을 보고 있는 동안에도 native UI, OS process, system picker, network service와 storage가 서로 다른 수명으로 움직인다.

운영체제는 process 생성·종료, permission, system UI와 background 실행 기회를 소유한다. 앱은 그 사건을 통제하지 못하며, 어떤 업무 상태를 즉시 durable하게 저장하고 시작 시 어떻게 조정할지를 소유한다. native application 계층은 두 책임 사이에서 OS 사건과 JavaScript 계약을 연결한다.

## 목표

이 장을 마치면 다음을 수행할 수 있어야 한다.

- JavaScript bundle, native binary와 OS 상태를 분리한다.
- foreground·background·terminated를 업무 상태와 혼동하지 않는다.
- process가 사라져도 남아야 하는 상태를 저장소로 이동한다.
- Expo config, generated native project와 직접 소유한 native code를 구분한다.
- Expo Go와 development build가 증명하는 범위를 설명한다.
- 모바일 기능을 route·application·domain·adapter 경계로 나눈다.

연결 실습은 [Stage 01](../exercises/field-notes/specs/01-runtime-navigation.md)이다.

## 이 장의 책임 경계

이 장은 React component와 effect의 일반 사용법을 다시 가르치지 않는다. 그 기준선은 [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app)에 맡기고, 복잡한 React 상태·비동기 경쟁은 [`web-front-react-nextjs`](https://github.com/seungwoo7050/guides/tree/web-front-react-nextjs)에 맡긴다. 여기서는 같은 UI가 OS process 종료, native binary와 재시작을 만날 때 생기는 모바일 고유 상태·실패만 다룬다.

| 상태·자원 | 실제 소유자 | 바꾸는 사건 | 보존할 불변식 |
|---|---|---|---|
| process·foreground 기회 | OS | launch, background, memory pressure, 사용자 종료 | callback 없이 종료돼도 committed data를 잃지 않는다. |
| native runtime·capability | 설치된 binary와 OS | build/install, OS update, permission/config 변경 | JavaScript가 설치 binary에 없는 API를 요구하지 않는다. |
| route intent·startup policy | application coordinator | launcher, link, notification, restoration | readiness 확인 전 private route를 확정하지 않는다. |
| record·outbox·attachment metadata | local repository | save, sync result, migration | 업무 commit과 재시도 근거를 함께 복원한다. |
| 일시 UI | component | focus, press, modal, render | process 종료 뒤 버려도 업무 정합성이 깨지지 않는다. |

정상 경로는 warm resume다. 대표 경계는 system picker나 deep link를 통한 cold start이고, 대표 실패는 save 직후 callback 없이 process가 사라지는 경우다.

## 세 실행 계층을 구분합니다

```text
JavaScript·React 계층
- component와 route
- application state machine
- domain rule
- native module 호출

Native application 계층
- Android Activity/Application, iOS application/scene
- native module과 view
- manifest, plist, entitlement, signing
- binary에 포함된 native dependency

운영체제 계층
- process 생성·종료
- permission과 system UI
- background scheduler
- notification delivery
- storage·network·memory pressure
```

React component가 unmount되는 것과 앱 process가 종료되는 것은 다르다. background로 갔다고 반드시 process가 죽는 것도 아니며, 화면이 다시 보였다고 JavaScript memory가 보존됐다는 보장도 없다.

## 화면 상태와 업무 상태를 분리합니다

Field Notes에서 다음 값은 수명이 다르다.

| 상태 | 예 | 권장 소유자 |
|---|---|---|
| 일시 UI | 열린 menu, press feedback | component |
| navigation | 현재 record id, modal route | router |
| 편집 draft | 저장하지 않은 title·note | 화면 또는 draft repository |
| local 업무 상태 | 저장된 record, outbox, conflict | SQLite |
| media | 촬영한 image bytes | app-owned file directory |
| credential | refresh token, 작은 device secret | secure storage |
| remote 정본 | server version과 policy | backend |
| 실행 관측 | app/build/runtime, sync attempt | logging·telemetry |

`useState`에 값이 있다는 사실은 process restart 뒤 복원된다는 뜻이 아니다. 반대로 모든 UI 상태를 database에 넣으면 stale screen과 migration 부담이 커진다.

상태마다 다음을 묻는다.

```text
누가 정본인가?
어떤 사건이 바꾸는가?
process가 지금 종료되면 잃어도 되는가?
다시 시작할 때 어디서 복원하는가?
오래된 값인지 어떻게 판정하는가?
```

## AppState는 신호이지 저장소가 아닙니다

`AppState`는 현재 app이 active/background 같은 상태인지 알려 준다. 이를 사용해 foreground 복귀 시 다음을 트리거할 수 있다.

- session과 remote data 재검증
- permission·locale·network 상태 재조회
- pending outbox 처리 요청
- 민감 화면 가리기 또는 unlock 요구

하지만 transition callback에서 모든 상태를 저장하는 설계는 안전하지 않다.

- OS가 callback을 충분히 실행할 시간을 주지 않을 수 있다.
- crash와 강제 종료에는 callback이 없다.
- platform transition 순서가 다를 수 있다.

중요한 local 변경은 사용자가 저장을 확정한 transaction 안에서 바로 기록한다. background event는 마지막 기회가 아니라 추가 최적화다.

## process 종료를 정상 입력으로 취급합니다

다음 실험을 기본으로 둔다.

```text
record 편집 저장
→ system picker 실행 또는 background 이동
→ process 종료
→ deep link나 launcher로 다시 시작
```

재시작 뒤 확인한다.

- 저장 완료 record가 남아 있다.
- 완료되지 않은 외부 작업을 무조건 성공으로 표시하지 않는다.
- pending upload와 outbox가 다시 실행 가능하다.
- route id가 존재하지 않으면 안전한 fallback으로 이동한다.
- 일시적인 loading·toast·in-flight promise는 복원하지 않는다.

Android에서는 다른 Activity를 다녀오는 동안 기존 Activity가 재생성되거나 process가 종료될 수 있다. system picker 결과처럼 platform이 복구 API를 제공한다면 adapter가 이를 startup reconciliation에 포함한다. 이 복구 API가 있다는 사실을 iOS나 다른 picker에도 일반화하지 않는다.

## binary와 bundle을 분리합니다

모바일 release에는 적어도 두 계약이 있다.

```text
Native binary
- native module과 OS capability
- manifest·plist·entitlement
- signing identity
- app identifier

JavaScript/update layer
- route·UI·application logic
- asset와 configuration 일부
```

JavaScript가 새 native method를 호출하는데 설치된 binary에 그 method가 없으면 update는 호환되지 않는다. 따라서 source version만 기록하지 말고 build와 runtime compatibility를 함께 기록한다.

이 구분은 [release·signing·update·store](10-release-signing-updates-and-store-delivery.md) 계약으로 이어진다.

## Expo config와 generated native project

Continuous Native Generation을 사용하면 native project는 다음 입력으로 재생성되는 산출물이다.

```text
Expo SDK template
+ app config
+ package와 autolinking
+ config plugins
+ local native modules
= android/와 ios/ project
```

이 방식에서는 generated 파일을 손으로 고친 뒤 그 변경을 정본으로 취급하지 않는다. 필요한 변경을 app config, config plugin이나 local module로 표현하고 clean generation에서 재현되는지 검사한다.

반대로 기존 brownfield app처럼 `android/`와 `ios/`를 직접 소유한다면 자동 생성이 덮어쓰지 않도록 workflow를 명확히 정한다. 두 방식을 애매하게 섞지 않는다.

## Expo Go와 development build의 증거 범위

이 가이드의 SDK 57 기준 경로는 development build를 기본 runtime으로 사용한다. Expo Go는 설치된 Expo Go가 해당 SDK를 실제로 지원할 때 Stage 01의 UI를 빠르게 관찰하는 선택 경로일 뿐이다. SDK 전환기에는 physical Expo Go의 지원 SDK가 template의 SDK와 다를 수 있으므로 [현재 create-expo-app 안내](https://docs.expo.dev/more/create-expo/)를 확인한다.

### Expo Go가 증명할 수 있는 것

- JavaScript·React 화면과 일부 Expo SDK 사용
- route와 일반 interaction의 빠른 확인
- 포함된 native module 안에서의 prototype

### Expo Go가 증명하지 못하는 것

- 실제 제품의 native dependency 집합
- custom permission message와 entitlement
- local native module
- 실제 push notification runtime
- signing·app identifier·store binary
- config plugin 결과

development build는 프로젝트가 선택한 native runtime을 포함한 개발용 binary다. Stage 01부터 사용할 수 있고, native 기능·configuration을 검증하는 Stage 03 이후에는 필수다.

## 기능 경계를 나눕니다

권장 구조는 framework 이름보다 dependency 방향이 중요하다.

```text
app/ 또는 routes/
  route parameter, screen composition, navigation intent

features/
  화면별 use case와 view model

domain/
  record, sync state, validation, conflict rule

repositories/
  local record·outbox interface

adapters/
  SQLite, FileSystem, SecureStore, HTTP, permission, notification

native/
  local Expo module과 platform configuration
```

domain rule이 `expo-sqlite`, `AppState`, camera API를 직접 import하면 process·permission·storage 실패를 독립적으로 검사하기 어렵다. adapter는 platform result를 application이 이해하는 명시적 상태로 변환한다.

예:

```ts
type CapabilityState =
  | { kind: "unknown" }
  | { kind: "available" }
  | { kind: "denied"; canAskAgain: boolean }
  | { kind: "limited" }
  | { kind: "unavailable"; reason: string };
```

이 예는 계층 분리를 보여 주기 위한 축약형이다. 실제 permission 계약에서는 capability availability와 `not-determined`·`granted`·`limited`·`denied` 상태를 별도로 모델링한다. Android와 iOS의 raw value가 달라도 app은 정규화된 의미를 기준으로 화면을 결정하되, platform 차이를 숨기지 않는다.

## startup을 상태 기계로 봅니다

나쁜 startup:

```text
App render
→ token이 있을 것이라 가정
→ DB migration과 remote fetch를 동시에 시작
→ deep link를 즉시 적용
```

권장 순서:

```text
native runtime 준비
→ local database open·migration
→ persisted session 읽기
→ pending external result reconciliation
→ initial link/notification intent 정규화
→ route 대상 존재·권한 검사
→ 화면 표시
→ foreground revalidation·sync 요청
```

모든 작업을 serial로 막을 필요는 없다. 하지만 어떤 결과가 어떤 전제를 요구하는지 명시한다. 예를 들어 public route는 session 확인 전 표시할 수 있지만 private record route는 local database와 authorization state가 준비돼야 한다.

## 실패를 계층별로 기록합니다

| 증상 | 가능한 계층 | 첫 증거 |
|---|---|---|
| app가 시작 즉시 종료 | native binary/config | device crash log, build/version |
| 화면만 비어 있음 | JS route/render | Metro/runtime error, route state |
| camera 버튼이 없음 | capability policy | permission·device capability state |
| 촬영 뒤 결과 손실 | lifecycle/picker adapter | process recreation, pending result |
| local record가 사라짐 | storage/migration | transaction log, DB schema version |
| sync가 멈춤 | application/network/background | outbox state, attempt id, AppState |

`모바일 버그`라는 하나의 범주로 묶지 않는다.

## 검증 범위와 한계

pure startup coordinator 검사는 event 순서와 route 결정을 결정적으로 검증할 수 있다. repository fixture는 process restart 뒤 복원 정책을 검증하고, development build의 실제 process 종료 실험은 JavaScript memory 없이 다시 시작되는 통합 경계를 검증한다.

하지만 다음은 각각 다른 근거가 필요하다.

- Metro reload는 native process 종료를 검증하지 않는다.
- simulator launch는 실제 OS의 memory pressure, picker와 signing을 보장하지 않는다.
- 한 platform의 성공은 다른 platform의 Activity/scene lifecycle을 보장하지 않는다.
- development build 성공은 preview/production binary, update compatibility와 store 전달을 보장하지 않는다.

따라서 자동 검사 결과와 Android·iOS 실제 기기 evidence를 분리해서 기록한다.

## Stage 01 완료 기준

- app 시작을 준비·복원·route 적용 단계로 설명한다.
- memory-only 상태와 persisted 상태를 목록화했다.
- list/detail/edit route를 직접 URL/deep link로 열 수 있다.
- 존재하지 않는 id와 인증되지 않은 private route에 fallback이 있다.
- background 이동과 process restart 뒤 저장 완료 상태를 복원한다.
- Expo Go와 development build의 차이를 프로젝트 문서에 기록한다.
- generated native project를 소유할지 CNG로 재생성할지 결정했다.
- 자동 coordinator 검사와 실제 process 종료 검사가 각각 보장하지 않는 범위를 기록했다.

다음은 화면이 보인다는 사실을 넘어 손가락·keyboard·작은 화면·보조기술에서도 같은 작업이 가능한지 검증한다. [layout·입력·접근성](02-layout-input-and-accessibility.md)으로 이어간다.
