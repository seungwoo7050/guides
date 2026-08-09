# Bytecode, VM과 call frame

Bytecode VM은 AST interpretation보다 실행 상태를 작게 만들고, native backend보다 구현 경계를 관찰하기 쉽습니다. Opcode, operand, stack effect와 frame invariant를 명세하면 compiler와 VM을 독립적으로 검사할 수 있습니다.

## 학습 목표

- stack VM과 register VM의 차이를 설명합니다.
- opcode별 stack effect와 control-flow target을 명세합니다.
- function chunk, constant pool, local slot과 call frame을 설계합니다.
- bytecode verifier와 disassembler로 잘못된 compiler 출력을 거부합니다.

## Stack VM

Expression `1 + 2 * 3`의 예:

```text
CONST 1        stack: [1]
CONST 2        stack: [1, 2]
CONST 3        stack: [1, 2, 3]
MUL_INT        stack: [1, 6]
ADD_INT        stack: [7]
RETURN         stack: []
```

Opcode가 암묵적으로 stack top을 사용하므로 encoding이 작고 compiler가 단순합니다. 반면 temporary의 위치가 implicit해 optimization과 random access가 어려울 수 있습니다.

## Register VM

```text
LOADK r0, 1
LOADK r1, 2
LOADK r2, 3
MUL   r1, r1, r2
ADD   r0, r0, r1
RET   r0
```

Data flow가 명시적이지만 instruction operand가 많고 register allocation 또는 virtual register 관리가 필요합니다. Mica capstone은 stack VM을 사용합니다.

## Bytecode unit

```text
Module
  constants
  functions
  entry_function

FunctionChunk
  name
  arity
  local_count
  code[]
  source_map[]
```

Constant pool에는 integer와 string literal을 둘 수 있습니다. Function reference는 stable FunctionId를 사용합니다.

## Opcode 명세

각 opcode에 다음을 기록합니다.

- encoding과 operand width
- precondition
- stack input/output
- control-flow successor
- runtime failure
- source origin

예:

```text
ADD_INT
pre: stack[-2], stack[-1] are Int
stack: [..., left, right] -> [..., result]
may fail: checked overflow R4002
next: ip + 1
```

```text
JUMP_IF_FALSE target
pre: stack top is Bool
stack: [..., condition] -> [...]
next: target if false else ip + 1
```

Stack effect table은 [Mica bytecode 명세](../../exercises/08-mica-capstone/spec/bytecode.md)에 있습니다.

## Compiler emission

AST의 recursive structure를 postfix instruction으로 낮춥니다.

```text
emit(Binary(Add, left, right)):
  emit(left)
  emit(right)
  emit(ADD_INT)
```

Short-circuit는 jump patching이 필요합니다.

```text
emit(left)
emit_jump_if_false(end)
emit(right)
patch(end)
```

Target offset이 instruction index인지 byte offset인지 고정합니다. Variable-width encoding에서 두 값을 혼동하면 잘못된 jump를 만듭니다.

## Local slot

Resolution/type phase가 symbol에 local slot을 할당하거나 bytecode lowering이 lifetime을 계산해 재사용할 수 있습니다.

단순한 capstone:

```text
slot 0..arity-1: parameter
그 뒤: local declaration 순서
```

Shadowed local은 다른 slot을 사용합니다. Scope exit 뒤 slot을 재사용하는 최적화는 debug 정보와 capture를 고려해야 하므로 선택 확장입니다.

## Call frame

Stack 하나에서 operand와 local을 함께 둘 수 있습니다.

```text
value_stack
[caller locals][arguments][callee locals][temporaries]
              ^ frame.base
```

Frame:

```text
function_id
ip
base
return_ip / caller frame index
```

`LOAD_LOCAL n`은 `stack[base + n]`을 읽습니다. Call 전 argument 수와 callee arity를 검사합니다. Return은 result를 보존하고 callee 영역을 제거한 뒤 caller stack에 result 하나를 놓습니다.

## Verifier

VM이 arbitrary bytecode를 받는다면 실행 전에 구조를 검사합니다.

- opcode와 operand가 유효합니다.
- jump target이 instruction boundary입니다.
- 모든 reachable path에서 stack depth가 음수가 되지 않습니다.
- merge point의 stack shape가 일치합니다.
- local index가 `local_count` 범위 안입니다.
- call target과 arity가 유효합니다.
- 함수 끝은 return 또는 terminal opcode입니다.

Stack depth는 CFG data-flow로 계산할 수 있습니다. Merge predecessor가 다른 depth를 만들면 verifier가 거부합니다.

Trusted compiler output만 실행해도 verifier는 compiler bug를 빨리 찾는 데 유용합니다.

## Dispatch loop

```text
while true:
    instruction = code[ip]
    ip += 1
    match instruction.opcode:
        ...
```

Threaded dispatch, computed goto와 JIT는 성능 확장입니다. 먼저 deterministic trace와 오류를 구현합니다.

Runtime loop invariant:

- `ip`는 현재 function code 범위 안입니다.
- frame `base`는 stack 범위 안입니다.
- opcode precondition이 만족됩니다.
- instruction budget이 감소합니다.

## Source map과 disassembler

Instruction마다 source span을 복사하면 크기가 커질 수 있습니다. Run-length table을 사용할 수 있습니다.

```text
instruction range [0, 4) → source span A
[4, 7) → source span B
```

Disassembler는 function, offset, opcode, operand, stack effect와 source line을 출력합니다. Compiler와 VM의 중간 계약을 관찰하는 핵심 도구입니다.

## Serialization과 version

Bytecode 파일을 저장하면 format version과 compatibility가 필요합니다.

```text
magic
format_version
language_version
target/runtime capabilities
constant/function tables
checksum 선택
```

같은 process 안에서만 사용하는 capstone은 JSON 또는 memory object로 시작할 수 있습니다. Portable artifact라고 부르려면 endianness, integer width, validation과 version 정책을 정의합니다.

## 대표 실패

- jump target을 instruction index와 byte offset으로 혼동합니다.
- `RETURN`이 callee temporary를 stack에 남깁니다.
- merge block의 stack depth가 predecessor마다 다릅니다.
- local slot이 shadowing된 symbol을 덮어씁니다.
- compiler가 잘못 만든 bytecode를 VM이 host `IndexError`로 crash합니다.
- source map이 optimization 뒤 오래된 instruction offset을 가리킵니다.
- untrusted bytecode를 verifier 없이 실행합니다.

## 실습 연결

[Interpreter와 VM exercise](../../exercises/04-interpreter-and-vm/README.md), `examples/bytecode-vm`과 [Mica bytecode 명세](../../exercises/08-mica-capstone/spec/bytecode.md)를 사용합니다. Capstone VM 경로는 disassemble output과 verifier 실패 fixture를 포함해야 합니다.

## 점검 질문

1. stack VM에서 merge point의 stack shape가 같아야 하는 이유는 무엇입니까?
2. local slot과 operand stack을 같은 array에 둘 때 frame base는 무엇을 가리킵니까?
3. short-circuit emission에서 어떤 jump를 patch합니까?
4. trusted compiler output에도 verifier가 유용한 이유는 무엇입니까?
5. bytecode를 file artifact로 만들 때 memory object보다 추가되는 계약은 무엇입니까?
