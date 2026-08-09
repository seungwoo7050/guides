# 함수, closure와 runtime error

함수 호출은 새 local scope를 만드는 것 이상입니다. argument 평가, parameter binding, call frame, return, recursion, capture와 stack/resource limit이 하나의 동적 계약을 이룹니다. Closure를 지원하면 lexical scope의 lifetime이 함수 호출보다 길어집니다.

## 학습 목표

- function declaration, function value와 activation을 구분합니다.
- call frame의 저장 상태와 recursion을 설명합니다.
- closure capture를 cell/upvalue로 모델링합니다.
- runtime error에 source call stack과 안정적인 code를 연결합니다.

## 세 개의 함수 개념

### Function declaration

Source에 있는 이름, parameter, return type와 body입니다.

### Function value

실행 중 변수에 저장하거나 argument로 전달할 수 있는 callable입니다. Top-level function만 호출하는 언어에서는 `FunctionId`로 충분할 수 있습니다.

### Activation / call frame

특정 호출 한 번의 parameter, local, return point와 temporary state입니다. Recursion은 같은 declaration으로 여러 activation을 만듭니다.

이 셋을 같은 객체로 취급하면 recursive call이 local state를 덮어씁니다.

## Call 순서

Mica의 호출 계약:

1. callee를 결정합니다.
2. argument를 source 순서대로 평가합니다.
3. argument 개수와 runtime representation을 검증합니다.
4. 새 frame을 만듭니다.
5. parameter slot에 값을 binding합니다.
6. body를 실행합니다.
7. return value를 caller에 전달합니다.
8. frame을 제거합니다.

Static checker가 3의 type 조건을 보장해도 VM corruption이나 FFI 경계를 위해 internal check를 둘 수 있습니다.

## Call frame

Tree-walk interpreter:

```text
Frame
  function_id
  environment
  call_site_span
```

Bytecode VM:

```text
Frame
  function_id
  instruction_pointer
  base_stack_index
  local_count
  call_site_origin
```

Native backend에서는 ABI가 parameter·return·callee-saved state와 stack layout을 결정합니다. 이 문서는 language-level frame을 다루고 실제 register/stack 규칙은 `computer-architecture`와 ABI 문서로 연결합니다.

## Recursion과 limit

```text
fn fact(n: Int) -> Int {
    if n <= 1 { return 1; }
    return n * fact(n - 1);
}
```

Tail call optimization을 보장하지 않으면 각 호출은 frame을 추가합니다. Host Python recursion을 그대로 사용하면 target stack limit과 host limit이 섞입니다.

정책:

- 명시적인 call depth limit
- bytecode VM의 own frame stack
- tail call을 language guarantee로 둘지 optimization으로 둘지 명시

Mica core는 tail call elimination을 보장하지 않고 runtime configuration의 call-depth limit을 초과하면 `R4003`을 반환합니다.

## Closure

Nested function이 outer binding을 capture합니다.

```text
fn outer() -> Fn {
    var n: Int = 0;
    fn next() -> Int {
        n = n + 1;
        return n;
    }
    return next;
}
```

`outer` frame이 종료된 뒤에도 `n`이 살아 있어야 합니다.

### Cell model

```text
local slot n -> Cell(value=0)
closure captures Cell pointer
```

Mutable capture를 여러 closure가 공유하면 같은 cell을 봅니다.

### Upvalue model

VM은 stack local을 open upvalue로 가리키다가 frame 종료 시 heap object로 close할 수 있습니다.

```text
open:  stack slot reference
closed: heap-stored value
```

Open upvalue 목록, close 순서와 duplicate capture가 runtime invariant입니다.

## Capture 분석

Resolution phase가 각 reference의 lexical depth와 captured symbol을 기록합니다.

```text
Local(symbol, slot)
Upvalue(symbol, upvalue_index)
Global(function_id)
Builtin(id)
```

Runtime이 이름을 다시 검색해 capture를 추측하지 않습니다. Closure conversion을 사용하면 hidden environment parameter와 explicit field access로 낮출 수 있습니다.

## Runtime error model

```text
RuntimeDiagnostic
  code
  message
  primary source origin
  call frames
  notes
```

예:

```text
runtime error[R4001]: division by zero
  --> math.mica:8:17
stack:
  divide at math.mica:8
  calculate at main.mica:3
  main at main.mica:1
```

Call stack에는 함수 이름뿐 아니라 call site를 기록합니다. Optimization과 inlining이 있으면 inline origin chain이 필요합니다.

## Panic, trap, exception을 구분합니다

- language runtime error: 명세가 정의한 사용자 프로그램 실패
- trap: backend가 즉시 중단시키는 low-level operation
- exception: catch 가능한 language control flow일 수 있음
- panic/internal error: compiler/runtime invariant 위반

Mica는 catch 가능한 exception을 지원하지 않습니다. Division by zero와 overflow는 diagnostic을 출력하고 프로그램을 종료하는 정의된 runtime error입니다.

## FFI 오류

Host function이 exception을 던지거나 잘못된 value를 반환할 수 있습니다.

정책을 명시합니다.

- 어떤 host exception을 target runtime error로 변환합니까?
- resource cleanup은 누가 합니까?
- host stack trace를 사용자에게 노출합니까?
- callback이 target VM으로 재진입할 수 있습니까?

FFI는 type checker가 보장할 수 없는 trust boundary입니다. Validation과 sandbox가 별도 필요합니다.

## 대표 실패

- Function declaration object에 local state를 저장해 recursion이 충돌합니다.
- closure가 종료된 stack slot을 가리킵니다.
- capture한 mutable value를 복사해 closure끼리 상태가 공유되지 않습니다.
- host recursion limit을 target language guarantee로 문서화합니다.
- runtime error가 현재 expression span만 보여 주고 call site를 잃습니다.
- internal VM bug를 division-by-zero 같은 사용자 오류로 변환합니다.

## 실습 연결

[Interpreter와 VM exercise](../../exercises/04-interpreter-and-vm/README.md)에서 recursive call frame과 optional closure cell을 구현합니다. Mica 핵심 capstone은 top-level function만 요구하며 closure는 선택 확장입니다.

## 점검 질문

1. function declaration과 activation을 같은 객체로 두면 recursion에서 무엇이 깨집니까?
2. mutable capture는 value copy와 cell 중 무엇을 요구합니까?
3. open upvalue는 언제 close합니까?
4. tail call은 language semantics와 optimization 중 어디에 속합니까?
5. runtime error stack에서 declaration span과 call site span은 어떤 역할을 합니까?
