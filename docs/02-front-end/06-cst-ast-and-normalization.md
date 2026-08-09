# CST, AST와 normalization

Syntax tree는 하나가 아닙니다. 원문을 정확히 다시 만들기 위한 concrete syntax tree와 의미 분석에 필요한 abstract syntax tree는 서로 다른 목적을 가집니다. 두 요구를 한 구조에 억지로 넣으면 formatter는 trivia를 잃고 type checker는 불필요한 구문 세부에 묶입니다.

## 학습 목표

- parse tree, CST와 AST의 목적을 구분합니다.
- trivia·delimiter·parenthesis를 어느 구조에서 보존할지 결정합니다.
- desugaring과 normalization이 source origin을 잃지 않게 합니다.
- node identity와 mutability를 batch·incremental use case에 맞게 설계합니다.

## 세 가지 표현

### Parse tree

Grammar production을 거의 그대로 반영합니다. parser generator가 만드는 tree가 여기에 가까울 수 있습니다.

```text
AdditiveExpression
  AdditiveExpression
    Primary(INT 1)
  PLUS
  MultiplicativeExpression
    Primary(INT 2)
```

Grammar debugging에는 유용하지만 의미 분석에는 중간 node가 많습니다.

### CST

모든 token, delimiter와 trivia를 보존해 source fidelity를 우선합니다.

```text
BinaryExpr
  left: Literal("1")
  whitespace: " "
  op: "+"
  whitespace: " "
  right: Literal("2")
```

Formatter, refactoring, syntax highlighting과 incremental parser에 적합합니다.

### AST

의미에 필요 없는 구문 차이를 제거합니다.

```text
Binary(op=Add, left=Int(1), right=Int(2))
```

Type checker, interpreter와 lowering에 적합합니다.

## 괄호를 지울지 결정합니다

`(a + b)`의 parenthesis는 계산 tree가 precedence를 이미 표현하므로 AST에서 제거할 수 있습니다. 하지만 다음 기능에는 필요할 수 있습니다.

- formatter가 사용자의 의도적 괄호를 보존
- linter가 불필요한 괄호를 진단
- refactoring 뒤 의미 보존 여부 확인

선택지:

1. CST에 괄호를 보존하고 AST에는 제거
2. AST에 `ParenthesizedExpr`를 유지
3. AST node에 `was_parenthesized` metadata 저장

도구 목표에 따라 선택하고 public schema에 기록합니다.

## AST node는 합성곱 타입으로 봅니다

개념적으로 expression은 다음 variant입니다.

```text
Expr = IntLiteral
     | BoolLiteral
     | StringLiteral
     | NameRef
     | Unary
     | Binary
     | Call
     | ErrorExpr
```

각 variant가 항상 갖는 field와 선택 field를 분리합니다. `Binary` node에 call 전용 field를 nullable로 몰아넣는 구조는 invariant를 약하게 만듭니다.

Python profile에서는 frozen `dataclass`와 union, C++20 profile에서는 `std::variant` 또는 class hierarchy를 사용할 수 있습니다. 핵심은 language representation이 아니라 invalid state를 줄이는 것입니다.

## AST와 semantic annotation을 분리합니다

처음에는 node에 모든 정보를 붙이고 싶을 수 있습니다.

```text
NameExpr
  text
  span
  resolved_symbol
  inferred_type
  constant_value
  generated_ir
```

하지만 phase마다 mutability와 invalidation이 달라집니다. Source edit 뒤 symbol과 type은 무효화되지만 syntax는 재사용할 수 있습니다.

대안:

```text
SyntaxTree                     immutable
ResolutionMap<NodeId, SymbolId>
TypeMap<NodeId, TypeId>
FlowFacts<BlockId, Fact>
IROriginMap<InstructionId, NodeId>
```

작은 batch compiler에서는 node annotation도 허용되지만 phase 완료 전후의 nullable state를 명확히 해야 합니다.

## Stable node identity

메모리 주소를 node id로 사용하면 serialization, incremental reparse와 deterministic test가 어렵습니다.

선택:

- tree 안의 순차 index
- source span + node kind의 조합
- arena allocation id
- incremental parser가 제공하는 green node identity

Span 기반 identity는 같은 위치의 문법이 바뀌면 충돌할 수 있고, 순차 index는 앞부분 edit에 모두 흔들릴 수 있습니다. 어떤 안정성이 필요한지 먼저 정합니다.

Mica batch profile은 parse invocation 안에서만 유효한 순차 `NodeId`를 사용합니다. LSP 확장에서는 document version을 포함하고 cache key를 별도로 둡니다.

## Normalization과 desugaring

표면 syntax를 작은 core language로 낮추면 interpreter와 type checker가 단순해집니다.

예:

```text
for item in items { body }
```

을 iterator와 while로 바꿀 수 있습니다. 하지만 다음을 보존해야 합니다.

- evaluation order
- variable scope와 capture
- break/continue target
- source diagnostic origin
- runtime error의 사용자 위치

Desugaring이 새 이름을 만들면 사용자 이름과 충돌하지 않는 hygienic identity가 필요합니다. 단순히 `_temp1` 문자열을 생성하면 사용자가 같은 이름을 선언했을 때 의미가 바뀔 수 있습니다.

## Lowering을 한 번에 너무 많이 하지 않습니다

다음 변환을 한 함수에 넣으면 오류를 찾기 어렵습니다.

```text
CST → name resolution → type inference → bytecode
```

작은 단계로 나눕니다.

```text
CST
→ AST: trivia와 grammar wrapper 제거
→ HIR: sugar 정규화, symbol/type annotation
→ MIR/CFG: control flow와 evaluation order 명시
→ bytecode 또는 target IR
```

모든 프로젝트가 HIR/MIR 이름을 써야 하는 것은 아닙니다. 표현 하나가 어떤 추상화를 보존하는지 문서화하면 됩니다.

## Visitor와 pattern matching

Tree operation은 두 방향으로 확장됩니다.

- node kind가 자주 늘고 operation은 적음
- operation이 자주 늘고 node kind는 안정적

Class hierarchy + visitor는 operation 추가가 번거로울 수 있고, tagged union + pattern matching은 variant 추가 시 모든 match를 갱신하게 합니다. Exhaustiveness check가 가능한 언어에서는 후자가 누락을 찾기 쉽습니다.

Traversal helper가 source order와 child ownership을 명확히 해야 합니다. Generic visitor가 declaration scope entry/exit 순서를 숨기지 않게 주의합니다.

## Serialization

AST JSON은 debugging과 test에 유용하지만 compiler 내부 객체를 그대로 공개하면 schema가 구현 세부에 묶입니다.

공개 dump에는 다음을 선택적으로 포함합니다.

- stable kind 이름
- source span
- 의미 있는 child field
- symbol/type id의 디버그 표현

Memory address, hash iteration order와 cache pointer는 제외합니다. Field order와 version을 고정해 fixture diff가 의미 있게 합니다.

## 대표 실패

- AST가 comment를 버려 formatter가 source를 재구성하지 못합니다.
- desugaring이 source origin을 모두 상위 statement로 붙여 runtime error 위치가 부정확합니다.
- node에 type을 직접 쓰고 incremental edit 뒤 오래된 type이 남습니다.
- generated temporary가 사용자 이름과 충돌합니다.
- AST JSON에 pointer 주소가 들어가 test가 매번 바뀝니다.
- visitor가 ErrorExpr를 처리하지 않아 crash합니다.

## 실습 연결

[Lexer·parser·AST exercise](../../exercises/02-lexer-parser-and-ast/README.md)에서 Mica CST/AST 선택과 JSON dump schema를 작성합니다. 최소한 source span, node kind, 명시적 child field와 ErrorExpr를 포함합니다.

## 점검 질문

1. formatter와 type checker가 같은 tree를 사용할 때 어떤 정보가 서로 방해됩니까?
2. parenthesis를 AST에서 제거하면 어떤 기능에 별도 정보가 필요합니까?
3. semantic annotation을 side table로 둘 때 key의 lifetime은 무엇입니까?
4. desugaring이 evaluation order를 보존했다는 것을 어떻게 검사합니까?
5. AST dump에서 deterministic하지 않은 field는 무엇입니까?
