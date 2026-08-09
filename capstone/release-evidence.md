# Release evidence

## release candidate identity

```text
release name:
source revision / clean-dirty state:
lockfile digest:
Node / npm:
Expo SDK / React Native / React:
app version:
Android versionCode:
iOS buildNumber:
runtimeVersion / update channel:
build profile / environment name:
DB schema version:
```

secret 값과 credential file은 첨부하지 않는다.

## build·publishing·install artifact

| platform | application id | 구분 | artifact/store identity | digest | signing의 비밀 아닌 식별자 | build/install evidence |
|---|---|---|---|---|---|---|
| Android | | publishing AAB | | | | |
| Android | | installable APK/split APK | | | | |
| iOS | | archive | | | | |
| iOS | | provisioned app/IPA/TestFlight build | | | | |

AAB는 직접 설치 artifact가 아니고 iOS archive도 임의 device 설치 증거가 아니다. source build digest는 store가 처리·재서명해 전달한 bytes를 자동으로 증명하지 않는다. store build/track과 실제 device install evidence를 별도 연결한다.

## generated native configuration

- CNG source와 clean generation command:
- Android merged manifest/application id/SDK/permission evidence:
- iOS built plist/entitlement/bundle id/minimum OS evidence:
- native dependency fingerprint와 boundary review:
- deep/app/universal link config:
- notification channel/background config:
- runtimeVersion/fingerprint 결정 근거:

## automated verification

| suite | exact command | result | evidence | 보장하지 않는 것 |
|---|---|---|---|---|
| type/lint | | | | |
| domain/public contracts | | | | |
| repository/migration | | | | |
| sync fault history/mutants | | | | |
| component/integration | | | | |
| JS bundle/CNG | | | | |
| dependency/license | | | | |

실행하지 않은 필수 suite를 성공으로 합산하지 않는다.

## device·journey verification

- [device matrix](device-test-matrix.md) release candidate 요약:
- capstone failure journey timeline/log bundle:
- Android 실제 기기 evidence:
- iOS 실제 기기 evidence:
- `not-run`과 exit capability 제한:

## data inventory

| 데이터 | 목적/trigger | local owner | remote 전송 | retention/delete | 사용자 control | telemetry 포함 |
|---|---|---|---|---|---|---|
| record text | | | | | | |
| photo | | | | | | |
| foreground location | | | | | | |
| credential | | | | | | |
| notification token | | | | | | |
| redacted diagnostic | | | | | | |

## signing·store·rollout

- credential owner/recovery/rotation:
- store listing/identifier/track:
- privacy/data-safety·permission 설명:
- review account/steps와 screenshot 일치:
- rollout stages, owner와 monitoring window:
- crash/migration/auth/sync/privacy stop threshold:
- remote update rollback vs binary forward-fix:

실행하지 않았다면 각 항목을 `not-run`으로 표시하고 필요한 계정·권한·증거를 적는다. local config 검사나 artifact 생성으로 store review·공개 rollout을 완료했다고 표현하지 않는다.

## known limits와 사람 승인

| 역할 | 검토 질문/범위 | pass/fail/not-run | 근거 | 잔여 위험 |
|---|---|---|---|---|
| 개발 | owner/invariant/fault history | | | |
| 제품·접근성 | 양 플랫폼 사용자 결과 | | | |
| privacy/security | data inventory/redaction | | | |
| release owner | artifact/signing/store/rollback | | | |

최종 판단은 **사람의 stable 검토 준비 완료 / 보정 필요 / 차단됨** 중 하나다. 자동 script가 `stable`을 쓰지 않는다.
