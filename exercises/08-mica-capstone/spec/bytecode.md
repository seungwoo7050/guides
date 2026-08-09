# Mica Bytecode Specification

## 1. 목적

이 명세는 선택 VM 경로의 최소 portable contract를 정합니다. 특정 binary encoding은 정하지 않습니다. JSON, Python object 또는 compact binary를 사용할 수 있지만 module dump와 verifier 결과를 재현할 수 있어야 합니다.

## 2. Module

```text
Module
- version: 1
- constants: [Int | Bool | String | Unit]
- functions: [Function]
- entry: function index of main
- source_table: optional source identity table
```

Function:

```text
Function
- name
- parameter_types
- return_type
- local_types         parameters first
- instructions
- source_map          instruction index -> source span
```

Function index, constant index와 local slot은 zero-based입니다. Parameter는 `local[0..parameter_count)`에 caller argument 순서대로 들어갑니다.

## 3. Value와 stack

VM value는 명시적 tag를 가집니다.

```text
Int(i64)
Bool(bool)
String(immutable text)
Unit
```

Operand stack은 frame마다 독립적입니다. Instruction 전후 stack effect와 type은 verifier가 결정할 수 있어야 합니다.

## 4. Instruction

아래 operand는 instruction object 또는 바로 뒤 encoded operand로 표현할 수 있습니다.

| Opcode | Operand | Stack before → after | 의미 |
|---|---|---|---|
| `CONST` | const index | `[] → [T]` | constant push |
| `LOAD_LOCAL` | slot | `[] → [T]` | local value push |
| `STORE_LOCAL` | slot | `[T] → []` | mutable/local initialization 저장 |
| `POP` | - | `[T] → []` | expression result discard |
| `UNIT` | - | `[] → [Unit]` | Unit push |
| `NEG_I64` | - | `[Int] → [Int]` | checked unary minus |
| `NOT_BOOL` | - | `[Bool] → [Bool]` | logical not |
| `ADD_I64` | - | `[Int, Int] → [Int]` | left + right, checked |
| `SUB_I64` | - | `[Int, Int] → [Int]` | checked |
| `MUL_I64` | - | `[Int, Int] → [Int]` | checked |
| `DIV_I64` | - | `[Int, Int] → [Int]` | trunc toward zero |
| `REM_I64` | - | `[Int, Int] → [Int]` | Mica remainder |
| `CMP_LT_I64` 등 | - | `[Int, Int] → [Bool]` | comparison |
| `EQ` | type tag | `[T, T] → [Bool]` | `Int/Bool/String` equality |
| `JUMP` | instruction index | unchanged | target으로 이동 |
| `JUMP_IF_FALSE` | instruction index | `[Bool] → []` | false면 target, true면 next |
| `CALL` | function index, argc | `[arg0..argN] → [Ret]` | argument order 보존 |
| `CALL_BUILTIN` | builtin id, argc | `[args] → [Ret]` | output sink effect |
| `RETURN` | - | `[Ret] → caller [Ret]` | current frame 종료 |

Stack table의 왼쪽에서 오른쪽은 push 순서이며 가장 오른쪽이 top입니다. Binary operation은 오른쪽 operand를 먼저 pop한 뒤 왼쪽을 pop하지만 의미 순서는 `left op right`입니다.

## 5. Control flow

Instruction index `0..len(instructions)-1`만 valid target입니다. Function 끝으로 fall-through할 수 없습니다. 모든 reachable path는 `RETURN`으로 끝나야 합니다.

Short-circuit는 branch로 낮춥니다. 예를 들어 `a && b`는 왼쪽을 검사한 뒤 false constant 또는 오른쪽 결과가 merge에서 하나의 `Bool`을 남겨야 합니다.

## 6. Call frame

```text
Frame
- function index
- instruction pointer
- locals
- operand stack
- caller call-site span
```

Call:

1. Argument를 왼쪽부터 caller stack에 계산합니다.
2. `CALL`이 arguments를 pop합니다.
3. 새 frame을 만들고 parameter local에 순서대로 저장합니다.
4. callee `ip = 0`에서 실행합니다.
5. `RETURN`이 return value를 caller stack에 push합니다.

`Unit`도 하나의 value로 push·return하므로 stack effect가 균일합니다.

## 7. Verifier

Module을 실행하기 전에 최소한 다음을 검사합니다.

### Structural

- version 지원
- entry/function/constant/local index 범위
- opcode와 operand shape
- jump target 유효
- source map span 유효

### Data-flow

각 instruction entry의 abstract stack type vector를 계산합니다.

- entry stack은 empty
- opcode operand type이 맞음
- underflow 없음
- branch successor의 stack vector가 정확히 같음
- `RETURN` 직전 stack은 declared return type 하나
- fall-through 없음

고정점이 끝나지 않거나 instruction 수·stack depth budget을 넘으면 module을 거부합니다.

### Optional initialized-local analysis

Compiler와 별개로 uninitialized local read를 거부할 수 있습니다. Core source의 initializer 필수와 compiler correctness가 이 오류를 막아야 하지만 malformed bytecode는 독립적으로 방어할 가치가 있습니다.

## 8. Runtime limit와 오류

- VM instruction 하나마다 execution budget을 1 감소합니다.
- `CALL` 전에 call-depth budget을 검사합니다.
- arithmetic는 source interpreter와 같은 checked i64 helper를 사용합니다.
- invalid bytecode는 runtime host exception이 아니라 실행 전 `MICA500x`로 거부합니다.
- verified module에서 impossible state가 나오면 `MICA9001`과 exit `2`입니다.

## 9. Disassembly

`disassemble FILE`은 최소 다음 정보를 안정적으로 출력합니다.

```text
function name(params) -> return
local types
instruction index, opcode, operand
stack effect 또는 inferred entry stack
source span
```

주소나 object identity처럼 실행마다 바뀌는 값은 출력하지 않습니다.

## 10. Differential 검증

같은 checked program을 interpreter와 VM으로 실행해 비교합니다.

- stdout byte sequence
- return value/tag
- runtime diagnostic code와 primary source span
- limit 정책을 같게 설정했을 때 종료 종류

실행 시간이 같을 필요는 없습니다.
