# Cortex-M와 RISC-V 개념 대응표

이 표는 architecture를 동일하게 만들려는 것이 아니라, 한 플랫폼에서 배운 질문을 다른 플랫폼에 옮기기 위한 출발점입니다. 정확한 register와 mechanism은 사용하는 core·privileged spec·SoC를 확인합니다.

| 질문 | Cortex-M에서 찾을 개념 | RISC-V에서 찾을 개념 | 공통 검토 |
|---|---|---|---|
| reset 뒤 첫 instruction | vector/reset entry와 vendor boot | reset vector/platform boot | 초기 privilege, stack/runtime 준비 주체 |
| 예외/interrupt entry | exception model, NVIC, vector table | trap, `mtvec`/`stvec`, platform interrupt controller | saved context, priority, masking, return |
| timer tick | SysTick 또는 SoC timer | platform timer, `mtime` 계열 또는 SBI/SoC | timebase, width, wrap, sleep continuity |
| global interrupt control | PRIMASK/BASEPRI 등 core mechanism | status interrupt-enable bit와 privilege | critical section 범위와 nesting |
| pending/priority | NVIC + peripheral status | local/platform interrupt controller + device | source clear와 controller complete 순서 |
| fault 원인 | fault status registers와 exception frame | `mcause`/`scause`, `mtval` 등 | precise/imprecise, PC와 context 보존 |
| privilege | Thread/Handler, privileged/unprivileged, optional TrustZone | M/S/U mode와 platform security | memory/peripheral access와 transition |
| memory protection | MPU/SAU 등 | PMP와 platform mechanism | region, permission, lock와 boot policy |
| memory ordering | architecture barrier와 device memory rule | fence와 memory model | MMIO ordering, DMA/cache API, compiler boundary |
| low power | WFI/WFE와 SoC power controller | WFI와 platform power management | wake source, clock/power domain, retained state |
| debug | CoreSight/SWD/JTAG와 CMSIS-DAP ecosystem | RISC-V debug module/JTAG/transport | halt side effect, exact target configuration |
| atomic operation | exclusive access/architecture extension | A extension 또는 critical section | availability, alignment, device memory 제한 |

## 옮길 때 유지할 질문

architecture 이름과 관계없이 다음을 조사합니다.

1. reset/boot contract는 무엇입니까?
2. exception이 저장하는 state와 software가 추가 저장할 state는 무엇입니까?
3. interrupt source, controller와 CPU enable이 각각 어디에 있습니까?
4. interrupt acknowledgement/complete 순서는 무엇입니까?
5. time source의 frequency, width와 sleep behavior는 무엇입니까?
6. MMIO access ordering과 cache/DMA visibility는 어떻게 보장합니까?
7. privilege와 memory protection을 누가 구성합니까?
8. debugger halt 중 어떤 peripheral와 watchdog이 계속 진행합니까?
9. SoC/platform가 core architecture에 추가한 mechanism은 무엇입니까?

## 잘못된 대응

- NVIC와 모든 RISC-V interrupt controller가 동일하다고 가정
- SysTick register를 platform-independent timer API처럼 취급
- `volatile`을 두 architecture의 barrier로 사용
- Cortex-M fault status field를 RISC-V trap cause에 이름만 바꿔 대응
- privilege mode 이름만으로 보안 boundary가 같다고 단정
- core manual만 읽고 SoC clock/reset/memory map을 생략

## 구현 profile 문서

새 architecture를 지원할 때 다음 표를 별도로 채웁니다.

```text
architecture/core:
SoC/platform:
reset entry:
exception/trap frame:
interrupt controller:
timer/timebase:
privilege/protection:
cache/DMA coherence:
power states:
debug transport:
official specs/revisions:
known errata:
```
