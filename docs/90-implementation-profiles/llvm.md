# LLVM 구현 프로필

LLVM은 Mica capstone의 선택 backend입니다. 이 프로필은 특정 LLVM release의 C++ API를 복사하는 문서가 아니라 LLVM IR와 JIT/AOT 경계에서 반드시 고정해야 할 계약을 제시합니다. 실제 API와 build option은 사용하는 release의 공식 문서를 확인합니다.

## 선행 완료

- typed Mica AST 또는 verified MIR
- evaluation order와 checked arithmetic 명세
- runtime builtin ABI
- interpreter conformance result

Frontend가 안정되기 전에 LLVM을 붙이면 source semantics bug와 API integration bug를 구분하기 어렵습니다.

## 최소 범위

지원:

- `Int`, `Bool`, `String`의 제한된 representation
- top-level function
- local variable
- if/while/return
- direct call
- print builtin

제외:

- closure
- GC moving object
- exception/unwind
- generic
- dynamic loading

## Module setup

기록할 것:

- target triple
- data layout
- source module identifier
- runtime declaration signature
- optimization level
- LLVM version/toolchain

Host execution만 하더라도 target machine의 data layout을 module과 일치시킵니다.

## Type mapping 예

```text
Mica Int    → i64
Mica Bool   → i1 내부, ABI boundary는 명시
Mica Unit   → void 또는 no-result convention
Mica String → runtime handle 또는 {ptr, length} contract
```

String layout을 임의로 LLVM struct에 박아 넣기 전에 ownership와 runtime ABI를 정합니다.

## Emission 순서

```text
1. 모든 function prototype 선언
2. runtime builtin 선언
3. function body block 생성
4. expression/control-flow lowering
5. function verifier
6. module verifier
7. optional pass pipeline
8. verifier 재실행
```

Forward call과 recursion 때문에 prototype pass를 먼저 수행합니다.

## Checked arithmetic

Plain `add i64`는 modulo result를 만들고, `nsw`를 붙이면 overflow 시 poison 의미를 도입합니다. Mica는 overflow diagnostic을 요구하므로 다음 중 하나를 사용합니다.

- overflow intrinsic + flag branch
- explicit range logic
- trusted runtime helper

`nsw`만 붙이고 trap을 생성하지 않는 것은 Mica semantics가 아닙니다.

## Short-circuit와 phi

`&&`/`||`는 block과 branch로 낮추고 merge에서 phi 또는 MIR block parameter lowering을 사용합니다. 오른쪽 expression을 entry에서 미리 emit하지 않습니다.

## Local variable

단순 경로는 entry block에 `alloca`, load/store와 `mem2reg` promotion을 사용할 수 있습니다. `alloca`를 현재 insertion point마다 만들면 loop에서 runtime allocation 의미가 달라질 수 있으므로 정책을 정합니다.

SSA MIR에서 바로 LLVM SSA value/phi로 낮추는 경로도 가능합니다.

## Runtime와 symbol

AOT:

```text
object + runtime library → system linker → executable
```

JIT:

```text
module → ORC layers → symbol materialization
runtime symbols registered/lookup
```

Builtin symbol의 name, calling convention와 lifetime을 compiler/runtime 양쪽에서 test합니다.

## Verification

- LLVM verifier pre/post optimization
- IR dump는 debug artifact로 저장
- interpreter vs JIT/AOT stdout/return/runtime error
- object section/symbol inspection
- wrong runtime signature known-bad
- checked overflow fixture

Verifier는 Mica semantics를 증명하지 않으므로 differential test를 생략하지 않습니다.

## Debug information 선택

최소:

- compile unit/file
- function/subprogram
- instruction source location

확장:

- lexical block
- local variable location
- inlined call

Optimization 뒤 정확하지 않은 variable location을 유지하지 않습니다.

## JIT 안전

학습 fixture 외의 source는 같은 process에서 실행하지 않습니다. 실제 서비스는 별도 process, resource limit, syscall/file/network policy와 crash isolation을 설계해야 합니다.

## 공식 자료

[공식 자료 목록](../../reference/sources.md)의 LLVM tutorial, Language Reference, ORC JIT와 debug information 문서를 사용합니다. Tutorial 예제의 global state나 단순 architecture를 production best practice로 그대로 복사하지 않습니다.
