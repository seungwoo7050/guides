# 실습 1 — firmware image와 memory audit

## 문제

소스가 컴파일됐다는 사실만으로 target에서 안전하게 실행되는 image라고 할 수 없습니다. startup code, linker script, Devicetree memory region, bootloader partition와 실제 ELF section이 같은 주소 계약을 사용해야 합니다. 이 실습에서는 하나의 firmware build를 선택해 **reset에서 `main`까지의 image·memory 계약**을 복원합니다.

## 학습 목표

- source, object, ELF, binary/hex와 flashed image를 구분합니다.
- vector table, startup, `.text`, `.rodata`, `.data`, `.bss`, stack, heap와 retained region을 찾습니다.
- VMA/LMA, flash/RAM budget와 alignment를 설명합니다.
- bootloader/application partition와 entry address를 검증합니다.
- image size 보고서가 보장하는 것과 보장하지 않는 것을 구분합니다.

## 입력 선택

다음 중 하나를 사용합니다.

1. 직접 만든 작은 bare-metal firmware
2. Zephyr sample의 ELF와 map
3. 공개 project에서 재현 가능하게 build한 artifact
4. 제공받은 ELF·map·linker script 묶음

source와 build configuration을 확보할 수 있는 입력을 우선합니다. 출처가 불명확한 binary만으로는 일부 항목을 `UNKNOWN`으로 남깁니다.

## 초기 상태

`workspace/README.md`에 다음을 고정합니다.

- target architecture, SoC와 board
- build command
- toolchain/version
- source revision
- bootloader 유무
- flash/RAM region
- debug/release configuration

## 수행 과제

### 1. artifact graph

```text
source/configuration
→ object/archive
→ linker script와 generated symbols
→ ELF
→ loadable image
→ programmer/bootloader가 쓰는 region
```

각 단계의 파일 이름과 owner를 적습니다.

### 2. section inventory

최소 표:

| section/region | load 위치 | run 위치 | 크기 | 초기화 주체 | reset 뒤 정책 |
|---|---:|---:|---:|---|---|
| vector | | | | CPU/boot | |
| `.text` | | | | image | immutable |
| `.data` | | | | startup copy | initialized |
| `.bss` | | | | startup zero | zero |
| stack | | | | runtime | bounded |
| heap/pool | | | | application/RTOS | policy |
| retention | | | | startup policy | validate |

### 3. reset path

- reset vector와 entry symbol
- initial SP 또는 stack region
- `.data` copy source/destination
- `.bss` zero range
- constructor/init 단계
- `main` 또는 kernel entry

linker symbol과 startup code가 같은 boundary를 사용하는지 확인합니다.

### 4. budget

다음을 계산하거나 tool output으로 확인합니다.

- flash used/free
- static RAM used/free
- stack budget
- heap/pool policy
- update slot 또는 secondary image 여유
- alignment/padding와 orphan section

“free RAM = total − `.data` − `.bss`”로 끝내지 않습니다. stack, heap, DMA pool, retention, runtime object와 memory-mapped region을 별도로 적습니다.

### 5. 실패 주입

실제 image를 망가뜨리지 않고 linker/configuration copy에서 수행합니다.

- RAM region을 작게 설정
- oversized stack 또는 static buffer
- section alignment 증가
- vector/entry region 이동
- orphan section 추가
- bootloader slot보다 큰 image

build 또는 검사가 어디에서 어떤 증거로 실패해야 하는지 기록합니다.

## 필수 결과물

```text
workspace/
├── README.md
├── artifact-graph.md
├── memory-map.md
├── reset-path.md
├── budget.md
├── evidence/
│   ├── map.txt
│   ├── sections.txt
│   ├── symbols.txt
│   └── size.txt
└── report.md
```

원본 artifact가 binary이면 그대로 복사하기보다 재현 위치와 hash를 기록해도 됩니다.

## 완료 조건

- 모든 loadable section의 load/run address를 설명합니다.
- vector와 reset entry를 exact ELF symbol로 찾습니다.
- `.data`와 `.bss` 초기화 범위를 linker와 startup 양쪽에서 확인합니다.
- static RAM 외의 runtime budget을 별도로 기록합니다.
- image/slot overflow가 silent truncate되지 않고 실패하도록 검사합니다.
- 결과를 exact build ID 또는 hash와 연결합니다.
- 미확인 항목을 추측으로 채우지 않습니다.

## 잘못된 완료

- `size` 명령 한 줄만 제출
- map file을 붙였지만 의미를 설명하지 않음
- debug build만 보고 release budget을 단정
- stack 사용을 static RAM 합계에 포함했다고 착각
- ELF address와 flashed address를 구분하지 않음
- bootloader partition를 application linker와 비교하지 않음

## 선택 확장

- debug/release와 feature configuration의 size diff
- call-graph 기반 stack estimate와 runtime watermark 비교
- retained crash record section 추가
- secondary slot/update trailer를 포함한 partition audit
- QEMU에서 reset handler와 `main` breakpoint 확인

## 검토 질문

1. `.data`의 VMA와 LMA가 다른 이유는 무엇입니까?
2. map file에서 보이는 free RAM이 실제 worst-case 여유와 같지 않은 이유는 무엇입니까?
3. bootloader가 vector를 다른 offset에서 찾는다면 application image에 어떤 계약이 필요합니까?
4. release artifact에 어떤 파일을 함께 보존해야 현장 주소를 symbolization할 수 있습니까?
