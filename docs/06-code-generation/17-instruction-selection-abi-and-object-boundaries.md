# Instruction selection, ABI와 object 경계

Backend는 IR operation을 target이 실행할 수 있는 instruction과 artifact로 낮춥니다. 이 과정은 단순 opcode 치환이 아니라 target data layout, legal type, register class, calling convention, relocation과 unwind 정보를 함께 만족해야 합니다.

## 학습 목표

- target-independent IR과 target-specific machine operation의 경계를 설명합니다.
- instruction selection, legalization, scheduling과 register allocation의 책임을 구분합니다.
- ABI가 call·stack·object interoperability에 제공하는 계약을 이해합니다.
- object file이 final address가 없는 상태에서 symbol과 relocation을 보존하는 이유를 설명합니다.

## Target description

Backend가 최소한 알아야 하는 정보:

```text
target triple
CPU/features
endianness
pointer width
integer/float legal widths
data layout와 alignment
calling convention
object format
relocation model
```

같은 IR이라도 target feature에 따라 instruction과 ABI가 달라질 수 있습니다. `x86-64`라는 이름만으로 OS ABI, object format과 feature set이 모두 정해지지 않습니다.

[`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture)는 ISA·pipeline·cache·실제 성능 모델을 소유합니다. 이 문서는 compiler가 그 경계에 전달하는 표현을 다룹니다.

## Legalization

IR이 target이 직접 지원하지 않는 type이나 operation을 포함할 수 있습니다.

예:

- 128-bit integer를 64-bit pair operation으로 분해
- integer remainder를 division sequence로 낮춤
- vector width를 smaller vector/scalar operation으로 분할
- boolean representation을 target convention에 맞춤

Legalization은 의미를 보존해야 합니다. Signedness, overflow, shift count와 floating semantics를 target instruction에 정확히 매핑합니다.

## Instruction selection

Tree pattern 예:

```text
add(mul(x, 2), y)
```

Target에 fused addressing mode나 multiply-add가 있을 수 있습니다. 선택 방식:

- tree pattern matching
- DAG selection
- rule-based rewrite
- global instruction selection

가장 적은 instruction이 항상 가장 빠른 것은 아닙니다. Latency, throughput, register pressure, code size와 feature availability를 고려합니다.

Mica 핵심 capstone은 native selector 구현을 요구하지 않습니다. 선택 과제에서는 작은 virtual ISA 또는 LLVM IR을 target으로 사용합니다.

## Machine IR와 virtual register

Instruction selection 뒤에도 실제 physical register를 바로 정하지 않을 수 있습니다.

```text
vreg1 = LOAD_CONST 1
vreg2 = ADD vreg0, vreg1
```

Machine instruction, register class, implicit flags와 clobber를 표현해야 합니다. Target instruction이 condition code를 암묵적으로 쓰고 만들면 data dependency에 포함합니다.

## Register allocation

Virtual register를 제한된 physical register와 spill slot에 배치합니다.

기본 단계:

1. liveness interval 또는 interference graph를 계산합니다.
2. register class와 fixed register constraint를 적용합니다.
3. 배치하지 못한 value를 stack에 spill합니다.
4. spill load/store를 삽입하고 필요하면 다시 할당합니다.

Linear scan은 JIT/작은 compiler에 단순하고 graph coloring은 더 복잡한 최적화를 가능하게 합니다. 구현보다 중요한 것은 call, clobber, subregister와 stack map 계약입니다.

## Calling convention

ABI는 다음을 정합니다.

- argument와 return을 register/stack 어디에 둡니까?
- caller-saved와 callee-saved register는 무엇입니까?
- stack alignment는 얼마입니까?
- aggregate를 value로 전달합니까, hidden pointer를 사용합니까?
- variadic call과 exception unwind는 어떻게 합니까?
- symbol naming과 linkage는 어떻게 합니까?

Compiler-generated function끼리만 호출해도 runtime·debugger·FFI와 연결하려면 일관된 convention이 필요합니다.

## Stack frame

대표 구성 요소:

```text
return address / caller state
saved registers
spill slots
local allocation
outgoing arguments
alignment padding
```

Frame pointer를 유지할지 생략할지, dynamic allocation과 unwind가 있는지에 따라 layout이 달라집니다. Source local과 stack slot은 일대일이 아닐 수 있습니다.

Prologue/epilogue는 다음 invariant를 지킵니다.

- callee-saved register 복원
- stack pointer와 alignment 복원
- unwind/debug metadata와 실제 frame 일치
- 모든 return path에서 cleanup 수행

## Object file

Compiler가 최종 주소를 모르는 상태에서 machine code를 object file로 만듭니다.

대표 내용:

- code section
- read-only/data/bss section
- symbol table
- relocation entry
- debug/unwind section
- section alignment와 visibility

External function call의 target address는 link 시점에 정해질 수 있습니다. Instruction 안의 빈 위치와 적용 방법을 relocation으로 남깁니다.

```text
relocation
  place: section + offset
  symbol: target symbol
  kind: absolute / PC-relative / GOT/PLT 등
  addend
```

Relocation 종류는 target·object format에 따라 다릅니다. 구체 표는 공식 ABI를 확인합니다.

## Position independence

Shared library와 ASLR 환경에서는 code/data가 고정 address에 있다는 가정을 피해야 합니다. PC-relative addressing, GOT/PLT 또는 target-specific relocation model을 사용합니다.

“position independent”는 모든 pointer가 상대값이라는 뜻이 아니라 loader가 임의 base에 배치할 수 있도록 필요한 reference를 표현했다는 뜻입니다.

## Unwind와 debug 경계

Exception을 지원하지 않아도 profiler와 stack trace가 unwind 정보를 사용할 수 있습니다. Optimization이 frame을 바꾸면 metadata도 갱신해야 합니다.

Debug location은 source line 하나만이 아닙니다.

- lexical scope
- variable location range
- inlined call chain
- optimized-out state
- prologue/epilogue boundary

정확한 machine state가 없는 변수를 debugger에 있는 것처럼 보고하지 않습니다.

## Backend verifier와 inspection

- machine instruction operand/register class 검사
- branch target과 block layout 검사
- stack frame alignment 계산
- callee-saved save/restore 검사
- object parser로 section/symbol/relocation 확인
- disassembler와 assembler round-trip 가능한 범위 확인
- small program을 reference interpreter와 비교

실제 execution test만으로 모든 ABI 위반을 찾을 수 없습니다. 우연히 register가 보존되어 통과할 수 있으므로 구조 검사와 stress call을 함께 사용합니다.

## 대표 실패

- IR `Bool`을 target ABI의 return representation과 다르게 전달합니다.
- call이 clobber하는 register를 allocator가 live value에 유지합니다.
- stack alignment가 variadic/native call 전에 깨집니다.
- relocation offset이 instruction field가 아니라 instruction 시작을 가리킵니다.
- prologue와 unwind metadata가 다릅니다.
- target feature가 없는 instruction을 emit합니다.
- instruction count만으로 selection 품질을 판단합니다.

## 실습 연결

[Backend 경계 exercise](../../exercises/06-backend-boundaries/README.md)에서 작은 three-address IR을 virtual ISA로 낮추고 call convention 표를 작성합니다. LLVM 경로를 선택하면 다음 문서의 verifier/object inspection을 사용합니다.

## 점검 질문

1. legalization과 instruction selection은 어떻게 다릅니까?
2. call instruction이 register allocator에 알려야 하는 implicit clobber는 무엇입니까?
3. object file이 final function address 대신 relocation을 저장하는 이유는 무엇입니까?
4. stack frame과 debug variable location이 일대일이 아닌 이유는 무엇입니까?
5. native execution 성공만으로 ABI 준수를 증명할 수 없는 이유는 무엇입니까?
