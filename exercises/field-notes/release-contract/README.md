# Field Notes release evidence contract

Stage 06과 capstone의 build·install·signing·store 증거를 서로 다른 상태로 보존하는 dependency-free runtime validator다. JSON key가 있다는 사실만 검사하지 않고 다음 잘못된 완료 주장을 거부한다.

- AAB를 Android 기기에 직접 설치했다고 기록함
- xcarchive를 iOS 설치 artifact로 기록함
- installed application ID/version/build가 build identity와 다름
- Android와 iOS 증거가 서로 다른 source/lock 상태를 가리킴
- 실행하지 않은 signing·install·store 검토에 이유와 필요한 증거가 없음
- 빈/잘못된 artifact digest를 provenance처럼 사용함

## 실행

```sh
fnm exec --using=24.19.0 npm --prefix exercises/field-notes/release-contract run typecheck
fnm exec --using=24.19.0 npm --prefix exercises/field-notes/release-contract test
fnm exec --using=24.19.0 npm --prefix exercises/field-notes/release-contract run validate:fixtures
```

fixture 값은 validator의 정상·거부 행동만 확인하는 합성 데이터다. 파일명에 AAB/IPA가 있고 digest 모양이 맞아도 실제 artifact가 아니다.

## artifact 역할

| 종류 | 이 contract의 역할 | 직접 설치 증거 |
|---|---|---|
| `android-aab` | Google Play publishing format | 불가; 같은 source의 APK 또는 Play-generated split 설치가 별도 필요 |
| `android-apk` | Android installable package | device/emulator에서 application identity를 관측해야 함 |
| `ios-xcarchive` | Xcode archive | 불가; export/provisioning 뒤 IPA 또는 app이 별도 필요 |
| `ios-ipa` | provisioning 조건이 있는 iOS distribution artifact | 허가된 실제 기기/TestFlight build evidence가 필요 |
| `ios-simulator-app` | simulator-only app | 실제 iOS 기기 evidence가 아님 |

local artifact의 SHA-256은 그 파일의 bytes만 식별한다. store upload·processing·재서명·split 생성 뒤 사용자에게 전달된 bytes까지 증명하지 않는다. `storeDeliveredBytesVerified`는 별도의 store delivery digest가 있을 때만 참이다.

## 자동 검사가 보장하지 않는 것

validator는 입력 JSON의 schema와 내부 일관성만 확인한다. 다음을 실행하거나 증명하지 않는다.

- Android/iOS native compile
- credential 소유권 또는 signature trust
- device install·upgrade·launch
- permission·background·notification behavior
- store upload·review·rollout·rollback
- evidence 문서가 조작되지 않았다는 사실
- 교육적 완성 또는 `stable` 승인

실제 결과는 [capstone release evidence](../../../capstone/release-evidence.md)에 redacted raw log·device matrix·artifact metadata와 함께 제출하고 사람이 검토한다.
