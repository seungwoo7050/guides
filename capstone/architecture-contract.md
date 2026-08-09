# Architecture contract

실제 프로젝트 값과 source link로 채운다.

## 1. 제품·비범위

- 사용자 문제:
- 핵심 작업:
- 이 release candidate가 의도적으로 하지 않는 것:
- backend/native 전문/조직 운영으로 넘기는 범위:

## 2. runtime과 source of truth

```text
JavaScript/React:
Native Android:
Native iOS:
OS services:
Test backend:
```

- native workflow: `[ ] CNG/generated` `[ ] android/ios 직접 소유`
- 정본 config와 clean generation 명령:
- generated directory의 commit 정책:
- development-build-first 경로와 Expo Go 비보장:

## 3. 상태 소유권

| 상태·자원 | 정본 owner | 변경 사건·입력 | restart 복원 | 불변식 | 삭제/retention |
|---|---|---|---|---|---|
| route/pending intent | | | | | |
| draft/record | | | | | |
| attachment bytes/metadata | | | | | |
| outbox/conflict | | | | | |
| credential | | | | | |
| capability/permission | | | | | |
| background attempt | | | | | |
| notification intent | | | | | |

## 4. dependency 방향

```text
route/screen
→ application use case/coordinator
→ domain model
→ repository/capability ports
→ SQLite/File/HTTP/Native adapters
```

실제 module map과 예외:

## 5. startup/navigation state machine

```text
raw launch/link/notification/restoration input
→ schema·freshness 검증
→ DB migration·file reconciliation
→ session/capability readiness
→ latest repository 조회
→ route 적용 또는 deterministic fallback
```

| source | normalized intent | duplicate/stale 기준 | readiness | fallback |
|---|---|---|---|---|
| internal | | | | |
| deep link | | | | |
| notification | | | | |
| restoration | | | | |

## 6. capability contract

| 기능 | availability owner | permission states | native config | 거절/부재 대체 | device evidence |
|---|---|---|---|---|---|
| photo picker | | | | | |
| camera | | | | | |
| foreground location | | | | | |
| notification | | | | | |
| background task | | | | | |

## 7. 필수 native-boundary review

custom module 작성이 아니라 실제 사용하는 dependency 하나를 읽는다.

| 경계 | 실제 source/config | owner·thread/lifecycle | 대표 정상 결과 | 대표 실패 | evidence/비보장 |
|---|---|---|---|---|---|
| TypeScript call/parse | | | | | |
| package/autolinking/plugin | | | | | |
| Android Kotlin/Java/config | | | | | |
| iOS Swift/Obj-C/config | | | | | |
| binary/runtime mismatch | | | | | |

양 플랫폼 application meaning 또는 fallback 비교:

## 8. 관측성과 privacy

- 수집 context:
- 제외할 record/photo/location/credential:
- crash, handled domain error, expected offline/cancel 구분:
- evidence redaction 검토자:

## 9. 검증과 잔여 위험

| 주장 | 자동·수동 검증 | 그 검증이 보장하는 것 | 보장하지 않는 것 |
|---|---|---|---|
| Android/iOS 동작 | | | |
| offline·기기 실패 처리 | | | |
| build·artifact 검증 | | | |

지원하지 않거나 `not-run`인 OS/device/capability와 사용자 영향:
