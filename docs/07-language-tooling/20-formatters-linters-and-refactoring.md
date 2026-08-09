# Formatter, linter와 refactoring

언어 도구는 compiler core의 syntax·symbol·type 정보를 사용자 source에 다시 적용합니다. Formatter는 layout을 바꾸되 의미를 보존해야 하고, linter는 compiler가 허용한 프로그램에서 위험하거나 불필요한 pattern을 찾으며, refactoring은 여러 위치의 코드를 구조적으로 변경합니다.

## 학습 목표

- source-preserving formatter와 canonical formatter를 구분합니다.
- comment ownership, parenthesis와 line breaking을 syntax model에 연결합니다.
- linter rule의 전제·severity·suppression·fix 안전성을 설계합니다.
- rename과 extract 같은 refactoring을 symbol identity와 transaction edit로 구현합니다.

## Formatter의 contract

가장 중요한 두 조건:

### Meaning preservation

```text
parse(source) ≈ parse(format(source))
```

Whitespace가 lexical boundary를 바꾸거나 parenthesis를 제거해 precedence가 달라지면 실패입니다.

### Idempotence

```text
format(format(source)) == format(source)
```

두 번 실행할 때 계속 줄이 바뀌면 editor save loop와 diff가 불안정해집니다.

그 밖의 정책:

- line ending 보존/정규화
- final newline
- indentation width와 tab
- maximum line width
- trailing comma
- comment 이동
- invalid syntax 처리

## Pretty-print document model

AST를 문자열에 바로 이어 붙이면 line width와 nested group을 처리하기 어렵습니다. 추상 document algebra를 사용할 수 있습니다.

```text
Text
Line
Concat
Indent
Group
IfBreak
```

`Group`은 한 줄에 맞으면 soft line을 space로, 넘으면 line break로 렌더링합니다. Layout search는 deterministic해야 하며 pathological source에서 time budget을 가집니다.

## CST와 comment

Formatter는 punctuation과 trivia를 알아야 합니다. AST만 있으면 comment 위치와 사용자가 넣은 빈 줄을 잃을 수 있습니다.

Comment attachment 정책 예:

- declaration 앞의 연속 line comment는 leading comment
- 같은 줄 뒤 comment는 trailing comment
- 두 node 사이 독립 comment는 source position을 기준으로 보존
- doc comment는 다음 declaration symbol과 연결

모든 comment를 “다음 token의 leading trivia”로만 두면 closing brace 앞 comment나 file-end comment가 어색해질 수 있습니다. Fixture로 정책을 고정합니다.

## Invalid source formatting

Editor에서는 syntax error 중에도 format 요청이 올 수 있습니다.

선택:

1. error node가 있으면 전체 format 거부
2. 정상 subtree만 range format
3. CST recovery token으로 best-effort format

자동으로 token을 삭제하거나 새 의미를 만드는 formatter는 위험합니다. Mica profile은 parse error가 있으면 full-document format을 거부하고 stable diagnostic을 반환하며, 선택적으로 정상 block의 range format만 허용합니다.

## Parenthesis

Formatter가 parenthesis를 제거하려면 parser와 같은 precedence/associativity table을 사용해야 합니다.

```text
(a + b) * c   괄호 필요
(a * b) + c   제거 가능할 수 있음
```

하지만 사용자 의도, float reassociation과 overloaded operator를 고려하면 의미상 불필요해도 보존 정책을 선택할 수 있습니다. Formatter와 linter 책임을 분리해 formatter는 보존하고 linter가 “불필요한 괄호”를 제안할 수도 있습니다.

## Linter rule

```text
Rule
  stable code
  required facts: syntax / symbol / type / flow / effect
  default severity
  message와 labels
  optional fix
  applicability
```

예:

- unused local: resolution + liveness
- unreachable statement: CFG
- constant condition: constant evaluator
- shadowing warning: scope model
- redundant comparison: type/operator semantics

Rule이 필요한 analysis를 명시하면 syntax-only editor mode에서 실행 가능한 subset을 선택할 수 있습니다.

## False positive와 severity

Compiler error와 linter warning을 혼동하지 않습니다. Linter는 팀·프로젝트 정책에 따라 허용될 수 있습니다.

- default severity
- project configuration
- file/line suppression
- generated code 제외
- baseline file
- rule version과 migration

Suppression comment도 syntax/trivia model에 들어가며 rename/formatter가 보존해야 합니다.

## Fix 안전성

Fix는 source version과 text edit 집합입니다.

```text
WorkspaceEdit
  documents:
    SourceId + Version -> non-overlapping TextEdit[]
```

`unused variable` fix가 declaration만 지우면 initializer의 effect를 잃을 수 있습니다.

```text
let unused: Int = side_effect();
```

따라서 pure initializer인지 확인하거나 binding만 제거하고 expression statement로 바꿔야 합니다. Fix precondition이 증명되지 않으면 suggestion만 제공합니다.

## Rename

안전한 rename:

1. cursor 위치의 resolved SymbolId를 찾습니다.
2. declaration과 reference index를 수집합니다.
3. 새 이름 lexical validity를 검사합니다.
4. 각 reference scope에서 conflict를 검사합니다.
5. import/export/mangle 정책을 확인합니다.
6. 같은 document version에 대한 edits를 만듭니다.
7. 적용 뒤 reparse·resolve로 검증합니다.

문자열 치환은 comment, string과 다른 scope의 동명 symbol을 바꾸므로 사용하지 않습니다.

## Extract function/local

더 복잡한 refactoring은 data-flow가 필요합니다.

Extract function:

- 선택 구간에 들어오는 value
- 밖에서 사용되는 정의
- control transfer(return/break/continue)
- captured mutable
- exception/effect
- source scope와 type

구간이 statement boundary와 맞지 않으면 거부할 수 있습니다. 자동 변환이 항상 가능하다고 가정하지 않습니다.

## Edit transaction

여러 파일을 바꾸는 refactoring은 일부만 적용되면 project를 깨뜨립니다.

- 모든 document version 확인
- edit range overlap 검사
- preview 제공
- apply atomicity 또는 rollback
- 저장 실패 처리
- apply 뒤 compiler check

LSP `WorkspaceEdit`는 client capability와 resource operation 지원을 확인해야 합니다.

## Tool test

Formatter:

- idempotence
- parse/semantic round-trip
- comment fixture
- width boundary
- invalid source 정책
- range format 밖 text 불변

Linter/refactoring:

- positive/negative case
- fix 적용 뒤 diagnostic 사라짐
- unrelated text 불변
- scope conflict 거부
- effect 보존
- stale document version 거부

## 대표 실패

- AST만 출력해 comment를 잃습니다.
- formatter가 parser와 다른 precedence table을 사용합니다.
- unused binding fix가 effectful initializer를 제거합니다.
- rename이 동명 shadowed variable까지 바꿉니다.
- multi-file edit가 일부 파일에만 적용됩니다.
- invalid source를 임의 복구해 저장 시 사용자 token을 삭제합니다.
- format 결과가 두 형태 사이에서 oscillate합니다.

## 실습 연결

[언어 도구 exercise](../../exercises/07-language-tools/README.md)에서 formatter 또는 linter/refactoring 하나를 선택합니다. Capstone 완료에는 formatter+linter 또는 LSP subset 중 하나가 필요합니다.

## 점검 질문

1. formatter의 의미 보존을 AST text snapshot이 아니라 어떻게 검사합니까?
2. comment ownership을 정하지 않으면 어떤 node 이동에서 문제가 생깁니까?
3. unused variable fix가 initializer를 지워도 되는 조건은 무엇입니까?
4. rename conflict는 어느 scope에서 검사합니까?
5. multi-file refactoring을 transaction으로 다뤄야 하는 이유는 무엇입니까?
