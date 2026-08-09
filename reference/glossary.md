# 용어

이 용어집은 특정 API 이름보다 상태 owner와 실패 의미를 먼저 고정한다. 자세한 행동 계약은 관련 개념 문서와 Field Notes spec을 따른다.

## lifecycle·navigation

### app lifecycle state

foreground/active, inactive, background와 process가 없는 terminated 상태를 구분하는 실행 상태다. OS가 전이를 중재하며 UI component 수명과 같지 않다.

### process recreation

OS 종료, 설정 변경, system UI 왕복 같은 사건 뒤 새 process가 durable state에서 업무를 복원하는 과정이다. 이전 memory state가 그대로 남는다고 가정하지 않는다.

### cold start / warm start

cold start는 app process가 없는 상태에서 시작하는 경우, warm start는 process가 살아 있는 상태에서 foreground로 오거나 새 intent를 받는 경우다.

### navigation intent

internal action, deep link, notification과 restoration을 공통 route 의도로 정규화한 값이다. 외부 payload를 그대로 route 정본으로 사용하지 않고 parse·validation·authorization 뒤 적용한다.

### restoration state

재시작 뒤 복원할 수 있도록 저장한 최소 navigation/UI 단서다. 업무 record의 정본을 복제하는 저장소가 아니며, 존재하지 않거나 권한 없는 entity를 열도록 강제하지 않는다.

## runtime·native boundary

### app binary

Android AAB/APK 또는 iOS IPA/app처럼 native code, resource, configuration과 JavaScript bundle의 초기 사본을 포함하는 빌드 산출물이다. AAB는 store 전달용 bundle일 수 있으며 그 자체가 device에 직접 설치 가능한 APK와 같지 않다.

### JavaScript bundle / update

React component와 application logic, asset reference를 묶은 실행 code다. remote update는 설치된 app binary가 제공하는 native API와 `runtimeVersion`이 호환될 때만 안전하다.

### runtimeVersion

설치된 native runtime과 remote JavaScript/assets update가 호환되는지 구분하는 identity다. app version, build number나 source commit과 동일하지 않다.

### development build

프로젝트가 선택한 native module과 configuration을 포함한 개발용 app binary다. Expo Go보다 실제 제품 runtime에 가깝지만 debug tooling과 개발 설정이 있어 production 성능·signing을 증명하지 않는다.

### preview / release-like build

내부 검토를 위해 production과 비슷한 optimization·native configuration으로 만든 artifact다. production signing, store processing, rollout 또는 사용자 upgrade 성공까지 자동으로 보장하지 않는다.

### Expo Go

미리 정해진 Expo native module을 포함한 공용 학습 app이다. 빠른 JS/UI 실험에 유용하지만 custom native code/configuration, app identity, signing·production binary를 증명하지 않는다.

### CNG

Continuous Native Generation. app config, config plugin과 package를 입력으로 Android/iOS native project를 반복 생성하는 workflow다. generated directory를 직접 고치는 방식과 source-of-truth가 다르다.

### config plugin

prebuild 시 native project의 manifest, plist, entitlement, build setting 같은 configuration side effect를 적용하는 code다.

### native module

JavaScript/TypeScript에서 Kotlin·Swift 등 native API를 호출하거나 native event/view를 사용할 수 있게 하는 binary code 경계다. promise·event·thread·lifecycle·error 의미가 public contract에 포함된다.

### platform adapter

Android와 iOS API 차이를 application이 이해하는 같은 의미로 변환하는 경계다. 차이를 숨기는 대신 capability, permission, cancellation과 failure를 명시적으로 반환한다.

## local data·sync

### local-first

핵심 사용자 작업을 local durable state에 먼저 완료하고 remote sync를 별도 수명으로 수행하는 설계다. server authorization·policy까지 local이 소유하거나 모든 remote data를 cache한다는 뜻은 아니다.

### durable local state

process restart 뒤에도 남아야 하는 record, outbox, conflict, migration metadata와 app-owned file이다. component state나 in-memory cache와 owner·수명이 다르다.

### outbox

local 업무 변경과 같은 transaction에 기록되는 remote command queue다. process restart·offline·retry 뒤에도 사용자 의도를 보존한다.

### command identity

한 번의 사용자 업무 의도를 안정적으로 식별하는 값이다. response를 잃어 같은 의도를 retry할 때 새로 만들지 않는다.

### attempted command

server에 보내기 시작한 command identity, payload와 `baseVersion`의 불변 snapshot이다. retry 중 newer local edit가 생겨도 이미 시도한 command의 의미를 몰래 바꾸지 않는다.

### baseVersion

사용자가 local 변경을 만들 때 기준으로 삼은 remote entity version이다. server current version과 다르면 conflict를 명시할 수 있다.

### UNKNOWN result

timeout·연결 종료 때문에 client가 결과를 받지 못했지만 server 처리 여부를 모르는 상태다. 확정 실패로 표시하거나 새 command로 같은 효과를 중복 적용하지 않는다.

### conflict

local 의도와 remote current state를 자동으로 덮어쓰면 불변식이나 사용자 의도를 잃는 상태다. 두 snapshot과 해결 결정을 보존하며 단순 network error와 구분한다.

### tombstone

offline delete나 복제에서 삭제 사실을 전달하기 위해 남기는 durable marker다. row를 즉시 없애 삭제 command와 version 정보를 잃는 일을 막는다.

### staging file / app-owned file

staging file은 picker/camera의 임시 URI에서 앱이 관리하는 durable file로 전환하는 중간 상태다. app-owned file은 앱이 lifecycle·backup·retention·cleanup 책임을 가진 사본이다. DB 연결 실패나 crash 뒤 orphan reconciliation이 필요하다.

## capability·permission·background

### capability availability

device, OS version와 현재 binary에 기능이 존재하는지 나타낸다. 사용자가 기능 접근을 허용했는지를 뜻하는 permission state와 다르다.

### permission state

권한의 not-required, not-determined, granted, limited, denied, restricted와 다시 요청 가능 여부를 포함한 제품 상태다. `not-required`는 전체 권한 grant가 아니라 해당 API가 요청 없이 제공하는 제한된 접근이다. 한 번 허용된 권한도 Settings·정책·OS 사건으로 철회될 수 있다.

### limited permission

사용자가 전체 resource가 아니라 선택된 사진 등 일부 범위만 허용한 상태다. denied와 다르며 기능별로 존재 여부와 의미가 다르다.

### system picker

OS가 소유하는 사진/문서 선택 UI다. 직접 camera capture와 permission·lifecycle이 같다고 가정하지 않는다. 다른 activity/scene 왕복과 pending result 복구를 고려한다.

### background task

app가 foreground가 아닐 때 OS가 조건과 quota에 따라 실행 기회를 줄 수 있는 작업이다. 정확한 실행 시각, 횟수, 완료 또는 delivery를 보장하지 않는다.

### bounded worker

작은 시간·item budget 안에서 durable state를 읽고 한정된 작업만 수행한 뒤 안전하게 중단할 수 있는 worker다. foreground와 background가 같은 idempotent core를 호출할 수 있다.

### notification intent

notification response에서 얻은 재참여 신호다. entity identifier나 action을 navigation intent로 parse하는 입력이지 record·권한·sync 결과의 정본이 아니다.

## build·검증

### application identity

Android `applicationId`와 iOS bundle identifier처럼 설치·signing·store record를 연결하는 식별자다. Expo project id와 같은 값이 아니다.

### source/build/runtime identity

source revision, application identifier, semantic version, build number, runtime fingerprint/policy와 고유 ref의 artifact 집합을 연결한 provenance다. signing claim/review, 설치 관찰과 store build를 각 artifact에 연결해 어느 code가 어느 publishing·설치 산출물에 들어갔는지 추적한다.

### installable artifact

대상 device/emulator에 실제 설치할 수 있는 APK/Play split 또는 iOS app/IPA/TestFlight build다. store upload용 AAB, xcarchive, JavaScript bundle, CNG 생성 성공만으로 대체하지 않는다. simulator `.app`은 physical iOS 설치 artifact가 아니다.

### acceptance evidence

어떤 초기 상태와 사건에서 어떤 DB·file·UI·artifact 결과가 나왔는지 재현 가능한 명령, test, trace, screenshot과 device/build 정보로 남긴 근거다.

### automated check

공개 행동·불변식의 일부를 반복 검사하는 도구다. 실제 device UX, 설명의 타당성, signing·store 권한이나 교육적 완성을 자동 증명하지 않는다.

### 사람의 stable 검토 준비 완료

소유 범위와 exit capability의 문서·실습·capstone 근거, 자동 검사 결과, 수동 evidence와 알려진 한계를 사람이 검토할 수 있게 모은 상태다. `stable` 승인 자체가 아니며 자동 검사기가 선언할 수 없다.
