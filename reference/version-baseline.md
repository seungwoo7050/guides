# 버전 기준과 구현 프로필

확인 기준일: **2026-08-10**

이 문서는 가이드의 개념 계약과 선택 구현 환경을 분리합니다. 핵심 문서는 특정 RTOS release가 없어도 읽고 검증할 수 있습니다. 아래 버전은 예제·실습을 실제 firmware project로 옮길 때 사용할 **재현 기준**입니다.

## 필수 가이드 검증 환경

| 항목 | 기준 |
|---|---|
| Python | 3.10 이상 |
| shell | POSIX 호환 `sh` |
| 도구 | `make`, `git`, `zip`은 배포에만 필요 |
| 외부 Python package | 없음 |
| network | 검증 중 불필요 |
| MCU/board | 불필요 |

루트 `prepare.sh`와 `verify.sh`는 Zephyr·cross compiler·QEMU를 설치하거나 요구하지 않습니다.

## 선택 Zephyr 프로필

| 항목 | 고정 기준 |
|---|---|
| Zephyr | 4.4.0 stable |
| 언어 기준 | Zephyr 4.4 기본 C17 |
| Python | 3.12 이상 |
| Zephyr SDK | 1.0.1 |
| host simulation | `native_sim` |
| Cortex-M/QEMU | `mps2/an521/cpu0` 또는 현재 문서에서 지원하는 동등 Cortex-M target |
| build frontend | `west` + CMake/Ninja |

[공식 release 목록](https://docs.zephyrproject.org/latest/releases/index.html)은 Zephyr 4.4.0을 2026-04-14 release로 열거합니다. [4.4 migration guide](https://docs.zephyrproject.org/latest/releases/migration-guide-4.4.html)는 4.3에서 4.4로 이동할 때 최소 Python이 3.10에서 3.12로 바뀌고 기본 C standard가 C17이 되며 최소 SDK가 1.0.0이라고 기록합니다. [공식 SDK 문서](https://docs.zephyrproject.org/latest/develop/toolchains/zephyr_sdk.html)가 확인일에 권장하는 1.0.1을 재현 profile로 고정했습니다. 즉 SDK 1.0.1은 4.4의 최소값 주장이 아니라 이 가이드의 선택한 patch 기준입니다.

Python 3.12, C17과 SDK 1.0.1은 **선택 Zephyr profile**의 묶음입니다. hardware와 Zephyr가 필요 없는 6개 host 실습과 capstone checker는 위 표처럼 Python 3.10 이상을 유지합니다. `prepare.sh`의 host 최소 조건을 Zephyr 조건과 혼동하지 않습니다. 이 가이드가 자동으로 최신 release로 이동하지도 않습니다. 다음 major/minor 또는 SDK patch로 올릴 때 문서·명령·generated artifact와 실습 가정을 다시 검토합니다.

## 선택 명령 예시

Zephyr source와 environment가 이미 준비됐다는 전제입니다.

```sh
west build -b native_sim samples/hello_world
./build/zephyr/zephyr.exe
```

Cortex-M33/QEMU 예:

```sh
west build -b mps2/an521/cpu0 samples/hello_world
west build -t run
```

board target과 run support는 사용하는 release의 board 문서에서 다시 확인합니다. secure/non-secure, multicore와 TF-M 경로는 기본 capstone 범위가 아닙니다.

## `native_sim`의 위치

`native_sim`은 다음에 적합합니다.

- application state와 RTOS API integration
- virtual/fake device
- sanitizer와 host debugger
- 빠른 반복과 test runner

다음을 보장하지 않습니다.

- Cortex-M exception frame
- 실제 peripheral register와 interrupt timing
- MCU flash와 power-loss behavior
- DMA/cache coherence
- 실제 저전력 current

기본 32-bit target과 64-bit target은 ABI가 다릅니다. pointer/`long` 폭에 민감한 code를 검사할 때 어떤 target을 사용했는지 기록합니다.

## QEMU target의 위치

Cortex-M QEMU target은 다음을 관찰하는 데 사용합니다.

- architecture startup와 vector
- exception/interrupt controller 일부
- linker/memory map
- 지원되는 UART·timer·GPIO와 driver

QEMU가 구현하지 않은 peripheral register와 electrical behavior는 실제 board 검증으로 남깁니다. `mps2/an521`은 QEMU와 unit test 사용이 중심인 Cortex-M33 target이며 실제 제품 hardware 적합성을 주장하지 않습니다.

## 실제 보드 프로필

가이드는 특정 보드를 필수 지정하지 않습니다. 보드를 선택할 때 다음을 기록합니다.

- board name와 revision
- SoC exact part/revision
- external sensor/storage part
- debug probe와 firmware
- power supply와 measurement equipment
- Zephyr board target
- overlay/Kconfig fragment
- programmer/recovery procedure

학습 목적에는 다음이 유용합니다.

- debug probe가 내장되거나 쉽게 연결됨
- UART와 GPIO가 노출됨
- I2C/SPI sensor 연결 가능
- controllable reset/power
- upstream Zephyr support와 sample 존재

## architecture reference

### Cortex-M

- CMSIS 6의 core interface와 사용하는 Cortex-M architecture manual
- SoC reference manual과 errata
- board schematic/pinout

Zephyr는 Cortex-M architecture-level 신규 개발에서 CMSIS 6 header 사용으로 이동 중이지만 legacy CMSIS 5도 vendor HAL compatibility를 위해 함께 존재할 수 있습니다. source가 어느 module과 version을 사용하는지 build manifest에서 확인합니다.

### RISC-V

- ratified unprivileged ISA
- privileged architecture
- platform/SoC interrupt, timer, debug와 memory map 문서

RISC-V라는 이름만으로 interrupt controller, timer, cache와 boot flow가 같다고 가정하지 않습니다.

## 업데이트 절차

기준 version을 바꿀 때:

1. [release 목록](https://docs.zephyrproject.org/latest/releases/index.html)에서 exact release와 발표일 확인
2. 이전 기준에서 새 기준으로 가는 공식 migration guide에서 Python, C standard, SDK, build, board naming, Kconfig/Devicetree, driver API와 test 변화 확인
3. `reference/sources.md`의 공식 링크, 판단 근거와 확인일 갱신
4. 예제 명령을 clean environment에서 재실행하고 exact `west`, Python, compiler와 SDK version 기록
5. generated `.config`, Devicetree와 ELF/map 비교
6. state model 가정이 API semantics와 충돌하는지 검토
7. `./prepare.sh && ./verify.sh` 실행
8. 미지원 또는 변경된 profile과 migration 결과를 문서화

“최신”이라는 표현만 바꾸지 말고 재현 가능한 버전과 변경 근거를 남깁니다.
