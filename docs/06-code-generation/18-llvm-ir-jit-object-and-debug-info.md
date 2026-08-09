# LLVM IR, JIT, object와 debug information

LLVM은 typed SSA 기반 IR, 분석·최적화, target code generation과 JIT infrastructure를 제공합니다. LLVM을 사용하면 backend 전체를 직접 만들 필요는 줄지만 source language의 semantics, well-formed IR와 runtime ABI를 compiler가 올바르게 제공해야 합니다.

## 학습 목표

- LLVM IR module, function, basic block, instruction과 value model을 이해합니다.
- LLVM verifier가 확인하는 well-formedness와 확인하지 않는 source semantics를 구분합니다.
- AOT object emission과 ORC JIT의 수명·symbol 경계를 설명합니다.
- debug information이 optimization과 source origin에 어떻게 연결되는지 이해합니다.

## LLVM IR은 target-neutral에 가깝지만 target-free가 아닙니다

LLVM IR은 typed SSA representation이며 memory operation, control flow, call과 target data layout을 표현합니다.

```llvm
 define i64 @add(i64 %a, i64 %b) {
 entry:
   %sum = add i64 %a, %b
   ret i64 %sum
 }
```

Module에는 target triple과 data layout이 들어갈 수 있습니다. Pointer size, alignment와 ABI lowering에 영향을 주므로 실제 code generation 전에 target machine과 일치해야 합니다.

## Value와 instruction

많은 LLVM instruction은 result value이기도 합니다.

```text
Instruction ∈ Value
Argument ∈ Value
Constant ∈ Value
```

SSA use-def chain을 통해 optimization이 값을 추적합니다. Memory는 일반 SSA value처럼 자동 versioning되지 않으므로 alias analysis와 memory model이 필요합니다.

## Basic block과 terminator

각 basic block은 terminator로 끝나야 합니다.

- `br`
- `switch`
- `ret`
- `unreachable`
- exception-related terminator

Phi node는 predecessor edge에 맞는 incoming value를 가집니다. Newer compiler architecture에서는 자체 MIR block parameter를 LLVM phi로 낮출 수 있습니다.

## Verifier

LLVM verifier는 다음 종류를 확인합니다.

- type과 operand compatibility
- definition/use와 dominance
- phi predecessor 관계
- terminator와 function structure
- 일부 attribute·calling convention invariant

Verifier가 통과한다고 Mica semantics가 맞는 것은 아닙니다.

예:

- short-circuit를 eager call로 잘못 낮춰도 LLVM IR은 well-formed일 수 있습니다.
- checked overflow를 plain `add`로 낮춰 trap을 잃어도 verifier는 모릅니다.
- argument evaluation order를 바꿔도 IR 자체는 유효할 수 있습니다.

Source language contract는 differential/conformance test로 별도 검증합니다.

## `undef`, poison과 undefined behavior

LLVM IR은 source language보다 강한 optimization 의미를 가진 값과 조건을 포함합니다. 잘못된 `nsw`, `nuw`, `inbounds`, alignment, dereferenceable attribute를 붙이면 실제 source가 허용하는 실행을 undefined/poison으로 바꾸고 miscompile을 만들 수 있습니다.

원칙:

- 증명한 property만 attribute/flag로 전달합니다.
- source overflow가 trap이면 overflow intrinsic과 explicit branch/trap을 고려합니다.
- uninitialized source value를 편의상 `undef`로 넣지 않습니다.
- verifier 통과와 semantic correctness를 동일시하지 않습니다.

구체 의미는 사용 중인 LLVM Language Reference를 확인합니다.

## IR construction

Builder API는 insertion point와 type을 관리하지만 phase contract는 compiler가 담당합니다.

권장 흐름:

```text
create module/context
→ declare runtime/builtin signature
→ predeclare user functions
→ emit function bodies
→ verify each function/module
→ optional optimization pipeline
→ verify again
→ execute or emit artifact
```

Function body emission 전에 signature를 모두 선언하면 forward call과 recursion을 처리할 수 있습니다.

## Runtime builtin

Mica `print_int`를 native runtime function으로 선언할 수 있습니다.

```llvm
 declare void @mica_print_int(i64)
```

Compiler와 runtime이 같은 symbol name, calling convention, integer width와 ownership을 사용해야 합니다. JIT에서는 process symbol을 lookup하거나 explicit absolute symbol로 등록할 수 있습니다.

## AOT object emission

```text
LLVM IR
→ target machine
→ optimization/codegen pipeline
→ object bytes
→ system linker
→ executable/shared library
```

Object emission 뒤 section·symbol·relocation을 검사하고 runtime library와 link합니다. Target triple과 linker가 서로 다른 platform을 가리키면 실패할 수 있습니다.

## ORC JIT 경계

현대 LLVM JIT는 ORC API 계열을 사용합니다. 개념적 구성:

- execution session
- JIT dylib / symbol table
- materialization unit
- object linking layer
- resource tracker

중요한 수명:

- LLVM context/module가 compile task 동안 살아 있음
- JIT에 추가된 code와 data의 resource owner
- 제거할 module의 symbol·memory cleanup
- host runtime symbol과 target symbol resolution
- concurrent compilation과 thread-safe context

“JIT에 module을 추가했다”는 것과 “모든 symbol이 지금 materialized됐다”는 것이 같지 않을 수 있습니다. Lazy compilation 정책을 문서화합니다.

## JIT sandbox

JIT code는 현재 process 권한으로 실행될 수 있습니다. 신뢰할 수 없는 source를 JIT하는 것은 parser input 처리보다 위험합니다.

- 별도 process
- memory/time/output limit
- syscall/network/file restriction
- runtime builtin allowlist
- crash isolation
- generated object 검증

학습 capstone의 LLVM 경로는 신뢰한 fixture만 사용하고 일반 사용자 source sandbox를 제공한다고 주장하지 않습니다.

## Debug information

Source language의 file, scope, subprogram, variable와 location을 metadata로 표현합니다.

필요한 mapping:

```text
SourceSnapshot/Span
→ AST/HIR origin
→ LLVM instruction debug location
→ machine location range
```

Optimization으로 instruction이 이동·합쳐지거나 variable이 constant/optimized-out이 될 수 있습니다. 잘못된 위치보다 “사용 불가”가 정확할 수 있습니다.

Inlined function은 call site와 callee source location chain을 보존합니다. Synthetic instruction에는 가장 가까운 사용자 action을 origin으로 선택하되 거짓 정밀도를 만들지 않습니다.

## Pass pipeline

LLVM default pipeline을 그대로 사용해도 source semantics에 맞는 IR를 제공해야 합니다. Custom pass를 추가하면 analysis invalidation, thread safety와 pipeline position을 검토합니다.

Debug/test mode에서는 다음을 실행합니다.

```text
verify before pipeline
→ run pass pipeline
→ verify after pipeline
→ differential execute against interpreter
```

IR text snapshot은 유용하지만 LLVM version에 따라 canonical print가 달라질 수 있으므로 structural test와 함께 사용합니다.

## 대표 실패

- target data layout 없이 host 기본값에 의존합니다.
- checked overflow에 `nsw`를 무조건 붙입니다.
- runtime function signature가 compiler declaration과 다릅니다.
- JIT module/resource tracker를 잃어 code memory를 제거하지 못합니다.
- untrusted source를 같은 process JIT로 실행합니다.
- debug location이 모든 instruction에 function 전체 span을 가리킵니다.
- verifier 통과를 source semantics 검증으로 오해합니다.

## 실습 연결

[Backend 경계 exercise](../../exercises/06-backend-boundaries/README.md)와 [LLVM 구현 프로필](../90-implementation-profiles/llvm.md)을 따릅니다. LLVM은 선택 확장이며 설치되지 않은 환경에서 branch 기본 검증이 실패하지 않습니다.

## 점검 질문

1. LLVM verifier가 확인하지 못하는 source-language 오류는 무엇입니까?
2. `nsw` 같은 flag를 잘못 붙이면 왜 optimization bug가 됩니까?
3. JIT symbol과 code memory의 수명은 누가 소유합니까?
4. AOT object와 JIT module은 runtime builtin을 어떻게 resolve합니까?
5. debug information에서 정확한 위치를 제공할 수 없는 경우 무엇을 해야 합니까?
