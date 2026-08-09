# Type rule, constraint와 checking

Type checker는 AST에 label을 붙이는 도구가 아니라 **어떤 연산과 상태 전이가 실행 전에 허용되는지**를 판정하는 phase입니다. 규칙을 코드의 if 문으로만 남기지 않고 입력 type, 결과 type과 실패 조건으로 표현해야 언어 명세와 구현을 함께 검토할 수 있습니다.

## 학습 목표

- type syntax, semantic type과 runtime representation을 구분합니다.
- typing judgment와 operator rule을 작성합니다.
- checking, inference, constraint와 unification의 역할을 구분합니다.
- ErrorType과 diagnostic origin으로 연쇄 오류를 통제합니다.

## 세 종류의 type 표현

### Type syntax

사용자가 source에 적은 tree입니다.

```text
Int
Fn(Int, Bool) -> String
List<Int>
```

Alias와 아직 resolve되지 않은 이름을 포함할 수 있습니다.

### Semantic type

Resolution 뒤 compiler가 동일성과 구조를 판단하는 내부 표현입니다.

```text
BuiltinType(INT)
FunctionType([INT, BOOL], STRING)
AppliedType(ListSymbol, [INT])
ErrorType(origin)
```

Alias를 유지할지 canonical type으로 펼칠지 정책을 정합니다.

### Runtime representation

같은 semantic type도 backend에서 여러 방식으로 표현될 수 있습니다.

```text
Bool  → i1 또는 tagged value
String → pointer+length 또는 managed object
```

Type checker가 특정 machine representation에 직접 묶이지 않게 합니다.

## Typing judgment

전형적인 표기:

```text
Γ ⊢ expression : Type
```

`Γ`는 symbol과 type을 담은 environment입니다.

정수 덧셈 규칙:

```text
Γ ⊢ e1 : Int    Γ ⊢ e2 : Int
-----------------------------
Γ ⊢ e1 + e2 : Int
```

조건문 조건:

```text
Γ ⊢ condition : Bool
```

이 규칙은 implementation language와 무관한 계약입니다. Code에서는 visitor, pattern matching 또는 table dispatch로 옮길 수 있습니다.

## Checking과 inference

### Synthesis

Expression에서 type을 계산합니다.

```text
42         ⇒ Int
name       ⇒ symbol type
left + right ⇒ operator rule result
```

### Checking

Expected type을 주고 expression이 맞는지 확인합니다.

```text
return expr        expected = function return type
let x: Int = expr  expected = Int
```

Bidirectional typing은 일부 node는 synthesize하고 일부 node는 expected type으로 check해 annotation 요구를 줄입니다.

Mica core는 declaration과 parameter에 type annotation을 요구하므로 local inference 범위를 expression result에 제한합니다.

## Function call

Call 검사 순서:

1. callee의 type을 구합니다.
2. callable인지 확인합니다.
3. 인자 수를 확인합니다.
4. 각 argument를 parameter type에 대해 검사합니다.
5. return type을 expression type으로 기록합니다.

Callee가 ErrorType이면 “호출할 수 없음”을 중복 보고하지 않습니다. 인자 수가 틀려도 겹치는 argument의 독립 오류를 검사할지 정책을 정합니다.

## Constraint와 unification

Annotation을 줄이거나 generic을 지원하면 equality constraint를 모을 수 있습니다.

```text
x + y
constraints:
  type(x) = Int
  type(y) = Int
  result  = Int
```

Type variable:

```text
α = List<β>
β = Int
```

Unification은 두 type 구조를 같게 만들 substitution을 계산합니다. Occurs check가 없으면 `α = List<α>` 같은 무한 type을 잘못 허용할 수 있습니다.

Constraint 생성과 해결을 분리하면 diagnostic origin을 잃기 쉽습니다. 각 constraint에 source span과 원래 규칙을 붙입니다.

Mica capstone 핵심에는 generic inference가 없지만 확장 실습에서 구현합니다.

## Subtyping과 coercion

Equality만 있는 언어는 단순합니다. Subtyping이나 implicit conversion을 추가하면 다음을 정해야 합니다.

- `S <: T` 판단 규칙
- function parameter/return variance
- numeric promotion
- overload resolution 순서
- conversion cost와 ambiguity
- runtime check가 필요한 cast

`Int`를 `Bool`로 자동 변환하는 편의 기능은 condition rule과 constant folding까지 영향을 줍니다. 작은 언어에서는 implicit coercion을 최소화하는 것이 phase contract를 명확하게 합니다. Mica는 implicit conversion을 허용하지 않습니다.

## Overload

`print` 하나에 여러 type을 받게 하면 overload candidate set이 생깁니다.

```text
print(Int)
print(Bool)
print(String)
```

Candidate filtering, conversion cost와 ambiguity diagnostic이 필요합니다. Mica core는 `print_int`, `print_bool`, `print_string` builtin을 분리해 이 문제를 제외합니다.

## ErrorType

ErrorType은 모든 type과 같다는 뜻이 아닙니다. 이미 진단된 원인을 후속 검사에서 전파하기 위한 sentinel입니다.

```text
type(unknown_name) = ErrorType(E2001)
type(ErrorType + Int) = ErrorType(E2001)
```

다음 원칙이 필요합니다.

- ErrorType 생성 위치는 diagnostic id를 가집니다.
- ErrorType 때문에 생긴 mismatch는 억제합니다.
- ErrorType과 무관한 sibling 오류는 유지합니다.
- Typed tree 완료 뒤 ErrorType 개수와 error diagnostic 수가 일관적인지 검사합니다.

## Constant value와 type을 분리합니다

`1 + 2`의 type은 `Int`이고 constant value는 `3`일 수 있습니다. Constant folding이 실패하거나 실행하지 않아도 type은 유지됩니다.

```text
TypeMap<NodeId, TypeId>
ConstMap<NodeId, Constant | NotConstant | Poison>
```

Overflow 정책이 runtime trap이면 compile-time folding도 같은 trap 의미를 보존해야 합니다. Host 언어의 무제한 정수를 그대로 사용해 overflow를 놓치지 않습니다.

## Type soundness를 과장하지 않습니다

“type checker를 통과했으니 안전하다”는 문장은 너무 넓습니다. Type checker가 보장하는 범위를 씁니다.

Mica core 예:

- builtin과 operator의 operand type이 맞습니다.
- function argument와 return type이 맞습니다.
- condition은 Bool입니다.
- unknown symbol이 없습니다.

보장하지 않는 것:

- 정수 overflow나 division by zero가 없습니다.
- stack/resource limit을 넘지 않습니다.
- FFI가 올바른 memory를 반환합니다.
- compiler implementation에 bug가 없습니다.

## 대표 실패

- type syntax node의 문자열 비교만 해 alias와 identity를 잘못 처리합니다.
- runtime representation을 semantic type과 동일시합니다.
- host 정수 연산으로 constant folding해 target overflow 규칙이 달라집니다.
- ErrorType에 대해 계속 diagnostic을 추가합니다.
- overload 후보 순서가 hash iteration에 따라 달라집니다.
- expected type을 전달하지 않아 lambda나 empty literal inference가 불가능해집니다.

## 실습 연결

[Resolution·type·flow exercise](../../exercises/03-resolution-types-and-flow/README.md)에서 Mica operator와 call typing table을 구현합니다. 실패 fixture는 [diagnostic 명세](../../exercises/08-mica-capstone/spec/diagnostics.md)의 `E3xxx` code를 사용합니다.

## 점검 질문

1. type syntax와 semantic type은 언제 분리됩니까?
2. synthesis와 checking 중 return expression에는 무엇이 적합합니까?
3. ErrorType이 모든 type과 같다는 구현이 왜 위험합니까?
4. constant folding과 runtime overflow semantics를 어떻게 맞춥니까?
5. “type safe”라는 주장을 어떤 구체적 보장으로 바꿔 써야 합니까?
