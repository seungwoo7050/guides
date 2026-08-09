# 확장 실습과 실제 프로젝트 연결

핵심 Part와 Mica capstone을 완료한 뒤 하나의 확장만 선택합니다. 기능을 많이 넣기보다 새 기능이 바꾸는 phase contract와 실패를 끝까지 연결합니다.

## 1. Nested function과 closure

추가 범위:

- nested declaration scope
- capture 분석
- mutable cell/upvalue
- closure value type
- VM open/closed upvalue
- lifetime와 GC root
- debug/rename reference

검증:

- outer frame 종료 뒤 값 유지
- 여러 closure가 mutable cell 공유
- shadowed capture 구분
- recursive closure와 cycle

## 2. Aggregate와 user-defined type

```text
struct Point { x: Int, y: Int }
```

필요 변화:

- type namespace와 declaration collection
- field resolution
- nominal/structural identity 선택
- layout와 initialization
- field place/value
- formatter·hover·definition
- FFI representation

Memory layout을 source field 순서와 자동 동일시하지 않습니다.

## 3. Generic과 type inference

```text
fn identity<T>(value: T) -> T
```

필요 변화:

- type parameter scope
- constraint와 unification
- occurs check
- monomorphization 또는 type erasure
- overload/ambiguity
- error reporting origin
- cache key에 type argument 포함

먼저 generic function 하나와 call inference만 구현하고 trait/constraint system 전체로 확대하지 않습니다.

## 4. Module과 import

```text
module graph
→ header/export collection
→ cycle policy
→ body resolution
→ initialization order
```

검증:

- deterministic module order
- duplicate/ambiguous import
- public signature 변경의 dependent invalidation
- initialization cycle
- private symbol visibility

## 5. Pattern matching과 exhaustiveness

- algebraic data type
- pattern binding scope
- guard
- exhaustiveness와 redundancy
- decision tree lowering
- source diagnostic

Nested pattern matrix는 알고리즘 문헌을 참조하고 작은 enum부터 시작합니다.

## 6. Exception과 cleanup

- throw/catch/finally syntax
- type/effect policy
- exceptional CFG edge
- cleanup region
- VM unwinding
- native unwind ABI
- stack trace와 source origin

Return, break, runtime error와 exception이 같은 cleanup을 지나도록 검증합니다.

## 7. Garbage collector

선택:

- mark-sweep
- reference counting + cycle 사례
- copying collector 모형

필수 기록:

- object layout
- root set
- allocation failure
- pause/trigger policy
- FFI handle
- finalizer 비보장

Host object를 wrapping한 것과 collector 자체를 구현한 것을 구분합니다.

## 8. SSA와 optimization pipeline

- dominance frontier
- phi insertion
- rename
- sparse constant propagation
- dead code elimination
- loop invariant code motion 선택
- analysis invalidation
- translation validation

각 pass에 known-bad와 interpreter differential test를 둡니다.

## 9. WebAssembly target

- Mica type→Wasm type mapping
- structured control flow
- linear memory와 string ABI
- import/export
- runtime builtin
- browser/WASI 실행 경계
- source map/debug 선택

Wasm sandbox가 host import의 권한까지 자동 제한하는 것은 아닙니다.

## 10. Incremental parser

두 경로:

- 직접 checkpoint/reparse range 구현
- Tree-sitter grammar와 adapter

검증:

```text
incremental result == full reparse result
```

Edit sequence를 random 생성하고 error recovery, comment, multiline string에서 비교합니다.

## 11. Language server 확장

- completion과 resolve
- references
- rename
- semantic tokens
- code action
- workspace symbol
- multi-root workspace

Latency budget, cancellation, partial result와 stale version을 기능별로 기록합니다.

## 12. Macro

Macro는 문자열 치환으로 시작하지 않습니다.

- token/AST macro 선택
- expansion phase
- hygiene와 generated symbol
- call/definition site origin
- recursion/depth limit
- cache와 incremental invalidation
- diagnostic expansion trace

## 13. Static analyzer

기존 Mica front-end를 사용해 checker를 추가합니다.

- null/resource state 같은 lattice
- interprocedural summary
- path sensitivity
- false positive와 suppression
- fix 안전성

Rule 개수보다 analysis fact와 counterexample trace의 정확성을 우선합니다.

## 14. 기존 프로젝트에 기여하기

프로젝트를 고를 때 phase와 첫 기여 범위를 찾습니다.

| 분야 | 첫 기여 예 |
|---|---|
| parser | 누락 recovery case와 regression fixture |
| compiler frontend | diagnostic span/message와 negative test |
| type checker | 작은 rule bug 최소 재현 |
| optimizer | verifier·known-bad·pass test |
| interpreter/VM | runtime error와 stack trace fixture |
| formatter | comment/idempotence regression |
| language server | stale version/cancellation bug |
| binding/FFI | ownership·error 문서와 test |

먼저 issue와 기여 규칙을 읽고, 현재 code가 실제로 보장하는 상태를 조사합니다. 대규모 architecture 변경보다 작은 재현·test·fix로 시작합니다.

## 확장 완료 기록

- 추가한 syntax/static/runtime contract
- 영향받은 phase 목록
- 새 error code와 compatibility
- 정상·경계·실패 fixture
- known-bad와 verifier 결과
- 성능/resource 측정이 있다면 조건
- core Mica와 달라진 점
- 남은 비보장과 다음 기여 후보
