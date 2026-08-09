# 용어집

이 문서는 가이드에서 반복 사용하는 용어의 **현재 문맥상 의미**를 정리합니다. architecture와 vendor마다 정확한 이름이 다를 수 있으므로 실제 구현에서는 공식 문서를 우선합니다.

## image와 memory

### host

firmware를 편집·build·flash·debug하는 개발 컴퓨터입니다.

### target

firmware가 실행되는 MCU, SoC, emulator 또는 board입니다.

### firmware image

target이 load 또는 execute할 code, initial data와 metadata의 배포 단위입니다. ELF, HEX, binary와 signed image는 서로 다른 artifact입니다.

### ELF

section, segment, symbol, relocation와 debug information을 담을 수 있는 executable/linkable format입니다. programmer가 ELF를 직접 쓰는지 변환한 binary/hex를 쓰는지 구분합니다.

### VMA / LMA

Virtual Memory Address는 실행 중 section이 놓이는 주소, Load Memory Address는 image에서 초기 byte가 저장되는 주소입니다. `.data`는 보통 LMA가 flash, VMA가 RAM입니다.

### vector table

reset과 exception/interrupt가 사용할 entry를 architecture가 정한 형태로 저장한 표입니다.

### startup code

reset entry에서 stack, memory section, runtime와 board/SoC 초기화를 준비해 `main` 또는 kernel entry로 넘기는 code입니다.

### linker script

section을 memory region과 address에 배치하고 startup/application이 사용할 symbol을 만드는 link-time 계약입니다.

### XIP

Execute In Place. code를 RAM으로 모두 복사하지 않고 non-volatile memory에서 직접 fetch하는 방식입니다.

### retention / `.noinit`

특정 startup/reset에서 지우지 않도록 배치한 memory입니다. byte가 남는 것과 record가 valid한 것은 다릅니다.

## hardware와 register

### MMIO

Memory-Mapped I/O. CPU memory access instruction으로 peripheral register를 읽고 쓰는 방식입니다.

### register semantic

register의 단순 bit 값뿐 아니라 read/write가 hardware state에 미치는 의미입니다. read-only, write-one-to-clear, read-to-clear와 self-clearing 등이 있습니다.

### `volatile`

C abstract machine에서 해당 object access를 관찰 가능한 side effect로 취급하도록 하는 qualifier입니다. atomicity, hardware memory barrier, cache coherence와 lock을 자동 보장하지 않습니다.

### reserved bit

문서가 일반 software 사용을 허용하지 않은 bit입니다. read-modify-write로 우연히 값을 바꾸지 않도록 지정된 write rule을 따릅니다.

### peripheral

GPIO, UART, timer, bus controller, ADC, flash controller와 같이 CPU core 외부에서 특정 I/O 기능을 수행하는 hardware block입니다.

### SoC

CPU core, memory, interrupt, clock, bus와 peripheral를 하나의 chip에 통합한 system-on-chip입니다.

### board support

SoC와 board wiring, clock, memory, pin, external device를 RTOS/build system에 연결하는 description와 초기화 code입니다.

## event와 execution context

### interrupt / IRQ

현재 흐름을 중단하고 exception handler를 실행하게 하는 hardware/software 사건입니다. pending, masking, priority와 acknowledgement가 별도 상태입니다.

### ISR

Interrupt Service Routine. interrupt context에서 실행되는 handler입니다. 실행 시간과 허용 API가 제한될 수 있습니다.

### deferred work

ISR가 최소 상태를 확보한 뒤 queue/work item/task로 넘겨 일반 context에서 처리하는 작업입니다.

### interrupt latency

hardware event가 발생한 시점부터 handler가 의미 있는 처리를 시작할 때까지의 시간입니다. masking, higher priority, architecture entry와 clock이 포함될 수 있습니다.

### jitter

주기 또는 latency가 기준값 주변에서 변하는 정도입니다. 평균과 worst observed/max bound를 구분합니다.

### generation/token

동일 resource를 재사용하는 여러 operation/session을 구분하는 식별자입니다. timeout 뒤 늦은 completion이 새 operation을 완료하지 못하게 합니다.

### superloop

하나의 foreground loop가 여러 state machine을 반복 진행하는 bare-metal 구조입니다.

### RTOS task/thread

scheduler가 독립 stack과 execution state를 관리하는 실행 주체입니다.

### priority inversion

높은 priority task가 낮은 priority task가 가진 resource를 기다리고, 중간 priority 작업이 낮은 task를 방해해 blocking이 길어지는 현상입니다.

### critical section

동시에 변경되면 안 되는 state를 보호하는 실행 구간입니다. interrupt masking과 mutex는 비용·context·보장 범위가 다릅니다.

## time와 resource

### monotonic clock

wall-clock 조정과 관계없이 순서와 elapsed time 측정에 사용하는 시계입니다. sleep/reset 동안 연속되는지는 platform contract입니다.

### timeout

operation을 더 기다리지 않기로 하는 정책 시각/기간입니다. timeout 발생이 hardware operation의 실제 종료를 자동 의미하지 않습니다.

### deadline

결과가 완료돼야 하는 시간 계약입니다. period와 같지 않을 수 있습니다.

### WCET

Worst-Case Execution Time. 특정 가정에서 실행 시간의 상한입니다. 몇 번 측정한 최대값과 동일하지 않습니다.

### stack watermark

관찰 기간에 stack이 사용된 최대 깊이를 추정하는 표시입니다. 모든 경로의 worst case를 자동 보장하지 않습니다.

### memory pool

고정 크기 또는 개수의 object/buffer를 미리 확보해 allocation latency와 capacity를 제한하는 구조입니다.

## bus와 DMA

### transaction

bus controller가 수행하는 address, direction, payload와 completion의 한 operation입니다. transaction success와 device operation success는 다릅니다.

### I2C

addressed two-wire serial bus입니다. ACK/NACK, arbitration, clock stretching와 repeated-start 의미는 controller/device 문서를 확인합니다.

### SPI

clocked full-duplex serial interface입니다. chip-select, mode, word size와 device command framing이 별도 계약입니다.

### DMA

CPU 대신 memory와 peripheral 사이 data를 이동하는 controller/engine입니다.

### cache maintenance

CPU cache와 DMA/device가 공유하는 memory의 visibility를 맞추기 위한 clean/flush/invalidate operation입니다. 방향과 architecture API가 중요합니다.

### scatter/gather

여러 buffer 또는 descriptor를 연결해 하나의 DMA operation으로 처리하는 방식입니다.

## persistence와 lifecycle

### erase unit / program unit

flash에서 erase와 program이 허용되는 최소 단위입니다. byte rewrite와 같은 것으로 취급하지 않습니다.

### torn write

power loss나 fault 때문에 write 일부만 반영된 상태입니다.

### commit marker

record/image metadata가 완성됐음을 durable하게 표시하는 field 또는 transition입니다. marker write 자체의 torn state도 고려합니다.

### schema version

persistent payload의 layout/meaning 판본입니다. firmware binary version과 별개입니다.

### watchdog

software progress가 정해진 기간 안에 확인되지 않으면 reset 또는 action을 발생시키는 독립 timer/감시 장치입니다.

### reset cause

power-on, watchdog, software, fault, brownout 등 reset을 유발한 원인 또는 hardware가 제공하는 분류입니다.

### safe state / safe mode

정상 기능을 계속할 수 없을 때 위험한 output을 제한하고 진단·복구만 허용하는 상태입니다. 제품별 정의가 필요합니다.

### bootloader

application image를 선택·검증·배치하고 실행 환경을 넘기는 firmware 단계입니다.

### candidate image

다운로드됐지만 아직 영구 confirmed가 아닌 update image입니다.

### trial image

제한된 시도/기간 동안 실행하며 self-test와 confirmation을 기다리는 image입니다.

### confirmation

trial image를 이후 reset에서도 계속 선택하도록 boot metadata를 durable하게 바꾸는 transition입니다.

### rollback / revert

trial 실패 뒤 이전 confirmed image로 돌아가는 lifecycle입니다. binary bytes만 복구돼도 persistent data가 호환되지 않으면 functional rollback은 실패할 수 있습니다.

## portability와 verification

### Devicetree

hardware topology와 instance property를 tree로 기술하는 description입니다. software feature policy 전체를 의미하지 않습니다.

### binding

`compatible`과 property schema/meaning을 정의해 hardware description과 driver가 합의하는 계약입니다.

### Kconfig

build할 software feature, dependency와 compile-time policy를 선택하는 configuration system입니다.

### device model

driver instance, initialization dependency와 runtime readiness를 공통 object/API로 연결하는 RTOS 구조입니다.

### fake / mock / stub

fake는 작은 실제 state를 가진 대체 구현, mock은 interaction expectation 검사, stub은 고정 response를 제공하는 test double입니다.

### simulator

대상 system의 선택된 상태와 사건을 software model로 실행합니다. 모델에 없는 hardware behavior는 증명하지 않습니다.

### emulator

target ISA와 board/peripheral 일부를 실행 가능한 형태로 흉내 냅니다. 실제 electrical/timing behavior와 같다고 가정하지 않습니다.

### HIL

Hardware-in-the-Loop. 실제 target board와 sensor, power, network 또는 actuator fixture를 자동 test에 연결합니다.

### build ID

현장 evidence를 exact source/configuration/toolchain/ELF와 연결하는 안정된 image 식별자입니다.

### invariant

정상·실패·복구 중에도 항상 유지돼야 하는 상태 조건입니다.
