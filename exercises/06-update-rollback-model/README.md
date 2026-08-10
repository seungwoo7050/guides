# 실습 6 — update와 rollback 모델

## 문제

새 image 다운로드, validation, install, trial boot, confirmation와 revert는 여러 reset과 power loss를 지나갑니다. slot bytes만 남아 있어도 metadata와 persistent schema가 모순되면 boot loop 또는 rollback 불능이 생깁니다. 이 실습은 **firmware lifecycle 상태 기계**를 구현하고 모든 전이를 failure trace로 검증합니다.

## 시작

[`examples/update-state-model`](../../examples/update-state-model/README.md)을 실행합니다. 제공 모델은 핵심 상태만 포함하며 production bootloader가 아닙니다.

이 디렉터리는 실행 가능한 `starter/`, 비교 기준인 `reference/`, 공개 failure
fixture와 `check.py`를 함께 제공합니다. reference와 starter의 판정 polarity를
먼저 확인한 뒤 starter를 별도 workspace에 복사해 구현합니다.

```sh
python3 exercises/06-update-rollback-model/check.py \
  --submission exercises/06-update-rollback-model/reference
python3 exercises/06-update-rollback-model/check.py \
  --submission exercises/06-update-rollback-model/starter --json
python3 examples/update-state-model/model.py \
  examples/update-state-model/fixtures/confirm-power-loss-cuts.json --check --trace
```

checker는 통과 시 `0`, 실행된 submission의 계약 위반 시 `1`, submission
경로나 checker fixture를 읽을 수 없으면 `2`를 반환합니다.

## image와 metadata

최소 image metadata:

```text
version/build id
hardware compatibility
payload hash/validity
schema range
confirmed 여부
```

boot state:

```text
CONFIRMED(v1)
CANDIDATE(v2)
TRIAL(v2, previous=v1, attempts)
REVERTING(v1)
RECOVERY
```

구현 방식은 swap, overwrite 또는 direct-XIP 중 하나를 가정하고 명시합니다.

## 사건

- `DOWNLOAD(version, compatible, valid)`
- `MARK_PENDING`
- `RESET`
- `BOOT_OK`
- `SELF_TEST_FAIL`
- `CONFIRM`
- `WATCHDOG_RESET`
- `POWER_LOSS(point)`
- `CORRUPT(slot/metadata)`
- `RECOVER`

각 사건의 실행 context와 durable write를 표시합니다.

## 핵심 불변식

1. boot 가능한 confirmed image 또는 recovery 경로가 최소 하나 있습니다.
2. invalid/incompatible candidate는 실행하지 않습니다.
3. trial image는 confirmation 전까지 previous image를 파괴하지 않습니다.
4. trial 실패 또는 confirmation deadline 초과 뒤 bounded attempts 안에 revert합니다.
5. metadata power loss 뒤 boot choice가 결정적입니다.
6. persistent data가 previous image와 호환되지 않으면 functional rollback을 주장하지 않습니다.
7. report는 selected image, slot, state와 rollback reason을 제공합니다.

## self-test와 confirmation

self-test 항목을 선택합니다.

- critical driver readiness
- storage decode/migration
- communication 최소 경로
- watchdog supervisor
- product-specific safe output

confirmation 시점을 정하고 너무 이른/늦은 조건을 fixture로 만듭니다.

## 필수 trace

- valid v2 normal update/confirm
- invalid signature/hash candidate
- wrong hardware candidate
- download incomplete
- trial immediate crash
- trial watchdog after partial operation
- repeated reset until revert
- confirm metadata write 중 power loss
- revert 중 power loss
- previous image corrupted
- both slots invalid → recovery
- new schema committed before confirm → rollback incompatibility
- version policy/anti-rollback reject를 abstract policy로 표현

## multi-image 선택 확장

application + network core처럼 두 image가 함께 바뀌는 경우:

```text
bundle manifest
compatible version set
install order
trial set
cross-image self-test
atomic/coordinated confirm
partial failure recovery
```

각 image를 독립 confirm했을 때 incompatible set가 남는 fixture를 추가합니다.

## 필수 결과물

```text
workspace/
├── lifecycle.md
├── image-format.md
├── state-model/
├── fixtures/
├── invariant-checker.md 또는 동등 검사
├── persistent-compatibility.md
└── report.md
```

## 완료 조건

- 모든 command는 허용 state에서만 성공합니다.
- reset은 RAM state가 아니라 durable metadata로 다음 image를 선택합니다.
- trial attempt와 confirmation deadline가 bounded입니다.
- invalid/wrong-board image를 거부합니다.
- power cut fixture마다 bootable/recovery 불변식을 검사합니다.
- binary rollback와 data compatibility를 별도 항목으로 판정합니다.
- 모델이 secure boot 또는 실제 flash atomicity를 증명하지 않는다고 기록합니다.

자동 checker는 `BOOT_OK`와 `SELF_TEST_PASS` gate, trial 중 rollback slot 보존,
dual-state metadata commit의 before/after cut, hardware/schema compatibility와
bounded revert를 모델 수준에서 확인합니다. 실제 signature, flash program
unit·erase endurance, MCUboot trailer/swap atomicity, brownout과 boot ROM은
검증하지 않습니다. target evidence에서 사용하는 bootloader mode, release,
partition, reset source와 raw flash dump를 별도로 남깁니다.

## 잘못된 완료

- update 성공 즉시 old image 삭제
- application이 실행되자마자 confirm
- reset 횟수 제한 없이 trial 반복
- signature valid만 보고 hardware compatibility 무시
- current version string만 저장하고 slot/state 없음
- schema migration 뒤 rollback 가능한지 검사하지 않음
- exception 발생을 곧바로 test success로 처리

## 선택 target 구현

- MCUboot trial/revert sample
- QEMU에서 crash/reset fixture
- 실제 보드에서 candidate download와 watchdog reset
- bootloader/application build ID telemetry

공식 bootloader mode와 사용하는 release 문서를 먼저 고정합니다.

## 검토 질문

1. trial image가 boot는 되지만 communication initialization 뒤 hang한다면 언제 confirm해야 합니까?
2. previous image bytes가 남아 있어도 functional rollback이 불가능한 경우를 설명해 보세요.
3. metadata가 두 copy일 때 sequence와 commit을 어떤 방식으로 복구할 수 있습니까?
4. recovery image가 update 대상과 같은 저장장치 결함에 의존하면 어떤 위험이 있습니까?
