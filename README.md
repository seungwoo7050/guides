# 임베디드 시스템 가이드

이 저장소는 C, 컴퓨터 구조와 운영체제의 기본 상태 모델을 익힌 개발자가 **펌웨어 애플리케이션, 장치 드라이버, RTOS 기반 시스템과 보드 지원 코드**에 처음 합류할 수 있도록 안내합니다.

목표는 특정 MCU의 레지스터 이름이나 한 제조사의 SDK를 외우는 것이 아닙니다. 다음 경계를 반복해서 추적하는 능력을 만듭니다.

```text
전원·reset
→ startup과 memory image
→ peripheral register와 driver
→ interrupt·timer·DMA
→ foreground 또는 RTOS task
→ flash·watchdog·power state
→ update·rollback
→ 관측·시험·현장 복구
```

각 장은 다음 질문을 중심으로 구성합니다.

- 누가 상태를 소유합니까?
- 어떤 하드웨어 사건이 상태를 바꿉니까?
- CPU, peripheral, DMA와 interrupt context 사이에서 버퍼와 실행 권한은 언제 이동합니까?
- deadline, memory와 energy budget은 어디에서 소비됩니까?
- reset이나 전원 손실 뒤에도 무엇이 참이어야 합니까?
- simulator, debugger, trace와 실제 보드가 각각 무엇을 증명합니까?

## 준비와 전체 검증

문서와 작은 상태 모델을 확인하는 기본 경로에는 embedded toolchain이나 실제 보드가 필요하지 않습니다.

```sh
./prepare.sh
./verify.sh
```

`prepare.sh`는 Python과 기본 도구를 확인하고 source fingerprint를 `.guide/embedded-systems/prepared.json`에 기록합니다. `verify.sh`는 marker가 현재 source와 일치하는지 확인한 뒤 저장소 밖 임시 복사본에서 다음을 검사합니다.

- 계획된 문서·실습·reference 구조
- Markdown 내부 링크
- 문서에서 참조하는 로컬 경로
- interrupt event와 update rollback 상태 모델
- 준비·검증 중 source 비변경

Zephyr, QEMU, cross compiler와 실제 보드는 선택 구현 프로필입니다. 설치되지 않았다는 이유로 문서 가이드 자체의 검증이 실패하지 않습니다.

## 시작 위치

전체 학습 경로와 선택 경로는 [학습 로드맵](docs/00-roadmap.md)에서 확인합니다.

### Part 1. 펌웨어 경계와 image

| 장 | 문서 | 중심 질문 |
|---:|---|---|
| 01 | [host, target과 펌웨어 수명주기](docs/01-firmware-boundary/01-host-target-and-firmware-lifecycle.md) | 운영체제 프로세스와 다른 펌웨어의 실행 경계는 무엇입니까? |
| 02 | [cross build, ELF와 memory budget](docs/01-firmware-boundary/02-cross-build-elf-map-and-memory-budget.md) | source가 target image가 되는 동안 어떤 artifact와 주소가 만들어집니까? |
| 03 | [reset, startup과 linker 계약](docs/01-firmware-boundary/03-reset-startup-and-linker-contract.md) | reset vector에서 `main`까지 누가 메모리와 runtime을 준비합니까? |
| 04 | [MMIO와 register 의미](docs/01-firmware-boundary/04-mmio-registers-and-volatile.md) | register read/write가 일반 메모리 접근과 다른 이유는 무엇입니까? |

### Part 2. peripheral, interrupt와 driver

| 장 | 문서 | 중심 질문 |
|---:|---|---|
| 05 | [GPIO, UART, timer와 driver 경계](docs/02-events-and-drivers/05-gpio-uart-timers-and-driver-boundaries.md) | application, driver와 hardware의 책임은 어디에서 나뉩니까? |
| 06 | [interrupt, priority와 deferred work](docs/02-events-and-drivers/06-interrupts-priority-and-deferred-work.md) | ISR에서 무엇을 끝내고 무엇을 다른 context로 넘겨야 합니까? |
| 07 | [I2C·SPI transaction과 device state](docs/02-events-and-drivers/07-i2c-spi-transactions-and-device-state.md) | bus transfer 성공과 장치 operation 성공을 어떻게 구분합니까? |
| 08 | [DMA, cache와 buffer ownership](docs/02-events-and-drivers/08-dma-cache-and-buffer-ownership.md) | CPU와 DMA가 같은 buffer를 사용할 때 소유권과 가시성을 어떻게 보존합니까? |

### Part 3. 시간, event loop와 RTOS

| 장 | 문서 | 중심 질문 |
|---:|---|---|
| 09 | [clock, timeout, deadline과 wraparound](docs/03-time-and-concurrency/09-clocks-timeouts-deadlines-and-wraparound.md) | time source와 deadline 주장을 어떤 단위와 오차로 검증합니까? |
| 10 | [superloop, 상태 기계와 event queue](docs/03-time-and-concurrency/10-superloop-state-machines-and-event-queues.md) | thread 없이도 여러 기능의 진행과 backpressure를 어떻게 다룹니까? |
| 11 | [RTOS task, queue와 priority inversion](docs/03-time-and-concurrency/11-rtos-tasks-queues-and-priority-inversion.md) | task를 늘리면서도 진행, 응답성과 종료를 어떻게 보존합니까? |
| 12 | [memory budget, stack과 allocation](docs/03-time-and-concurrency/12-memory-budgets-stacks-and-allocation.md) | 제한된 RAM·flash에서 최악의 자원 사용을 어떻게 설명합니까? |

### Part 4. 신뢰성, power와 update

| 장 | 문서 | 중심 질문 |
|---:|---|---|
| 13 | [reset cause, watchdog와 fault recovery](docs/04-reliability-and-lifecycle/13-reset-cause-watchdog-and-fault-recovery.md) | 멈춤을 reset으로 바꾸는 것에서 끝나지 않고 원인과 복구를 어떻게 남깁니까? |
| 14 | [power, clock, sleep와 wakeup](docs/04-reliability-and-lifecycle/14-power-clocks-sleep-and-wakeup.md) | 저전력 상태 전후의 장치·시간·pin 계약을 어떻게 복원합니까? |
| 15 | [flash persistence와 power loss](docs/04-reliability-and-lifecycle/15-flash-persistence-and-power-loss.md) | erase/write 중 전원이 끊겨도 마지막 유효 상태를 어떻게 찾습니까? |
| 16 | [boot image, update와 rollback](docs/04-reliability-and-lifecycle/16-boot-images-update-and-rollback.md) | 새 image를 시험하고 확인하거나 되돌리는 상태 기계는 무엇입니까? |

### Part 5. portability, 검증과 기여

| 장 | 문서 | 중심 질문 |
|---:|---|---|
| 17 | [Devicetree, Kconfig와 device model](docs/05-portability-and-verification/17-devicetree-kconfig-and-device-model.md) | hardware description과 software 선택을 분리해 driver를 어떻게 연결합니까? |
| 18 | [debugging, tracing과 crash evidence](docs/05-portability-and-verification/18-debugging-tracing-and-crash-evidence.md) | debugger가 없는 현장에서도 원인을 좁힐 근거를 어떻게 남깁니까? |
| 19 | [simulation, unit, integration과 HIL](docs/05-portability-and-verification/19-simulation-unit-integration-and-hil.md) | host test, emulator와 실제 보드가 각각 어떤 실패를 찾습니까? |
| 20 | [upstream 기여와 production 경계](docs/05-portability-and-verification/20-upstream-contribution-and-production-boundaries.md) | 가이드 이후 실제 RTOS·driver·board 저장소에 어떻게 합류합니까? |

## 실습과 capstone

이 브랜치는 문서가 중심입니다. 실습은 대규모 정답 구현보다 **문제·입력·상태·실패·검증 계약**을 고정합니다.

- [실습 전체 안내](exercises/README.md)
- [firmware image와 memory audit](exercises/01-image-and-memory-audit/README.md)
- [interrupt event 경로](exercises/02-interrupt-event-path/README.md)
- [sensor driver 상태 기계](exercises/03-sensor-driver-state-machine/README.md)
- [deadline과 priority 검토](exercises/04-deadline-and-priority-review/README.md)
- [power-loss-safe persistence](exercises/05-power-loss-persistence/README.md)
- [update와 rollback 모델](exercises/06-update-rollback-model/README.md)
- [현장 센서 노드 capstone](capstone/field-sensor-node/README.md)

`examples/`에는 hardware 없이 실행할 수 있는 두 개의 작은 상태 모델만 제공합니다. 모델은 실제 interrupt controller, flash나 bootloader를 대체하지 않습니다. 문서의 상태 전이를 결정적으로 관찰하기 위한 도구입니다.

## 기준 구현 프로필

핵심 개념은 특정 RTOS에 종속되지 않습니다. 선택 구현 프로필은 다음과 같습니다.

- Zephyr 4.4.0 stable과 C17
- Zephyr SDK 1.0.1
- host application 검증용 `native_sim`
- Cortex-M interrupt·memory map 관찰용 QEMU board
- 실제 보드 한 개는 선택 사항

정확한 기준과 업데이트 원칙은 [버전 기준](reference/version-baseline.md)을 확인합니다.

## 선행지식

필수:

- `c` 브랜치의 C 언어·메모리·API·빌드 영역
- `computer-architecture` 브랜치의 데이터 표현, ISA, 주소와 memory hierarchy 기본 개념
- `operating-systems` 브랜치의 interrupt, scheduling, synchronization와 device I/O 상태 모델

권장:

- `cybersecurity`의 위협 모델과 key·identity 경계는 secure boot와 provisioning을 확장할 때 필요합니다.

`git`은 embedded 업무 트랙의 공통 기반이고, `unix-systems`의 process·file·serial 관찰 능력은 선택적 host 도구 배경입니다. 둘을 이 브랜치의 직접 필수·권장 계약과 혼동하지 않습니다.

## 카탈로그와 트랙 위치

이 브랜치는 `specialization`이며 embedded 트랙의 기본 경로는 다음과 같습니다.

```text
git → c → computer-architecture → operating-systems → embedded-systems
```

`systems-programming`, `cybersecurity`, `game-engine-core` 트랙에서는 핵심 경로 뒤의 `advanced` 선택지입니다. 카탈로그의 `connects`와 `continues_to`는 비어 있으므로 내부 후속 브랜치를 임의로 약속하지 않습니다. 완료 뒤에는 실제 Zephyr·vendor SDK의 application, driver, board와 test issue로 이동합니다.

이 브랜치에서는 C pointer, object lifetime, compiler/linker의 일반 개념과 CPU interrupt 원리를 처음부터 다시 가르치지 않습니다. 펌웨어에서 달라지는 적용 경계만 설명합니다.

## 완료 후 가능한 일

전체 과정을 마치면 다음을 수행할 수 있어야 합니다.

- 낯선 firmware 저장소에서 board·SoC·driver·application·build configuration 경계를 찾습니다.
- ELF, map과 linker script에서 code, data, stack, heap, vector table과 flash partition을 추적합니다.
- register의 access semantic을 datasheet에서 읽고 안전한 driver API로 감쌉니다.
- ISR, deferred work와 task 사이의 event·buffer ownership을 설명합니다.
- I2C·SPI·DMA 실패를 bus, controller, device와 application 상태로 분리합니다.
- deadline·jitter·stack·heap·flash·energy budget의 측정 조건과 비보장 범위를 기록합니다.
- watchdog, reset cause, crash record와 safe state를 하나의 복구 경로로 연결합니다.
- power loss 중에도 유효한 persistent record와 firmware rollback 상태를 설계합니다.
- host unit test, simulator, emulator와 실제 보드 검증을 목적에 맞게 나눕니다.
- 작은 application, driver, board support 또는 test 변경을 upstream 프로젝트에 제출합니다.

## 의도적으로 다루지 않는 것

- 일반 POSIX 애플리케이션과 C 언어 입문의 반복
- 전자회로 설계 전체
- 모바일 앱
- 특정 보드 제품 매뉴얼 전체
- CPU pipeline, cache와 ISA의 전체 설명
- PCB signal integrity, RF와 EMC 설계
- FPGA·HDL
- Linux kernel driver와 일반-purpose OS porting
- Bluetooth, Wi-Fi, TCP/IP stack 전체
- 기능 안전 인증, 의료·자동차·항공 규격 준수 절차
- cryptographic primitive 구현, key provisioning과 공격적 보안
- 특정 vendor SDK와 한 MCU family의 register 목록 암기

이러한 범위가 필요해지면 현재 문서에서 책임 경계를 확인한 뒤 해당 전문 프로젝트와 공식 자료로 확장합니다.
