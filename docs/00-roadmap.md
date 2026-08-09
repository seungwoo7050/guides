# 학습 로드맵과 범위 계약

이 문서는 임베디드 시스템 가이드의 대상 독자, 선행지식, 기본 읽기 순서, 선택 경로, 실습과 완료 기준을 고정합니다. 각 장을 peripheral 용어집처럼 읽지 않고 다음 하나의 수명주기로 연결합니다.

```text
reset
→ image와 memory 초기화
→ hardware configuration
→ event와 interrupt
→ scheduling과 resource budget
→ persistence·power·watchdog
→ update·rollback
→ field evidence와 contribution
```

## 대상 독자

- C로 다중 파일 프로그램과 작은 library를 작성해 본 개발자
- MCU 예제의 LED·UART 출력은 실행했지만 startup, linker, interrupt와 RTOS 경계를 체계적으로 설명하기 어려운 개발자
- vendor SDK의 application 또는 driver 저장소에 합류하려는 개발자
- Zephyr 같은 RTOS의 application, driver, board, test에 첫 기여를 준비하는 개발자
- simulator와 실제 보드 결과를 구분하며 firmware failure를 재현하려는 개발자

전자회로를 처음 설계하거나 특정 산업 규격 인증을 수행하는 과정은 아닙니다.

## 선행지식

### 필수

`c` 브랜치에서 다음을 수행할 수 있어야 합니다.

- pointer, object lifetime과 memory ownership을 추적합니다.
- header, translation unit, static library와 linker의 기본 역할을 설명합니다.
- 오류 반환과 부분 성공 뒤 상태를 API 계약으로 정합니다.
- Makefile과 compiler warning으로 다중 파일 프로그램을 검증합니다.

`computer-architecture` 브랜치에서 다음 개념을 알아야 합니다.

- bit width, signed/unsigned 표현과 endianness
- ISA, register, load/store와 exception
- virtual/physical address를 구분하는 이유
- cache line, memory hierarchy와 memory ordering이 존재한다는 사실

`operating-systems` 브랜치에서 다음 상태 모델을 설명할 수 있어야 합니다.

- interrupt와 deferred completion
- scheduling, blocking, wakeup과 synchronization
- device request, DMA completion과 resource lifetime

실제 assembly 작성, kernel 구현과 RTOS 사용 경험은 필수 조건이 아닙니다.

### 권장

- `cybersecurity`: secure boot, provisioning과 debug access의 위협 모델을 확장할 때

`git`은 embedded 트랙 전체의 공통 기반입니다. `unix-systems`의 serial device, process, file permission와 debugger 사용 경험은 선택적 host 도구 배경이며 카탈로그의 직접 `requires`나 `recommends`는 아닙니다.

## 카탈로그 계약과 트랙

- 종류: `specialization`
- 직접 필수: `c`, `computer-architecture`, `operating-systems`
- 권장 인접 기반: `cybersecurity`
- `connects`, `continues_to`: 없음

embedded 트랙의 기본 선형 경로는 `git → c → computer-architecture → operating-systems → embedded-systems`입니다. `systems-programming`, `cybersecurity`, `game-engine-core` 트랙에서는 핵심 경로 뒤의 `advanced` 선택지이며 그 트랙들의 선형 진입 경로에는 포함되지 않습니다.

## 완료 후 할 수 있어야 하는 일

1. host와 target, board·SoC·CPU·peripheral·driver·application 경계를 구분합니다.
2. ELF, map, symbol과 linker script를 이용해 image가 flash와 RAM에 배치되는 과정을 추적합니다.
3. reset vector에서 startup, `.data`, `.bss`, clock, runtime과 `main`까지의 상태를 설명합니다.
4. register access semantic과 reserved bit를 datasheet에서 읽고 안전한 MMIO 연산을 설계합니다.
5. ISR에서 완료할 최소 작업과 thread·event loop로 넘길 작업을 구분합니다.
6. I2C·SPI·DMA transaction의 controller, device, buffer와 completion 상태를 분리합니다.
7. monotonic time, duration, timeout, deadline, latency와 jitter를 같은 단위로 섞지 않습니다.
8. superloop 또는 RTOS에서 queue overflow, priority inversion, deadlock과 shutdown을 검증합니다.
9. flash·RAM·stack·heap·buffer·energy budget을 숫자와 측정 조건으로 기록합니다.
10. reset, watchdog, crash record, safe state와 boot-loop 방지를 하나의 recovery path로 연결합니다.
11. power loss 중 persistent state와 firmware update 상태가 유효한 이전 상태로 복구되도록 설계합니다.
12. host test, `native_sim`, QEMU, fake driver, HIL과 실제 보드의 증명 범위를 구분합니다.
13. 실제 RTOS·vendor SDK 저장소에서 작은 application, driver, board 또는 test 변경을 제출합니다.

## 다섯 Part의 역할

### Part 1. 펌웨어 경계와 image

운영체제 프로세스가 없는 target에서 어떤 image가 어디에 놓이고, reset 뒤 어떤 코드가 runtime을 준비하는지 추적합니다.

- [01 host, target과 펌웨어 수명주기](01-firmware-boundary/01-host-target-and-firmware-lifecycle.md)
- [02 cross build, ELF와 memory budget](01-firmware-boundary/02-cross-build-elf-map-and-memory-budget.md)
- [03 reset, startup과 linker 계약](01-firmware-boundary/03-reset-startup-and-linker-contract.md)
- [04 MMIO와 register 의미](01-firmware-boundary/04-mmio-registers-and-volatile.md)

### Part 2. peripheral, interrupt와 driver

CPU와 peripheral이 비동기적으로 상태를 바꿀 때 API, ISR, bus와 DMA 사이의 소유권을 정합니다.

- [05 GPIO, UART, timer와 driver 경계](02-events-and-drivers/05-gpio-uart-timers-and-driver-boundaries.md)
- [06 interrupt, priority와 deferred work](02-events-and-drivers/06-interrupts-priority-and-deferred-work.md)
- [07 I2C·SPI transaction과 device state](02-events-and-drivers/07-i2c-spi-transactions-and-device-state.md)
- [08 DMA, cache와 buffer ownership](02-events-and-drivers/08-dma-cache-and-buffer-ownership.md)

### Part 3. 시간, event loop와 RTOS

하나의 CPU와 제한된 memory에서 여러 기능의 진행과 응답 시간을 관리합니다.

- [09 clock, timeout, deadline과 wraparound](03-time-and-concurrency/09-clocks-timeouts-deadlines-and-wraparound.md)
- [10 superloop, 상태 기계와 event queue](03-time-and-concurrency/10-superloop-state-machines-and-event-queues.md)
- [11 RTOS task, queue와 priority inversion](03-time-and-concurrency/11-rtos-tasks-queues-and-priority-inversion.md)
- [12 memory budget, stack과 allocation](03-time-and-concurrency/12-memory-budgets-stacks-and-allocation.md)

### Part 4. 신뢰성, power와 update

reset과 전원 손실을 예외가 아니라 설계 입력으로 취급합니다.

- [13 reset cause, watchdog와 fault recovery](04-reliability-and-lifecycle/13-reset-cause-watchdog-and-fault-recovery.md)
- [14 power, clock, sleep와 wakeup](04-reliability-and-lifecycle/14-power-clocks-sleep-and-wakeup.md)
- [15 flash persistence와 power loss](04-reliability-and-lifecycle/15-flash-persistence-and-power-loss.md)
- [16 boot image, update와 rollback](04-reliability-and-lifecycle/16-boot-images-update-and-rollback.md)

### Part 5. portability, 검증과 기여

한 board에서 동작한 코드를 hardware description, driver model과 계층별 시험으로 일반화하고 실제 프로젝트에 제출합니다.

- [17 Devicetree, Kconfig와 device model](05-portability-and-verification/17-devicetree-kconfig-and-device-model.md)
- [18 debugging, tracing과 crash evidence](05-portability-and-verification/18-debugging-tracing-and-crash-evidence.md)
- [19 simulation, unit, integration과 HIL](05-portability-and-verification/19-simulation-unit-integration-and-hil.md)
- [20 upstream 기여와 production 경계](05-portability-and-verification/20-upstream-contribution-and-production-boundaries.md)

## 기본 읽기 순서

처음 학습할 때는 `01 → 20` 순서로 진행합니다. 각 Part의 문서는 앞 장의 상태를 입력으로 사용합니다.

```text
01 → 02 → 03 → 04
                  ↓
05 → 06 → 07 → 08
                  ↓
09 → 10 → 11 → 12
                  ↓
13 → 14 → 15 → 16
                  ↓
17 → 18 → 19 → 20
```

## 목적별 선택 경로

| 목적 | 권장 경로 |
|---|---|
| firmware application 기여 | 01 → 02 → 03 → 05 → 06 → 09 → 10 → 11 → 12 → 13 → 18 → 19 → 20 |
| peripheral driver 기여 | 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 17 → 18 → 19 → 20 |
| RTOS application 설계 | 01 → 02 → 06 → 09 → 10 → 11 → 12 → 13 → 14 → 18 → 19 |
| board bring-up | 01 → 02 → 03 → 04 → 05 → 06 → 13 → 17 → 18 → 19 → 20 |
| persistent storage와 update | 01 → 02 → 03 → 12 → 13 → 15 → 16 → 18 → 19 |
| 저전력 sensor node | 05 → 06 → 07 → 09 → 10 → 12 → 13 → 14 → 15 → 19 |

선택 경로는 빠진 개념을 이미 이해한다는 전제입니다. state transition을 설명하기 어렵다면 앞 장으로 돌아갑니다.

## 문서와 실습의 대응

| 문서 범위 | 설계 실습 | 핵심 결과 |
|---|---|---|
| 01~03 | [image와 memory audit](../exercises/01-image-and-memory-audit/README.md) | ELF·map·reset path 조사 보고서 |
| 04~06 | [interrupt event 경로](../exercises/02-interrupt-event-path/README.md) | ISR·queue·worker 상태와 overflow 검증 |
| 05~08 | [sensor driver 상태 기계](../exercises/03-sensor-driver-state-machine/README.md) | bus와 device failure를 분리한 driver contract |
| 09~12 | [deadline과 priority 검토](../exercises/04-deadline-and-priority-review/README.md) | task·queue·stack·latency budget |
| 13~15 | [power-loss-safe persistence](../exercises/05-power-loss-persistence/README.md) | cut-point마다 마지막 유효 record 복구 |
| 13~16 | [update와 rollback 모델](../exercises/06-update-rollback-model/README.md) | trial·confirm·revert 상태 기계 |
| 전체 | [현장 센서 노드 capstone](../capstone/field-sensor-node/README.md) | acquisition·storage·power·recovery·verification 통합 |

각 실습은 실행 가능한 starter, 하나의 비교 reference, 정상·경계·실패 fixture와 공개 행동 checker를 제공합니다. reference는 유일한 설계를 뜻하지 않습니다. 선택적으로 Zephyr나 vendor SDK로 옮기되 framework API가 상태 설명을 대신하지 않습니다.

## 구현 프로필

### 문서·상태 모델 경로

필수 환경:

- Python 3.10 이상
- POSIX 호환 `sh`
- `make`

`./verify.sh`는 hardware, Zephyr workspace나 cross toolchain을 요구하지 않습니다.

### Zephyr 경로

2026-08 기준 권장 기준선:

- Zephyr 4.4.0 stable
- Zephyr SDK 1.0.1
- Python 3.12 이상
- C17
- application logic: `native_sim`
- Cortex-M exception·memory map: QEMU가 지원되는 MPS2 계열 target
- 실제 peripheral·power·electrical 검증: 선택한 physical board

프로젝트가 LTS를 요구하면 Zephyr 3.7 LTS를 선택할 수 있습니다. 명령과 API는 사용하는 release의 문서를 확인합니다.

## 다른 가이드와의 경계

### `c`

C syntax, pointer, memory ownership, build와 test의 일반 원리는 `c`가 소유합니다. 이 가이드는 target image, linker section, MMIO, ISR와 제한 자원에 적용합니다.

### `computer-architecture`

ISA, exception, cache, memory ordering과 address translation의 구조적 원리는 `computer-architecture`가 소유합니다. 이 가이드는 실제 peripheral register, vector table, DMA와 firmware memory layout에 적용합니다.

### `operating-systems`

scheduling, semaphore, wait queue, page cache와 device completion의 일반 상태 모델은 `operating-systems`가 소유합니다. 이 가이드는 MMU가 없거나 제한된 MCU, RTOS API, static resource와 deadline에 맞게 적용합니다.

### `cybersecurity`

이 가이드는 boot slot, image lifecycle와 rollback의 상태 계약을 소유합니다. image authenticity, key provisioning, debug authorization, threat model과 anti-rollback security policy의 심화는 `cybersecurity`가 소유합니다.

### 명시적인 비소유 범위

- 일반 POSIX 애플리케이션
- 전자회로 설계 전체
- 모바일 앱
- 특정 보드 제품 매뉴얼 전체

필요한 접점은 현재 펌웨어의 상태·자원·실패 모델에 적용되는 만큼만 설명하고 소유 브랜치 또는 공식 제품 문서로 연결합니다.

## 검증의 한계

- host 상태 모델은 interrupt latency, peripheral timing과 electrical behavior를 증명하지 않습니다.
- QEMU나 `native_sim` 통과는 실제 cache, DMA, flash endurance, power draw와 wakeup timing을 증명하지 않습니다.
- 한 보드의 HIL 시험은 다른 silicon revision, clock tree와 온도·전압 범위를 보장하지 않습니다.
- 평균 실행 시간은 worst-case execution time이 아닙니다.
- watchdog reset 성공은 오류 원인 보존과 안전한 복구를 자동으로 보장하지 않습니다.
- cryptographic signature 검증 성공은 전체 update supply chain의 안전을 증명하지 않습니다.

## 완료 기준

- `./prepare.sh` 뒤 `./verify.sh`가 성공합니다.
- 6개 실습의 필수 host 설계·상태 모델과 정상·경계·실패 fixture를 모두 완료합니다.
- capstone의 [acceptance criteria](../capstone/field-sensor-node/acceptance.md)에 열거된 12개 필수 시나리오를 결정적으로 재현합니다.
- Zephyr, QEMU 또는 실제 보드에서는 한 개의 end-to-end slice를 선택할 수 있지만 host 모델 완료를 대신하지 않으며 hardware profile 자체는 브랜치 필수 조건이 아닙니다.
- simulator와 실제 board의 관찰 결과를 같은 보장으로 표현하지 않습니다.
- 낯선 firmware 저장소에서 작은 issue를 재현하고 test·문서·코드 변경 중 하나를 리뷰 가능한 형태로 제시합니다.
