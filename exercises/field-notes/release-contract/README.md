# Field Notes release evidence contract

Stage 06과 capstone의 build·install·signing·store 증거를 서로 다른 상태로 보존하는 dependency-free runtime validator다. JSON key 존재만 검사하지 않고, 같은 source/build 후보 안에서 artifact 역할과 관찰 evidence가 서로 맞는지 검사한다.

이 package가 반환하는 `consistent`는 **입력한 evidence끼리 모순되지 않는다**는 뜻이다. 명령이 native build, signature trust, 실제 device 또는 store를 직접 검사했다는 뜻이 아니다.

같은 package의 EAS profile validator는 [`../reference/eas.json`](../reference/eas.json)을 `unknown`에서 읽어 profile 상속과 공개 설정 불변식을 검사한다. `configurationValid=true`도 설정 모양만 맞는다는 뜻이다. 결과의 `guarantees`는 native build, artifact bytes, signing, install/launch, store, EAS Update와 stable 승인을 모두 `false`로 유지한다.

## 실행

```sh
fnm exec --using=24.19.0 npm --prefix exercises/field-notes/release-contract run typecheck
fnm exec --using=24.19.0 npm --prefix exercises/field-notes/release-contract test
fnm exec --using=24.19.0 npm --prefix exercises/field-notes/release-contract run validate:fixtures
fnm exec --using=24.19.0 npm --prefix exercises/field-notes/release-contract run validate:eas-profile
```

fixture 값은 schema version 2의 정상·거부 행동만 확인하는 합성 데이터다. 파일명과 digest 모양이 맞아도 실제 artifact, 서명, 설치 또는 store evidence가 아니다.

## EAS build profile 계약

`reference/eas.json`은 공통 `base`에서 Node `24.19.0`을 상속하고 공개 profile을 정확히 세 개만 둔다.

| profile | development client | distribution | Android 결과 계약 |
|---|---:|---|---|
| `development` | `true` | `internal` | development client/internal 설정이 만드는 설치용 APK |
| `preview` | `false` 기본 | `internal` | 명시적 `android.buildType=apk` |
| `production` | `false` 기본 | `store` 기본 | 명시적 APK override가 없는 EAS 기본 AAB |

EAS 공식 문서상 development build는 developer tool을 포함하고 store 제출 대상이 아니다. Internal/preview build는 직접 설치 가능한 Android APK에 적합하고, production의 기본 Android 형식은 Play용 AAB다. AAB는 device에 직접 설치하는 파일이 아니다. 따라서 profile 이름이나 성공한 configuration validation만으로 세 artifact 역할을 서로 바꾸지 않는다.

각 공개 profile의 `env`에는 비민감 `FIELD_NOTES_BUILD_PROFILE` label 하나만 둔다. secret/token/credential/API URL 이름, URL 또는 credential 모양의 값과 platform별 env override는 validator가 거부한다. 실제 secret이 나중에 필요하면 committed `eas.json`이 아니라 EAS environment의 적절한 visibility와 사람 검토를 사용해야 한다. client bundle에 들어가는 값은 secret이 될 수 없다.

validator는 다음을 함께 거부한다.

- `base` 이외의 추가 profile 또는 세 공개 profile 누락
- 알 수 없는 `extends`, 순환 상속과 EAS 한도를 넘는 상속 깊이
- root/Android/iOS에서 Node `24.19.0` pin을 덮어쓰는 profile
- development client/store, preview development client/non-APK, production internal/APK 조합
- `cli.requireCommit=true` 또는 `cli.appVersionSource=local` 누락
- `channel`을 build 성공이나 remote update 준비처럼 선언하는 설정

`fixtures/eas-known-wrong.json`은 위 허위 양성을 한 파일에 모은 합성 거부 fixture다. 이 파일은 EAS CLI에 전달할 profile 예시가 아니다.

### local version source를 선택한 이유와 대가

이 교육 reference는 `cli.appVersionSource=local`과 `cli.requireCommit=true`를 사용한다. version/build number의 정본을 reviewed repository source에 두어 release evidence의 commit과 사람이 비교할 수 있게 하려는 선택이다. `requireCommit`은 EAS CLI가 build 준비 시 git index가 깨끗한지 확인하게 한다. 이것만으로 업로드된 source, 실제 artifact 또는 store build가 그 commit과 같다는 사실을 증명하지는 않는다.

Expo는 EAS CLI 12부터 developer-facing build version에는 `remote` source와 production `autoIncrement`를 권장한다. 이는 중복 `versionCode`/`buildNumber`로 인한 store 거부 위험을 줄이고 동시 build 운영에 유리하다. 반대로 local source는 번호를 app config/native source에서 사람이 조정해야 하고, CI 동시성·누락·중복을 자동 해결하지 않는다. 이 branch는 source evidence 학습을 위해 local을 택했으며 production 운영팀이 remote로 전환할 때는 version 정본, sync 절차와 evidence 수집 방식을 별도로 검토해야 한다. validator 통과는 다음 store version이 유일하다는 증거가 아니다.

### EAS Update 비소유 범위

이 단계는 EAS Build profile만 정의한다. `channel`을 두지 않고 EAS Update publish, branch/channel mapping, runtime compatibility, rollout 또는 remote delivery를 구현하거나 검사하지 않는다. build profile 검사가 통과해도 remote update 성공을 주장할 수 없다.

공식 1차 근거:

- [Configure EAS Build with eas.json](https://docs.expo.dev/build/eas-json/)
- [App version management](https://docs.expo.dev/build-reference/app-versions/)
- [Build APKs for Android Emulators and devices](https://docs.expo.dev/build-reference/apk/)
- [Internal distribution](https://docs.expo.dev/build/internal-distribution/)
- [Android build process](https://docs.expo.dev/build-reference/android-builds/)
- [Environment variables in EAS](https://docs.expo.dev/eas/environment-variables/)

## 한 release candidate와 여러 artifact

`artifacts[]`의 각 항목은 고유 `ref`를 가진다. 같은 `ReleaseEvidence` 안의 artifact는 상위의 source revision, lock digest, app identity, version/build/runtime과 build profile을 공유하므로 **같은 source 후보**다. 설치, signing, store evidence는 문자열 설명만 남기지 않고 해당 `artifactRef`를 가리킨다.

| platform | 첫 artifact | 설치 후보 | 완료 집계가 의미하는 것 |
|---|---|---|---|
| Android | publishing AAB | 같은 후보의 APK 또는 Play-generated split set | AAB와 설치 후보가 모두 식별됨 |
| iOS | xcarchive | 같은 후보의 provisioned IPA 또는 TestFlight build | archive와 설치 후보가 모두 식별됨 |

artifact set 완료는 compile, signing, installation 또는 store 완료가 아니다. 예를 들어 AAB와 APK digest를 기록했어도 실제 기기 설치가 `not-run`이면 physical-device evidence는 거짓이다.

## artifact 역할과 설치 device matrix

| 종류 | 역할 | 허용하는 설치 관찰 |
|---|---|---|
| `android-aab` | Google Play publishing format | 직접 설치 불가 |
| `android-apk` | Android installable package | physical Android 또는 emulator |
| `android-play-split-set` | 특정 Play store build가 만든 설치 후보 | physical Android |
| `ios-xcarchive` | Xcode archive | 직접 설치 불가 |
| `ios-ipa` | provisioning 조건이 있는 iOS distribution artifact | physical iOS |
| `ios-testflight-build` | 특정 App Store Connect/TestFlight build | physical iOS |
| `ios-simulator-app` | simulator-only app | iOS simulator |

따라서 simulator `.app`을 physical-device evidence로, IPA를 simulator evidence로, APK를 iOS식 simulator evidence로 기록하면 거부한다. Cross-platform 실제 기기 집계는 양쪽 설치가 모두 `physical`이고, 양쪽 artifact set이 완성됐으며, source/lock identity가 같을 때만 참이다.

## runtime과 launch 관찰

`installation.status=verified`는 다음을 모두 포함한다.

- 설치에 사용한 `artifactRef`
- redacted device class/identity
- 관찰한 application ID, version과 build number
- 관찰한 `runtimeVersion`
- build와 설치 양쪽에 기록한 runtime fingerprint 또는 policy ref
- `launchResult=passed`
- 시각과 raw evidence 참조

관찰 runtime이나 fingerprint/policy가 build 후보와 다르거나 launch가 통과하지 않았다면 verified installation으로 받아들이지 않는다. 이 비교도 제출된 문자열의 일관성 검사다. 앱을 실행하거나 effective runtime을 대신 측정하지 않는다.

## signing claim과 사람 검토

모든 artifact에는 signing 상태를 하나씩 둔다.

- `not-run`: 실행하지 않은 이유와 필요한 evidence
- `claimed`: artifact-linked redacted identity, 관찰 방법·시각·evidence를 제출자가 선언
- `manually-reviewed`: claim에 reviewer, review 시각과 별도 review evidence를 연결

`claimed`를 자동으로 verified로 올리지 않으며, `manually-reviewed`도 signature trust chain, credential 소유권, private key 보호 또는 store accept를 암호학적으로 증명하지 않는다. 이 validator는 그 사람 검토 기록의 schema와 artifact ref만 검사한다. 비밀 key·credential file은 evidence에 넣지 않는다.

## store upload, store build와 전달 bytes

실행한 store evidence는 다음을 분리한다.

- `publishingArtifactRef`: Android AAB 또는 iOS upload IPA
- `storeBuildRef`: Play/App Store Connect의 immutable build identity
- track과 upload/review/release 관찰
- `deliveredBytes`: `not-run`, `declared`, `manually-reviewed` 중 하나

Play split set과 TestFlight build는 `store-build` artifact로 모델링하고 같은 `storeBuildRef`를 가져야 한다. 전달 digest는 store-build artifact를 가리켜야 하므로 local AAB/IPA digest를 그대로 사용자 전달 bytes처럼 재사용하면 거부한다.

`declared`는 제출자의 관찰 선언이고 `manually-reviewed`는 그 선언에 사람 review를 추가한 상태다. 어느 상태도 자동 `storeDeliveredBytesVerified` boolean으로 승격하지 않는다. 특히 Android의 device별 split 집합, store 재서명, encryption/thinning 등은 단일 source artifact SHA-256과 같다고 추정하지 않는다.

## 대표 known-wrong 거부

검사는 다음 허위 양성을 포함해 거부한다.

- AAB 또는 xcarchive를 직접 설치했다고 기록
- simulator `.app`을 physical device에, IPA를 simulator에 설치했다고 기록
- artifact ref 중복·미존재 또는 artifact별 signing 상태 누락
- installed application ID/version/build/runtime/policy 불일치
- launch 실패를 verified installation으로 기록
- APK를 Play publishing artifact로 지정
- local publishing digest를 store-delivered bytes로 지정
- Play/TestFlight artifact와 store build identity가 불일치
- reviewer가 없는 signing/store `manually-reviewed` 상태
- Android와 iOS가 다른 source/lock 상태인데 cross-platform 완료로 집계

## 자동 검사가 보장하지 않는 것

validator는 입력 JSON schema와 내부 일관성만 확인한다. 다음을 실행하거나 증명하지 않는다.

- artifact 경로의 실제 파일 존재, byte size 또는 SHA-256 재계산
- Android/iOS native compile과 generated configuration의 진위
- credential 소유권, signature trust 또는 provisioning 유효성
- device install·cold start·upgrade·permission·background·notification behavior
- store upload·processing·review·전달 bytes·rollout·rollback
- evidence 문서와 reviewer identity가 조작되지 않았다는 사실
- 교육적 완성 또는 `stable` 승인

실제 결과는 [capstone release evidence](../../../capstone/release-evidence.md)에 redacted raw log·device matrix·artifact/store identity와 함께 제출하고 사람이 검토한다.
