# 임베디드 변경 evidence 템플릿

이 템플릿은 checker 결과와 사람의 설계·운영 판단을 분리합니다. 자동 검사 통과만으로 교육적 완료나 실제 hardware 보장을 선언하지 않습니다.

## 0. 계약 추적과 판정 상태

```text
catalog owns:
exit capability:
concept document:
exercise/fixture:
capstone scenario:
submission revision:
automated_check_command:
automated_exit_code:
automated_json_report:
human_review: NOT_TESTED
reviewer/date:
```

`human_review`의 기본값은 정확히 `NOT_TESTED`(미검증)입니다. reviewer가 아래 raw evidence, 한계, safety와 recovery를 실제로 확인한 뒤에만 판정과 근거를 함께 바꿉니다. checker `0`은 공개 계약 통과, `1`은 의미 실패, `2`는 사용할 수 없는 인터페이스·입력을 뜻하며 사람 판정을 대신하지 않습니다. `NOT_TESTED`는 자동 PASS 집계에 포함하지 않습니다.

## 1. 문제

```text
기대 동작:
실제 동작:
영향:
재현 빈도:
최초 확인 시점:
```

## 2. target와 build

```text
repository/source revision:
board와 revision:
SoC/MCU part와 revision:
external device:
toolchain/SDK:
Python/C standard:
build command:
Kconfig fragment:
Devicetree overlay:
image build ID/hash:
bootloader version:
```

첨부:

- final `.config`
- merged Devicetree/generated description
- ELF와 map 보관 위치
- size/stack report

## 3. 실행 조건

```text
power supply/voltage:
clock configuration:
temperature 또는 환경:
debugger 연결 여부:
logging/tracing configuration:
fixture/probe/analyzer:
firmware state before run:
safety/isolation precondition:
```

## 4. 재현 절차

```text
1.
2.
3.
```

reset/flash/cleanup을 포함해 다른 사람이 known state에서 시작할 수 있게 작성합니다.

## 5. 상태와 사건

```text
state owner:
state before:
input event/context:
transition:
state after:
유지해야 할 invariant:
```

## 6. raw evidence

```text
serial log:
trace:
register dump:
crash record:
bus capture:
logic analyzer:
current measurement:
flash bytes/metadata:
```

원시 파일의 hash와 decoder/version을 남깁니다.

## 7. 원인과 반증

```text
확인한 사실:
현재 가설:
가설을 지지하는 evidence:
이미 배제한 원인:
아직 확인하지 못한 조건:
```

의도를 code에서 확인하지 못했다면 사실로 표현하지 않습니다.

## 8. 변경

```text
변경한 owner/contract:
왜 이 계층이 맞는가:
호환성 영향:
RAM/flash/stack 영향:
timing/power 영향:
reset/update 영향:
```

## 9. 검증

| 검사 | 환경 | 기대 | 실제 | 판정 |
|---|---|---|---|---|
| normal | | | | |
| boundary | | | | |
| failure | | | | |
| recovery | | | | |

추가:

```text
host/model checker command, exit code와 JSON:
reference/starter/known-wrong/missing polarity (0/1/1/2):
simulator/emulator:
actual board:
미검증 범위:
human_review: NOT_TESTED
```

capstone 제출에는 12개 행을 모두 채웁니다. `자동` 열에는 checker 결과와 JSON의 check ID, `raw evidence`에는 trace·flash bytes·metadata·분석표의 경로와 hash, `사람 판정`에는 판단 근거 또는 `NOT_TESTED`(미검증)를 씁니다.

| scenario/fixture | 결합하는 핵심 경계 | 자동 | raw evidence | 사람 판정 |
|---|---|---|---|---|
| [S01 normal cycle](../capstone/field-sensor-node/fixtures/S01-normal-cycle.json) | 정상 acquisition·queue·store·sleep 주기와 memory/time budget | | | `NOT_TESTED` |
| [S02 identity mismatch](../capstone/field-sensor-node/fixtures/S02-identity-mismatch.json) | I2C/SPI device identity 실패와 safe state | | | `NOT_TESTED` |
| [S03 burst overflow](../capstone/field-sensor-node/fixtures/S03-burst-overflow.json) | ISR→task queue 상한과 명시적 overflow | | | `NOT_TESTED` |
| [S04 timeout/late interrupt](../capstone/field-sensor-node/fixtures/S04-timeout-late-interrupt.json) | timeout 뒤 generation·buffer ownership | | | `NOT_TESTED` |
| [S05 persistence power loss](../capstone/field-sensor-node/fixtures/S05-persistence-power-loss.json) | torn write 뒤 old/new complete record | | | `NOT_TESTED` |
| [S06 storage full/offline](../capstone/field-sensor-node/fixtures/S06-storage-full-offline.json) | bounded storage·backpressure·offline 진행 | | | `NOT_TESTED` |
| [S07 upload unknown/retry](../capstone/field-sensor-node/fixtures/S07-upload-unknown-retry.json) | unknown outcome와 idempotent retry | | | `NOT_TESTED` |
| [S08 watchdog crash](../capstone/field-sensor-node/fixtures/S08-watchdog-crash.json) | progress watchdog·crash evidence·bounded recovery | | | `NOT_TESTED` |
| [S09 sleep-entry race](../capstone/field-sensor-node/fixtures/S09-sleep-entry-race.json) | pending event와 sleep/wakeup 불변식 | | | `NOT_TESTED` |
| [S10 trial crash/revert](../capstone/field-sensor-node/fixtures/S10-trial-crash-revert.json) | BOOT_OK gate, trial crash와 durable revert | | | `NOT_TESTED` |
| [S11 confirm power loss](../capstone/field-sensor-node/fixtures/S11-confirm-power-loss.json) | confirm metadata cut 뒤 boot 가능한 slot | | | `NOT_TESTED` |
| [S12 schema rollback](../capstone/field-sensor-node/fixtures/S12-schema-rollback.json) | rollback image와 persistent schema compatibility | | | `NOT_TESTED` |

## 10. rollback와 운영

```text
변경 rollback 방법:
field device migration:
telemetry/alert:
known residual risk:
후속 작업:
```

## 11. 안전, cleanup과 복구 확인

```text
위험 source와 격리 방법:
전압/current/pin/actuator 제한:
factory 또는 last-known-good image 위치와 hash:
calibration/identity backup:
programmer/recovery-mode 절차와 사전 확인 결과:
시험 중단 조건:
생성한 임시 파일·wiring·resource:
cleanup 명령과 결과:
known state 복원 확인:
복구하지 못한 상태:
```

외부 service나 실제 board를 사용하지 않았다면 `not used`라고 쓰고 host 모델이 증명하지 못하는 timing·electrical·power 항목을 미검증 범위에 남깁니다. 필수 검사를 실행하지 못했거나 known state로 복구하지 못한 결과를 성공으로 표시하지 않습니다.
