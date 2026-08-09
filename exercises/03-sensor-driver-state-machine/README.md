# 실습 3 — sensor driver 상태 기계

## 문제

I2C/SPI transfer가 성공해도 sensor operation이 성공한 것은 아닙니다. 장치는 reset, configuration, conversion wait, data-ready, read, timeout와 fault 상태를 가질 수 있습니다. 이 실습에서는 register read/write 모음이 아니라 **operation lifecycle을 소유하는 driver**를 설계합니다.

## 목표 장치

실제 sensor를 선택하거나 다음 abstract device를 사용합니다.

- identity register
- reset command
- configuration register
- one-shot conversion command
- busy/data-ready status
- 16-bit sample register
- optional CRC/status fault

bus는 NACK, timeout, short transfer와 stuck 상태를 반환할 수 있습니다.

## 상태

최소 상태:

```text
UNBOUND
RESETTING
PROBING
IDLE
CONFIGURING
CONVERTING(generation, deadline)
READY
READING
FAULT(reason)
SUSPENDED
```

모든 상태를 그대로 코드 enum으로 만들 필요는 없지만 public operation과 failure trace에서 같은 의미가 드러나야 합니다.

## public contract

예시:

```text
init(config)             → ready 또는 명시적 failure
start_sample(deadline)   → generation/token
poll/interrupt(status)   → progress
read_sample(token)       → sample 또는 error
cancel(token)            → terminal result
suspend()/resume()
recover()
```

blocking API를 선택해도 내부 timeout·cancel·reset state를 문서화합니다.

## bus와 device failure를 분리합니다

| 분류 | 예시 | 다음 상태 후보 |
|---|---|---|
| transport | NACK, timeout, short transfer | retry/fault/recover bus |
| identity | wrong device/revision | permanent unavailable |
| protocol | invalid status, CRC | retry or fault |
| operation | conversion timeout | abort/reset/recover |
| lifecycle | suspend 중 request | reject/defer |
| configuration | unsupported range | caller error, state unchanged |

모든 오류를 `-EIO` 하나로 합치지 않고 raw status와 semantic class를 연결합니다.

## 요구사항

### initialization

- dependency/bus readiness 확인
- reset 뒤 ready 조건
- identity와 revision
- default register와 desired configuration diff
- partial configuration 실패 뒤 상태

### sampling

- command가 accepted된 시각
- conversion deadline
- polling 또는 data-ready interrupt
- generation/token
- sample validity와 scale/unit
- 늦은 completion

### retry

retry 가능한 오류와 불가능한 오류를 구분합니다. retry가 device operation을 중복 시작할 수 있는지 확인합니다.

### cancellation

- bus transaction cancel 가능 여부
- device conversion abort 가능 여부
- buffer와 callback lifetime
- cancel 반환 뒤 늦은 interrupt

### power/reset

suspend/resume, device power cycle와 MCU reset 뒤 configuration이 유지된다고 가정하지 않습니다.

## fake bus

host test에서는 다음 behavior를 script로 주입합니다.

```text
EXPECT_WRITE(register, value) → OK/NACK/TIMEOUT
EXPECT_READ(register) → bytes/SHORT/ERROR
ADVANCE_TIME(delta)
RAISE_DATA_READY
```

fake는 register access semantic과 device state를 가진 편이 좋습니다. 단순 mock 호출 순서만 검사하면 잘못된 recovery도 통과할 수 있습니다.

이 디렉터리는 바로 실행할 수 있는 `starter/`, 비교 가능한 `reference/`,
stateful I2C/SPI·MMIO·DMA 모델인 `lab_support.py`와 결정론적 `fixtures/`를
제공합니다. reference를 먼저 검증한 뒤 starter를 별도 작업 디렉터리에
복사해 완성합니다.

```sh
python3 exercises/03-sensor-driver-state-machine/check.py \
  --submission exercises/03-sensor-driver-state-machine/reference
python3 exercises/03-sensor-driver-state-machine/check.py \
  --submission exercises/03-sensor-driver-state-machine/starter --json
```

checker는 성공 시 `0`, 계약 위반 시 `1`, submission 경로나 checker 입력을
읽을 수 없으면 `2`를 반환합니다. `generated-config/devicetree.json`과
`kconfig.json`은 최종 hardware topology와 software 선택의 증거이며 driver
source에 board address나 pin을 다시 하드코딩하는 근거가 아닙니다.

## 필수 fixture

- normal init + sample
- wrong identity
- reset timeout
- configuration 중 두 번째 write 실패
- conversion exactly at deadline
- conversion after deadline
- interrupt before wait begins
- duplicate data-ready
- cancel then stale completion
- suspend with in-flight request
- resume 뒤 reconfiguration 필요
- bus recover 뒤 device state unknown

## Devicetree/Kconfig 확장

선택 구현에서는 다음을 분리합니다.

- Devicetree: bus, address/chip-select, interrupt GPIO, power/reset GPIO
- Kconfig: driver enable, optional CRC/trigger mode, buffer/resource policy
- application config: sampling interval와 product policy

## 필수 결과물

```text
workspace/
├── device-contract.md
├── state-machine.md
├── error-model.md
├── fixtures/
├── implementation/
├── generated-config/        선택
├── evidence/
└── report.md
```

## 완료 조건

- public operation마다 허용 state와 terminal result가 있습니다.
- transport success와 device readiness를 구분합니다.
- timeout/cancel 뒤 stale completion이 새 request를 완료하지 않습니다.
- configuration 실패 뒤 previous/unknown state를 명확히 합니다.
- retry budget과 recovery escalation이 bounded입니다.
- sample에는 unit, scale, timestamp와 validity가 있습니다.
- optional target test는 bus trace와 build/configuration을 함께 보존합니다.

자동 checker는 상태 전이, W1C acknowledge, generation, timeout/cancel,
DMA/cache ownership과 생성 설정의 공개 계약만 확인합니다. 실제 bus timing,
cache controller instruction, electrical signal, interrupt latency와 특정 RTOS
API의 ISR-safety는 증명하지 않습니다. 실제 target 결과에는 board revision,
toolchain, raw trace와 이 미검증 범위를 별도로 기록합니다.

## 잘못된 완료

- register helper만 있고 operation state가 없음
- fixed delay 뒤 무조건 ready로 가정
- timeout 후 buffer/callback 즉시 재사용
- wrong identity를 정상 장치처럼 계속 사용
- resume 후 register state가 유지된다고 무조건 가정
- board address와 pin을 driver source에 hard-code

## 검토 질문

1. I2C write 성공 뒤 sensor reset 완료를 별도로 기다려야 하는 이유는 무엇입니까?
2. conversion generation이 없을 때 늦은 data-ready가 어떤 request를 잘못 완료할 수 있습니까?
3. configuration 중간 실패 뒤 rollback과 full reset 중 무엇을 선택할지 기준을 적어 보세요.
4. driver API가 raw register 값을 그대로 반환하지 않고 unit/scale contract를 제공해야 하는 이유는 무엇입니까?
