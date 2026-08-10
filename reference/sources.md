# 공식 자료

이 가이드는 교육용 상태 모델과 실제 architecture·RTOS·SoC 보장을 구분합니다. 실제 프로젝트를 수정할 때는 아래 공식 자료와 사용하는 chip/board의 datasheet, reference manual, errata를 우선합니다.

확인 기준일: **2026-08-10**

## 기준 version의 공식 근거

| 이 가이드의 선택 profile | 공식 근거와 판단 |
|---|---|
| Zephyr 4.4.0 | [Zephyr Releases](https://docs.zephyrproject.org/latest/releases/index.html)가 4.4.0을 2026-04-14 release로 열거하고 [4.4 release notes](https://docs.zephyrproject.org/latest/releases/release-notes-4.4.html)가 해당 release의 변경을 기록합니다. 이 가이드는 확인일의 재현 기준으로 4.4.0을 고정하며 “항상 최신”을 주장하지 않습니다. |
| Python 3.12 이상 | 공식 [4.4 migration guide](https://docs.zephyrproject.org/latest/releases/migration-guide-4.4.html)가 Zephyr 4.3에서 4.4로 이동할 때 최소 Python이 3.10에서 3.12로 바뀌었다고 명시합니다. 이 조건은 선택 Zephyr profile에만 적용합니다. 6개 host 실습과 capstone checker의 별도 최소 계약은 Python 3.10 이상입니다. |
| C17 | 같은 migration guide가 Zephyr 4.4의 기본 C standard가 C17로 바뀌었음을 기록합니다. 일반 C 학습 범위나 모든 vendor toolchain이 C17이라는 뜻은 아닙니다. |
| Zephyr SDK 1.0.1 | migration guide의 4.4 최소 SDK는 1.0.0이고, 공식 [Zephyr SDK 설치 문서](https://docs.zephyrproject.org/latest/develop/toolchains/zephyr_sdk.html)는 확인일에 권장하는 참조 SDK patch로 1.0.1을 제시합니다. 따라서 이 profile은 최소값이 아니라 재현 가능한 권장 patch인 1.0.1을 고정합니다. |

version을 올릴 때 release note만 읽지 않고 반드시 이전 기준에서 새 기준으로 가는 migration guide를 확인합니다. 위 링크는 모두 Zephyr project의 공식 문서이며 실제 build에는 manifest와 설치된 `west`, Python, compiler와 SDK version을 함께 기록합니다.

## Zephyr project

### release와 시작

- [Zephyr Releases](https://docs.zephyrproject.org/latest/releases/index.html): stable/LTS release와 release note 진입점
- [Zephyr 4.4 Release Notes](https://docs.zephyrproject.org/latest/releases/release-notes-4.4.html): C17 기본, subsystem와 API 변경
- [Zephyr 4.4 Migration Guide](https://docs.zephyrproject.org/latest/releases/migration-guide-4.4.html): 4.3에서 4.4로 옮길 때의 Python, C standard, SDK와 API 변경
- [Getting Started Guide](https://docs.zephyrproject.org/latest/develop/getting_started/index.html): workspace와 toolchain 준비
- [Zephyr SDK](https://docs.zephyrproject.org/latest/develop/toolchains/zephyr_sdk.html): cross toolchain, QEMU와 host tool
- [Build System](https://docs.zephyrproject.org/latest/build/cmake/index.html): configuration/build 단계와 generated target

### hardware description와 driver

- [Introduction to Devicetree](https://docs.zephyrproject.org/latest/build/dts/intro-syntax-structure.html)
- [Devicetree HOWTOs](https://docs.zephyrproject.org/latest/build/dts/howtos.html)
- [Devicetree bindings](https://docs.zephyrproject.org/latest/build/dts/bindings.html)
- [Kconfig](https://docs.zephyrproject.org/latest/build/kconfig/index.html)
- [Device Driver Model](https://docs.zephyrproject.org/latest/kernel/drivers/index.html)
- [Board Porting Guide](https://docs.zephyrproject.org/latest/hardware/porting/board_porting.html)

hardware fact, software option와 runtime device readiness를 같은 개념으로 취급하지 않습니다. final generated Devicetree와 `.config`를 실제 build artifact로 확인합니다.

### interrupt, time, DMA와 power

- [Interrupts](https://docs.zephyrproject.org/latest/kernel/services/interrupts.html)
- [Timing Functions](https://docs.zephyrproject.org/latest/kernel/timing_functions/index.html)
- [Timers](https://docs.zephyrproject.org/latest/kernel/services/timing/timers.html)
- [Workqueue Threads](https://docs.zephyrproject.org/latest/kernel/services/threads/workqueue.html)
- [DMA](https://docs.zephyrproject.org/latest/hardware/peripherals/dma.html)
- [Cache Guide](https://docs.zephyrproject.org/latest/hardware/cache/guide.html)
- [System Power Management](https://docs.zephyrproject.org/latest/services/pm/system.html)
- [Device Runtime Power Management](https://docs.zephyrproject.org/latest/services/pm/device_runtime.html)
- [Task Watchdog](https://docs.zephyrproject.org/latest/services/task_wdt/index.html)
- [Hardware Information과 reset cause](https://docs.zephyrproject.org/latest/hardware/peripherals/hwinfo.html)

ISR callback context, DMA channel ownership, cache maintenance와 power-management API의 정확한 보장은 release와 driver/SoC 문서를 확인합니다.

### storage, boot와 update

- [Flash API](https://docs.zephyrproject.org/latest/hardware/peripherals/flash.html)
- [Flash Map](https://docs.zephyrproject.org/latest/services/storage/flash_map/flash_map.html)
- [Non-Volatile Storage](https://docs.zephyrproject.org/latest/services/storage/nvs/nvs.html)
- [Settings](https://docs.zephyrproject.org/latest/services/storage/settings/index.html)
- [MCUmgr](https://docs.zephyrproject.org/latest/services/device_mgmt/mcumgr.html)
- [MCUboot with Zephyr](https://docs.zephyrproject.org/latest/services/device_mgmt/dfu.html)

storage library를 사용해도 power-loss, schema, wear와 rollback compatibility를 제품 요구사항에 맞춰 검증합니다.

### simulation, test와 debug

- [`native_sim`](https://docs.zephyrproject.org/latest/boards/native/native_sim/doc/index.html)
- [QEMU Cortex-M3 target](https://docs.zephyrproject.org/latest/boards/qemu/cortex_m3/doc/index.html)
- [MPS2+ AN521](https://docs.zephyrproject.org/latest/boards/arm/mps2/doc/mps2_an521.html)
- [Testing with Twister](https://docs.zephyrproject.org/latest/develop/test/twister.html)
- [Test Framework](https://docs.zephyrproject.org/latest/develop/test/ztest.html)
- [Application Debugging](https://docs.zephyrproject.org/latest/develop/debug/index.html)
- [Logging](https://docs.zephyrproject.org/latest/services/logging/index.html)
- [Tracing](https://docs.zephyrproject.org/latest/services/tracing/index.html)

simulator/emulator에서 지원하는 peripheral와 timing만 주장합니다.

## MCUboot

- [MCUboot design](https://docs.mcuboot.com/design.html): image slot, swap/revert와 trailer state
- [MCUboot Zephyr README](https://github.com/mcu-tools/mcuboot/blob/main/docs/readme-zephyr.md): Zephyr integration
- [MCUboot release notes](https://docs.mcuboot.com/release-notes.html): 사용 release의 behavior와 migration

실제 update mode는 overwrite, swap, direct-XIP 등에서 다릅니다. signature validation과 functional rollback도 별도 계약입니다.

## Arm Cortex-M와 CMSIS

- [CMSIS documentation](https://arm-software.github.io/CMSIS_6/latest/General/index.html)
- [CMSIS-Core](https://arm-software.github.io/CMSIS_6/latest/Core/index.html)
- [Arm Architecture Reference Manuals](https://developer.arm.com/Architectures)
- [Arm Cortex-M documentation](https://developer.arm.com/Processors/Cortex-M)

CPU core manual만으로 SoC peripheral, clock, reset와 memory map을 판단하지 않습니다. SoC reference manual과 errata를 함께 사용합니다.

## RISC-V

- [RISC-V ISA Specifications](https://docs.riscv.org/reference/isa/)
- [Unprivileged ISA](https://docs.riscv.org/reference/isa/unpriv/unpriv-index.html)
- [Privileged Architecture](https://docs.riscv.org/reference/isa/priv/priv-index.html)
- [RISC-V Debug Specification](https://docs.riscv.org/reference/debug/introduction.html)

platform interrupt controller, timer, boot protocol와 memory map은 SoC/platform 문서를 확인합니다.

## C와 toolchain

- [GCC documentation](https://gcc.gnu.org/onlinedocs/)
- [Clang documentation](https://clang.llvm.org/docs/)
- [GNU binutils](https://sourceware.org/binutils/docs/)
- [ELF specification index](https://refspecs.linuxfoundation.org/elf/)

compiler/linker option, section, map와 optimization은 사용하는 version을 기록합니다. `volatile`의 언어 의미를 MMIO ordering, atomicity 또는 inter-core synchronization 보장으로 확대하지 않습니다.

## chip, board와 device 문서

실제 구현에서 가장 중요한 자료는 선택 부품의 문서입니다.

- MCU datasheet
- SoC reference manual
- architecture/core manual
- silicon errata
- board schematic, layout note와 revision
- external sensor/storage datasheet
- debug/programming manual
- boot ROM와 security lifecycle 문서

문서에는 다음을 함께 기록합니다.

```text
manufacturer
part number와 revision
문서 번호
문서 revision/date
확인한 section/table
실제 board/chip marking
```

검색 결과나 vendor SDK header만으로 register 의미를 확정하지 않습니다.

## 자료 사용 원칙

1. architecture 보장, SoC 구현, board wiring와 application policy를 구분합니다.
2. 최신 웹 페이지 제목보다 사용한 release/문서 revision을 기록합니다.
3. 교육용 상태 모델의 단순화를 실제 hardware behavior로 확대하지 않습니다.
4. register reset value, reserved bit, write semantic와 errata를 함께 확인합니다.
5. 성능·power·endurance 수치는 조건과 허용 오차를 포함합니다.
6. 개인 블로그의 결론을 옮기기 전에 공식 명세와 실제 artifact로 검증합니다.
