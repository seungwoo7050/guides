# 플랫폼 경계 지도

이 표는 Android와 iOS 차이를 하나의 boolean이나 raw enum으로 숨기기 위한 것이 아니다. 운영체제가 소유하는 사건·자원, 앱이 소유하는 업무 의미와 native adapter가 번역해야 할 결과를 빠르게 복원하기 위한 지도다.

## 먼저 실제 소유자를 구분합니다

```text
OS
process·Activity/scene·permission·system UI·scheduler·notification delivery

설치된 native binary
manifest/plist/entitlement·native dependency·app identifier·signing된 capability

application
startup readiness·navigation intent·fallback·업무 state transition

repository
record·draft checkpoint·outbox·attachment metadata·reconciliation marker

remote system
account authorization·server version·push registration 처리·remote policy
```

OS 사건의 정확한 시점과 횟수는 앱이 소유하지 않는다. 앱이 소유하는 불변식은 중단·중복·순서 역전 뒤에도 committed data와 사용자 의도를 설명할 수 있고, raw platform 결과를 같은 업무 의미로 수렴시키는 것이다.

## 공통 contract와 platform adapter

| 문제 | 실제 상태·사건 소유자 | 공통 application contract | Android adapter가 확인할 것 | iOS adapter가 확인할 것 |
|---|---|---|---|---|
| process·app state | OS | active/background 신호, restart reconciliation | Activity·process recreation, focus/blur, recent/force-stop 차이 | active/inactive/background, scene, 사용자 app-switcher 종료 |
| startup intent | OS source + application coordinator | raw source → normalized intent → readiness → route/fallback | launcher/new intent, Activity recreation, initial link/notification | cold/warm URL·notification response, scene/application entry |
| restoration | router/repository + OS 후보 | versioned route/entity id를 현재 data/session으로 재검증 | saved state·재생성 payload의 freshness | restoration 후보와 current scene/session의 일치 |
| back | OS gesture + router | discard/save/navigation decision | system back·gesture·Activity navigation | navigation gesture·modal dismiss·interactive transition |
| layout | OS window | constraint 변화가 draft·selection을 바꾸지 않음 | insets, edge-to-edge, navigation mode, split/fold | safe area, scene/window size, size class |
| keyboard·focus | OS input + screen | action/error 접근과 실패 뒤 draft 보존 | resize/pan, software/hardware keyboard, TalkBack focus | keyboard avoidance, VoiceOver focus, modal 복귀 |
| photo picker | system picker | selected/cancelled/error + durable-copy reconciliation | provider URI, Activity/process recreation, pending-result API | selected asset, iCloud-backed result, 임시 file 수명 |
| camera | OS/device | capture/cancel/error + interruption | camera hardware/Activity/device 차이 | camera permission/session/interruption |
| location | OS service | coordinate + accuracy + time 또는 explicit failure | precise/approximate, service availability | reduced/full accuracy, authorization status |
| permission | OS + 사용자 | not-determined/granted/limited/denied/restricted와 fallback | can-ask-again, Settings 변경, capability/build 설정 | limited/provisional 등 capability별 상태와 Settings 변경 |
| notification | OS/provider + application | message → validated intent → current state reconciliation | channel, Android permission, token, tap | permission, category, token, tap |
| background | OS scheduler + app worker | bounded·restartable worker trigger | WorkManager/vendor policy, recent/force-stop 차이 | BGTaskScheduler/system policy, expiration, physical-device 제한 |
| secure storage | platform storage | 작은 credential read/write/recovery 결과 | Keystore-backed encryption, uninstall/backup behavior | Keychain accessibility, reinstall/backup behavior |
| file | platform filesystem + repository | app-owned copy, checksum, row/file reconciliation | files/cache/storage pressure | documents/library/cache, backup·offload 정책 |
| release | build/store systems + release owner | app/build/runtime/source/artifact identity | applicationId, versionCode, keystore, AAB와 install APK 구분 | bundle id, buildNumber, profile, archive/IPA/TestFlight 구분 |

## 추상화 기준

좋은 공통 interface:

- 두 platform에서 같은 업무 의미를 가진다.
- raw platform 상태를 잃지 않고 필요한 차이를 union에 표현한다.
- capability availability와 permission을 섞지 않는다.
- permission·cancel·unavailable·temporary failure를 구분한다.
- thread·lifecycle·cleanup 책임을 가진다.
- 정상뿐 아니라 중단·중복·stale input의 final state가 정해져 있다.
- 실제 기기 contract test와 그 evidence의 한계를 함께 기록한다.

나쁜 공통 interface:

```ts
function doNativeThing(): Promise<any>
```

또는 한쪽 platform의 raw enum, path나 callback 순서를 공통 domain에 그대로 노출하는 방식이다.

## platform-specific code를 허용할 때

- convention이 실제 사용자 경험을 크게 바꿈
- capability가 한 platform에만 있음
- permission·lifecycle 의미가 다름
- 성능 또는 native SDK 요구가 다름
- 공통 abstraction이 더 많은 condition과 bug를 만듦

허용하더라도 상위 업무 결과와 fallback을 같은 문서에 기록한다. platform-specific 성공 경로만 두고 다른 platform을 `unsupported` 문자열 하나로 숨기지 않는다.

## 대표 경계·실패 질문

각 adapter를 검토할 때 다음을 묻는다.

1. 정상 입력에서 어떤 application union을 반환하는가?
2. OS가 callback 없이 process를 종료하면 어떤 durable state가 남는가?
3. 같은 result·tap·task가 두 번 오면 업무 효과가 중복되는가?
4. 늦은 결과가 새 route·draft·permission state를 덮는가?
5. permission이나 capability가 Settings·build·account 변경으로 사라지면 fallback은 무엇인가?
6. JavaScript와 native layer 중 어느 쪽이 thread, cancellation과 cleanup을 소유하는가?
7. 한 platform에만 있는 raw 상태를 공통 의미로 잃지 않고 표현했는가?

## 검증 evidence와 한계

| evidence | 확인할 수 있는 것 | 확인하지 못하는 것 |
|---|---|---|
| pure normalization test | raw result→application union, malformed/stale/duplicate 분기 | 실제 OS raw value와 callback 수명 |
| component/integration test | route·fallback·visible/accessible result | native config, process kill, 실제 보조기술 발화 |
| emulator/simulator | 기본 platform entry·layout·일부 system UI | 실제 camera, scheduler, battery, store-installed binary의 전체 행동 |
| development build 실제 기기 | project native dependency/config, permission, cold/warm process 경계 | production signing·optimization·store 전달 |
| preview/store test track | install·upgrade·signed artifact와 배포 경로 | 모든 OS/vendor/device와 향후 store policy |

한쪽 platform의 evidence를 다른 쪽 결과로 추정하지 않는다. 실제 기기를 사용할 수 없다면 emulator/simulator나 원격 device 결과를 부분 evidence로 남길 수 있지만, camera·background·notification·TalkBack/VoiceOver와 설치 artifact에 대해 무엇을 검증하지 못했는지 명시한다.

## 인접 브랜치에 맡기는 범위

- React·URL·HTTP 애플리케이션 기초: [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app)
- React 상태·접근성·성능 심화: [`web-front-react-nextjs`](https://github.com/seungwoo7050/guides/tree/web-front-react-nextjs)
- DNS·TCP·TLS 경로 분석: [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks)
- 일반 위협 모델·credential 공격과 방어: [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity)
- 공개 backend·DNS·TLS·배포 운영: [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra)

이 브랜치는 Kotlin·Swift 언어 전체나 native Android/iOS framework 전문 과정을 다시 만들지 않는다. 필요한 native source와 configuration을 읽어 JavaScript·native·OS 실패 경계를 좁히는 수준을 소유한다.
