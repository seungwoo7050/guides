# 선행 지식·환경 점검

이 문서는 학습을 시작할 수 있는 기준과 host·device·account 제약을 구분한다. 모든 장비와 계정을 처음부터 갖출 필요는 없지만, 없는 항목을 자동 검사 성공으로 대신해서는 안 된다.

## 필수 지식

### TypeScript

- union과 narrowing
- `unknown`과 runtime parsing
- async/await, cancellation과 stale result 거절
- module과 package boundary

### React

- props/state와 controlled form
- effect setup/cleanup
- context 또는 dependency injection의 책임
- list key와 render identity

### 웹·네트워크

- HTTP method/status/body
- authentication과 authorization 구분
- JSON parse와 application validation
- timeout·retry·idempotency의 기본 의미

### Git·검증

- clean checkout과 lockfile install
- 작은 의미 단위 commit
- test 실패 재현
- 변경 전후 명령·결과·환경 근거 기록

## 권장 지식

- SQLite와 transaction 기초
- Android Studio emulator 또는 Xcode simulator 실행 경험
- TalkBack/VoiceOver 사용 경험
- 실제 API 또는 작은 backend 구현 경험

## repository runtime과 SDK 하한

두 version을 혼동하지 않는다.

| 항목 | 기준 | 의미 |
|---|---|---|
| Node.js `24.19.0` | `.nvmrc` | 이 저장소가 준비·검증을 재현하는 pin |
| npm `11.17.0` | `packageManager`와 lockfile | dependency graph와 script 실행 pin |
| Node.js `22.13.x` | Expo SDK 57 공식 matrix | SDK가 지원하는 최소 version; 이 저장소의 권장 version이 아님 |

`24.19.0`이 없다면 version manager로 설치한 뒤 저장소 root에서 활성화한다. 더 최신 Node/npm이 우연히 동작해도 기준 환경을 검증한 것이 아니다. 정확한 package patch는 `package-lock.json`이 소유하며 임의로 전체 upgrade하지 않는다.

## host별 가능한 범위

| host | 가능한 자동·개발 범위 | 추가 조건 | 보장하지 않는 것 |
|---|---|---|---|
| macOS | 문서/domain 검사, Android build, iOS simulator/device build | Android Studio/JDK/SDK, iOS에는 호환 Xcode와 Command Line Tools | 실제 device·signing·store 심사는 별도 |
| Linux | 문서/domain 검사, Android emulator/device build | Android Studio/JDK/SDK 또는 호환 CLI toolchain | local iOS native compile/signing |
| Windows | 문서/domain 검사, Android emulator/device build | PowerShell/WSL2 선택을 고정하고 Android toolchain 연결 | local iOS native compile/signing |

`prepare.sh`가 Node/npm/Python과 dependency를 준비해도 Android SDK, full Xcode, simulator, 실제 device와 developer account를 자동 생성하지 않는다. `verify.sh`가 tool 부재를 보고하면 해당 platform을 통과로 간주하지 말고 수동 또는 다른 host evidence를 연결한다.

## SDK 57와 기준 runtime

- SDK 57 프로젝트는 `create-expo-app`의 SDK 57 template을 명시해야 한다.
- 이 과정은 **development-build-first**다. 선택한 native module·app config·permission을 포함한 자기 앱 binary를 기준 runtime으로 사용한다.
- native code가 있는 package 추가, app config 변경, Expo SDK upgrade 뒤에는 native project 재생성과 binary rebuild가 필요할 수 있다.
- Expo Go는 고정된 native module을 가진 학습용 app이다. 성공하더라도 app identity, native config, remote push, app/universal link, signing 또는 production binary를 증명하지 않는다.
- 2026-08-09 기준 SDK 전환기에는 app store의 물리 iPhone용 Expo Go가 SDK 57을 열지 못할 수 있다. emulator/simulator에 호환 Expo Go를 설치할 수 있어도 이 브랜치의 device/release evidence를 대체하지 않는다.

변동 가능한 내용은 [공식 자료와 version 기준](official-sources.md)에서 확인한다.

## 플랫폼 도구

### 공통

- Git
- Node.js `24.19.0`과 npm `11.17.0`
- Python `3.11` 이상: repository 검사 script 지원 하한
- 충분한 저장 공간과 dependency를 내려받을 network
- text editor와 terminal

### Android 경로

- Android Studio 또는 호환 Android SDK/command-line tools
- JDK와 SDK 36 build platform/tooling
- Android 7 이상 emulator 또는 실제 device
- 실제 device 사용 시 USB debugging 승인과 data cable 또는 검증된 무선 연결

emulator는 process restart, 일부 layout와 자동 흐름에 유용하지만 camera 품질, notification 전달, vendor battery restriction, background scheduling과 실제 성능을 보장하지 않는다.

### iOS 경로

- macOS
- Expo SDK 57 matrix와 호환되는 full Xcode와 Command Line Tools
- iOS 16.4 이상 simulator 또는 실제 device
- 실제 iPhone 사용 시 Developer Mode, 고유 bundle identifier와 signing 설정

simulator는 camera, remote push, background scheduling, thermal·memory·battery와 실제 signing/install 행동을 모두 재현하지 않는다. Xcode CLI 일부만 있거나 simulator bundle만 성공한 것은 installable iOS artifact evidence가 아니다.

## device·account·비용 경계

- Android와 iOS 실제 기기를 적어도 한 대씩 사용할 수 있으면 가장 강한 evidence를 만들 수 있다. 없다면 emulator/simulator 결과를 제출하되 대체하지 못한 항목을 명시한다.
- local Android/iOS simulator build는 Expo 계정을 요구하지 않을 수 있다. EAS cloud build/update/submit을 사용하면 Expo account, network와 서비스 quota가 필요하다.
- 물리 iPhone 설치와 배포 방식에 따라 Apple signing identity와 Developer Mode가 필요하다. App Store 제출은 적절한 Apple Developer/App Store Connect 권한이 필요하다.
- Google Play 제출은 Play Console app와 제출 권한이 필요하다.
- 개발자 프로그램 비용, store 정책, 제출 요구, cloud quota는 바뀔 수 있다. release 시점의 공식 console 문서에서 다시 확인한다.
- credential·device registration·store access를 개인 임시 계정에 묶지 말고 실제 소유자와 회수·rotation 경로를 기록한다.

계정이나 실제 device가 없다는 이유로 credential을 공유받거나 production project를 연습 대상으로 사용하지 않는다. 이 가이드의 fault server와 test data는 허가된 local 범위에서만 사용한다.

## 첫 실행 전 점검

저장소 root에서 다음을 확인한다.

```sh
node --version
npm --version
python3 --version
./prepare.sh
```

그다음 사용할 platform마다 다음 질문에 답한다.

- 어떤 host, OS, Xcode/Android SDK, simulator/emulator/device version을 사용하는가?
- development build를 어떤 source revision과 app identifier로 만들었는가?
- camera·location·notification permission을 안전하게 reset할 수 있는 test device인가?
- production credential·실사용자 data 없이 실패를 재현하는가?
- EAS나 store account가 없다면 어느 release 항목을 `미검사`로 남길 것인가?
- 실제 device가 없다면 emulator/simulator가 보장하지 못하는 항목을 evidence에 적었는가?

## 복습 경로

| 막히는 영역 | 기존 브랜치 |
|---|---|
| JavaScript·TypeScript·React·HTTP | [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app) |
| React 상태·비동기·접근성·성능 | [`web-front-react-nextjs`](https://github.com/seungwoo7050/guides/tree/web-front-react-nextjs) |
| DNS·TCP·TLS·timeout | [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks) |
| Git 변경·통합·복구 | [`git`](https://github.com/seungwoo7050/guides/tree/git) |
| 일반 보안·공격면·credential | [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity) |
| 공개 서비스 배포·관측 | [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra) |

모든 브랜치를 다시 완료하지 않는다. 사전 진단에 답하지 못하거나 실제 구현에서 막힌 부분만 참조한다.
