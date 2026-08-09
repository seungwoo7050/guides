# 버전 기준과 구현 프로필

확인 기준일: **2026-08-09**

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

Zephyr 4.4.0은 2026-04-14에 발표된 stable release이고, 4.4 release는 최소 Python을 3.12로 올리고 C17을 기본 C standard로 선택했으며 SDK 1.0 계열을 지원합니다. 재현 기준은 현재 공식 설치 문서의 patch release인 SDK 1.0.1까지 고정합니다. 이 가이드가 자동으로 최신 release로 이동하지는 않습니다. 다음 major/minor 또는 SDK patch로 올릴 때 문서·명령·generated artifact와 실습 가정을 다시 검토합니다.

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

1. release note에서 C standard, build, board naming, Kconfig/Devicetree, driver API와 test 변화 확인
2. `reference/sources.md` 링크와 확인일 갱신
3. 예제 명령을 clean environment에서 재실행
4. generated `.config`, Devicetree와 ELF/map 비교
5. state model 가정이 API semantics와 충돌하는지 검토
6. `./prepare.sh && ./verify.sh` 실행
7. 미지원 또는 변경된 profile을 문서화

“최신”이라는 표현만 바꾸지 말고 재현 가능한 버전과 변경 근거를 남깁니다.
