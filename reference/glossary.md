# 용어

## 언어 계약

### Concrete syntax

사용자가 실제로 쓰는 token과 구두점의 구조입니다. 괄호, comma, comment와 trivia를 포함할 수 있습니다.

### Abstract syntax

평가·type checking·변환에 필요한 의미 구조입니다. 불필요한 구두점은 제거할 수 있지만 source origin을 잃어서는 안 됩니다.

### Static semantics

Parsing 뒤 실행 전에 검사하는 이름, type, 흐름과 선언 규칙입니다.

### Dynamic semantics

Program이 실행 상태를 어떻게 바꾸고 어떤 값을 만들며 언제 실패하는지 정하는 규칙입니다.

### Phase contract

한 compiler 단계가 받는 입력, 내는 출력, 보존하는 정보, 사용자 오류와 internal invariant를 기록한 경계입니다.

## Source와 진단

### Source snapshot

특정 version의 immutable source text입니다. Incremental server에서는 path보다 `(document, version)` identity가 중요합니다.

### Span

Source 안의 half-open byte 범위 `[start, end)`입니다.

### Trivia

Whitespace와 comment처럼 semantic AST에는 직접 필요 없지만 formatting과 source reconstruction에 필요한 token 주변 정보입니다.

### Diagnostic

Code, severity, phase, message, primary/secondary span, note와 fix를 가진 구조화 오류·경고 데이터입니다.

### Recovery

오류 하나 뒤에도 parser나 analyzer가 제한된 유용한 결과를 만들기 위해 token을 건너뛰거나 error node를 삽입하는 정책입니다.

## Front-end

### Lexer

문자 stream을 token stream으로 바꿉니다.

### Parser

Token stream을 문법 구조로 바꿉니다.

### Recursive descent

문법 rule을 서로 호출하는 함수로 표현하는 top-down parsing 방식입니다.

### Pratt parser

Operator의 binding power로 prefix, postfix와 infix expression precedence를 처리하는 방식입니다.

### CST

Concrete syntax tree. 구두점·comment·오류 노드 등 source와 가까운 구조입니다.

### AST

Abstract syntax tree. 이후 semantic phase가 소비하도록 정규화한 구조입니다.

### Desugaring

여러 surface syntax를 더 작은 core construct로 낮추는 변환입니다.

## 이름과 type

### Scope

특정 위치에서 visible한 binding의 집합과 parent 관계입니다.

### Binding

Source declaration이 이름과 entity를 연결한 결과입니다.

### Symbol identity

같은 문자열 이름이 shadowing돼도 declaration별로 구분하는 안정된 identity입니다.

### Name resolution

Name reference를 어떤 symbol에 연결하거나 unresolved로 판정하는 과정입니다.

### Type checking

Expression과 statement가 type rule을 만족하는지 검사합니다.

### Constraint

아직 확정되지 않은 type 사이에 반드시 만족해야 하는 equality·subtyping 등의 관계입니다.

### Unification

Type variable과 structure의 equality constraint를 풀어 substitution을 만드는 과정입니다.

### Error type

Root type 오류 뒤의 연쇄 진단을 줄이기 위해 사용하는 특별한 복구 type입니다.

### Definite assignment

어떤 program point에 도달하는 모든 path에서 variable이 초기화됐는지 계산하는 분석입니다.

## 실행

### Environment

Name/symbol을 value 또는 mutable location에 연결하는 runtime 구조입니다.

### Call frame

한 function invocation의 instruction position, locals, operand stack와 caller 정보를 소유하는 상태입니다.

### Closure

Function code와 declaration 시점의 captured environment를 묶은 runtime value입니다.

### Tree-walk interpreter

AST node를 직접 방문하며 실행하는 interpreter입니다.

### Bytecode

Source와 machine instruction 사이의 portable한 실행 instruction 형식입니다.

### Virtual machine

Bytecode의 명시적인 stack/register/frame 상태를 갱신하며 실행하는 runtime입니다.

### Runtime service

Allocation, string, I/O, panic/diagnostic처럼 generated code와 실행 환경 사이에서 제공하는 기능입니다.

## IR와 분석

### IR

Intermediate representation. 특정 분석·변환·code generation 목적에 맞게 program을 표현한 구조입니다.

### Basic block

중간에 branch 없이 처음부터 끝까지 순차 실행되고 마지막에 하나의 terminator가 있는 instruction sequence입니다.

### CFG

Control-flow graph. Basic block을 node로, 가능한 control transfer를 edge로 나타냅니다.

### Terminator

Block의 successor나 function 종료를 정하는 마지막 instruction입니다.

### Data-flow analysis

CFG 위에서 abstract fact를 transfer하고 join하며 fixed point를 계산하는 분석입니다.

### Lattice

Data-flow fact의 정보 순서, join/meet와 수렴을 정의하는 구조입니다.

### Dominance

Entry에서 node `B`로 가는 모든 path가 node `A`를 지나면 `A`가 `B`를 dominate한다고 합니다.

### SSA

Static single assignment. 각 value definition이 한 번만 나타나고 merge에서 phi 또는 block parameter로 값을 합치는 표현입니다.

### Lowering

높은 수준 construct를 더 낮은 수준의 명시적인 control/data operation으로 바꾸는 변환입니다.

### Verifier

IR·bytecode의 구조, type, dominance, stack와 control-flow invariant를 실행 전 검사하는 component입니다.

### Optimization pass

Program의 관찰 의미를 보존하면서 IR을 바꾸는 변환입니다.

### Differential test

같은 input을 두 구현·두 execution path에 실행해 관찰 결과를 비교합니다.

### Metamorphic test

의미를 보존한다고 알려진 input 변환 전후 결과가 가져야 하는 관계를 검사합니다.

## Backend와 artifact

### Instruction selection

IR operation을 target instruction pattern으로 선택합니다.

### Legalization

Target이 직접 지원하지 않는 type·operation을 지원 가능한 형태나 helper call로 바꿉니다.

### ABI

독립적으로 생성된 code가 호출·data layout·register·stack·unwind를 공유하도록 정한 binary contract입니다.

### Object file

Code, data, symbol, relocation와 metadata를 담은 link 전 artifact입니다.

### Relocation

최종 address가 정해질 때 linker/loader가 고쳐야 하는 위치와 계산 방식입니다.

### JIT

Just-in-time compilation. 실행 process 안에서 IR 등을 machine code로 만들고 연결해 실행합니다.

### FFI

Foreign function interface. 서로 다른 언어/runtime 사이의 call, value representation, ownership와 error contract입니다.

## 개발 도구

### Formatter

Source의 의미와 필요한 trivia를 보존하면서 canonical layout을 만드는 도구입니다.

### Linter

Program이 유효하더라도 오류 가능성·유지보수성·정책 문제를 찾는 analysis rule 집합입니다.

### Refactoring

사용자 의도를 보존하며 여러 source location을 구조적으로 변경하는 작업입니다.

### Incremental analysis

Source edit 뒤 전체 계산을 반복하지 않고 invalidated dependency만 다시 계산합니다.

### Language server

Editor와 별도 process에서 diagnostics, hover, definition 등의 언어 기능을 protocol로 제공합니다.

### LSP

Language Server Protocol. Editor/client와 language server의 JSON-RPC message, lifecycle, document sync와 language feature를 표준화합니다.

### Stale result

분석이 시작된 source version보다 새 edit가 적용된 뒤 도착해 더 이상 게시하면 안 되는 결과입니다.
