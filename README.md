# 모바일 애플리케이션 개발

이 브랜치는 웹 애플리케이션 경험이 있는 개발자가 **Android와 iOS에서 설치·재시작·오프라인 사용·기기 기능·배포까지 검증할 수 있는 앱**을 만들도록 안내한다.

기본 구현 경로는 **TypeScript + React Native + Expo SDK 57**이다. 이것은 Kotlin·Swift·Flutter를 비교하는 기술 목록이 아니다. 하나의 제품을 두 운영체제에서 완성하면서 모바일에만 존재하는 실행 수명, 권한, 저장소, background 작업, native binary와 배포 계약을 학습한다.

> 이 저장소의 자동 검사는 재현 가능한 준비 상태와 공개 행동의 일부만 확인한다. 검사 통과만으로 교육적 완성이나 `stable`을 선언하지 않는다. 이 작업본의 목표 상태는 **사람의 stable 검토 준비 완료**이며, 최종 승인은 별도의 사람 검토가 맡는다.

## 대상 독자와 시작점

작은 TypeScript·React 웹 앱을 만들고 Git으로 변경을 제출해 본 개발자를 대상으로 한다. 필수 선행 경로는 [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app)이며, React 상태·비동기 경쟁·접근성, 네트워크, 보안이 막히면 각각 `web-front-react-nextjs`, `computer-networks`, `cybersecurity`의 필요한 부분만 복습한다.

- 빠른 진단과 전체 순서: [로드맵과 선행 지식](docs/00-roadmap-and-prerequisites.md)
- host·device·account 준비: [선행 지식 점검](reference/prerequisites.md)
- 처음 보는 용어: [용어](reference/glossary.md)
- version과 API 정본: [공식 자료와 version 기준](reference/official-sources.md)

프로그래밍·TypeScript·React 자체를 처음 배우는 과정은 아니다. macOS가 아닌 host에서도 문서와 대부분의 domain 검사를 진행할 수 있지만, iOS native build는 macOS와 호환되는 Xcode가 필요하고 실제 기기·서명·store 제출은 별도의 장치·계정·권한이 필요하다.

`main`의 **모바일 애플리케이션 개발** 트랙에서 엄밀한 필수 항목은 `git` 공통 기반, `web-app`, 이 브랜치다. 처음 접하는 독자에게 제시된 기본 선형 경로는 `git → web-app → web-front-react-nextjs → mobile-app`이며, 여기서 `web-front-react-nextjs`는 필수 의존성이 아니라 모바일 진입 전에 React 상태·접근성 경계를 보강하는 권장 단계다. `computer-networks`·`cybersecurity`·`web-infra`도 필요에 따라 연결한다. **웹 프런트엔드 개발** 트랙에서는 모바일 실행 환경으로 확장하려는 독자의 심화 선택지다. 어느 경로에서도 이 브랜치가 일반 웹·네트워크·보안·운영 정본을 대체하지 않는다.

## 이 브랜치가 소유하는 것

아래 다섯 항목은 `main` catalog의 소유 범위를 그대로 사용한다.

1. **모바일 앱 수명 주기와 navigation** — foreground·background·terminated, process 재생성, route·deep link·notification intent·상태 복원
2. **오프라인 캐시·동기화** — durable local state, SQLite·file ownership, outbox, 재시도·중복·순서 역전·conflict
3. **카메라·위치·알림·background 작업** — capability와 permission, privacy, OS가 중재하는 실행 기회와 안전한 degradation
4. **Android·iOS 빌드·서명·배포** — app identity, native configuration, build profile, signing, runtime compatibility와 release evidence
5. **네이티브 모듈 경계 읽기** — JavaScript API에서 config plugin·generated project·Kotlin/Swift·OS failure까지 [경계 추적](reference/native-project-reading.md)

touch·safe area·keyboard·접근성, session·network 오류, 성능·관측성은 독립 소유 범위를 넓히려는 장이 아니다. 위 다섯 모바일 계약을 실제 화면과 기기에서 검증하는 데 필요한 범위로 다룬다.

## 의도적으로 다루지 않는 범위

`main` catalog의 비소유 범위도 그대로 유지한다.

- **Kotlin·Swift 언어 전체**: 이 브랜치에서는 native public boundary를 읽고 작은 변경을 좁혀 검증하는 데 필요한 만큼만 사용한다.
- **네이티브 Android·iOS 전문 트랙**: Compose·SwiftUI/UIKit·플랫폼 framework 심화는 현재 내부 정본으로 제공하지 않는다.
- **모바일 백엔드 운영**: API·push provider·identity provider의 production 운영은 이 브랜치가 소유하지 않는다. 일반 공개 서비스 운영은 [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra)가 소유한다.

HTML·CSS·TypeScript·React·HTTP의 일반 원리는 [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app), React의 웹 심화는 [`web-front-react-nextjs`](https://github.com/seungwoo7050/guides/tree/web-front-react-nextjs), DNS·TCP·TLS는 [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks), 일반 보안은 [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity)의 정본을 사용한다. 이 브랜치에서는 그 원리가 mobile OS·process·device·binary 경계에서 어떻게 달라지는지만 다룬다.

## 종료 능력과 판단 근거

완료 뒤 주장할 수 있는 능력은 다음 세 가지뿐이다. 각 주장은 문서 독서가 아니라 관측 가능한 근거를 요구한다.

| exit capability | 필요한 대표 근거 |
|---|---|
| **Android·iOS에서 동작하는 앱을 만든다** | Field Notes Stage 01~05의 공통 업무 흐름, platform 차이 기록, Android·iOS 실제 기기 결과; 대체 환경만 썼다면 미충족 범위 명시 |
| **오프라인·권한·기기 기능 실패를 처리한다** | restart·migration·permission 거절/철회·중복/UNKNOWN 응답·conflict·background 미실행을 포함한 상태·불변식 증거 |
| **실제 빌드와 배포 산출물을 검증한다** | source revision, app/build/runtime identity, install/upgrade smoke와 signing·store 준비를 구분한 release evidence |

이는 모바일 전문가가 됐거나 production backend·store 심사를 운영했다는 뜻이 아니다. 자동 검사가 실행하지 못한 실제 device·signing·store 항목은 `미검사`로 남기고, 사람이 evidence를 검토한다.

## 기준 환경

| 항목 | 이 저장소의 기준 | 구분 |
|---|---|---|
| Node.js | `24.19.0` (`.nvmrc`) | 재현을 위한 repository pin |
| npm | `11.17.0` (`packageManager`와 lockfile) | 재현을 위한 repository pin |
| Python | `3.11` 이상 | prepare/verify script 지원 하한 |
| Expo SDK | `57` | 학습·dependency 기준 |
| React Native / React | `0.86` / `19.2.3` | Expo SDK 57 compatibility |
| Expo가 요구하는 최소 Node | `22.13.x` | SDK 지원 하한이며 이 저장소의 pin과 다름 |
| Android | 7 이상, compile/target SDK 36 | Expo SDK 57 support matrix |
| Apple platform | iOS 16.4 이상 | Expo SDK 57 support matrix |
| navigation | Expo Router | route·link 통합 경로 |
| native workflow | development build + CNG | 제품에 가까운 기준 runtime |

정확한 package patch version은 lockfile이 소유한다. SDK 57 프로젝트는 template version을 명시해 생성한다. **이 가이드는 development-build-first**다. Expo Go는 제한된 native module을 가진 학습용 runtime이며, 현재 SDK 전환기에는 app store의 물리 iPhone용 Expo Go가 SDK 57을 열지 못할 수 있다. Expo Go나 simulator에서 보인 결과는 native configuration·signing·production binary의 증거가 아니다. 변동 가능한 기준과 확인일은 [공식 자료 목록](reference/official-sources.md)에 기록한다.

## 학습 순서

| 순서 | 문서 | 핵심 질문 | 연결 실습 |
|---:|---|---|---|
| 0 | [로드맵과 선행 지식](docs/00-roadmap-and-prerequisites.md) | 무엇을 이미 알아야 하며 어디까지 만드는가? | 전체 |
| 1 | [모바일 runtime과 프로젝트 경계](docs/01-mobile-runtime-and-project-boundaries.md) | 화면이 사라져도 어떤 상태가 살아 있어야 하는가? | Stage 01 |
| 2 | [layout·입력·접근성](docs/02-layout-input-and-accessibility.md) | 손가락·keyboard·화면·보조기술이 달라도 같은 작업이 가능한가? | Stage 01 |
| 3 | [navigation·link·상태 복원](docs/03-navigation-links-and-state-restoration.md) | 외부 intent와 재시작 뒤 어떤 화면을 열어야 하는가? | Stage 01 |
| 4 | [network·session·오류 계약](docs/04-networking-session-and-error-contracts.md) | 연결 여부와 요청·업무 성공을 어떻게 분리하는가? | Stage 02·04 |
| 5 | [local data·offline·sync](docs/05-local-data-offline-and-sync.md) | local 의도와 server 상태를 어떻게 안전하게 수렴시키는가? | Stage 02·04 |
| 6 | [permission·기기 기능·privacy](docs/06-permissions-device-capabilities-and-privacy.md) | 권한을 잃어도 핵심 작업이 가능한가? | Stage 03 |
| 7 | [background·notification·lifecycle](docs/07-background-work-notifications-and-lifecycle.md) | 실행 시점을 OS가 결정해도 작업이 안전한가? | Stage 05 |
| 8 | [Kotlin·Swift와 native boundary](docs/08-native-boundary-kotlin-swift-and-builds.md) | JavaScript 밖의 설정·코드·오류를 어떻게 읽는가? | Stage 03·06 |
| 9 | [테스트·성능·관측성](docs/09-testing-performance-and-observability.md) | simulator 성공을 실제 품질 증거로 바꾸려면 무엇이 필요한가? | Stage 06 |
| 10 | [release·signing·update·store](docs/10-release-signing-updates-and-store-delivery.md) | 어떤 artifact가 어느 사용자에게 전달되는가? | Stage 06 |
| 90 | [실무 체크리스트](docs/90-practical-checklist.md) | 기존 저장소 합류와 출시 전에 무엇을 확인하는가? | 전체 |

## 누적 실습: Field Notes

현장 조사자가 네트워크가 없는 장소에서도 기록을 남기는 앱을 단계적으로 완성한다.

```text
Stage 01  기록 목록·상세·편집과 deep link·restart
Stage 02  SQLite local record, file ownership와 outbox
Stage 03  camera·picker·선택적 위치와 permission degradation
Stage 04  idempotent command, UNKNOWN 결과·순서 역전·conflict
Stage 05  opportunistic background sync와 notification cold start
Stage 06  native boundary, Android·iOS 품질 matrix와 release evidence
```

[`exercises/field-notes`](exercises/field-notes/README.md)는 의도적으로 미완성인 skeleton, 공개 행동 계약, 대표 실패와 reference를 제공한다. 순수 동기화 전이는 [`examples/sync-model`](examples/sync-model/README.md)에서 관찰한다. 단계 결과를 단순히 크게 반복하지 않고 여러 실패를 한 release candidate에 결합하는 종료 과제는 [capstone](capstone/README.md)이다.

누적 reference의 정확한 자동 검증 범위는 현재 root/reference package scripts, [Field Notes의 상태 설명](exercises/field-notes/README.md#누적-reference와-단계별-시작-상태)과 해당 source에서 실행한 `verify.sh` 결과로 확인한다. package·test·문서가 존재한다는 사실을 해당 Stage의 실제 device·release 완료나 자동 `stable` 근거로 해석하지 않는다.

## 시작과 검증

```sh
./prepare.sh
./verify.sh
```

`prepare.sh`는 지원 도구와 lockfile dependency를 재현하고, `verify.sh`는 reference 통과와 의도적으로 미완성인 skeleton·known-wrong behavior의 거부를 포함한 자동 근거를 모은다. 실제 Android/iOS binary, permission dialog, background scheduler, screen reader, signing 또는 store 심사를 실행하지 못했다면 성공으로 바꾸지 않는다. 수동 evidence와 검토 질문은 capstone 양식을 따른다.

## 가이드 이후

완료 뒤에는 튜토리얼 앱을 하나 더 복제하지 말고 다음 프로젝트로 이동한다.

```text
기존 Expo/React Native 저장소 실행
→ 한 화면의 route·data·native dependency 복원
→ 실제 기기에서 작은 실패 재현
→ 수정과 회귀 검사
→ preview build 공유
→ Android·iOS 차이와 미검사 범위를 포함한 PR
```

모바일 backend 공개 운영이 업무가 되면 `web-infra`와 해당 backend 정본으로 이동한다. Kotlin/Compose 또는 Swift/SwiftUI 자체가 주 업무가 되면 이 브랜치의 native boundary evidence를 출발점으로 외부 전문 경로를 선택한다. 현재 catalog에는 별도의 네이티브 전문 브랜치가 등록돼 있지 않다.

`mobile-app`에 등록된 필수 후속 브랜치(`continues_to`)는 없다. 따라서 완료 뒤 기본 경로는 브랜치 개수를 늘리는 일이 아니라 위 실제 프로젝트에서 작은 변경을 끝내는 것이다.
