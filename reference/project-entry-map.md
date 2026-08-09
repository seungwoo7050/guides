# 실제 프로젝트 진입 지도

이 목록은 추천 순위가 아니라 capstone phase를 실제 저장소의 작은 변경으로 연결하는 예시입니다. 기여 전 해당 프로젝트의 최신 contributing guide, issue policy, build와 test를 직접 확인합니다.

## 작은 첫 기여 유형

| 관심 영역 | 첫 변경 후보 | 필요한 증거 |
|---|---|---|
| Lexer/parser | crash 또는 잘못된 recovery fixture | 최소 source, expected tree/diagnostic, termination |
| Diagnostic | 잘못된 span·중복 오류·불명확한 note | before/after output, source location test |
| Name/type | shadowing·overload·flow regression | symbol/type table 또는 semantic test |
| Interpreter/VM | runtime 오류·stack verifier·disassembly | malformed input, deterministic trace |
| IR/pass | verifier 누락·잘못된 transform | before/after IR, semantic/differential test |
| Formatter/linter | comment 손실·false positive·unsafe fix | idempotence, round-trip, focused fixture |
| Language server | stale diagnostic·position 오류 | JSON-RPC transcript, document version |
| Build/tooling | 오래된 command·불안정 test | clean build, exact platform/version |

## 조사할 프로젝트 범주

### Interpreter와 runtime

- CPython
- Lua
- Ruby
- language-specific small interpreter repositories

처음에는 object model 전체보다 parser diagnostic, library test, bytecode disassembly와 작은 regression을 찾습니다.

### Compiler infrastructure

- LLVM/Clang
- GCC
- Rust compiler
- Swift compiler

전체 build 비용이 크므로 component-specific test command와 issue label을 먼저 조사합니다. IR pass나 backend를 처음부터 만들기보다 diagnostic fixture, verifier test, 작은 analysis bug가 현실적인 진입점입니다.

### Static analyzer와 type checker

- TypeScript
- Pyright
- mypy
- Clang Static Analyzer

Symbol identity, narrowing, incremental cache와 diagnostic compatibility를 Mica의 resolution/type/flow 단계와 대응해 봅니다.

### Parser와 syntax tooling

- Tree-sitter core와 language grammar
- formatter/linter 프로젝트
- editor parser libraries

Grammar 변경은 parse 성공만 확인하지 않고 corpus, conflict, error recovery와 generated node shape를 함께 검토합니다.

### Language server

- clangd
- rust-analyzer
- typescript-language-server 계열
- 각 언어의 공식 language server

Protocol adapter보다 snapshot/query architecture, cancellation, stale result와 position conversion 관련 test를 먼저 찾습니다.

## 저장소 조사 기록

```text
project와 revision
build/test command
관심 phase의 source path
public input/output contract
대표 error/recovery test
작은 issue 또는 known limitation
Mica와 같은 점
Mica보다 복잡한 production constraint
첫 기여 후보와 비범위
```

프로젝트 이름을 아는 것보다 한 하위 시스템의 변경이 어떤 test와 release contract를 통과하는지 복원하는 것이 목표입니다.
