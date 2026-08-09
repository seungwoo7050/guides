# Device test matrix

`pass`, `fail`, `not-run`, `not-applicable`만 사용한다. `not-run`을 빈칸이나 성공으로 바꾸지 않고 필요한 host/device/account와 exit capability 영향을 적는다.

## 위험 기반 환경

| ID | kind | platform/device | OS | screen/memory | app/build/runtime | source revision | 선택 이유 |
|---|---|---|---|---|---|---|---|
| A-min | emulator/device | Android | | | | | |
| A-main | emulator/device | Android | | | | | |
| I-min | simulator/device | iOS | | | | | |
| I-main | simulator/device | iOS | | | | | |

네 대의 물리 기기가 필수라는 뜻은 아니다. 다만 실제 기기에서만 관찰할 수 있는 camera, notification/background, 보조기술, 성능·install 항목을 양 플랫폼에서 수행하지 못했다면 그 한계를 남긴다.

## install·upgrade·identity

| 사례 | Android 결과/evidence | iOS 결과/evidence | 비보장·차이 |
|---|---|---|---|
| fresh install/cold launch | | | |
| previous schema+unsynced outbox upgrade | | | |
| process kill/restart | | | |
| delete/reinstall와 secure credential | | | |
| publishing artifact vs actual install | | | |

## lifecycle·navigation

| 사례 | Android | iOS | 최종 route/DB·근거 |
|---|---|---|---|
| malformed/stale deep link cold start | | | |
| duplicate notification cold start | | | |
| warm intent while editing | | | |
| system back/back gesture | | | |
| picker 중 process recreation | | | |
| screen lock/recent 제거/force-stop 구분 | | | |

## permission·device·background

| 사례 | Android | iOS | 대체 행동·근거 |
|---|---|---|---|
| system picker cancel/result | | | |
| camera deny→grant→revoke | | | |
| location deny/timeout/low accuracy | | | |
| notification channel/permission/token | | | |
| background 미실행·중단·중복 | | | |
| foreground resume 수렴 | | | |

## offline·sync

| 사례 | Android | iOS | final DB/outbox/UI·근거 |
|---|---|---|---|
| offline create/edit/delete | | | |
| response loss/same command retry | | | |
| active sync+new edit+late success | | | |
| malformed/version regression | | | |
| conflict와 새 resolution command | | | |
| auth block/permanent failure | | | |

## 접근성·layout

| 흐름 | TalkBack | VoiceOver | 큰 글자/keyboard/작은 화면 | evidence/사람 판단 |
|---|---|---|---|---|
| 목록·heading·sync state | | | | |
| form label·validation·draft | | | | |
| permission 대체 | | | | |
| conflict 비교·해결 | | | | |
| modal/route focus 복귀 | | | | |

자동 accessibility tree 결과는 실제 보조기술 흐름을 대신하지 않는다. 수행자는 “상태 변화가 중복 announcement를 만들지 않는가?”, “오류 뒤 focus와 draft가 보존되는가?”, “색·gesture 없이 같은 action이 가능한가?”에 답한다.

## release-like 성능

| 사용자 작업 | device/build | 반복·도구 | 예산 | 실제 결과 | profile/known limit |
|---|---|---|---|---|---|
| cold start→의미 있는 목록 | | | | | |
| 1,000 record scroll | | | | | |
| 20 thumbnail scroll | | | | | |
| edit local commit | | | | | |
| outbox 100개 중 interaction | | | | | |

## 미검사 항목

| 항목 | 이유/필요 조건 | 대체 evidence | 대체가 보장하지 않는 것 | exit capability 영향 |
|---|---|---|---|---|
| | | | | |
