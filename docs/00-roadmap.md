# 학습 로드맵

## 대상 독자

하나 이상의 언어로 함수, 조건문, 반복문, 자료구조와 모듈을 작성해 본 개발자를 대상으로 합니다. 이 가이드는 Python·C++ 문법 입문서가 아니며 compiler theory 전체를 증명하는 과정도 아닙니다.

실행 가능한 예제와 capstone skeleton에는 Python 3.12 이상, POSIX shell, `make`와 Git이 필요합니다. 핵심 문서는 언어 중립이며 C++20·LLVM·Tree-sitter·LSP 경로는 선택 확장입니다.

## 선행지식

### 필수

- 함수 호출과 지역 변수의 실행 상태를 손으로 추적할 수 있습니다.
- list, map, stack과 tree의 기본 연산을 사용할 수 있습니다.
- 작은 프로그램의 정상·경계·실패 입력을 작성할 수 있습니다.

### 권장

- [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms): tree traversal, graph, fixed-point와 복잡도
- [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture): ISA, register, stack, ABI와 object 실행 경계
- [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems): process, virtual memory, file와 runtime 자원
- 구현 언어 하나: `python`, `cpp` 또는 `c`

모든 권장 브랜치를 완주할 필요는 없습니다. 각 문서가 필요한 접점을 명시하며 원래 브랜치의 소유 내용을 반복하지 않습니다.

## 종료 능력

가이드를 마친 독자는 다음을 할 수 있어야 합니다.

- 언어의 syntax, static semantics와 runtime semantics를 서로 다른 계약으로 작성합니다.
- source offset과 line/column을 변환하고 오류 뒤에도 유용한 diagnostic을 유지합니다.
- lexer와 parser의 상태, lookahead, precedence와 recovery를 설명합니다.
- CST와 AST를 목적에 맞게 구분하고 source 정보를 잃지 않는 lowering을 설계합니다.
- scope와 symbol identity를 기준으로 name resolution을 구현합니다.
- type rule을 judgment 또는 constraint로 쓰고 오류 전파와 중복 진단을 통제합니다.
- tree-walk interpreter 또는 bytecode VM의 environment, frame, stack과 runtime error를 구현합니다.
- CFG, data-flow, SSA의 전제와 optimization이 보존해야 하는 의미를 설명합니다.
- verifier, differential test, property test, fuzzing과 fixture로 phase 변환을 검사합니다.
- formatter·linter·language server 중 하나를 syntax와 semantic model 위에 구축합니다.
- 실제 compiler 또는 언어 도구 저장소에서 작은 bug·diagnostic·test·pass 변경에 진입합니다.

## 다루지 않는 것

- 형식 언어 이론과 type theory 전체
- parser generator별 API 암기
- 산업용 C++·Rust·JavaScript 언어 명세 전체
- register allocator, garbage collector, linker 또는 debugger의 완전한 구현
- 특정 LLVM 버전의 모든 C++ API
- 특정 editor extension 패키징
- 고성능 production JIT, tiered compilation과 profile-guided optimization 전체

이 주제들은 [확장 실습](80-extended-practice.md)과 실제 프로젝트에서 이어갑니다.

## 학습 순서

### Part 1. 언어 계약과 source model

1. [언어 경계와 phase contract](01-language-contract/01-language-boundary-and-phase-contracts.md)
2. [문자, source span과 위치](01-language-contract/02-source-text-spans-and-positions.md)
3. [진단, 오류 분류와 복구 계약](01-language-contract/03-diagnostics-errors-and-recovery.md)

이 Part에서 뒤의 모든 단계가 공유하는 source identity, 오류 코드와 phase 책임을 고정합니다.

### Part 2. Front-end

4. [Lexing과 token stream](02-front-end/04-lexing-and-token-streams.md)
5. [문법, recursive descent와 Pratt parsing](02-front-end/05-grammar-recursive-descent-and-pratt.md)
6. [CST, AST와 normalization](02-front-end/06-cst-ast-and-normalization.md)

문자를 구조로 바꾸되 parser가 언어의 모든 의미를 검사하려 하지 않도록 경계를 지킵니다.

### Part 3. 정적 의미

7. [Scope, symbol과 name resolution](03-semantics/07-scopes-symbols-and-name-resolution.md)
8. [Type rule, constraint와 checking](03-semantics/08-types-constraints-and-checking.md)
9. [Control flow, definite assignment와 effect](03-semantics/09-control-flow-definite-assignment-and-effects.md)

AST의 문자열 이름을 symbol identity와 type으로 연결하고, 모든 경로에서 return·초기화 조건이 유지되는지 검사합니다.

### Part 4. 실행과 runtime

10. [Tree-walk interpreter와 environment](04-execution/10-tree-walk-interpreter-and-environments.md)
11. [함수, closure와 runtime error](04-execution/11-functions-closures-and-runtime-errors.md)
12. [Bytecode, VM과 call frame](04-execution/12-bytecode-vm-and-call-frames.md)
13. [메모리 관리와 runtime service](04-execution/13-memory-management-and-runtime-services.md)

언어의 동적 의미를 명시적인 상태 전이로 구현합니다. capstone 핵심 경로는 host runtime을 사용하며 garbage collector 자체는 선택 확장입니다.

### Part 5. IR, 분석과 최적화

14. [Lowering, basic block과 CFG](05-ir-and-analysis/14-lowering-basic-blocks-and-cfg.md)
15. [Data-flow, dominance와 SSA](05-ir-and-analysis/15-dataflow-dominance-and-ssa.md)
16. [Optimization, correctness와 verifier](05-ir-and-analysis/16-optimization-correctness-and-verification.md)

분석 결과를 사실처럼 가정하지 않고 lattice, transfer function, convergence와 verifier 조건으로 기록합니다.

### Part 6. Backend와 실행 artifact

17. [Instruction selection, ABI와 object 경계](06-code-generation/17-instruction-selection-abi-and-object-boundaries.md)
18. [LLVM IR, JIT, object와 debug information](06-code-generation/18-llvm-ir-jit-object-and-debug-info.md)
19. [Linking, loading과 FFI](06-code-generation/19-linking-loading-and-ffi.md)

실제 ISA와 object format의 세부는 다른 가이드와 공식 명세에 맡기고, compiler가 어떤 계약을 전달해야 하는지 다룹니다.

### Part 7. 언어 도구와 검증

20. [Formatter, linter와 refactoring](07-language-tooling/20-formatters-linters-and-refactoring.md)
21. [Incremental analysis와 language server](07-language-tooling/21-incremental-analysis-and-language-servers.md)
22. [Testing, fuzzing와 compatibility](07-language-tooling/22-testing-fuzzing-and-compatibility.md)

편집 중인 불완전한 source를 처리하고, 진단·format·rename이 사용자 코드를 손상하지 않는지 검증합니다.

### Part 8. 통합 capstone

[Mica 언어 구현 capstone](08-mica-capstone.md)과 [`exercises/08-mica-capstone`](../exercises/08-mica-capstone/README.md)을 사용합니다.

필수 완료 경로:

```text
lexer
→ parser / AST
→ name resolution / type checking
→ tree-walk interpreter
→ diagnostic conformance
```

그 다음 하나를 선택합니다.

```text
A. bytecode compiler + VM
B. CFG/MIR + LLVM 또는 다른 backend
```

도구 경로에서도 하나를 선택합니다.

```text
formatter + linter
또는
LSP의 diagnostics / hover / definition subset
```

## Exercise 대응

| Part | Exercise | 자동 검사 범위 |
|---:|---|---|
| 1 | [Source와 diagnostic](../exercises/01-source-and-diagnostics/README.md) | 예제 renderer와 span fixture |
| 2 | [Lexer·parser·AST](../exercises/02-lexer-parser-and-ast/README.md) | Pratt 예제, AST schema와 수동 rubric |
| 3 | [Resolution·type·flow](../exercises/03-resolution-types-and-flow/README.md) | symbol table·type case·data-flow 예제 |
| 4 | [Interpreter와 VM](../exercises/04-interpreter-and-vm/README.md) | bytecode trace 예제와 runtime case |
| 5 | [IR와 pass](../exercises/05-ir-analysis-and-passes/README.md) | CFG·fixed-point·pass proof rubric |
| 6 | [Backend 경계](../exercises/06-backend-boundaries/README.md) | IR/object inspection 기록 |
| 7 | [언어 도구](../exercises/07-language-tools/README.md) | idempotence·round-trip·edit fixture |
| 8 | [Mica capstone](../exercises/08-mica-capstone/README.md) | 단계별 CLI conformance runner |

## 권장 반복 방식

각 phase에서 다음 기록을 남깁니다.

1. 입력 schema와 허용되지 않는 입력을 정의합니다.
2. 출력 schema와 보존해야 할 source·symbol·type 정보를 정의합니다.
3. 정상 상태 전이와 실패 종류를 분리합니다.
4. 가장 작은 입력을 손으로 추적합니다.
5. 구현 뒤 snapshot보다 구조적 invariant를 검사합니다.
6. known-bad 변형이 검사기에 거부되는지 확인합니다.
7. 다음 phase가 현재 출력에 암묵적으로 의존하지 않는지 검토합니다.

## 완료 기준

- Part 1–7의 핵심 문서와 대응 exercise rubric을 완료합니다.
- Mica 핵심 CLI의 `lex`, `parse`, `check`, `run` 계약을 구현합니다.
- 정상 fixture와 최소 5개 실패 fixture를 독립적으로 추가합니다.
- 진단에는 stable code, primary span과 설명이 포함됩니다.
- tree-walk 실행 경로와 bytecode/LLVM 중 하나를 구현합니다.
- formatter/linter 또는 LSP subset 하나를 구현합니다.
- 자동 검사가 거부하지 못하는 범위와 아직 구현하지 않은 언어 기능을 기록합니다.

## 자동 검증의 한계

저장소의 `verify.sh`는 문서·링크·명세 일관성, 작은 예제와 skeleton의 의도된 실패를 확인합니다. 완성 compiler의 의미 보존, 모든 입력에 대한 parser 종료, type soundness, optimization correctness 또는 editor 호환성을 증명하지 않습니다. capstone conformance runner도 공개 fixture에 대한 관찰 증거이며 추가 property·differential·fuzz 검증이 필요합니다.
