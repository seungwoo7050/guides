# Mica 언어 구현 capstone

`Mica`는 이 가이드의 개념을 하나의 작은 정적 타입 언어에 연결하기 위한 학습용 명세입니다. 산업용 언어의 기능을 축소해서 흉내 내는 것이 아니라, source 위치·진단·name/type·실행·artifact·tooling의 경계를 끝까지 완성할 수 있도록 범위를 제한합니다.

전체 작업 지침과 파일은 [`exercises/08-mica-capstone`](../exercises/08-mica-capstone/README.md)에 있습니다.

## 완료 목표

필수 경로:

```text
UTF-8 source snapshot
→ token + trivia + diagnostic
→ AST + recovery node
→ symbol resolution
→ static type / flow check
→ tree-walk interpreter
→ normalized IR / CFG verifier
→ data-flow fixed point / meaning-preserving pass
```

실행 확장 하나:

```text
A. bytecode compiler + verifier + VM
B. verified IR + LLVM 또는 다른 target backend
```

도구 확장 하나:

```text
A. canonical formatter + linter rule 3개 이상
B. language server: diagnostics + hover + definition
```

## 왜 기능을 제한합니까?

Mica core에는 다음이 없습니다.

- user-defined type, class와 inheritance
- generic과 overload
- module/import
- exception과 pattern matching
- pointer, array와 object mutation
- nested function과 closure
- macro와 compile-time execution

이 기능들은 각각 name/type/runtime/tooling을 크게 확장합니다. Core를 완성한 뒤 [확장 실습](80-extended-practice.md)에서 하나씩 추가합니다.

## 언어 요약

### Type

```text
Int       signed 64-bit, checked overflow
Bool
String    immutable Unicode text
Unit
```

Implicit conversion은 없습니다.

### Program

Top-level에는 function만 옵니다. Entry point는 정확히 다음 signature입니다.

```text
fn main() -> Int
```

### Declaration과 statement

```text
let name: Type = expression;   // immutable
var name: Type = expression;   // mutable
name = expression;
if condition { ... } else { ... }
while condition { ... }
return expression;
expression;
{ nested block }
```

`let`과 `var` 모두 initializer가 필수입니다.

### Expression

- integer, boolean, string literal
- name reference
- unary `-`, `!`
- arithmetic `+ - * / %`
- comparison `< <= > >=`
- equality `== !=`
- short-circuit `&& ||`
- function call
- parenthesized expression

### Builtin

```text
print_int(Int) -> Unit
print_bool(Bool) -> Unit
print_string(String) -> Unit
```

## 명세 정본

| 문서 | 정하는 것 |
|---|---|
| [언어 명세](../exercises/08-mica-capstone/spec/language.md) | type, evaluation order, scope, runtime failure |
| [문법](../exercises/08-mica-capstone/spec/grammar.ebnf) | token과 syntax structure |
| [진단](../exercises/08-mica-capstone/spec/diagnostics.md) | stable code, JSON, exit status |
| [Normalized AST](../exercises/08-mica-capstone/spec/normalized-ast.md) | 공개 node kind와 child field |
| [Semantic summary schema](../exercises/08-mica-capstone/spec/semantic.schema.json) | SymbolId·type·flow와 AST 연결 |
| [Bytecode](../exercises/08-mica-capstone/spec/bytecode.md) | VM 경로의 opcode·stack effect·frame |
| [Conformance](../exercises/08-mica-capstone/spec/conformance.md) | CLI, fixture와 완료 판정 |

설명 문서와 구현이 다르면 `spec/`가 capstone의 정본입니다. 명세 자체에 모순이 있으면 구현을 추측해 맞추지 말고 issue와 decision record로 수정합니다.

## 권장 architecture

```text
mica/
├── source.py          SourceId, snapshot, span, line map
├── diagnostic.py      structured diagnostic와 renderer
├── token.py
├── lexer.py
├── syntax.py          AST/CST와 NodeId
├── parser.py
├── symbol.py
├── resolver.py
├── types.py
├── typecheck.py
├── flow.py
├── interpreter.py
├── ir.py              필수 normalized IR/CFG
├── optimizer.py       필수 analysis/pass
├── bytecode.py        실행 선택 A
├── compiler.py        실행 선택 A
├── vm.py              실행 선택 A
├── backend.py         실행 선택 B
├── formatter.py       도구 선택 A
├── lints.py           도구 선택 A
├── server.py          도구 선택 B
└── driver.py          CLI adapter
```

이 구조를 그대로 복사할 필요는 없습니다. Phase input/output와 dependency direction을 유지해야 합니다.

```text
driver
→ source/diagnostic
→ lexer/parser
→ resolver/type/flow
→ execution/backend/tool adapters
```

Semantic core가 CLI나 LSP JSON-RPC에 직접 의존하지 않게 합니다.

## 단계 1. Source와 diagnostic

### 구현

- immutable UTF-8 source snapshot
- half-open byte span
- line map
- diagnostic JSON과 text renderer
- error budget과 deterministic ordering

### 완료 증거

- ASCII, 한글, non-BMP 문자 fixture
- `LF`와 `CRLF`
- zero-width EOF span
- invalid span constructor가 internal check에 거부됨
- same diagnostic JSON이 반복 실행에서 동일함

## 단계 2. Lexer와 parser

### 구현

- token kind와 trivia 정책
- longest match
- integer/string literal
- recursive descent declaration/statement parser
- Pratt expression parser
- ErrorExpr/ErrorStmt와 synchronization
- normalized AST JSON dump

### 완료 증거

- precedence/associativity matrix
- unterminated string과 invalid escape
- missing delimiter recovery
- arbitrary invalid token stream에서 timeout 없이 종료
- parser가 source span 범위를 벗어나지 않음

## 단계 3. Resolution, type와 flow

### 구현

- top-level function signature collection
- lexical scope와 SymbolId
- local shadowing, same-scope duplicate
- type rule와 ErrorType
- all-path return, unreachable 선택 warning
- `main` signature validation

### 완료 증거

- forward function call과 recursion
- unknown name와 duplicate declaration
- shadowed name이 다른 SymbolId
- operator/call/condition/return mismatch
- ErrorType로 같은 원인의 연쇄 진단 억제

## 단계 4. Tree-walk interpreter

### 구현

- tagged runtime value
- lexical environment와 mutable cell
- left-to-right evaluation
- short-circuit
- function call frame와 recursion limit
- checked i64 arithmetic
- output sink와 runtime stack diagnostic

### 완료 증거

- 정상 fixture stdout/return
- 오른쪽 effect가 실행되지 않는 short-circuit
- division by zero
- `MIN / -1`과 arithmetic overflow
- call-depth budget
- runtime 오류 뒤 host traceback이 사용자 출력에 섞이지 않음

## 단계 5. IR, CFG, data-flow와 pass

### 구현

- typed AST→normalized IR lowering
- basic block, terminator, value/type와 source origin
- 실행 전 CFG/IR verifier
- loop가 있는 data-flow fixed point
- checked constant fold와 unreachable removal 등 pass 두 개 이상
- pass가 무효화한 analysis 추적과 verifier 재실행

### 완료 증거

- normalized IR과 CFG edge dump
- malformed target/terminator/definition-use를 거부하는 verifier
- worklist convergence trace
- pass 전후 IR과 `changed` 결과
- 정상 result와 runtime diagnostic의 interpreter/IR differential
- `x / x → 1`처럼 trap/effect를 지우는 known-bad pass 거부

이 단계는 필수지만 공개 conformance runner가 교육적 완료를 자동 판정하지 않습니다. [`EVIDENCE.md`](../exercises/08-mica-capstone/skeleton/EVIDENCE.md)에 증거와 사람 판정을 남깁니다.

## 단계 6A. Bytecode VM

### 구현

- bytecode module/function/constant pool
- compiler emission과 jump patching
- local slot과 call frame
- bytecode verifier
- disassembler와 source map
- VM execution budget

### 완료 증거

- interpreter와 VM differential result
- invalid jump/local/stack merge fixture를 verifier가 거부
- nested branch/loop/function call
- runtime diagnostic code와 source origin 일치

## 단계 6B. LLVM 또는 다른 target backend

### 구현

- 필수 단계의 verified IR을 target contract에 맞게 lowering
- short-circuit/control flow 의미 보존
- typed value와 function declaration
- LLVM 또는 선택 target emission
- runtime builtin link
- object/JIT 실행

### 완료 증거

- MIR verifier
- LLVM verifier 사용 시 전후 통과
- interpreter와 backend differential result
- target/data layout 기록
- unsupported feature의 명시적 diagnostic

## 단계 7A. Formatter와 linter

### Formatter

- full-document canonical format
- comment 정책
- precedence 기반 parenthesis
- parse error 시 거부 또는 명시한 range policy
- idempotence와 parse round-trip

### Linter 최소 rule

- unused local
- unreachable statement
- shadowing 또는 constant condition

Fix는 effect와 source version을 보존할 수 있는 경우만 제공합니다.

## 단계 7B. Language server

최소 method:

- initialize/shutdown/exit
- textDocument open/change/close
- diagnostics
- hover
- definition

조건:

- document version
- position encoding 변환
- cancellation 또는 stale result discard
- batch semantic core 재사용

Completion, references와 rename은 선택입니다.

## CLI 계약

```sh
python -m mica lex FILE --json
python -m mica parse FILE --json
python -m mica check FILE --json
python -m mica run FILE --engine interpreter|vm --json
python -m mica verify-bytecode MODULE.json --json
python -m mica disassemble FILE --json # VM 경로
python -m mica format FILE             # formatter 경로
python -m mica lint FILE --json        # formatter+linter 경로
python -m mica serve                  # LSP 경로
```

Exit status:

```text
0 성공
1 source/runtime의 정의된 오류
2 CLI 사용 오류, 미구현 또는 internal compiler error
```

Structured JSON을 요청한 command는 stdout에 JSON만 쓰고 log/renderer는 stderr로 분리합니다.

## 제출물

- source와 실행 명령
- `IMPLEMENTATION.md`: phase 구조와 ownership
- `DECISIONS.md`: 명세 해석과 trade-off
- `LIMITATIONS.md`: 미구현·비보장 범위
- `EVIDENCE.md`: core·필수 IR·선택 실행/tooling·known-bad·사람 판정
- 테스트와 새 fixture
- conformance 실행 로그
- CFG/data-flow/pass trace와 의미 보존 결과
- VM/LLVM 또는 tooling 선택 경로 설명

## 완료 판정

공개 runner를 통과하는 것만으로 완료되지 않습니다.

1. 공개 fixture를 통과합니다.
2. 학습자가 만든 정상 fixture 3개 이상을 추가합니다.
3. 학습자가 만든 phase별 실패 fixture 5개 이상을 추가합니다.
4. known-bad 변경 하나가 자신의 검사에 거부됨을 기록합니다.
5. 필수 IR/CFG/data-flow/pass 증거와 verifier/differential을 제출합니다.
6. VM/backend 실행 확장 하나와 formatter+linter/LSP 도구 확장 하나를 완료합니다.
7. 같은 입력이 반복 실행에서 deterministic result를 냅니다.
8. 구현하지 않은 언어 기능을 명시적으로 거부합니다.
9. 실제 compiler/interpreter/tool 프로젝트 하나를 조사해 phase 대응표를 작성합니다.
10. `EVIDENCE.md`의 사람 판정에 미해결 `보완 필요`가 없습니다.

## 검수할 위험

- parser가 type/resolution을 함께 수행해 recovery 상태가 semantic table에 들어감
- AST node를 직접 mutate하고 stale type/symbol이 남음
- Python value semantics가 Mica overflow/type 규칙을 침범함
- diagnostic message만 test하고 code/span을 확인하지 않음
- VM이 invalid bytecode를 host exception으로 crash함
- formatter가 comment 또는 parenthesis로 의미를 바꿈
- LSP가 오래된 document version 결과를 게시함
- LLVM verifier 통과를 Mica 의미 보존으로 오해함
