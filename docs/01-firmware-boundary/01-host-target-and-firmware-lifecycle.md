# host, target과 펌웨어 수명주기

일반 애플리케이션은 운영체제가 만든 process 안에서 시작하고 종료합니다. MCU firmware는 전원이 들어오거나 reset이 해제된 순간부터 CPU, memory, clock과 peripheral 초기 상태를 직접 받아 실행합니다. 같은 C 코드라도 **누가 실행 환경을 만들고 실패 뒤 무엇이 남는지**가 다릅니다.

## 학습 목표

- host와 target의 역할을 구분합니다.
- board, SoC, CPU core, peripheral, driver와 application의 경계를 설명합니다.
- power-on, reset, boot, run, sleep, fault와 update를 하나의 수명주기로 추적합니다.
- simulator에서 관찰한 상태와 실제 silicon이 보장하는 상태를 구분합니다.

## 선행 개념

C 프로그램의 compile·link·run 흐름과 CPU가 instruction을 fetch하고 exception을 처리한다는 기본 개념이 필요합니다.

## host와 target은 서로 다른 실행 주체입니다

```text
host
- editor와 build tool 실행
- cross compiler·linker 실행
- debugger·flash tool 제어
- test report와 artifact 보관

       firmware image 전송
                ↓

target
- reset vector에서 시작
- target ISA instruction 실행
- on-chip flash·RAM 사용
- peripheral와 interrupt 처리
- 전원·clock·reset 상태의 영향을 받음
```

host compiler로 만든 실행 파일이 target에서 실행되지 않을 수 있습니다. target ISA, ABI, calling convention, endianness, object format과 memory map이 일치해야 합니다. 반대로 `native_sim`처럼 target application logic을 host executable로 만드는 환경은 실제 MCU가 아니라 **host ABI 위의 시험 프로필**입니다.

## board, SoC와 CPU를 구분합니다

```text
board
├── SoC 또는 MCU
│   ├── CPU core
│   ├── interrupt controller
│   ├── clock·reset controller
│   ├── SRAM·flash controller
│   └── UART·GPIO·I2C·SPI·DMA 같은 peripheral
├── external sensor·flash·radio
├── regulator·oscillator
└── connector·button·LED
```

- **CPU core**는 ISA와 exception 실행 계약을 제공합니다.
- **SoC/MCU**는 core에 memory, interrupt, clock, DMA와 peripheral을 결합합니다.
- **board**는 특정 pin 연결, 외부 장치, oscillator와 전원 구성을 고정합니다.
- **application**은 제품 기능과 정책을 소유합니다.
- **driver**는 hardware operation을 안정된 software contract로 바꿉니다.

같은 MCU를 사용해도 board의 oscillator, pin, external flash와 sensor가 다르면 firmware configuration이 달라집니다. board 이름을 SoC 이름처럼 사용하면 driver와 board support의 책임이 섞입니다.

## firmware는 reset을 기준으로 다시 시작합니다

대표적인 상태는 다음과 같습니다.

```text
POWER_OFF
  ↓ power applied
RESET_ASSERTED
  ↓ reset released
BOOT_EARLY
  ↓ startup·clock·memory init
APPLICATION_INIT
  ↓ dependencies ready
RUNNING
  ├─ interrupt·event
  ├─ SLEEP → WAKEUP
  ├─ FAULT → RESET_ASSERTED
  └─ UPDATE_PENDING → BOOT_EARLY
```

각 reset이 같은 초기 상태를 보장한다고 가정하면 안 됩니다.

- power-on reset은 전원 domain 전체를 초기화할 수 있습니다.
- watchdog reset은 일부 peripheral이나 retention memory를 남길 수 있습니다.
- software reset은 debug state, clock 또는 external device를 초기화하지 않을 수 있습니다.
- wakeup은 reset이 아니라 이전 RAM과 execution context를 계속 사용할 수 있습니다.

정확한 보장은 SoC reference manual과 board 회로를 확인합니다.

## firmware에는 process 경계가 없을 수 있습니다

작은 MCU에서는 다음이 흔합니다.

- 하나의 flat physical address space
- process별 virtual memory 없음
- application과 driver가 같은 privilege로 실행
- global/static object가 전체 수명 동안 유지
- crash가 process 종료가 아니라 system reset으로 이어짐
- stdout·filesystem·wall clock이 존재하지 않거나 선택 기능임

따라서 잘못된 pointer write 하나가 다른 모듈뿐 아니라 vector table, driver state나 persistent buffer를 손상시킬 수 있습니다. RTOS가 task를 제공해도 process isolation을 자동으로 제공하지 않습니다. MPU와 privilege partition이 있다면 그 설정과 보장 범위를 별도로 확인합니다.

## external hardware도 독립된 상태를 가집니다

MCU가 reset돼도 external sensor, flash, modem 또는 power controller가 같은 시점에 reset되지 않을 수 있습니다.

```text
MCU reset
├── internal UART controller: reset됨
├── GPIO output latch: SoC 규칙에 따라 변함
└── external sensor: 계속 measurement 중일 수 있음
```

application 초기화는 “항상 power-on default에서 시작한다”가 아니라 다음 중 하나를 선택해야 합니다.

1. external device를 명시적으로 reset합니다.
2. 현재 상태를 읽어 원하는 상태로 수렴시킵니다.
3. 이전 operation의 completion 또는 timeout을 처리합니다.
4. 상태를 알 수 없으면 safe state로 이동합니다.

## 상태 소유권을 표로 고정합니다

| 상태 | 소유자 | 바꾸는 사건 | 관찰 근거 |
|---|---|---|---|
| reset cause | reset controller | power, watchdog, software reset | hardware flag, retained record |
| clock source | clock controller/board | startup, power transition | register, measured frequency |
| pin function | pin controller/board description | init, sleep, wake | register, logic analyzer |
| device operation | peripheral + external device | command, interrupt, timeout | status register, bus trace |
| application mode | application state machine | event, fault, update | retained log, state output |
| firmware image | bootloader/flash layout | install, confirm, revert | slot metadata, image hash |

소유자가 둘 이상이면 transition protocol이 필요합니다. 예를 들어 DMA buffer는 CPU가 채우는 동안 CPU 소유이고 transfer 시작 뒤 DMA 소유가 됩니다.

## 구현 프로필을 먼저 기록합니다

새 firmware 저장소를 열면 다음을 적습니다.

```text
host OS:
build system:
toolchain:
target architecture/ABI:
board:
SoC:
CPU core:
RTOS 또는 bare metal:
flash 방법:
debug transport:
console/log transport:
reset 종류:
```

이 정보 없이 “빌드됐다”, “reset했다”, “timer가 정확하다”라는 문장은 재현하기 어렵습니다.

## 실패를 분류합니다

### build 성공, target 실행 실패

- 잘못된 board 또는 ABI
- image load address 불일치
- startup/vector table 누락
- clock 또는 memory controller 초기화 실패
- external oscillator나 power 조건 불일치

### simulator 성공, board 실패

- simulator가 모델링하지 않은 peripheral semantic
- alignment·cache·DMA 문제
- 실제 interrupt priority와 latency
- pin, voltage, pull-up과 bus wiring
- flash erase/write와 power loss

### reset 뒤 간헐 실패

- external device가 reset되지 않음
- retained state를 초기화하지 않음
- reset cause에 따른 recovery path 누락
- bootloader와 application의 memory 계약 충돌

## 직접 수행할 조사

아무 firmware 저장소 하나를 선택하고 다음 파일을 찾습니다.

1. board 또는 target 선택 지점
2. linker script 또는 memory region 정의
3. reset/startup 또는 vector table
4. application entry point
5. clock·pin 초기화
6. console 또는 logging backend
7. flash·debug 명령
8. build artifact 위치

찾지 못한 항목은 “없음”이라고 추측하지 말고 build system이 생성하는지, SDK가 소유하는지 기록합니다.

## 직접 확인할 문제

1. watchdog reset 뒤 external sensor가 계속 이전 conversion을 수행한다면 init은 어떤 상태를 처리해야 합니까?
2. `native_sim`에서 통과한 pointer-size test가 32-bit MCU에서 실패할 수 있는 이유를 설명해 보세요.
3. board와 SoC를 같은 이름으로 취급하면 pin·clock·external device 변경에서 어떤 책임 문제가 생깁니까?
4. RTOS task가 여러 개 있어도 process isolation이라고 부를 수 없는 이유를 적어 보세요.

## 이 장이 보장하지 않는 것

특정 MCU의 reset sequence, voltage, clock 안정화 시간과 pin default는 설명하지 않습니다. 실제 구현에서는 사용하는 silicon revision의 datasheet, reference manual, errata와 board schematic을 확인해야 합니다.
