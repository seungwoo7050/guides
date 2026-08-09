# 로드맵과 선행 지식

이 문서는 `mobile-app`의 범위 계약이다. 먼저 독자와 선행 능력을 확인하고, catalog의 owns 5개가 학습 결과·문서·단계 실습·capstone·exit capability로 이어지는 경로를 고정한다.

## 목표 독자

다음 중 하나에 해당하는 개발자를 대상으로 한다.

- 작은 React 웹 애플리케이션을 만들었고 모바일 프로젝트에 합류하려는 개발자
- Expo 예제를 실행했지만 offline·permission·background·release 경계를 체계적으로 다루지 못한 개발자
- Android 또는 iOS 한쪽 경험이 있고 공통 React Native 제품 경계를 이해하려는 개발자
- AI가 생성한 모바일 코드를 실제 기기와 배포 계약으로 검증해야 하는 개발자

이 과정은 프로그래밍을 처음 배우는 입문 과정이 아니다.

## 시작 전에 할 수 있어야 하는 일

필수 기준선은 [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app)의 다음 결과다.

- TypeScript type과 runtime value가 다르다는 사실을 알고 외부 `unknown` 값을 parse한다.
- React component, props, state, controlled input과 effect setup/cleanup을 사용한다.
- HTTP status, body parsing, authentication과 application error를 구분한다.
- async 작업의 완료 순서가 시작 순서와 다를 수 있음을 안다.
- Git 저장소에서 install·build·test 명령을 찾고 작은 변경과 근거를 제출한다.

권장 기준선은 다음과 같다.

- [`web-front-react-nextjs`](https://github.com/seungwoo7050/guides/tree/web-front-react-nextjs)의 상태 소유권·request generation·접근성 원리
- [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks)의 DNS·TCP·TLS·timeout 경계
- [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity)의 최소 권한·민감정보·감사 원리

도구·host·device·account의 구체적인 준비와 대체 경로는 [선행 지식 점검](../reference/prerequisites.md)에 있다. React나 TypeScript 자체가 막힌다면 이 브랜치에서 다시 배우지 말고 기존 정본으로 돌아간다.

## 사전 진단

다음 질문 중 네 개 이상에 답하지 못하면 해당 개념을 먼저 복습한다.

1. component state, durable local state와 server state가 왜 다른가?
2. request 취소와 늦은 response 거절은 왜 서로 대체할 수 없는가?
3. TypeScript assertion이 외부 JSON을 검증하지 못하는 이유는 무엇인가?
4. session credential과 일반 화면 preference를 같은 저장소에 두면 왜 안 되는가?
5. HTTP 200과 업무 성공이 다른 경우를 설명할 수 있는가?
6. 사용자가 뒤로 가기를 했을 때 route와 화면 state를 어떻게 다시 맞추는가?
7. effect setup과 cleanup을 같은 수명 계약으로 설명할 수 있는가?
8. 작은 변경을 재현 가능한 test와 함께 제출할 수 있는가?

## 이 브랜치의 고유 문제

웹과 모바일은 React component를 공유할 수 있지만 실행 환경은 같지 않다.

```text
웹
browser tab이 열려 있는 동안 비교적 명시적인 navigation과 network lifecycle

모바일
OS가 process·activity·scene·background 작업·permission·notification을 중재
```

따라서 모바일 과정은 React 문법이 아니라 다음 상태와 실패를 소유한다.

- 사용자가 다른 앱으로 이동하거나 OS가 process를 종료한다.
- internal action, deep link, notification과 restoration이 같은 route를 다르게 요청한다.
- network가 연결돼 보여도 API에 도달하지 못하고, 응답을 잃으면 server 처리 여부가 불명확하다.
- permission은 미결정·허용·제한·거절·철회 상태를 오간다.
- system picker나 다른 Activity/scene 뒤 기존 JavaScript process가 사라질 수 있다.
- background task는 정확한 시각에 실행되거나 완료된다고 보장되지 않는다.
- JavaScript update와 설치된 native binary의 API가 호환되지 않을 수 있다.
- simulator와 실제 기기의 camera·notification·battery·memory 행동이 다르다.

상태의 owner, 상태를 바꾸는 사건, 정상·경계·대표 실패, 보존할 불변식, 검증과 비보장 범위는 각 개념 장과 Field Notes spec에서 이어서 설명한다.

## 소유·비소유 범위

`main` catalog의 소유 범위는 다음 다섯 가지다.

1. 모바일 앱 수명 주기와 navigation
2. 오프라인 캐시·동기화
3. 카메라·위치·알림·background 작업
4. Android·iOS 빌드·서명·배포
5. 네이티브 모듈 경계 읽기

비소유 범위는 **Kotlin·Swift 언어 전체**, **네이티브 Android·iOS 전문 트랙**, **모바일 백엔드 운영**이다. Kotlin·Swift 문법과 플랫폼 framework를 독립 과정처럼 확장하지 않고 public native boundary를 읽는 데 필요한 만큼만 다룬다. API·push provider·identity provider 운영을 실습 서버로 확대하지 않는다.

일반 React·HTTP·보안·서비스 운영은 각각 `web-app`/`web-front-react-nextjs`, `computer-networks`, `cybersecurity`, `web-infra`가 소유한다. 이 브랜치는 mobile lifecycle·device·binary에 생기는 delta와 실패만 설명한다. catalog에 없는 네이티브 전문 영역은 존재하는 내부 브랜치처럼 링크하지 않는다.

## 기준 stack과 development-build-first

```text
TypeScript              기존 웹 진입 경로 재사용
React Native            Android·iOS 공통 UI와 native component 경계
Expo SDK 57             일관된 native package와 build workflow
Expo Router             route와 deep link를 같은 경로 계약으로 관리
Development Build       프로젝트 native module·config를 포함한 기준 runtime
CNG                      app config·plugin에서 native project를 재현
SQLite                   restart 뒤 남는 구조화 local data
FileSystem               앱이 소유하는 media file
SecureStore              작은 credential·key-value secret
```

이 stack이 유일한 정답은 아니다. 중요한 것은 library를 바꿔도 다음 계약을 보존하는가다.

- UI는 durable local state와 sync 상태를 명확히 읽는다.
- credential과 일반 data의 저장소·수명을 분리한다.
- native dependency·permission·config 변경과 binary rebuild를 추적한다.
- background 실행이 없어도 foreground resume에서 결국 동기화된다.
- Android·iOS 차이를 adapter와 device matrix에 남긴다.

이 저장소는 Node `24.19.0`과 npm `11.17.0`을 재현 pin으로 사용한다. Expo SDK 57의 최소 Node `22.13.x`와 같은 뜻이 아니다. SDK 57 프로젝트는 `default@sdk-57`처럼 template을 명시하고 development build를 처음부터 기준 runtime으로 삼는다. Expo Go는 짧은 JS/UI 관찰에 선택적으로 사용할 수 있지만, 그 결과를 Stage 완료나 native 설정 증거로 인정하지 않는다. 특히 SDK 전환기의 물리 iPhone에서는 app store의 Expo Go가 SDK 57을 지원하지 않을 수 있다.

## 읽기 순서와 누적 실습

| 단계 | 읽을 문서 | Field Notes 결과 | 반드시 재현할 대표 실패 |
|---:|---|---|---|
| 01 | 01·02·03 | app shell, list/detail/edit, lifecycle·navigation intent 복원 | malformed/stale link, process restart, 작은 화면·큰 글자 |
| 02 | 04·05 전반 | SQLite CRUD, owned file, restart 복원, outbox 생성 | transaction 중단, migration, offline start |
| 03 | 06·08 전반 | camera·picker·선택적 위치, permission 상태와 adapter | denied/limited/revoked, pending picker result, unavailable device |
| 04 | 04·05 후반 | bounded sync worker, stable command identity, conflict 화면 | response loss, duplicate, reorder, 401, malformed response, conflict |
| 05 | 07 | opportunistic background sync, notification route | task 미실행·중단·중복, notification cold start와 stale payload |
| 06 | 08 후반·09·10 | native boundary 추적, device matrix, release evidence | binary/runtime 불일치, install/upgrade 실패, 미검사 gate |

각 stage는 다음 순서로 진행한다.

```text
문서의 owner·사건·불변식·실패를 읽음
→ spec의 시작 상태와 의도적 미완성을 확인
→ public behavior와 관측 결과를 먼저 정의
→ 최소 구현
→ 정상·경계·대표 실패를 재현
→ 자동 결과와 사람 판단 evidence를 구분해 기록
→ 다음 stage에서 같은 상태를 확장
```

## owns에서 exit capability까지의 추적

아래 표는 파일 존재가 아니라 사람이 따라갈 수 있는 학습 근거를 정의한다. capstone은 각 행을 따로 반복하지 않고 하나의 release candidate failure journey에서 여러 행을 결합한다.

| owns | 학습 결과 | 개념 설명 | 단계 실습·대표 실패 | capstone 근거 | 연결 exit capability |
|---|---|---|---|---|---|
| 모바일 앱 수명 주기와 navigation | OS/process/UI 수명을 분리하고 모든 진입을 검증된 navigation intent로 복원한다. | 01·02·03·07 | Stage 01 malformed/stale deep link·restart, Stage 05 notification cold start | restart와 notification 진입 뒤 DB 최신 상태로 올바른 route 복원 | Android·iOS에서 동작하는 앱을 만든다; 오프라인·권한·기기 기능 실패를 처리한다 |
| 오프라인 캐시·동기화 | local 의도와 file을 durable하게 보존하고 중단·중복·순서 역전·conflict 뒤 수렴시킨다. | 04·05 | Stage 02 transaction/migration, Stage 04 UNKNOWN·duplicate·reorder·conflict | offline edit부터 response loss·newer edit·conflict 해결까지 통합 trace | Android·iOS에서 동작하는 앱을 만든다; 오프라인·권한·기기 기능 실패를 처리한다 |
| 카메라·위치·알림·background 작업 | capability·permission·OS 실행 기회를 구분하고 핵심 기록 흐름을 degradation한다. | 06·07 | Stage 03 denied/limited/revoked, Stage 05 task 미실행·중복 | 사진 기록, 선택적 위치 거절, background 미실행과 notification 재진입 evidence | Android·iOS에서 동작하는 앱을 만든다; 오프라인·권한·기기 기능 실패를 처리한다 |
| Android·iOS 빌드·서명·배포 | source·app·build·runtime·artifact identity를 연결하고 install/upgrade/release gate를 판정한다. | 08·09·10 | Stage 06 platform build·device matrix·runtime mismatch·미검사 gate | 두 platform artifact identity와 install/upgrade 검토, signing/store 비보장 명시 | 실제 빌드와 배포 산출물을 검증한다 |
| 네이티브 모듈 경계 읽기 | Expo module 하나를 JS API에서 config·Android/iOS source·runtime failure까지 추적한다. | 06·08·09 | Stage 03 adapter/config, Stage 06 [native boundary review](../reference/native-project-reading.md)·rebuild failure | 선택한 module의 JS→config→Kotlin/Swift→OS trace와 두 platform 의미 비교 | Android·iOS에서 동작하는 앱을 만든다; 실제 빌드와 배포 산출물을 검증한다 |

문서 번호는 이 디렉터리의 `01`~`10`을 뜻하고, Stage spec은 [`exercises/field-notes`](../exercises/field-notes/README.md), 누적 종료 근거는 [capstone](../capstone/README.md)에 있다.

## 구현 프로필

### 전체 경로

처음 모바일 프로젝트를 만드는 경우 Stage 01부터 순서대로 진행한다.

### React Native 경험자

다음을 기존 저장소의 실행 결과로 증명할 수 있으면 Stage 01의 단순 UI 구현은 줄일 수 있다.

- route와 deep link가 같은 screen contract를 사용한다.
- process restart 뒤 persisted state를 복원한다.
- Android와 iOS의 back·safe area·keyboard 차이를 검사한다.

하지만 Stage 02의 durable local state, Stage 04의 실패 모델, Stage 06의 release evidence는 생략하지 않는다.

### native 개발 경험자

Kotlin·Swift 문법 설명은 건너뛸 수 있지만 다음 boundary evidence를 별도로 제출한다.

- generated native project와 직접 소유하는 native code의 경계
- JavaScript promise/event와 native thread·lifecycle의 연결
- runtimeVersion과 binary compatibility
- 두 플랫폼에서 같은 application meaning을 반환하는 adapter

## 완료 기준

가이드를 완료하려면 다음 결과가 있어야 한다.

- Field Notes Stage 01~06의 공개 계약을 구현하거나 동등한 프로젝트에서 같은 실패를 증명했다.
- offline 시작·기록·process restart·schema migration 뒤 local 의도가 보존된다.
- permission 거절·제한·철회와 capability 부재에도 핵심 기록 작업이 유지된다.
- 중복·UNKNOWN 결과·순서 역전·conflict가 있는 sync를 검사했다.
- background task가 실행되지 않아도 foreground resume로 수렴한다.
- camera와 picker를 구분하고 위치·notification 진입을 device evidence로 검토했다.
- native module 하나의 JavaScript→config→Android/iOS→runtime 경계를 추적했다.
- Android와 iOS 각각의 실제 installable build와 source/build/runtime identity를 기록했다. 실행하지 못한 platform은 대체 증거와 비보장 범위를 `미검사`로 남기되, 해당 exit capability를 완료했다고 판정하지 않는다.
- screen reader, 큰 글자, 작은 화면, 느린 네트워크, app restart와 install/upgrade를 검토했다.
- [capstone](../capstone/README.md)의 통합 failure journey와 사람 검토 질문에 필요한 evidence를 제출했다.

`prepare.sh`와 `verify.sh`의 성공은 위 항목 중 자동화 가능한 일부만 보조한다. 실제 device, 사용자 경험, signing·store 접근과 설명의 타당성은 사람이 검토한다. 완료는 전문가 자격이나 catalog `stable` 자동 승인이 아니라 기존 모바일 저장소에서 작은 기능을 끝까지 책임질 준비가 됐다는 뜻이다.

## 다음 프로젝트 경로

```text
기존 Expo/React Native 저장소의 toolchain과 build profile 확인
→ 한 화면의 route·local data·native dependency owner 복원
→ 실제 device에서 대표 실패 하나 재현
→ 작은 수정과 domain/device 회귀 검사
→ preview artifact와 source identity 공유
→ Android·iOS 차이·미검사 범위·rollback을 포함한 PR
```

일반 서비스 공개 운영은 `web-infra`, 네트워크 진단은 `computer-networks`, 보안 검토는 `cybersecurity`의 정본과 연결한다. 별도 네이티브 전문 브랜치는 현재 catalog에 없으므로, Kotlin/Compose 또는 Swift/SwiftUI가 주 업무가 될 때는 외부 전문 자료와 실제 프로젝트로 확장한다.

catalog의 `continues_to`는 비어 있다. 완료 뒤 필수 후속 브랜치를 임의로 만들지 않고, 위 프로젝트 경험을 기본 종료 경로로 삼는다.
