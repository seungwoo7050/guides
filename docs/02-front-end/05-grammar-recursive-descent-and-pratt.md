# 문법, recursive descent와 Pratt parsing

Parser는 token stream을 syntax structure로 바꿉니다. 핵심은 parser 종류의 이름이 아니라 grammar가 모호하지 않은지, lookahead가 결정적이며 오류 뒤에도 종료하는지, precedence가 언어 명세와 일치하는지입니다.

## 학습 목표

- EBNF를 parser 함수와 연결합니다.
- left recursion과 공통 prefix가 recursive descent에 미치는 영향을 설명합니다.
- Pratt parser의 binding power로 unary·binary·call precedence를 구현합니다.
- local recovery와 synchronization으로 여러 오류를 안전하게 보고합니다.

## Grammar는 허용 구조의 계약입니다

Mica 일부를 EBNF로 쓰면 다음과 같습니다.

```ebnf
function   = "fn", IDENT, "(", parameters?, ")", "->", type, block ;
block      = "{", statement*, "}" ;
statement  = let_decl | return_stmt | if_stmt | while_stmt
           | assignment, ";" | expression, ";" | block ;
expression = ... precedence levels ... ;
```

Grammar는 다음을 명시해야 합니다.

- 반복이 빈 입력을 허용하는지
- separator 뒤 trailing comma를 허용하는지
- declaration과 expression이 같은 prefix를 갖는지
- dangling `else`가 어느 `if`에 붙는지
- assignment가 expression인지 statement인지

Parser 구현이 우연히 받아들이는 문장을 언어 명세로 간주하지 않습니다.

## Recursive descent

각 nonterminal을 함수로 대응합니다.

```text
parse_function()
parse_block()
parse_statement()
parse_expression()
```

장점:

- source grammar와 제어 흐름을 함께 읽기 쉽습니다.
- custom diagnostic과 recovery를 넣기 쉽습니다.
- 작은 언어에 충분합니다.

주의할 점:

- direct/indirect left recursion은 그대로 구현하면 무한 재귀합니다.
- 공통 prefix를 구분하려면 lookahead 또는 grammar factoring이 필요합니다.
- recursion depth가 사용자 입력에 비례할 수 있습니다.

## Left recursion을 제거합니다

다음 grammar는 recursive descent에 직접 사용할 수 없습니다.

```ebnf
expr = expr, "+", term | term ;
```

호출하자마자 `expr`이 다시 `expr`을 부릅니다. 반복 형태로 바꿉니다.

```ebnf
expr = term, { "+", term } ;
```

하지만 precedence level마다 함수를 나누면 연산자가 많아질수록 boilerplate가 커집니다. Pratt parser가 이 부분을 단순화합니다.

## Pratt parsing의 핵심은 binding power입니다

Pratt parser는 token이 expression 시작에 등장할 때의 `nud/null denotation`과 왼쪽 expression 뒤에 등장할 때의 `led/left denotation`을 구분합니다.

개념적인 loop:

```text
left = parse_prefix()
while min_bp < binding_power(current_token):
    operator = advance()
    left = parse_infix(left, operator)
return left
```

Binding power 예:

| 연산 | left bp | right bp | 결합 |
|---|---:|---:|---|
| `=` | 1 | 0 | 오른쪽 |
| `||` | 2 | 3 | 왼쪽 |
| `&&` | 4 | 5 | 왼쪽 |
| `== !=` | 6 | 7 | 왼쪽 |
| `< <= > >=` | 8 | 9 | 왼쪽 또는 비연쇄 정책 |
| `+ -` | 10 | 11 | 왼쪽 |
| `* / %` | 12 | 13 | 왼쪽 |
| call `()` | 20 | 21 | 왼쪽 |

숫자 자체보다 상대 순서와 associativity가 중요합니다.

```text
1 + 2 * 3       => +(1, *(2, 3))
a - b - c       => -( -(a, b), c )
f(1)(2)         => call(call(f, 1), 2)
```

`-`는 prefix와 infix 역할을 모두 가지므로 token kind만으로 node를 결정하지 않습니다.

## Assignment target을 구분합니다

Assignment를 expression에 넣으면 왼쪽이 assignable place인지 검사해야 합니다.

```text
x = 1          허용
f() = 1        거부
(x + y) = 1    거부
```

Parser가 `AssignmentExpr(target, value)`를 만들고 semantic phase가 target category를 검사할 수도 있습니다. Mica core는 단순화를 위해 assignment를 statement로 두고 왼쪽을 identifier로 제한합니다.

## Dangling else

```text
if a {
    if b { work(); }
    else { other(); }
}
```

Brace language에서는 구조가 명확하지만 brace 없는 grammar에서는 `else`가 가장 가까운 unmatched `if`에 붙는 규칙을 보통 사용합니다. Formatter와 AST가 같은 association을 유지해야 합니다.

## Lookahead와 backtracking

가능하면 작은 고정 lookahead로 declaration 종류를 결정합니다.

```text
FN       → function
LET/VAR  → variable declaration
IF       → if statement
```

무제한 backtracking은 오류 위치를 뒤로 돌리고 같은 입력을 반복 parse해 비용이 급격히 커질 수 있습니다. 꼭 필요하면 memoization과 commit point를 정의합니다.

## Error recovery

`expect(RIGHT_PAREN)`가 실패했을 때 선택지는 다음과 같습니다.

- zero-width synthetic `)`를 삽입하고 계속합니다.
- 현재 token 하나를 삭제하고 다시 시도합니다.
- `)` 또는 statement boundary까지 이동합니다.
- 현재 construct를 `ErrorNode`로 닫습니다.

복구는 다음 invariant를 지킵니다.

```text
성공 node를 반환하거나
token index를 전진시키거나
명시적으로 abort합니다.
```

Recovery node에도 span과 diagnostic origin을 남겨 formatter와 semantic phase가 이미 깨진 영역을 인식하게 합니다.

## Parser stack과 입력 제한

사용자가 괄호 수십만 개를 보내면 recursive parser가 host stack을 소모할 수 있습니다. Production parser는 다음을 고려합니다.

- nesting depth limit
- token count 또는 time budget
- cancellation
- iterative parsing이 필요한 construct
- 오류 시 stack trace를 사용자에게 그대로 노출하지 않음

Language server는 신뢰할 수 없는 편집 입력을 반복 처리하므로 특히 중요합니다.

## Parser test

Golden AST snapshot만으로는 부족합니다.

- precedence table의 모든 인접 연산자 조합
- associativity case
- EOF 직전 누락 token
- 각 delimiter의 insertion/deletion recovery
- random token stream에서 종료 보장
- parse→print→parse 구조 동치
- known-bad parser가 거부되는 최소 fixture

AST snapshot을 사용할 때 source 위치와 node id처럼 의도적으로 변할 수 있는 field를 분리합니다.

## 실습 연결

[Lexer·parser·AST exercise](../../exercises/02-lexer-parser-and-ast/README.md)와 `examples/pratt-parser`에서 precedence와 associativity를 관찰합니다. Mica 전체 grammar는 [grammar.ebnf](../../exercises/08-mica-capstone/spec/grammar.ebnf)에 있습니다.

## 점검 질문

1. left recursion이 recursive descent에서 왜 종료하지 않습니까?
2. 오른쪽 결합 연산자는 left/right binding power가 어떻게 다릅니까?
3. synthetic token의 span은 어떻게 표현합니까?
4. parser recovery가 semantic phase에 거짓 symbol을 만들지 않게 하려면 무엇이 필요합니까?
5. parser가 임의 입력에서 종료한다는 것을 어떤 test로 확인합니까?
