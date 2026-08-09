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
runtime fingerprint 또는 policy ref:
build profile / environment name:
DB schema version:
```

secret 값과 credential file은 첨부하지 않는다.

## machine-checkable release manifest

[`release-contract`](../exercises/field-notes/release-contract/README.md)의 schema version 2로 `artifact-manifest.json`을 제출한다. 한 manifest의 `source`·`application`·`build`는 같은 release candidate를 식별하고 `artifacts[]`의 `ref`는 중복되지 않아야 한다.

| artifact ref | platform | kind/역할 | local file 또는 store build identity | digest | source/build 연결 | evidence |
|---|---|---|---|---|---|---|
| | Android | `android-aab` / publishing | | | | |
| | Android | `android-apk` 또는 `android-play-split-set` / install candidate | | | | |
| | iOS | `ios-xcarchive` / archive | | | | |
| | iOS | `ios-ipa` 또는 `ios-testflight-build` / install candidate | | | | |

Android 후보는 AAB와 APK/Play split을, iOS 후보는 xcarchive와 IPA/TestFlight build를 별도 ref로 가진다. AAB는 직접 설치 artifact가 아니고 xcarchive도 임의 device 설치 증거가 아니다. 같은 상위 source/build identity를 공유한다는 사실과 각 artifact bytes/store identity를 모두 남긴다.

### artifact-linked signing

| artifactRef | 상태 (`not-run`/`claimed`/`manually-reviewed`) | redacted signing identity | 관찰 방법·시각·evidence | reviewer/date/review evidence | 알려진 한계 |
|---|---|---|---|---|---|
| | | | | | |

모든 artifact에 상태를 하나씩 둔다. `claimed`는 제출자 관찰이고 `manually-reviewed`는 그 claim에 사람 검토 기록을 연결한 상태다. 어느 상태도 signature trust chain, credential 소유권·보관 또는 store accept를 자동 증명하지 않는다. secret과 credential file은 첨부하지 않는다.

### artifact-linked installation

| platform | artifactRef | device class·redacted identity | installed app id/version/build | observed runtimeVersion | observed runtime fingerprint/policy | launch result | evidence |
|---|---|---|---|---|---|---|---|
| Android | | physical / emulator / 미검사 | | | | | |
| iOS | | physical / simulator / 미검사 | | | | | |

실제 기기 exit evidence는 `physical`만 인정한다. Android APK의 emulator와 iOS simulator `.app`의 simulator 결과는 별도 대체 환경 증거다. IPA/TestFlight를 simulator에, simulator `.app`을 physical device에 설치했다고 기록하지 않는다. `verified` installation은 build 후보와 같은 app id/version/build/runtime/fingerprint-or-policy와 `launchResult=passed`를 요구한다.

### store identity와 전달 bytes 관찰

| platform | publishingArtifactRef | storeBuildRef | track/status | delivered bytes 상태 | delivered artifactRef/digest | reviewer/evidence·한계 |
|---|---|---|---|---|---|---|
| Android | | | | `not-run` / `declared` / `manually-reviewed` | | |
| iOS | | | | `not-run` / `declared` / `manually-reviewed` | | |

Android의 publishing ref는 AAB, iOS의 upload ref는 IPA를 가리킨다. Play split/TestFlight install evidence는 store build identity와 연결한다. source AAB/archive/IPA digest는 store가 처리·재서명·split/thinning 뒤 전달한 bytes를 자동 증명하지 않는다. `declared`는 관찰자의 선언이고 `manually-reviewed`는 그 선언의 사람 검토 상태일 뿐이며 자동 `verified`로 합산하지 않는다.

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
- artifact별 signing claim/manual review와 비보장 범위:
- store listing/identifier/track:
- publishing artifact ref/store build ref/delivered bytes observation:
- privacy/data-safety·permission 설명:
- review account/steps와 screenshot 일치:
- rollout stages, owner와 monitoring window:
- crash/migration/auth/sync/privacy stop threshold:
- remote update rollback vs binary forward-fix:

실행하지 않았다면 각 항목을 `not-run`으로 표시하고 필요한 계정·권한·증거를 적는다. local config 검사, artifact 생성 또는 release-contract schema 통과로 signing trust, store review·delivered bytes·공개 rollout을 완료했다고 표현하지 않는다.

## known limits와 사람 승인

| 역할 | 검토 질문/범위 | pass/fail/not-run | 근거 | 잔여 위험 |
|---|---|---|---|---|
| 개발 | owner/invariant/fault history | | | |
| 제품·접근성 | 양 플랫폼 사용자 결과 | | | |
| privacy/security | data inventory/redaction | | | |
| release owner | artifact/signing/store/rollback | | | |

최종 판단은 **사람의 stable 검토 준비 완료 / 보정 필요 / 차단됨** 중 하나다. 자동 script가 `stable`을 쓰지 않는다.
