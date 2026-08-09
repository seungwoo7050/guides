# 명령 참고

이 문서는 명령어 암기표가 아니다. 각 명령이 어떤 상태를 만들고 무엇을 증명하는지 함께 적는다. version과 option은 프로젝트 lockfile과 최신 공식 문서를 확인한다.

## 프로젝트 생성

```sh
npx create-expo-app@latest field-notes --template default@sdk-57
```

- SDK transition의 기본 template 차이를 피하기 위해 SDK를 명시한다.
- 생성 뒤 package.json과 lockfile의 실제 versions를 기록한다.
- 이 브랜치의 기준은 Expo SDK 57, React Native 0.86, React 19.2.3, Node 24.19.0이다. Expo가 지원하는 최소 Node와 이 저장소가 고정한 재현 runtime을 구분한다.
- 2026-08 현재 공식 시작 문서는 transition 동안 **물리 기기 Expo Go**를 쓰려면 SDK 54를 선택하라고 안내한다. SDK 57 실습은 emulator/simulator 또는 프로젝트 development build를 기본으로 하고, Expo Go는 실제 포함 module/runtime이 호환될 때만 제한적 확인에 쓴다.

## 개발 server

```sh
npx expo start
npx expo start --dev-client
```

`--dev-client`는 프로젝트용 development build에 연결한다. Metro가 떴다는 사실은 native binary가 새 config를 포함한다는 뜻이 아니다.

이 저장소에서는 고정 runtime으로 다음처럼 실행한다.

```sh
fnm exec --using=24.19.0 npm ci
fnm exec --using=24.19.0 npm run test:reference
```

## Stage 04 local fault endpoint

local fault server는 host `127.0.0.1:3104`에만 bind한다. app 실행 환경별 endpoint는 다음과 같다.

| app 환경 | `EXPO_PUBLIC_FIELD_NOTES_SYNC_URL` | 추가 조건 |
|---|---|---|
| iOS simulator | `http://127.0.0.1:3104/commands` | simulator evidence로만 기록 |
| Android emulator | `http://10.0.2.2:3104/commands` | Android emulator host alias |
| Android physical device | `http://127.0.0.1:3104/commands` | `adb reverse tcp:3104 tcp:3104`, 종료 뒤 `adb reverse --remove tcp:3104` |
| iOS physical device | 허가된 격리 HTTPS endpoint 또는 `미검사` | 이 저장소는 loopback reverse bridge를 제공하지 않음 |

전체 명령, 안전 경계와 정리 절차는 [fault server README](../exercises/field-notes/fault-server/README.md#app-실행-환경별-endpoint)를 따른다. iOS device를 연결하려고 unauthenticated test control endpoint를 LAN이나 공개 tunnel에 노출하지 않는다. platform cleartext policy를 production 전역에서 낮추지 말고, 안전한 HTTPS test endpoint가 없다면 실제 device network fault 항목을 `미검사`로 둔다.

## compatible package 설치

```sh
npx expo install <package>
```

현재 Expo SDK와 맞는 package version을 선택한다. 설치 뒤 native config/plugin과 새 build 필요 여부를 확인한다.

## local native build

```sh
npx expo run:android
npx expo run:ios
```

- native project가 없으면 prebuild가 실행될 수 있다.
- 실제 command의 generation side effect를 `git diff`로 확인한다.
- iOS device build에는 macOS/Xcode와 signing 조건이 필요하다.

## clean native generation

```sh
npx expo prebuild --clean
```

CNG 프로젝트에서 app config와 plugins가 native project를 재현하는지 검사한다. 직접 소유하는 `android/`·`ios/` 변경을 무심코 지우지 않는다.

package install 없이 generation 결과만 볼 필요가 있다면 현재 CLI가 지원하는 option을 공식 문서에서 확인한다.

## project 검사

```sh
npx expo-doctor
```

package/version/config 문제를 찾는 보조 도구다. 실제 device behavior와 release smoke를 대체하지 않는다.

## EAS development·preview·production build 예

```sh
eas build --platform android --profile development
eas build --platform ios --profile preview
eas build --platform all --profile production
```

cloud service는 선택 사항이다. local native build나 다른 CI를 사용할 수 있다. 어느 경로든 source·profile·toolchain·artifact digest를 기록한다.

## update

현재 Field Notes reference는 EAS Update를 구성하지 않으며 `eas.json`에도 channel이 없다. 아래는 별도 제품이 `expo-updates`, runtime compatibility와 channel owner를 명시적으로 도입한 뒤에만 사용하는 선택 확장 예다. 이 저장소에서 그대로 실행할 준비 명령이 아니다.

```sh
eas update --channel preview --message "검증 설명"
```

실행 전에 build의 runtimeVersion과 update의 native API 호환성을 확인한다. native module/config 변경은 remote update만으로 전달하지 않는다.

## 제출

```sh
eas submit --platform android
eas submit --platform ios
```

upload와 public release를 구분한다. store console의 track/TestFlight, metadata, review와 rollout을 별도로 확인한다.

## Android 기기·process 관찰 예

```sh
adb devices
adb shell am force-stop <application-id>
adb shell monkey -p <application-id> 1
adb logcat
```

`force-stop`은 일반 process kill이나 recent 제거와 의미가 다르다. 테스트 목적과 기대 상태를 기록한다.

설치·activity·job scheduler 명령은 Android version에 따라 달라질 수 있으므로 현재 platform tools help를 사용한다.

## iOS simulator 예

```sh
xcrun simctl list devices
xcrun simctl install booted <path-to-app>
xcrun simctl launch booted <bundle-id>
xcrun simctl terminate booted <bundle-id>
```

simulator는 camera·background scheduler·push·biometric·battery의 실제 기기 행동을 완전히 대체하지 않는다.

## 이 브랜치 검사

```sh
./prepare.sh
./verify.sh
```

Stage 04 자동 근거를 좁혀 다시 실행할 때는 다음 세 층을 구분한다.

```sh
npm run test:stage04
python3 scripts/expect_skeleton_rejection.py
python3 scripts/verify_mutants.py
```

첫 명령은 production reference SQLite/fetch와 sync-engine/fault-server behavior를 검사한다. 두 번째는 Stage 01 skeleton의 명명된 navigation/form 실패만 확인하고, 세 번째는 순수 sync-model의 세 known-wrong mutation만 거부한다. 어느 명령도 attachment upload/link protocol, 실제 credential refresh, device radio 또는 production backend를 증명하지 않는다.

Stage 06의 machine-checkable release evidence schema만 좁혀 검사할 때는 다음을 사용한다.

```sh
fnm exec --using=24.19.0 npm --prefix exercises/field-notes/release-contract run typecheck
fnm exec --using=24.19.0 npm --prefix exercises/field-notes/release-contract test
fnm exec --using=24.19.0 npm --prefix exercises/field-notes/release-contract run validate:fixtures
```

fixture와 validator `OK`는 `artifacts[]`, artifact ref, runtime/device matrix와 claim/review 상태의 schema 일관성만 확인한다. 실제 artifact digest, signature trust, credential ownership, device 설치나 store-delivered bytes를 검증하지 않는다.

`prepare.sh`는 고정 Node/npm과 lockfile로 `node_modules/`를 재생성하고 `.guide/mobile-app/`에 source/runtime fingerprint와 environment report를 쓴다. 학습자 source, skeleton workspace와 device 상태는 바꾸지 않는다. 준비 뒤 source나 runtime이 바뀌면 `verify.sh`는 오래된 marker를 거부한다.

`verify.sh`는 저장소 밖의 unique temporary directory에 log를 남기고 필수 suite를 끝까지 집계한다. 출력된 절대 log path를 evidence에 연결하며, 같은 이름의 repository file이나 고정 `/tmp` log를 덮어쓰지 않는다. `.guide/mobile-app/`만 정리하려면 `make clean`을 사용한다.

검사 결과에는 자동 실행, `not-run` 수동 항목과 environment limitation이 구분돼야 한다. 현재 verify의 CNG·Metro bundle은 native compile이나 artifact 생성/digest가 아니다. Android/iOS compile, AAB/APK/xcarchive/IPA 생성과 실제 file digest, signing·install·store는 외부 gate이며 별도 명령/evidence가 없으면 `NOT-RUN`으로 남긴다. 자동 통과는 교육적 완성이나 stable 판정이 아니며, cloud build·signing·store upload·실제 Android/iOS device 결과를 대신하지 않는다.
