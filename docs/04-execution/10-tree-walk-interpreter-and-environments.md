# Tree-walk interpreter와 environment

Tree-walk interpreter는 AST의 동적 의미를 가장 직접적으로 실행합니다. 빠른 실행보다 언어 규칙을 명시적인 상태 전이로 확인하는 데 적합하며, 이후 bytecode·LLVM backend의 기준 oracle로도 사용할 수 있습니다.

## 학습 목표

- expression evaluation과 statement execution의 결과를 구분합니다.
- lexical environment, variable slot과 mutability를 모델링합니다.
- evaluation order와 short-circuit를 명시합니다.
- return과 runtime error를 host exception에 무분별하게 섞지 않습니다.

## 실행 상태

단순 interpreter의 상태:

```text
InterpreterState
  current_environment
  call_stack
  output_sink
  instruction_budget
  runtime_configuration
```

Expression은 value를 만들고 statement는 control outcome을 만들 수 있습니다.

```text
evaluate(expr, env) -> Value | RuntimeError
execute(stmt, env)  -> Continue | Return(Value) | RuntimeError
```

`return`을 일반 value로 표현하면 block loop가 계속 실행될 수 있습니다. Control outcome을 별도 tagged result로 두면 함수 경계를 명확히 처리할 수 있습니다.

## Environment와 location

Immutable `let`과 mutable `var`를 지원하면 이름이 바로 value를 가리키는지, mutable location을 가리키는지 구분해야 합니다.

```text
Environment: SymbolId -> Binding
Binding:
  immutable Value
  mutable Cell(Value)
```

Name resolution을 완료한 뒤에는 runtime lookup을 문자열로 하지 않고 SymbolId 또는 local slot으로 할 수 있습니다. 문자열 lookup은 초기 prototype에 편리하지만 shadowing과 rename bug를 숨길 수 있습니다.

## Lexical scope

Block 진입 시 child environment를 만들고 종료 시 parent로 돌아갑니다.

```text
execute_block(statements, child(parent=current))
```

다음 조건을 확인합니다.

- block local은 밖에서 보이지 않습니다.
- outer immutable binding을 assignment할 수 없습니다.
- shadowing은 새 binding을 만들고 outer value를 변경하지 않습니다.
- runtime error나 return으로 빠져나가도 current environment를 원래 상태로 복원합니다.

Host의 `try/finally` 또는 명시적 context stack을 사용해 cleanup을 보장할 수 있습니다.

## Evaluation order

언어가 function argument를 왼쪽에서 오른쪽으로 평가한다고 정했다면 interpreter loop가 그 순서를 보존해야 합니다.

```text
f(first(), second())
```

두 함수가 output이나 mutable state를 바꾸면 순서가 관찰됩니다. Host language의 container iteration에 맡기지 않습니다.

Binary expression도 같은 계약이 필요합니다. Mica는 왼쪽 operand를 먼저 평가하고 runtime error가 나면 오른쪽을 실행하지 않습니다.

## Short-circuit

`&&`와 `||`는 일반 binary operator와 다릅니다.

```text
a && b
1. a 평가
2. false면 false 반환
3. true일 때만 b 평가
```

Generic `evaluate(left); evaluate(right); apply(op)` 구조에 넣으면 오른쪽 effect가 잘못 실행됩니다. Parser precedence와 interpreter evaluation이 같은 연산자 table을 공유하더라도 short-circuit handler는 별도로 둡니다.

## Statement execution

Block:

```text
for statement in statements:
    outcome = execute(statement)
    if outcome != Continue:
        return outcome
return Continue
```

`if`는 condition이 Bool이라는 static 보장을 전제로 하지만 internal consistency check를 남길 수 있습니다. Typed tree를 우회한 test input이 들어오면 internal error로 구분합니다.

`while`은 다음 budget을 고려합니다.

- iteration limit 또는 global step budget
- cancellation
- output/resource limit
- runtime error propagation

학습용 interpreter가 무한 loop로 verifier를 멈추지 않도록 capstone runner는 timeout을 사용합니다.

## Builtin과 외부 effect

Builtin을 일반 function symbol처럼 등록하면 resolution·type checking과 runtime dispatch를 연결하기 쉽습니다.

```text
BuiltinSymbol(
  name="print_int",
  type=Fn([Int], Unit),
  implementation=host_print_int
)
```

하지만 semantic type과 host callable pointer를 같은 public structure에 묶지 않습니다. Compiler service가 AST를 serialize할 때 host 객체가 섞일 수 있습니다.

Output은 직접 `stdout`에 쓰기보다 `OutputSink` interface를 통해 test에서 capture합니다.

## Runtime value representation

Mica core의 값:

```text
IntValue(i64)
BoolValue(bool)
StringValue(utf8/host string)
UnitValue
FunctionValue(FunctionId)
```

Host의 `bool`이 `int`의 subtype인 언어에서는 `True + 1`이 우연히 실행될 수 있습니다. Tagged wrapper 또는 명시적 kind check로 target language의 type을 보존합니다.

## Checked arithmetic

Mica `Int`는 signed 64-bit이고 overflow는 runtime error입니다. Python profile은 host integer가 무제한이므로 연산 뒤 범위를 직접 검사합니다.

```text
MIN = -2^63
MAX = 2^63 - 1
if result < MIN or result > MAX:
    RuntimeError(R4002, operator_span)
```

Division은 0 검사뿐 아니라 `MIN / -1` overflow를 확인합니다. Integer division rounding 정책도 명세합니다.

## Return 처리

Host exception을 `return` signal로 사용할 수 있지만 모든 exception을 잡아 return으로 해석하면 내부 bug를 숨깁니다.

안전한 선택:

- `ReturnOutcome(value)` tagged result
- private `ReturnSignal` exception만 catch

Host `KeyError`, `IndexError` 또는 assertion은 internal error로 남겨야 합니다.

## Interpreter를 oracle로 사용합니다

Bytecode compiler나 optimizer의 결과를 tree-walk interpreter와 비교할 수 있습니다.

```text
same source
→ typed AST interpreter result
→ bytecode VM result
→ stdout, return value, runtime error code 비교
```

두 구현이 같은 parser/type checker bug를 공유할 수 있으므로 완전한 증명은 아닙니다. 그래도 execution backend 차이를 찾는 강한 differential test입니다.

## 대표 실패

- runtime name lookup을 text로 해 shadowed symbol을 혼동합니다.
- block exit 전 environment를 복원하지 않습니다.
- host `bool`과 `int` 관계가 target type 규칙을 침범합니다.
- function argument 평가 순서가 map iteration에 따라 달라집니다.
- short-circuit 오른쪽을 항상 실행합니다.
- 모든 host exception을 사용자 runtime error로 바꿔 compiler bug를 숨깁니다.
- Python의 arbitrary precision 때문에 target overflow를 놓칩니다.

## 실습 연결

[Interpreter와 VM exercise](../../exercises/04-interpreter-and-vm/README.md)에서 typed AST evaluator와 output sink를 구현합니다. Mica capstone runner는 정상 출력과 runtime error code를 확인합니다.

## 점검 질문

1. environment가 value와 mutable cell을 구분해야 하는 이유는 무엇입니까?
2. return을 일반 expression value로 처리하면 어떤 문제가 생깁니까?
3. host language value와 target language value를 직접 공유할 때 어떤 차이가 새어 나옵니까?
4. tree-walk interpreter가 bytecode backend의 oracle이 될 수 있는 범위는 어디까지입니까?
5. timeout과 step budget은 language semantics입니까, 실행 정책입니까?
