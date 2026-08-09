# Devicetree, Kconfig와 device model

같은 driver source를 여러 board와 SoC에서 재사용하려면 **hardware instance의 사실**, **software 기능 선택**, **runtime device object**를 서로 다른 계층으로 나눠야 합니다. 이 구분이 없으면 pin 번호, clock, interrupt와 bus address가 application code에 흩어지고, build가 성공해도 다른 board에서 조용히 잘못된 장치를 제어할 수 있습니다.

이 장은 Zephyr를 선택 구현 프로필로 사용하지만, 핵심은 특정 macro를 외우는 것이 아닙니다. hardware description, build configuration, driver instance와 application dependency가 하나의 graph를 가리키는지 추적합니다.

## 학습 목표

- board, SoC, peripheral, external device와 application의 소유권을 구분합니다.
- Devicetree가 표현하는 hardware fact와 Kconfig가 선택하는 software policy를 분리합니다.
- compatible, binding, node, property, alias와 chosen의 역할을 설명합니다.
- compile-time instance 생성과 runtime `device` readiness를 연결합니다.
- overlay와 configuration 변경이 실제 artifact에 반영됐음을 증명합니다.

## 세 종류의 상태를 분리합니다

```text
hardware description
- 어떤 장치가 어디에 연결되어 있는가
- address, interrupt, clock, pin, bus 관계

software configuration
- 어떤 subsystem과 driver를 build할 것인가
- buffer size, feature, logging과 policy 선택

runtime device state
- init이 끝났는가
- dependency가 ready인가
- suspend/error/recovery 중인가
```

이 세 상태를 한 파일이나 `#ifdef` 묶음으로 합치면 board 차이와 feature 차이를 구분하기 어렵습니다.

## Devicetree는 hardware topology를 설명합니다

대표 구조:

```text
SoC
├── GPIO controller
├── I2C controller
│   └── sensor at address 0x48
├── SPI controller
│   └── flash with chip-select
└── UART controller
```

node에는 다음 정보가 들어갈 수 있습니다.

- `compatible`: 어떤 binding과 driver family가 해석할지
- `reg`: address 또는 bus-local identifier
- `interrupts`: interrupt line과 trigger information
- `clocks`, `resets`, `dmas`: provider와 specifier
- `pinctrl-*`: pin routing과 electrical mode의 선택
- `status`: instance 사용 여부
- bus-specific property
- application-specific metadata

Devicetree는 “이 driver를 반드시 build한다”는 정책 전체가 아닙니다. build system과 Kconfig가 driver source를 포함하지 않으면 node가 있어도 runtime object가 없을 수 있습니다.

## binding은 description의 schema와 의미를 고정합니다

binding은 다음을 연결합니다.

```text
compatible string
→ 허용·필수 property
→ property type와 의미
→ bus 관계
→ generated access contract
```

좋은 binding은 vendor register 이름을 application에 노출하지 않고, 같은 종류의 장치를 공통 의미로 설명합니다. 반대로 board 하나를 맞추기 위해 의미가 불분명한 boolean property를 계속 추가하면 driver와 description 경계가 무너집니다.

binding 검토 질문:

1. property가 실제 hardware fact입니까, software policy입니까?
2. 단위가 명확합니까?
3. required/default 조건이 hardware variation을 정확히 표현합니까?
4. 이미 공통 binding에 있는 의미를 다시 만들고 있습니까?
5. property 변경이 backward compatibility에 어떤 영향을 줍니까?

## Kconfig는 software 선택과 dependency를 표현합니다

Kconfig가 담당할 수 있는 것:

- subsystem 또는 driver enable
- 선택 implementation
- compile-time buffer와 resource budget
- logging/assertion level
- optional protocol 기능
- platform capability dependency

Kconfig가 담당하면 안 되는 대표 사례:

- 특정 board의 I2C address
- 실제 interrupt line
- pin routing
- 존재하는 hardware instance 수

이 값들은 hardware description의 영역입니다.

`select`를 과도하게 사용하면 dependency가 강제로 켜져 유효하지 않은 조합이 만들어질 수 있습니다. user-visible option, hidden capability, dependency와 default의 책임을 구분합니다.

## generated artifact를 실제로 확인합니다

source 파일만 읽으면 최종 configuration을 알 수 없습니다. 다음 artifact를 함께 봅니다.

- merged Devicetree와 generated header
- final `.config`
- build system이 선택한 source 목록
- linker map의 driver/data section
- runtime device initialization 결과

```text
board base description
+ SoC include
+ shield 또는 board revision
+ application overlay
→ final hardware tree

Kconfig defaults
+ board/SoC defaults
+ application config
+ command-line fragments
→ final software configuration
```

어느 입력이 마지막 값을 덮어썼는지 기록해야 재현할 수 있습니다.

## compile-time instance와 runtime readiness

driver instance 생성의 대표 흐름:

```text
enabled node
→ binding match
→ generated constants
→ config/data object
→ init entry와 device object
→ dependency init
→ runtime ready
```

compile이 성공했다고 device가 usable한 것은 아닙니다.

- bus controller init 실패
- clock/reset dependency 미준비
- external device identity mismatch
- pin conflict
- power domain off
- probe 중 timeout

application은 device handle 획득과 readiness, operation failure를 구분해야 합니다.

## alias, chosen와 label의 경계

- alias는 application이 board별 node path 차이를 숨기는 안정된 이름으로 사용할 수 있습니다.
- chosen은 console, memory, flash partition처럼 system-wide 역할을 특정 node에 연결할 수 있습니다.
- node label은 source tree에서 참조하기 위한 식별자입니다.
- runtime device name string은 compile-time identity와 같은 의미가 아닐 수 있습니다.

application이 raw node path나 vendor-specific instance 번호에 의존하면 board portability가 떨어집니다.

## overlay는 patch이며 새 정본이 아닙니다

overlay를 사용할 때 확인합니다.

- 어느 base tree에 적용됩니까?
- board revision과 shield 조합은 무엇입니까?
- 기존 property를 덮어쓰는지 node를 추가하는지 알 수 있습니까?
- 최종 merged tree를 versioned build artifact로 남겼습니까?
- production board와 test board overlay가 혼동되지 않습니까?

overlay 파일이 존재한다는 사실이 build에 적용됐다는 증거는 아닙니다.

## driver API와 hardware description의 경계

application은 다음처럼 사용해야 합니다.

```text
semantic operation
sensor_sample_fetch()
flash_write_record()
gpio_set_output()
```

다음처럼 board wiring을 직접 해석하지 않습니다.

```text
if BOARD_X:
    register = 0x40001234
    bit = 7
```

driver는 generated hardware constants를 사용하되, register semantic과 operation state는 driver가 소유합니다.

## porting 실패를 좁히는 순서

1. 정확한 board target과 revision을 확인합니다.
2. final merged Devicetree에서 node와 `status`를 확인합니다.
3. binding match와 generated property를 확인합니다.
4. final Kconfig에서 driver와 dependency enable을 확인합니다.
5. build에 driver source와 instance가 포함됐는지 확인합니다.
6. init order와 dependency readiness를 확인합니다.
7. pin, clock, reset, interrupt와 bus trace를 실제 hardware에서 관찰합니다.
8. application API failure와 hardware absence를 구분합니다.

## 실패와 불변식

다음 불변식을 유지합니다.

- board wiring은 application source에 중복되지 않습니다.
- hardware property와 software policy의 소유 파일이 구분됩니다.
- enabled instance마다 필요한 dependency가 build와 runtime에서 존재합니다.
- final generated description과 configuration을 release artifact로 재현할 수 있습니다.
- driver가 ready하지 않으면 application이 정상 동작처럼 진행하지 않습니다.

검사 사례:

- compatible typo
- required property 누락
- disabled bus 아래 enabled child
- Kconfig driver off
- pin conflict
- overlay 미적용
- board revision 불일치
- dependency init 실패
- 같은 alias를 다른 의미의 장치에 연결

## 실습 연결

[sensor driver 상태 기계](../../exercises/03-sensor-driver-state-machine/README.md)에서 abstract device description을 만들고, 선택 구현에서는 같은 계약을 Devicetree binding과 Kconfig dependency로 옮깁니다.

## 직접 확인할 문제

1. sensor sampling frequency를 Devicetree property와 Kconfig 중 어디에 둘지 조건별로 설명해 보세요.
2. node가 `okay`인데 `device_is_ready()`가 실패할 수 있는 경로를 작성해 보세요.
3. application overlay가 실제 build에 반영됐음을 어떤 artifact로 증명할 수 있습니까?
4. board별 `#ifdef`를 alias와 driver API로 제거하는 migration을 설계해 보세요.

## 이 장이 보장하지 않는 것

Devicetree syntax와 Kconfig expression 전체를 암기 과정으로 다루지 않습니다. binding format, generated macro와 init API는 사용하는 Zephyr release의 공식 문서를 확인합니다.
