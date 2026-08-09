# 언어 경계와 phase contract

Compiler나 interpreter를 처음 만들 때 가장 흔한 실패는 모든 검사를 parser에 넣거나, runtime이 type checker의 빈틈을 임의로 보완하게 만드는 것입니다. 언어 구현은 여러 phase가 이어진 하나의 프로그램이지만 각 phase의 입력·출력·오류·보장을 분리해야 합니다.

## 학습 목표

- syntax, static semantics와 dynamic semantics를 구분합니다.
- phase별 입력·출력과 보존해야 할 정보를 계약으로 작성합니다.
- “parser가 받아들였다”와 “프로그램이 유효하다”를 구분합니다.
- batch compiler와 editor service가 같은 core model을 공유할 수 있게 설계합니다.

## 언어는 세 층의 계약을 가집니다

### Syntax

어떤 token 배열이 구조적으로 문장이 되는지 정의합니다.

```text
let total: Int = price + tax;
```

위 문장이 grammar에 맞는지는 이름 `price`가 실제로 존재하는지, `tax`가 `Int`인지와 무관합니다. parser는 구조를 만들고 recovery 가능한 syntax error를 보고하는 단계입니다.

### Static semantics

실행 전에 확인할 이름, 타입, control-flow와 선언 규칙입니다.

- `price`와 `tax`는 현재 scope에서 보이는가?
- `+`가 두 피연산자의 type에 정의되어 있는가?
- `total`의 선언 type과 식의 type이 일치하는가?
- 이 문장이 도달 가능한 위치에 있는가?

문법적으로 완전한 AST도 정적 의미에서는 거부될 수 있습니다.

### Dynamic semantics

유효한 프로그램이 실행될 때 상태가 어떻게 변하는지 정의합니다.

```text
(environment, expression) → (environment, value)
```

정수 overflow, division by zero, stack limit, I/O 실패처럼 type checker만으로 제거하지 못한 runtime failure도 여기 속합니다.

## Phase는 의미를 변환하는 함수입니다

대표적인 batch pipeline을 단순화하면 다음과 같습니다.

```text
SourceSnapshot
  └─lex→ TokenStream + LexDiagnostics
        └─parse→ SyntaxTree + ParseDiagnostics
              └─resolve→ ResolvedTree + ResolutionDiagnostics
                    └─type→ TypedTree + TypeDiagnostics
                          └─lower→ IR
                                └─execute / emit→ Result or Artifact
```

각 화살표는 다음 네 가지를 명시해야 합니다.

1. 입력이 어떤 상태여야 합니까?
2. 성공 출력은 무엇을 보장합니까?
3. 사용자 오류는 어떤 구조로 반환합니까?
4. 내부 invariant 위반은 어떻게 중단합니까?

사용자 오류와 compiler bug를 같은 예외로 처리하면 진단 품질과 복구 경계가 무너집니다.

## Phase contract 표를 작성합니다

| Phase | 입력 | 출력 | 보장 | 정상적인 실패 |
|---|---|---|---|---|
| lex | immutable source snapshot | token과 trivia | token span이 source 범위 안에 있음 | 잘못된 문자, 닫히지 않은 문자열 |
| parse | token stream | CST/AST | 모든 node span과 자식 순서가 유효 | 예상 token 누락, 잘못된 문장 |
| resolve | AST + module context | symbol reference | 모든 resolved reference가 stable symbol을 가리킴 | 알 수 없는 이름, 중복 선언 |
| type | resolved tree | typed tree | 각 expression에 type 또는 error type이 있음 | type mismatch, 잘못된 call |
| lower | typed tree | IR | IR verifier invariant를 만족 | 일반적으로 사용자 오류 없음 |
| execute | verified code/IR | value와 effect | 언어가 정한 evaluation order | division by zero, resource limit |

`lower` 이후 사용자 오류가 계속 발생한다면 이전 phase가 보장하지 않은 조건이 무엇인지 다시 확인해야 합니다. backend가 source-level type error를 처음 발견하는 구조는 phase 경계가 새고 있다는 신호입니다.

## 한 phase가 너무 많은 책임을 갖지 않게 합니다

다음 구현은 작을 때는 편리하지만 곧 문제가 됩니다.

```text
parser가 scope table을 수정
parser가 type을 추론
AST constructor가 bytecode를 생성
VM이 알 수 없는 variable을 자동 생성
```

문제는 단순한 코드 정리가 아닙니다.

- syntax recovery 도중 잘못된 symbol이 등록됩니다.
- 같은 AST를 formatter와 type checker가 공유하기 어렵습니다.
- incremental edit에서 어느 cache를 무효화할지 알 수 없습니다.
- test가 phase 하나의 실패를 독립적으로 재현하지 못합니다.

작은 구현에서도 데이터 구조를 완전히 분리할 필요는 없지만, 적어도 함수의 입력·출력과 오류 ownership은 분리합니다.

## Source identity를 끝까지 보존합니다

진단과 개발 도구를 제공하려면 phase가 source 위치를 잃지 않아야 합니다.

```text
Token.span
ASTNode.span
Symbol.declaration_span
IRInstruction.origin
MachineLocation.debug_origin
```

모든 IR instruction이 정확히 한 source expression과 대응하지는 않습니다. desugaring이나 optimization으로 여러 source가 합쳐질 수 있습니다. 따라서 origin은 단일 line number가 아니라 0개 이상의 source origin 집합이나 transformation chain일 수 있습니다.

핵심 원칙은 “위치를 항상 하나 붙인다”가 아니라 **어떤 phase에서 어느 정도 정확한 source 대응을 보장하는지** 기록하는 것입니다.

## Batch와 incremental 실행을 구분합니다

Batch compiler는 전체 입력 snapshot을 한 번 처리하고 artifact를 만들 수 있습니다. editor service는 사용자가 닫지 않은 괄호와 아직 type이 없는 식을 입력하는 동안에도 응답해야 합니다.

두 경로를 완전히 따로 만들면 의미 규칙이 달라지기 쉽습니다. 권장 구조는 다음과 같습니다.

```text
공통 core
- syntax model
- symbol/type rule
- diagnostic code

batch adapter
- 파일 집합
- 종료 코드
- artifact emission

incremental adapter
- document version
- cancellation
- cache invalidation
- partial result
```

Editor가 recovery node를 허용하더라도 저장·build 시 사용하는 static semantics가 달라져서는 안 됩니다.

## Compiler pipeline이 항상 선형인 것은 아닙니다

실제 구현은 반복과 분기를 포함합니다.

- module graph를 먼저 만들고 각 파일을 병렬 parse할 수 있습니다.
- type inference가 name resolution 결과를 다시 요구할 수 있습니다.
- macro expansion 뒤 다시 parse할 수 있습니다.
- optimization pass manager가 여러 pass를 반복합니다.
- LSP request는 syntax만 필요한 기능과 type까지 필요한 기능이 다릅니다.

그래도 각 edge의 contract를 쓰면 복잡한 graph를 다룰 수 있습니다. “compiler는 lexer→parser→codegen”이라는 그림은 시작점이지 전체 architecture가 아닙니다.

## 실패 설계

### 사용자 오류

구조화된 diagnostic으로 반환하고 가능한 범위에서 다음 오류를 계속 찾습니다.

### 지원하지 않는 기능

언어가 거부하는 것인지 구현이 아직 못 하는 것인지 구분합니다.

```text
E3104: generic type은 Mica core에 포함되지 않습니다
I9001: LLVM backend에서는 closure emission을 아직 지원하지 않습니다
```

첫 번째는 명세상 오류, 두 번째는 구현 capability 문제입니다.

### 내부 오류

불가능해야 하는 상태는 조용히 사용자 오류로 바꾸지 않습니다.

```text
resolved tree에 UnboundReference가 남아 있음
verified IR의 basic block에 terminator가 없음
stack effect 계산과 VM stack depth가 불일치
```

내부 오류는 별도 종료 코드와 phase·node identity를 남겨 재현 가능하게 합니다. source 전체나 민감한 경로를 무조건 출력하지는 않습니다.

## 실습 연결

[Source와 diagnostic exercise](../../exercises/01-source-and-diagnostics/README.md)에서 Mica pipeline의 phase contract 표를 작성합니다. 각 phase마다 입력 schema, 사용자 오류, 내부 invariant와 다음 phase가 의존하는 보장을 한 줄 이상 적습니다.

## 점검 질문

1. parser가 성공하면 어떤 사실까지 보장합니까?
2. type checker가 실행 순서를 결정합니까, 확인만 합니까?
3. optimization 뒤 source 위치가 하나로 대응하지 않으면 어떤 구조가 필요합니까?
4. 사용자 오류와 compiler bug의 종료 코드와 기록은 어떻게 다릅니까?
5. editor의 부분 AST가 batch compiler의 의미 규칙을 바꾸지 않게 하려면 무엇을 공유해야 합니까?

## 범위 경계

Graph traversal, fixed-point와 복잡도 자체는 `algorithms`가 소유합니다. ISA와 실제 CPU 실행은 `computer-architecture`가 소유합니다. 이 문서는 그 지식을 phase의 입력·출력 계약에 적용합니다.
