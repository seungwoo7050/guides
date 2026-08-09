# Testing, fuzzing와 compatibility

언어 구현은 입력 공간이 매우 크고 phase가 많아 예제 몇 개로 정확성을 확인할 수 없습니다. Test 전략은 각 phase contract, 변환 동치, 잘못된 입력에서의 종료와 public artifact 호환성을 서로 다른 증거로 다뤄야 합니다.

## 학습 목표

- unit, golden, property, differential, metamorphic와 fuzz test의 역할을 구분합니다.
- parser·type checker·optimizer·VM의 known-bad를 검사기가 거부하게 합니다.
- random failure를 최소화하고 deterministic fixture로 보존합니다.
- source·diagnostic·AST/IR·bytecode·FFI의 compatibility 정책을 설계합니다.

## Test pyramid가 phase graph를 따라야 합니다

### Lexer

- token kind/span/value
- longest match
- Unicode/newline/escape
- invalid input에서도 progress

### Parser

- precedence/associativity
- recovery와 ErrorNode
- arbitrary token에서 termination
- parse/print/parse

### Semantic

- scope/shadowing
- symbol identity
- type rule positive/negative
- flow merge와 loop fixed point

### Runtime

- evaluation order
- recursion/frame cleanup
- checked arithmetic
- runtime diagnostic stack

### IR/backend

- verifier invariant
- differential execution
- pass precondition
- ABI/object structure

### Tooling

- format idempotence/round-trip
- rename scope safety
- stale version/cancellation
- incremental/full equivalence

## Unit test

작은 pure operation에 적합합니다.

- line map 변환
- token scanner
- precedence table
- type relation
- stack effect
- transfer function

Private implementation detail만 고정하지 않습니다. Refactoring해도 contract가 같으면 test가 유지되게 합니다.

## Golden/snapshot

Diagnostic renderer, AST/IR dump와 formatter에 유용합니다.

장점:

- 전체 구조 변화가 보임
- review하기 쉬움

위험:

- update 명령으로 오류를 그대로 승인
- pointer/id/order 같은 noise
- 의미 없는 formatting change가 큰 diff 생성

Snapshot은 stable normalized schema를 사용하고 각 변경의 이유를 review합니다.

## Property test

특정 입력이 아니라 항상 성립해야 하는 property를 검사합니다.

```text
all token spans within source
lexer always reaches EOF
format(format(x)) == format(x)
parse(format(valid x)) semantically equals parse(x)
bytecode verifier accepts compiler output
incremental parse equals full parse
```

Generator가 유효한 source와 intentionally invalid source를 모두 만들 수 있어야 합니다.

## Differential test

독립 구현 결과를 비교합니다.

- tree-walk interpreter vs bytecode VM
- unoptimized vs optimized IR
- incremental vs full analysis
- custom lexer/parser vs reference library subset

두 구현이 같은 front-end와 helper를 공유하면 공통 bug를 놓칠 수 있습니다. 비교 독립성을 기록합니다.

## Metamorphic test

정답 oracle 없이 의미를 보존해야 하는 변형을 적용합니다.

- alpha-renaming
- 의미 없는 parenthesis 추가
- comment/whitespace 변경
- unreachable declaration 추가 정책상 영향 없을 때
- constant expression과 동치 literal 교체 overflow 전제 하

Transformation precondition이 틀리면 test 자체가 잘못됩니다.

## Fuzzing

### Lexer/parser fuzz

Arbitrary bytes/token을 넣고 다음을 봅니다.

- crash 없음
- time/memory budget
- span invariant
- recovery loop 종료

### Grammar-based fuzz

Type-correct source 또는 특정 construct를 생성해 깊은 phase를 탐색합니다.

### Mutation fuzz

Valid corpus를 token 삭제·삽입·교체·중첩해 recovery를 자극합니다.

### IR/bytecode fuzz

Verifier는 arbitrary invalid artifact를 거부해야 합니다. Verified artifact만 VM/backend로 넘깁니다.

Untrusted JIT/native 실행은 별도 process sandbox에서 합니다.

## Failure minimization

Fuzzer failure는 큰 random source일 수 있습니다. Delta debugging으로 다음을 줄입니다.

- file/module 삭제
- statement/expression subtree 제거
- literal 단순화
- identifier 통합
- token range 삭제

최소화 중 failure signature를 안정적으로 정의합니다.

```text
crash type + phase + top stack frame
wrong output + backend pair
verifier code
hang timeout point
```

최소 case를 deterministic fixture와 regression test로 저장합니다.

## Mutation testing과 known-bad

Test가 실제로 오류를 잡는지 implementation을 일부러 바꿉니다.

- precedence swap
- resolver scope pop 제거
- ErrorType suppression 제거
- short-circuit eager execution
- jump offset off-by-one
- overflow check 제거
- formatter comment 삭제

모든 mutation을 자동화할 필요는 없지만 핵심 verifier에는 known-bad fixture를 둡니다.

## Determinism

Compiler 결과가 hash seed, thread scheduling, absolute path와 timestamp에 불필요하게 의존하지 않게 합니다.

- diagnostic 정렬
- stable symbol/block dump order
- fixed random seed 기록
- normalized path
- reproducible build option
- parallel pass 결과 merge order

Determinism이 language semantics인 것은 아니지만 test·cache·build provenance에 중요합니다.

## Compatibility surface

### Source language

- syntax와 semantics version
- deprecated feature와 migration
- edition/feature flag

### Diagnostic

- stable code 의미
- message text는 변경 가능 여부
- JSON schema version

### AST/IR dump

- debugging 전용인지 public API인지
- field/version policy

### Bytecode/artifact

- magic/version
- runtime compatibility
- verifier와 capability

### FFI/ABI

- symbol, layout, calling convention
- library version
- ownership/error contract

Public이라고 선언한 표면만 호환성을 약속합니다. 내부 IR text를 사용자가 사용한다고 해서 자동으로 stable API가 되지는 않지만 변경 위험을 문서화합니다.

## Backward/forward compatibility

- old compiler가 new source를 읽는가?
- new compiler가 old source/artifact를 읽는가?
- runtime이 다른 compiler version bytecode를 거부하는가?
- unknown field/opcode를 skip할 수 있는가?
- feature negotiation이 있는가?

Silent misinterpretation보다 명시적 version mismatch가 안전합니다.

## CI matrix

문서 중심 branch의 기본 CI:

- Python supported versions
- POSIX shell/link 검사
- examples deterministic output
- capstone spec schema
- skeleton intended failure

실제 implementation project:

- OS/architecture/compiler matrix
- debug/release/sanitizer
- optimization levels
- JIT/AOT
- incremental/full
- fuzzer smoke + 장기 scheduled run

## 대표 실패

- snapshot update로 잘못된 output을 승인합니다.
- fuzzer가 crash만 보고 semantic mismatch를 보지 않습니다.
- random seed와 generated source를 저장하지 못해 재현하지 못합니다.
- optimized/unoptimized가 같은 evaluator helper를 공유해 differential test가 약합니다.
- bytecode version mismatch를 무시해 opcode를 다른 의미로 실행합니다.
- diagnostic message 전체를 API로 고정해 문구 개선이 불가능해집니다.
- parser hang input을 timeout만 늘려 숨깁니다.

## 실습 연결

각 exercise는 최소 한 개의 known-bad를 요구합니다. Mica capstone은 [conformance 명세](../../exercises/08-mica-capstone/spec/conformance.md)와 runner를 제공하며 학습자가 fixture와 property를 추가해야 완료됩니다.

## 점검 질문

1. formatter에 idempotence와 semantic round-trip 두 property가 모두 필요한 이유는 무엇입니까?
2. differential test의 두 구현이 얼마나 독립적입니까?
3. fuzzer failure를 어떤 signature로 최소화합니까?
4. diagnostic code와 message 중 무엇을 stable API로 둘 수 있습니까?
5. version mismatch에서 명시적 거부가 silent compatibility보다 나은 이유는 무엇입니까?
