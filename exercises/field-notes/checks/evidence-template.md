# Evidence template

하나의 주장을 재현하고 사람이 검토할 수 있게 작성한다. 자동 output과 수동 판단을 섞어 하나의 `통과`로 만들지 않는다.

## 식별

```text
acceptance ID / Stage:
관련 owns:
관련 exit capability:
작성자 / 실행자:
검토자:
실행 시각과 timezone:
결과: 통과 | 실패 | 미검사 | 비적용
```

`미검사`이면 이유, 필요한 tool/device/account와 다음 검토자를 적는다. `비적용`이면 제품 범위 근거와 승인한 reviewer를 적는다.

## 주장과 판정 질문

무엇이 어떤 초기 상태와 사건에서 동작하거나 안전하다고 주장하는가?

- 관측 가능한 public behavior:
- 보존해야 하는 불변식:
- 사람이 판단해야 하는 질문:

내부 함수명, SQL 문자열 또는 screenshot 모양을 주장으로 쓰지 않는다.

## source·build·환경

```text
source revision:
source/lockfile digest:
platform / host OS:
device 또는 emulator/simulator와 실제 기기 여부:
device OS / vendor:
app identifier:
app version / versionCode 또는 buildNumber:
runtimeVersion / update identity:
runtime fingerprint 또는 policy ref:
build profile / toolchain:
artifact ref / kind / local-or-store identity / digest:
DB schema / fixture version:
network / account / permission / capability 상태:
```

field가 적용되지 않으면 비워 두지 말고 이유를 적는다. credential, token, signing secret, 실제 사용자 data는 포함하지 않는다.

## 초기 durable 상태

사건 전 관련 상태를 기록한다.

```text
records/localRevision/remoteVersion:
outbox commandId·attempted snapshot·lease:
conflict:
attachment/file/checksum:
session/account binding:
remote snapshot/server apply count:
scheduler/notification response claim:
```

민감 payload 대신 normalized ID, version, checksum과 상태를 사용한다.

## 사건·fault 순서

1. 준비 명령 또는 사람이 수행한 action
2. 주입한 fault/OS 사건과 정확한 시점
3. retry, restart, background/foreground, notification tap 등 후속 사건

deterministic fault server를 사용했다면 fault control과 seed/clock을 적는다. 실제 OS 사건이면 device 조작과 관찰 시각을 적는다.

## 기대 결과

```text
expected durable state:
expected public/UI observation:
expected remote/apply history:
forbidden outcome:
```

## 실제 결과

```text
actual durable state:
actual public/UI observation:
actual remote/apply history:
차이와 판정 근거:
```

## 자동 evidence

- 실행한 command 전체:
- exit status:
- test case 이름:
- normalized trace/log 위치:
- DB/server snapshot 위치:
- reference 통과 결과:
- skeleton/known-wrong 거부 결과:

실행하지 않은 command를 성공으로 적지 않는다. source 문자열 검사나 snapshot 한 장만으로 불변식을 증명했다고 주장하지 않는다.

## 사람·기기 evidence

- 실제 기기 여부와 device ID:
- reviewer가 수행한 흐름:
- 평가 질문별 답:
- screenshot/screen recording/accessibility 발화/trace 위치:
- Android/iOS 차이:
- UX·접근성 판단과 근거:

사람 판단이 필요한 경우 자동 test로 임의 점수화하지 않는다. screenshot은 보조 자료이며 focus, 발화, background 실행, install/upgrade를 혼자 증명하지 않는다.

## build·artifact evidence

- resolved app config / CNG 결과:
- native compile command와 exit status:
- schema v2 source/application/build identity:
- Android AAB ref + APK/Play split ref 또는 `not-run` 근거:
- iOS xcarchive ref + IPA/TestFlight ref 또는 `not-run` 근거:
- artifact별 signing 상태(`not-run`/`claimed`/`manually-reviewed`), redacted identity와 review evidence:
- install/upgrade artifactRef, device class, observed app/build/runtime/policy, launch 결과:
- store를 실행했다면 publishingArtifactRef, storeBuildRef, track/status:
- store-delivered bytes 상태(`not-run`/`declared`/`manually-reviewed`), artifactRef/digest와 review evidence:

CNG, JS bundle, native compile, signed artifact, device install과 store processing을 각각 구분한다. `claimed`/`declared`를 자동 검증으로, schema 통과를 signature trust·credential ownership·store-delivered bytes 증명으로 바꾸지 않는다.

## 보장하지 않는 범위와 알려진 한계

- 실행하지 않은 platform/device/OS:
- fake가 대체한 실제 OS/provider/backend:
- account/signing/store 미검사:
- sample·측정·관찰 한계:
- 실패 시 복구/후속 변경:

## 검토 기록

```text
reviewer:
review date:
decision:
follow-up owner:
follow-up evidence due:
```

자동 검사 통과는 교육적 완성이나 `stable` 승인 기록이 아니다.
