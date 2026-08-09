# Field Notes release evidence contract

Stage 06과 capstone의 build·install·signing·store 증거를 서로 다른 상태로 보존하는 dependency-free runtime validator다. JSON key 존재만 검사하지 않고, 같은 source/build 후보 안에서 artifact 역할과 관찰 evidence가 서로 맞는지 검사한다.

이 package가 반환하는 `consistent`는 **입력한 evidence끼리 모순되지 않는다**는 뜻이다. 명령이 native build, signature trust, 실제 device 또는 store를 직접 검사했다는 뜻이 아니다.

## 실행

```sh
fnm exec --using=24.19.0 npm --prefix exercises/field-notes/release-contract run typecheck
fnm exec --using=24.19.0 npm --prefix exercises/field-notes/release-contract test
fnm exec --using=24.19.0 npm --prefix exercises/field-notes/release-contract run validate:fixtures
```

fixture 값은 schema version 2의 정상·거부 행동만 확인하는 합성 데이터다. 파일명과 digest 모양이 맞아도 실제 artifact, 서명, 설치 또는 store evidence가 아니다.

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
