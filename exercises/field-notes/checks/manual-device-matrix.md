# Manual device matrix

실제 Android/iOS 행동, 접근성, lifecycle과 install/upgrade를 기록한다. emulator/simulator도 별도 environment로 유용하지만 실제 기기 행을 대신 채우지 않는다.

## 결과 규칙

```text
통과
실패
미검사 — 실행하지 않았으며 이유와 필요한 evidence를 적음
비적용 — 제품 범위 근거와 reviewer를 적음
```

한 platform 결과를 다른 platform에 복사하지 않는다. 자동 contract 통과를 device `통과`로 변환하지 않는다.

## 환경

| ID | Platform | 실제 기기/대체 환경 | Device·model | OS·vendor | App id/version/build | Runtime/update·fingerprint/policy | Profile·installed artifactRef/digest | 수행자/date |
|---|---|---|---|---|---|---|---|---|
| A1 | Android | 미검사 |  |  |  |  |  |  |
| I1 | iOS | 미검사 |  |  |  |  |  |  |

실제 기기가 없으면 `A-EMU`, `I-SIM` 같은 별도 행을 추가하고 “대체 환경”으로 표시한다. A1/I1을 simulator 결과로 채우지 않는다.

## 공통 핵심 흐름

| 흐름 | A1 | I1 | 필요한 관측·증거/차이 |
|---|---|---|---|
| fresh install·cold start | 미검사 | 미검사 | install 명령/경로, artifact identity, 첫 route |
| malformed/stale deep link cold start | 미검사 | 미검사 | crash/private route 없음, fallback |
| offline record create·restart | 미검사 | 미검사 | DB/outbox snapshot, pending UI |
| local commit 직후 process kill | 미검사 | 미검사 | committed record/command 복원 |
| 이전 version/schema upgrade | 미검사 | 미검사 | fixture identity, migration, data/outbox/file |
| photo picker cancel/success·process 왕복 | 미검사 | 미검사 | draft, owned file, pending result |
| direct camera deny/grant/cancel | 미검사 | 미검사 | picker와 다른 permission/capability 경로 |
| location deny/timeout/success | 미검사 | 미검사 | optional degradation, accuracy/time |
| network 복구와 response loss retry | 미검사 | 미검사 | same command snapshot, apply count 1 |
| version conflict 비교·해결 | 미검사 | 미검사 | local/remote 보존, 새 command |
| app background/active sync | 미검사 | 미검사 | 같은 worker/lease와 final state |
| background task 미실행 뒤 foreground | 미검사 | 미검사 | pending 유지와 app-active 재개 |
| notification foreground | 미검사 | 미검사 | in-app 상태와 중복 announcement 여부 |
| notification background tap | 미검사 | 미검사 | current repository 기반 route |
| notification cold-start tap | 미검사 | 미검사 | migration/session 뒤 route/fallback |
| duplicate/stale notification | 미검사 | 미검사 | 추가 effect 없음, resolved state 재생성 금지 |
| permission revoke 후 foreground | 미검사 | 미검사 | stale granted 사용 금지, 대체 action |
| account logout 뒤 이전 notification | 미검사 | 미검사 | 이전 user route/data 노출 없음 |

## Android 고유 확인

| 검사 | A1 | 필요한 관측·증거 |
|---|---|---|
| Android 13+ channel 생성 | 미검사 | channel id/importance와 생성 시점 |
| channel→permission→token 순서 | 미검사 | API/event trace; denied에서 token mapping 없음 |
| notification permission deny/grant/revoke | 미검사 | OS dialog/Settings와 app normalized state |
| system back·gesture와 unsaved draft | 미검사 | confirm/focus/draft 결과 |
| recent 제거와 process recreation | 미검사 | 실제 관찰과 next startup state |
| force-stop 뒤 task/notification | 미검사 | force-stop을 일반 background와 구분 |
| vendor battery restriction | 미검사 | device 설정/정책과 관찰; 다른 vendor 일반화 금지 |
| APK/Play split install·upgrade | 미검사 | physical install artifactRef/digest 또는 storeBuildRef, applicationId/versionCode/runtime, launch |
| AAB와 store/install 경계 | 미검사 | publishing AAB ref와 APK/Play split ref를 분리하고 AAB를 install 성공으로 표시하지 않음 |

## iOS 고유 확인

| 검사 | I1 | 필요한 관측·증거 |
|---|---|---|
| notification permission deny/grant/revoke | 미검사 | OS dialog/Settings와 app normalized state |
| notification cold/warm response | 미검사 | response identity와 route decision |
| app/scene background·사용자 종료 | 미검사 | task/process 관찰과 next startup state |
| picker/camera scene 왕복 | 미검사 | result/cancel과 draft/file state |
| interactive back/modal dismiss | 미검사 | confirm/focus/draft 결과 |
| xcarchive와 IPA/TestFlight install·upgrade | 미검사 | archive ref와 physical install artifactRef/storeBuildRef, bundle id/buildNumber/runtime, launch; simulator `.app` 대체 금지 |
| remote update/runtime compatibility | 미검사 | effective runtimeVersion과 binary/update identity |

full Xcode, signing identity 또는 실제 iPhone이 없으면 iOS CNG·bundle 결과를 이 표의 device 통과로 쓰지 않는다. 각 행은 `미검사`로 유지하고 필요한 host/device/account를 적는다.

## 접근성

| 검사 | A1 TalkBack | I1 VoiceOver | 증거/차이 |
|---|---|---|---|
| 목록 탐색·heading·상태 | 미검사 | 미검사 | 발화 순서와 state 의미 |
| form label·error·focus | 미검사 | 미검사 | 오류 수정과 draft 보존 |
| camera/location 거절 대체 경로 | 미검사 | 미검사 | 핵심 record action 도달 |
| sync pending/auth/conflict announcement | 미검사 | 미검사 | 중복/누락과 다음 action |
| conflict 비교·선택 | 미검사 | 미검사 | local/remote 구분과 focus |
| modal 닫기 focus 복귀 | 미검사 | 미검사 | 연 control 또는 합리적 목적지 |
| notification 진입 뒤 현재 화면 | 미검사 | 미검사 | route title/state announcement |

자동 accessibility prop 검사는 이 행을 채우지 않는다. 실제 발화, focus, gesture 대체 경로를 사람이 검토한다.

## layout·입력

| 검사 | A1 | I1 | 증거/차이 |
|---|---|---|---|
| 큰 font scale | 미검사 | 미검사 | text/action 잘림·겹침 없음 |
| 작은/좁은 화면 | 미검사 | 미검사 | 핵심 action과 state 도달 |
| keyboard가 save/error를 가리지 않음 | 미검사 | 미검사 | focus·scroll·draft 결과 |
| landscape/split 또는 비지원 정책 | 미검사 | 미검사 | 회전 뒤 record/draft 보존 |
| color 이외 sync/error 표현 | 미검사 | 미검사 | text/icon/accessibility state |

## release-like 성능·resource

| 검사 | A1 | I1 | 측정 조건·결과/한계 |
|---|---|---|---|
| cold/warm launch | 미검사 | 미검사 | sample count, thermal/power/network |
| 1,000 records scroll | 미검사 | 미검사 | frame/interaction 관찰 |
| 20 thumbnails | 미검사 | 미검사 | memory/image behavior |
| edit save transaction | 미검사 | 미검사 | duration과 UI response |
| 100-command sync 중 interaction | 미검사 | 미검사 | worker budget과 responsiveness |
| background/active transition | 미검사 | 미검사 | battery/task trace 한계 |

development mode 또는 simulator 결과를 release-like 실제 device 수치로 바꾸지 않는다.

## lifecycle 차이 기록

각 platform에서 다음을 사건별로 기록한다.

```text
screen lock/unlock
home/background/active
recent 목록 제거 또는 사용자 종료
Android force-stop
device reboot
OS가 process를 종료한 관찰
```

각 사건에서 callback 수신 여부, process identity, DB/outbox/lease, pending notification, next startup route를 남긴다. 한 OS/version/device의 관찰을 모든 platform/vendor 행동으로 일반화하지 않는다.

## 사람 검토 질문

- 현재 상태와 다음 action을 화면과 보조기술 모두에서 이해할 수 있는가?
- background/notification이 실행·delivery 보장처럼 표현되지 않는가?
- permission 거절·철회와 offline/auth/conflict에서 핵심 local record를 잃지 않는가?
- 실제 설치한 artifact의 source/build/runtime identity를 재현할 수 있는가?
- `미검사` 항목과 필요한 device/account/tool이 숨겨져 있지 않은가?
- simulator/fake/자동 검사가 보장하지 못한 범위를 결과 옆에 적었는가?

각 통과/실패는 [`evidence-template.md`](evidence-template.md)로 연결한다.
