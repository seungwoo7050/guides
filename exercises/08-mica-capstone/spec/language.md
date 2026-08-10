# Mica Core Language Specification

## 1. Status와 우선순위

이 문서는 Mica core의 static semantics와 runtime semantics를 정합니다. 문법은 `grammar.ebnf`, 외부 오류 형식은 `diagnostics.md`, CLI fixture 판정은 `conformance.md`가 정본입니다.

문서가 충돌하면 다음 우선순위를 사용합니다.

```text
conformance fixture의 명시된 기대값
→ spec 문서
→ 가이드의 설명 예제
→ skeleton의 내부 구조
```

Fixture 또는 spec에 모순이 발견되면 구현별 예외를 추가하지 말고 decision record와 명세 수정을 먼저 제안합니다.

## 2. Source model

- Source는 유효한 UTF-8 byte sequence입니다.
- Core identifier는 ASCII 문자와 숫자만 사용합니다.
- String literal 내용은 Unicode text입니다.
- 모든 span은 source 시작부터 센 **UTF-8 byte offset**의 half-open interval `[start, end)`입니다.
- Source snapshot은 한 command 실행 중 immutable입니다.
- Line ending은 `LF`와 `CRLF`를 허용합니다. Line map은 둘을 한 번의 line break로 처리합니다.
- Tab display width는 text renderer의 선택이며 semantic span에 포함되지 않습니다.

## 3. Lexical elements

### Identifier

```text
[A-Za-z_][A-Za-z0-9_]*
```

Keyword는 identifier보다 먼저 분류합니다.

```text
fn let var if else while return true false
Int Bool String Unit
```

### Whitespace와 comment

Space, tab, `LF`, `CRLF`는 token 사이에서 무시합니다. `//`부터 line break 직전까지 line comment입니다.

Comment와 whitespace를 CST/trivia로 보존할지는 구현 선택이지만 formatter 경로는 comment의 source span과 상대 순서를 보존해야 합니다.

### Integer literal

Decimal digit만 허용합니다.

```text
0
[1-9][0-9]*
```

Underscore, radix prefix와 suffix는 core에 없습니다. Literal 값은 `0..9223372036854775807` 범위여야 합니다. 음수는 literal token이 아니라 unary `-` expression입니다.

### String literal

Double quote로 둘러싸며 다음 escape만 허용합니다.

```text
\n  newline
\r  carriage return
\t  tab
\\  backslash
\"  quote
```

Raw newline과 EOF 전에 닫히지 않은 string은 lexical error입니다. Source의 다른 Unicode 문자는 string 안에서 그대로 허용합니다.

### Operator와 delimiter

```text
+ - * / %
! == !=
< <= > >=
&& ||
=
( ) { } , : ; ->
```

`=`와 `==`, `!`와 `!=`, `<`와 `<=`, `>`와 `>=`, `-`와 `->`에는 longest match를 적용합니다.

## 4. Program과 declaration

Program은 top-level function declaration의 순서 있는 목록입니다. 다른 top-level statement는 허용하지 않습니다.

Function signature:

```text
fn name(parameter, ...) -> ReturnType { body }
```

Parameter:

```text
name: Type
```

Function 이름은 program 전체의 한 namespace를 사용합니다. 모든 signature를 body보다 먼저 수집하므로 뒤에 선언된 function 호출과 direct recursion을 허용합니다.

Builtin function은 다음 signature로 미리 선언됩니다.

```text
print_int(value: Int) -> Unit
print_bool(value: Bool) -> Unit
print_string(value: String) -> Unit
```

사용자 function은 builtin과 같은 이름을 선언할 수 없습니다.

Entry point는 정확히 하나이며 signature는 다음과 같아야 합니다.

```text
fn main() -> Int
```

## 5. Type

Core type:

```text
Int       signed 64-bit integer
Bool      true 또는 false
String    immutable Unicode scalar sequence
Unit      의미 있는 값이 없는 단일 값
```

Implicit conversion, subtype, overload와 generic은 없습니다. 같은 type은 명시된 이름이 같을 때만 같습니다.

`Unit`은 variable·parameter type으로 사용할 수 없습니다. Function return type과 builtin 결과에는 사용할 수 있습니다.

## 6. Scope, binding과 mutation

Function body는 lexical scope입니다. 각 nested block은 child scope를 만듭니다.

Declaration:

```text
let name: Type = expression;   immutable local
var name: Type = expression;   mutable local
```

Initializer는 declaration이 현재 scope에 들어가기 전에 검사·평가합니다. 따라서 다음 self-reference는 허용하지 않습니다.

```text
let x: Int = x;
```

같은 scope에 같은 이름을 다시 선언할 수 없습니다. Nested child scope에서 outer local을 shadowing하는 것은 허용합니다. Parameter는 function body의 outermost local scope에 immutable binding으로 들어갑니다.

Name resolution 우선순위:

```text
가장 가까운 local/parameter
→ top-level function와 builtin
→ unknown name error
```

Assignment:

```text
name = expression;
```

Target은 현재 visible한 `var` local이어야 합니다. `let`, parameter, function과 builtin에는 assign할 수 없습니다.

## 7. Statement

Statement는 source 순서대로 실행합니다.

- local declaration
- assignment
- expression statement
- block
- `if` / `else`
- `while`
- `return`

`if`와 `while` condition type은 `Bool`이어야 합니다.

Non-`Unit` function은 모든 reachable path에서 값을 반환해야 합니다. `Unit` function은 body 끝에 도달하면 암묵적으로 `Unit`을 반환합니다.

`return expression;`은 current function의 return type과 정확히 같아야 합니다. `return;`은 `Unit` function에서만 허용합니다.

## 8. Expression typing

### Literal와 name

| Expression | Type |
|---|---|
| integer literal | `Int` |
| `true`, `false` | `Bool` |
| string literal | `String` |
| local/parameter name | binding의 declared type |
| function name | expression value가 아님; call callee에서만 사용 |

### Unary

| Operator | Input | Result |
|---|---|---|
| `-` | `Int` | `Int` |
| `!` | `Bool` | `Bool` |

### Binary

| Operator | Operand | Result |
|---|---|---|
| `+ - * / %` | `Int`, `Int` | `Int` |
| `< <= > >=` | `Int`, `Int` | `Bool` |
| `== !=` | 같은 `Int`, `Bool` 또는 `String` | `Bool` |
| `&& ||` | `Bool`, `Bool` | `Bool` |

`Unit` equality는 허용하지 않습니다. String concatenation은 core에 없습니다.

### Call

Callee는 top-level function 또는 builtin 이름이어야 합니다. Argument 수와 type은 signature와 정확히 같아야 하며 argument는 왼쪽부터 평가합니다.

## 9. Evaluation order와 effect

- Statement는 source 순서입니다.
- Unary operand는 한 번 평가합니다.
- Binary operand는 왼쪽, 오른쪽 순서입니다.
- Call argument는 왼쪽부터 평가합니다.
- `&&`는 왼쪽이 `false`이면 오른쪽을 평가하지 않습니다.
- `||`는 왼쪽이 `true`이면 오른쪽을 평가하지 않습니다.
- Assignment RHS는 target cell을 변경하기 전에 완전히 평가합니다.
- Builtin print는 provided output sink에 text와 `\n`을 추가합니다.

Interpreter, VM과 backend는 이 관찰 순서를 보존해야 합니다.

## 10. Integer semantics

모든 `Int` operation은 mathematical integer로 계산한 뒤 signed 64-bit 범위를 검사합니다.

```text
MIN = -9223372036854775808
MAX =  9223372036854775807
```

범위를 벗어나면 wrap하지 않고 runtime diagnostic `MICA4002`를 반환합니다.

Division:

- divisor가 0이면 `MICA4001`입니다.
- quotient는 0 방향으로 truncation합니다.
- remainder는 `a == (a / b) * b + (a % b)`를 만족합니다.
- `MIN / -1`은 overflow입니다.

Unary minus of `MIN`도 overflow입니다.

Decimal integer token 자체는 `0..MAX`만 허용하며 범위를 벗어난 literal은 lex 단계 `MICA1004`입니다. `MIN`은 특별한 음수 literal이 아니라 `-9223372036854775807 - 1`처럼 허용된 literal과 연산으로 구성합니다. 따라서 `MIN / -1`과 `-MIN` runtime 경계는 양의 out-of-range literal을 허용하지 않고도 관찰할 수 있습니다.

## 11. String semantics

String은 immutable Unicode text입니다. `==`와 `!=`는 code point sequence equality를 사용합니다. Unicode normalization과 locale collation은 하지 않습니다.

`print_string`은 string 내용 뒤에 newline 하나를 추가합니다. Source escape는 runtime value로 decode된 뒤 출력합니다.

## 12. Runtime state와 limit

한 실행은 최소 다음 상태를 가집니다.

```text
function table
call frame stack
current environment 또는 local slots
output sink
remaining call-depth budget
remaining execution-step budget
```

기본 최소 지원 limit:

- call depth: 256 frame
- execution step: 1,000,000 semantic step

CLI가 limit을 조정하게 할 수 있지만 0 이하 값은 사용 오류입니다. Limit 초과는 host stack overflow나 강제 종료가 아니라 정의된 runtime diagnostic입니다.

## 13. Runtime diagnostic

- division by zero: `MICA4001`
- checked integer overflow: `MICA4002`
- call-depth limit: `MICA4003`
- execution-step limit: `MICA4004`
- internal impossible state: exit `2`, `MICA9001`

Runtime diagnostic primary span은 실패를 일으킨 operator 또는 call site입니다. Call stack note는 callee 진입 순서가 아니라 **실패 지점에서 caller 방향**으로 deterministic하게 기록합니다.

## 14. Host independence

Host language의 다음 동작을 Mica 의미로 사용하지 않습니다.

- Python arbitrary precision integer
- C/C++ signed overflow
- host 언어의 truthiness
- host exception traceback
- host dictionary의 accidental iteration order
- host recursion limit

Adapter가 명시적으로 Mica type·overflow·order·diagnostic으로 변환해야 합니다.
