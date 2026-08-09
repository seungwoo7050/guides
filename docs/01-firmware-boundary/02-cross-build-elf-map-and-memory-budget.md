# cross build, ELF와 memory budget

펌웨어 build의 최종 결과는 단순한 “실행 파일”이 아닙니다. debugger가 사용하는 ELF, flashing에 사용하는 binary 또는 HEX, symbol·map·disassembly와 서명·manifest가 서로 다른 목적을 가집니다. image가 target memory에 어떻게 배치되는지 읽지 못하면 code가 빌드돼도 boot failure, RAM overflow와 slot 충돌을 설명하기 어렵습니다.

## 학습 목표

- compile, assemble, link, objcopy와 image packaging 단계를 구분합니다.
- ELF section, segment, symbol, relocation과 map file의 역할을 설명합니다.
- flash와 RAM 소비를 static data, runtime copy, stack, heap과 reserved region으로 나눕니다.
- build configuration과 artifact를 재현 가능한 단위로 기록합니다.

## 선행 개념

C translation unit, object file, static library와 linker의 일반 역할을 알고 있어야 합니다.

## cross build의 입력과 출력

```text
C/assembly source
→ preprocessor
→ target object files
→ static libraries
→ linker script + memory regions
→ ELF
   ├── symbol/debug information
   ├── loadable segments
   └── section addresses
→ objcopy/package
   ├── .bin
   ├── .hex
   ├── signed image
   └── combined multi-image artifact
```

- **object file**에는 target machine code와 아직 결정되지 않은 symbol reference가 있습니다.
- **ELF**는 section, symbol, address와 debug information을 함께 보존합니다.
- **binary**는 지정된 loadable byte만 평평하게 담을 수 있어 symbol과 빈 address gap 의미가 사라집니다.
- **Intel HEX/S-record**는 address와 data를 record로 표현합니다.
- **signed image**는 bootloader가 해석하는 header, payload, hash와 signature metadata를 추가할 수 있습니다.

flash tool이 `.bin`을 받는다고 ELF가 불필요한 것은 아닙니다. crash symbolization, size 조사와 debugger에는 ELF를 보존해야 합니다.

## section과 segment를 구분합니다

대표적인 section:

| section | 일반적인 내용 | load/run 관계 |
|---|---|---|
| `.text` | instruction과 read-only code | flash에서 실행하거나 RAM으로 복사 |
| `.rodata` | constant table과 string | 주로 flash |
| `.data` | 초기값이 있는 writable object | 초기값은 flash, 실행 중 object는 RAM |
| `.bss` | zero-initialized object | image에 byte를 저장하지 않고 startup이 RAM을 0으로 만듦 |
| `.noinit` | reset 뒤 의도적으로 유지할 수 있는 RAM | startup이 초기화하지 않음 |
| vector table | reset/exception handler address | CPU가 요구하는 address·alignment |
| custom section | DMA, retained, boot metadata 등 | linker 계약에 따라 결정 |

section은 compiler와 linker가 코드를 분류하는 논리 단위입니다. program segment는 loader가 memory에 load할 범위를 표현합니다. 둘의 수와 경계가 항상 일치하지 않습니다.

## load address와 run address가 다를 수 있습니다

`.data`는 초기값을 flash image에 저장하지만 실행 중 writable object는 RAM에 있어야 합니다.

```text
flash load image
[.text][.rodata][.data initial bytes]

RAM after startup
[.data copied][.bss zeroed][heap][stacks][buffers]
```

따라서 다음 두 주소를 구분합니다.

- **LMA(load memory address)**: image byte가 저장된 위치
- **VMA(virtual/run memory address)**: CPU가 실행 중 해당 section을 접근하는 위치

MCU가 MMU를 사용하지 않아도 linker 용어에서 VMA가 사용될 수 있습니다. 이것을 process virtual memory와 같은 뜻으로 해석하지 않습니다.

## map file은 “무엇이 왜 들어왔는지”를 보여 줍니다

size summary만 보면 전체 `.text`가 늘어난 이유를 알 수 없습니다. map file과 symbol size를 함께 봅니다.

조사 항목:

- memory region 시작 주소와 크기
- 각 output section의 address와 size
- 어떤 object/library가 section에 기여했는지
- 예상하지 않은 runtime·formatting·floating-point library
- stack·heap·retention·DMA reservation
- bootloader, application, secondary slot과 storage partition
- alignment 때문에 생긴 gap

예시 명령은 toolchain마다 이름이 다릅니다.

```sh
<target>-size firmware.elf
<target>-readelf -h -S -l firmware.elf
<target>-nm --print-size --size-sort firmware.elf
<target>-objdump -d -S firmware.elf
```

출력 형식을 복사하는 것이 아니라 질문에 필요한 정보만 기록합니다.

## flash 사용량과 RAM 사용량은 한 숫자가 아닙니다

### flash budget

```text
bootloader
+ primary image slot
+ secondary/scratch slot
+ constant data
+ filesystem/settings area
+ factory data
+ alignment·metadata
+ future update margin
```

### RAM budget

```text
.data + .bss
+ main/ISR/task stacks
+ heap 또는 memory pools
+ network·driver·DMA buffers
+ retained/noinit region
+ RTOS kernel objects
+ worst-case simultaneous operation margin
```

link-time RAM 사용량은 dynamic allocation과 stack high-water mark를 포함하지 않을 수 있습니다. 반대로 `.data`는 flash 초기값과 RAM object를 모두 소비합니다.

## stack budget은 task 수만 세어서는 부족합니다

각 execution context의 최악 경로를 봅니다.

- main 또는 boot stack
- interrupt stack 또는 각 exception stack
- RTOS task stack
- nested interrupt가 공유 stack에 추가하는 frame
- library call의 local object와 formatting buffer
- FPU context save, exception frame와 architecture-specific metadata

stack analyzer나 watermark는 관찰한 경로의 근거입니다. 검사하지 않은 call path와 interrupt nesting을 자동으로 보장하지 않습니다.

## build configuration도 artifact의 일부입니다

재현 가능한 firmware 결과에는 다음이 필요합니다.

```text
source revision
module/dependency revisions
toolchain와 version
board/target
configuration fragments
Devicetree overlay 또는 board files
linker script/partition layout
build command와 environment
output ELF hash
signing/package parameters
```

“같은 source”라도 configuration symbol, overlay, compiler version과 generated header가 다르면 다른 firmware입니다.

## code size를 줄이기 전에 원인을 분류합니다

- 기능 자체가 추가됐는가?
- logging level 또는 assertion이 바뀌었는가?
- unused section 제거가 꺼졌는가?
- 작은 호출 하나가 큰 library를 끌어왔는가?
- template/inline/format string이 중복됐는가?
- debug information과 loadable size를 섞었는가?
- alignment와 partition metadata가 증가했는가?

단순히 `-Os`를 추가하기 전에 map과 symbol diff를 확인합니다.

## 실패와 검증

### linker 성공 뒤 boot 실패

- vector table address/alignment 불일치
- image header와 bootloader offset 불일치
- `.data` copy source 또는 destination 잘못됨
- stack top이 유효 RAM 밖에 있음
- multi-image region overlap

### build 시 RAM 여유, runtime overflow

- task stack과 heap을 size report가 빠뜨림
- DMA/network buffer가 runtime에 생성됨
- recursive call 또는 큰 local array
- interrupt nesting과 FPU frame

### update image가 slot에 들어가지 않음

현재 primary image size만 보지 말고 header, trailer, encryption/signature metadata, alignment와 future migration 여유를 포함합니다.

## 실습 연결

[firmware image와 memory audit](../../exercises/01-image-and-memory-audit/README.md)에서 실제 또는 공개 sample ELF·map을 선택해 다음을 제출합니다.

- memory region 표
- section·symbol 상위 소비자
- reset vector와 entry point
- flash/RAM budget
- 보존해야 할 artifact
- 한계와 확인하지 못한 dynamic usage

## 직접 확인할 문제

1. `.bss`가 binary 파일 크기에 거의 포함되지 않아도 RAM을 소비하는 이유를 설명해 보세요.
2. `.data` 4KiB 증가가 flash와 RAM 양쪽에 영향을 줄 수 있는 이유를 적어 보세요.
3. ELF를 버리고 `.bin`만 보관하면 현장 crash 분석에서 잃는 정보를 나열해 보세요.
4. link-time size가 통과해도 runtime stack overflow가 발생할 수 있는 경로를 세 가지 적어 보세요.

## 이 장이 보장하지 않는 것

특정 compiler의 section 이름, vendor boot image format과 flash tool 명령은 프로젝트마다 다릅니다. 실제 저장소의 linker script, build report, bootloader 문서와 toolchain 매뉴얼을 우선합니다.
