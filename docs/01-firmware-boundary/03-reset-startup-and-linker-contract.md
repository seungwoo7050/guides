# reset, startup과 linker 계약

C의 `main`은 firmware의 첫 instruction이 아닙니다. reset 뒤 CPU가 어디에서 stack pointer와 entry address를 얻는지, 누가 `.data`를 복사하고 `.bss`를 지우는지, clock과 runtime을 어떤 순서로 준비하는지 이해해야 초기 boot failure와 reset 종류에 따른 차이를 조사할 수 있습니다.

## 학습 목표

- reset vector에서 `main`까지의 단계와 각 소유자를 구분합니다.
- vector table, stack, `.data`, `.bss`, `.noinit`와 constructor의 초기화 계약을 설명합니다.
- linker script와 startup code가 공유하는 symbol·address 계약을 추적합니다.
- early boot failure를 debugger, map와 최소 출력으로 좁힙니다.

## reset 뒤 CPU가 받는 입력

정확한 규칙은 architecture마다 다르지만 MCU firmware는 보통 다음 정보를 사용합니다.

- reset exception entry 또는 vector table base
- 초기 stack pointer 또는 stack region
- 현재 privilege와 interrupt mask
- reset default clock
- memory alias 또는 boot mode
- reset cause와 retained register

C runtime이 준비되기 전에는 global variable, stack 크기, clock frequency와 peripheral이 application이 기대하는 상태가 아닐 수 있습니다.

## 대표 startup 순서

```text
reset asserted/released
→ CPU architectural reset state
→ vector table에서 초기 stack/Reset_Handler 획득
→ 최소 core·memory 설정
→ optional clock·memory controller 설정
→ .data: flash에서 RAM으로 copy
→ .bss: zero fill
→ .noinit/retention: 정책에 따라 보존
→ C/C++ runtime와 constructors
→ board/SoC/driver initialization
→ main 또는 RTOS kernel entry
```

모든 프로젝트가 같은 순서를 사용하지 않습니다. external RAM을 `.data`가 사용한다면 memory controller가 copy보다 먼저 준비돼야 합니다. clock을 너무 일찍 바꾸면 flash wait state나 debug transport가 깨질 수 있습니다.

## vector table은 함수 배열 이상의 계약입니다

vector table에는 architecture에 따라 다음이 포함될 수 있습니다.

- 초기 stack pointer
- reset handler
- core exception handlers
- peripheral IRQ handlers
- reserved entries

확인 항목:

- table의 load/run address
- alignment
- bootloader가 application vector를 어디에서 찾는지
- runtime relocation 여부
- default handler가 어떤 evidence를 남기는지
- handler symbol이 weak alias인지 실제 구현인지

interrupt가 default infinite loop로 들어간다면 “아무것도 일어나지 않았다”가 아니라 **처리되지 않은 vector가 발생한 상태**입니다.

## linker symbol은 startup code의 API입니다

startup code는 linker가 만든 symbol을 사용합니다.

```text
__data_load_start
__data_start
__data_end
__bss_start
__bss_end
__stack_top
```

이름은 프로젝트마다 다르지만 의미는 같습니다. linker script와 startup code 중 하나만 바꾸면 copy 길이, stack 주소와 memory region이 어긋날 수 있습니다.

```c
for (dst = data_start, src = data_load; dst < data_end; ++dst, ++src) {
    *dst = *src;
}
for (dst = bss_start; dst < bss_end; ++dst) {
    *dst = 0;
}
```

실제 구현은 word width, alignment, ECC 초기화와 copy table을 고려할 수 있습니다.

## `.noinit`와 retention은 자동 영속성이 아닙니다

startup이 특정 RAM을 지우지 않으면 reset 뒤 byte가 남을 수 있습니다. 그러나 다음을 확인해야 합니다.

- 어떤 reset에서 해당 power domain이 유지됩니까?
- RAM ECC나 parity initialization이 필요합니까?
- compiler/linker가 object를 정확한 section에 두었습니까?
- record version, length와 checksum이 있습니까?
- 오래된 firmware가 남긴 layout을 새 firmware가 해석할 수 있습니까?

retained memory는 valid marker와 integrity check 없이 신뢰하지 않습니다.

## clock initialization은 memory와 timing 계약을 바꿉니다

clock tree 변경은 단순한 “속도 설정”이 아닙니다.

- flash access wait state
- bus divider
- peripheral input clock
- timer tick frequency
- UART baud calculation
- power domain과 oscillator startup
- timeout conversion

clock이 안정되기 전에 timeout을 같은 단위로 계산하거나 UART를 초기화하면 early log가 깨질 수 있습니다. clock source transition에는 failure와 fallback policy가 필요합니다.

## driver initialization에는 의존 순서가 있습니다

```text
clock/reset controller
→ pin controller
→ bus controller
→ peripheral driver
→ external device driver
→ application service
```

RTOS device model이 init level을 제공해도 dependency가 자동으로 맞는 것은 아닙니다. hardware description, build configuration와 driver declaration이 같은 graph를 가리켜야 합니다.

## early boot failure를 좁히는 순서

1. 실제 reset cause와 boot mode를 확인합니다.
2. debugger로 reset PC와 initial SP를 확인합니다.
3. ELF와 map에서 vector table address를 확인합니다.
4. `Reset_Handler`에 breakpoint를 둡니다.
5. `.data` source/destination과 `.bss` range를 확인합니다.
6. clock 변경 전후의 fault 위치를 분리합니다.
7. constructors와 driver init을 단계별로 비활성화합니다.
8. UART가 준비되지 않았다면 GPIO pulse, debugger memory 또는 trace를 사용합니다.

printf를 더 추가하면 stack, timing과 peripheral 초기화 순서를 바꿔 결함을 숨길 수 있습니다.

## reset 종류별 초기화 정책

| reset 종류 | 다시 초기화할 후보 | 보존할 후보 | 주의점 |
|---|---|---|---|
| power-on | 전체 clock·memory·peripheral | factory data | 전원 안정화와 brownout |
| watchdog | MCU internal state | crash record, external device state | boot loop와 원인 덮어쓰기 |
| software | application/driver state | boot request, retained reason | peripheral가 reset되지 않을 수 있음 |
| wakeup | 필요한 clock·peripheral | RAM·task state 또는 retention | wake source clear와 time discontinuity |
| bootloader jump | application runtime | boot metadata | vector/stack/interrupt state handoff |

## 실패와 불변식

startup 완료 뒤 최소 불변식:

- stack pointer가 유효하고 정렬돼 있습니다.
- `.data`는 image 초기값과 일치합니다.
- `.bss`는 0입니다.
- vector table은 현재 image의 handler를 가리킵니다.
- application이 사용하는 clock frequency가 실제 설정과 일치합니다.
- 사용 전 dependency가 ready입니다.
- reset cause와 crash evidence를 소비하기 전에 보존했습니다.

## 실습 연결

[firmware image와 memory audit](../../exercises/01-image-and-memory-audit/README.md)에서 reset path와 linker symbol을 조사합니다. actual board가 없다면 Zephyr QEMU sample이나 공개 ELF·map artifact를 사용할 수 있습니다.

## 직접 확인할 문제

1. `.data` copy 전에 external RAM controller를 준비해야 하는 image layout을 설명해 보세요.
2. watchdog reset 직후 crash record를 `.bss`에 두면 왜 사라집니까?
3. bootloader가 application으로 jump하기 전에 interrupt와 vector table 상태를 정리해야 하는 이유를 적어 보세요.
4. UART log가 나오지 않을 때 `main`에 도달하지 않았다고 단정할 수 없는 이유를 설명해 보세요.

## 이 장이 보장하지 않는 것

architecture별 reset register, TrustZone transition, multi-core release와 vendor startup assembly의 구체 규칙은 해당 architecture·SoC 문서를 확인해야 합니다.
