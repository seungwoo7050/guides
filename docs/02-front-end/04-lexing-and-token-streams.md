# Lexing과 token stream

Lexer는 source byte를 의미 있는 token과 trivia로 나눕니다. 단순한 정규식 목록처럼 보이지만 longest match, keyword, escape, newline, mode와 오류 위치가 parser와 formatter의 계약을 결정합니다.

## 학습 목표

- token kind, lexeme, literal value와 span을 분리합니다.
- longest match와 우선순위 규칙을 결정적으로 적용합니다.
- whitespace·comment를 버릴지 보존할지 목적에 맞게 선택합니다.
- 잘못된 입력에서도 lexer가 전진하고 정확한 오류 범위를 남기게 합니다.

## Token은 문자열보다 많은 정보를 가집니다

```text
Token
  kind:       IDENT | INT | PLUS | ...
  span:       source의 byte range
  lexeme:     필요할 때 source에서 조회
  value:      decode된 정수·문자열 등 선택 값
  leading:    comment/space trivia 선택
  synthetic:  parser recovery가 만든 token인지 여부
```

Lexeme를 token마다 복사할 필요는 없습니다. Immutable source와 span이 있으면 slice로 얻을 수 있습니다. 반면 string escape를 해석한 runtime value는 원문과 다르므로 별도 저장하거나 semantic phase에서 계산합니다.

## Cursor invariant

Lexer loop는 다음 상태를 가집니다.

```text
source_bytes
cursor
current token start
mode
```

매 반복은 반드시 하나를 만족해야 합니다.

1. `cursor`가 증가합니다.
2. EOF token을 만들고 종료합니다.
3. 내부 오류로 중단합니다.

잘못된 UTF-8 또는 알 수 없는 문자에서 diagnostic만 만들고 cursor를 유지하면 무한 loop가 됩니다.

## Longest match와 우선순위

`=`과 `==`, `<`과 `<=`처럼 prefix가 같은 token이 있습니다.

```text
==  는 EQ_EQ 한 개
=   는 EQ 한 개
```

기본 원칙은 같은 시작점에서 가능한 가장 긴 token을 선택하는 maximal munch입니다. 길이가 같을 때 keyword와 identifier 규칙처럼 명시적 우선순위를 둡니다.

Identifier를 먼저 읽은 뒤 전체 lexeme가 keyword table에 있으면 keyword kind로 바꾸는 방식이 단순합니다.

```text
fn main()  → FN IDENT LEFT_PAREN RIGHT_PAREN
format     → IDENT
```

Contextual keyword는 lexer가 무조건 keyword로 만들지 않고 parser 또는 semantic context에서 해석할 수 있습니다. 어떤 단계가 소유하는지 명세에 고정합니다.

## 숫자 literal

다음 항목은 서로 다른 결정입니다.

- 허용 진법
- `_` separator 위치
- leading zero
- suffix
- 최대 bit width
- 부호의 소유 phase

`-42`를 하나의 signed literal token으로 만들면 binary subtraction과 precedence 처리가 복잡해집니다. Mica는 `-` token과 `42` token으로 나누고 parser가 unary expression을 만듭니다.

정수 범위 초과를 lexer가 보고할 수도 있고 type/runtime phase가 보고할 수도 있습니다. Lexer가 arbitrary precision 임시 값을 읽고 target type 결정 뒤 검사하면 suffix와 context를 지원하기 쉽습니다. Mica core는 10진수만 허용하고 `0..INT64_MAX`를 벗어난 token을 lex 단계 `MICA1004`로 보고합니다.

## 문자열과 escape

문자열 scanner는 일반 mode와 다른 상태를 가질 수 있습니다.

```text
"hello\nworld"
```

분리해야 할 것:

- raw source span
- decoded value
- escape별 source span
- 닫는 quote 존재 여부

잘못된 escape 하나 때문에 문자열 전체를 잘못된 문자로 보고하지 않습니다. 가능한 경우 닫는 quote까지 진행하고 escape 위치에 diagnostic을 붙입니다. 닫히지 않은 문자열은 newline 허용 정책에 따라 줄 끝 또는 EOF까지 span을 잡습니다.

Interpolation을 지원하면 mode stack이 필요할 수 있습니다.

```text
"value = ${expr}"
```

문자열 조각과 expression lexer를 오가며 brace depth를 추적해야 합니다. Mica core는 interpolation을 지원하지 않아 이 복잡성을 의도적으로 제외합니다.

## Whitespace와 comment

Parser에 필요 없는 공백을 완전히 버릴 수 있지만 formatter·doc comment·source-preserving refactoring에는 trivia가 필요합니다.

선택지:

1. token의 leading/trailing trivia로 소유
2. CST의 독립 node로 보존
3. 별도 trivia stream과 offset index 유지

Comment ownership이 모호하면 node 이동 시 comment가 사라지거나 다른 declaration에 붙습니다. 문법에는 영향이 없어도 public tooling contract에 포함됩니다.

## Layout-sensitive language

Python처럼 indentation이 block을 결정하면 lexer는 line start, indent stack, 괄호 depth를 상태로 가집니다.

```text
INDENT
DEDENT
NEWLINE
```

Tab 혼합, 빈 줄, comment-only line과 EOF에서 남은 DEDENT를 어떻게 만들지 명세해야 합니다. 이 가이드는 원리를 설명하지만 Mica는 brace를 사용해 layout token을 요구하지 않습니다.

## Token stream API

Parser가 필요한 최소 연산:

```text
peek(k)
current()
advance()
match(kind)
expect(kind)
position()
```

`peek`가 EOF 뒤에도 안정적으로 EOF를 반환하면 parser 경계 검사가 단순해집니다. Token 배열 전체를 먼저 만들 수도 있고 lazy lexer를 사용할 수도 있습니다.

### Eager

- diagnostic과 token snapshot이 안정적입니다.
- parser가 임의 lookahead를 쉽게 사용합니다.
- 큰 파일에서 메모리를 더 사용합니다.

### Lazy

- 필요한 만큼만 읽습니다.
- mode와 parser feedback을 연결하기 쉽습니다.
- rollback, error recovery와 incremental cache가 복잡해집니다.

작은 compiler는 eager tokenization으로 시작하는 편이 좋습니다.

## Incremental lexing

Edit가 발생해도 lexical state가 멀리 전파될 수 있습니다. 예를 들어 block comment 시작을 추가하면 파일 끝까지 token이 바뀔 수 있습니다.

Incremental lexer는 안정된 checkpoint를 저장합니다.

```text
line start offset
lexer mode
indent stack 또는 delimiter state
prefix token hash
```

변경 전후 상태와 token suffix가 같아지는 지점에서 재사용할 수 있습니다. 정확성 검증 없이 “수정된 줄만 다시 lex”하면 multiline string과 comment에서 틀립니다.

## 대표 실패

- keyword prefix를 잘못 분리해 `format`을 `for` + `mat`으로 만듭니다.
- `==`를 `=` 두 개로 만듭니다.
- 잘못된 escape에서 cursor가 전진하지 않습니다.
- comment span이 newline을 잘못 소유해 formatter가 빈 줄을 없앱니다.
- `CRLF`에서 `\r`을 unknown token으로 만듭니다.
- EOF token span이 source length를 넘습니다.

## 실습 연결

[Lexer·parser·AST exercise](../../exercises/02-lexer-parser-and-ast/README.md)에서 Mica token kind, longest-match fixture와 잘못된 문자열 case를 구현합니다.

## 점검 질문

1. `-42`를 한 token으로 만들 때 생기는 parser 경계는 무엇입니까?
2. comment를 버리면 어떤 도구 기능이 어려워집니까?
3. lexical error 뒤 cursor 전진을 어떻게 보장합니까?
4. contextual keyword의 소유 phase는 어디입니까?
5. multiline state가 있는 lexer를 한 줄만 재실행하면 왜 틀릴 수 있습니까?
