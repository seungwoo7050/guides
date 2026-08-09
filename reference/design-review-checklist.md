# 언어 구현 설계 검토표

## Source와 위치

- [ ] Source snapshot identity와 version이 있습니다.
- [ ] Core offset 단위가 byte/code point/UTF-16 중 무엇인지 명시했습니다.
- [ ] Span은 half-open이며 모든 constructor에서 범위를 검사합니다.
- [ ] `LF`, `CRLF`, tab, non-BMP와 zero-width EOF case가 있습니다.
- [ ] Protocol/rendering position을 core span과 분리했습니다.

## Front-end

- [ ] Lexer longest-match와 keyword 우선순위가 명세돼 있습니다.
- [ ] 모든 parser loop가 성공 시 cursor를 전진합니다.
- [ ] Precedence와 associativity matrix가 fixture에 있습니다.
- [ ] Recovery synchronization set와 error budget이 있습니다.
- [ ] CST/trivia와 AST의 목적을 구분합니다.
- [ ] AST node identity와 source origin이 deterministic합니다.

## 이름·type·flow

- [ ] String name과 SymbolId를 구분합니다.
- [ ] Declaration collection과 body resolution 순서가 명시돼 있습니다.
- [ ] Same-scope duplicate와 legal shadowing을 구분합니다.
- [ ] Error symbol/type가 연쇄 진단을 줄입니다.
- [ ] Type rule과 implicit conversion 정책이 문서화돼 있습니다.
- [ ] Return·reachability·initialization이 모든 CFG path를 고려합니다.

## Runtime

- [ ] Value representation에 explicit type/tag가 있습니다.
- [ ] Evaluation order와 short-circuit를 검사합니다.
- [ ] Mutable binding의 location/cell ownership이 명확합니다.
- [ ] Call frame, recursion과 execution budget이 있습니다.
- [ ] Host exception/overflow/truthiness가 언어 의미로 새지 않습니다.
- [ ] Runtime diagnostic가 source span과 call context를 보존합니다.

## IR와 optimization

- [ ] Basic block은 terminator를 하나만 갖습니다.
- [ ] CFG successor/predecessor와 value use가 verifier에 검사됩니다.
- [ ] Data-flow lattice, join, transfer와 종료 조건을 기록합니다.
- [ ] SSA dominance와 merge rule을 검사합니다.
- [ ] Pass별 pre/postcondition과 invalidation을 명시합니다.
- [ ] Effect·trap·overflow·evaluation order를 관찰 의미에 포함합니다.
- [ ] Known-bad pass가 differential/metamorphic test에 거부됩니다.

## Backend와 artifact

- [ ] Target triple·data layout·ABI·runtime version을 기록합니다.
- [ ] Unsupported operation의 legalization 또는 diagnostic가 있습니다.
- [ ] Checked source operation을 target UB로 낮추지 않습니다.
- [ ] Object symbol·section·relocation를 실제 도구로 관찰합니다.
- [ ] FFI의 ownership·lifetime·error·thread contract를 문서화합니다.
- [ ] JIT memory와 symbol lifetime 종료 순서를 검증합니다.

## Tooling

- [ ] Formatter가 idempotent합니다.
- [ ] Format 전후 parse/semantic 관계를 검사합니다.
- [ ] Comment와 필요한 parenthesis를 보존합니다.
- [ ] Lint rule의 analysis dependency와 false-positive 정책이 있습니다.
- [ ] Refactoring은 SymbolId와 source version을 사용합니다.
- [ ] LSP stdout에는 protocol만 쓰고 log를 분리합니다.
- [ ] Document version·position encoding·stale result를 처리합니다.
- [ ] Cancellation과 resource budget이 있습니다.

## Test와 compatibility

- [ ] Phase unit fixture가 있습니다.
- [ ] 정상·경계·실패·recovery case가 있습니다.
- [ ] Snapshot만 아니라 invariant를 검사합니다.
- [ ] Property, differential, metamorphic 또는 fuzz 중 하나 이상을 사용합니다.
- [ ] Crash input을 최소화해 regression fixture로 보존합니다.
- [ ] Diagnostic code·AST/IR schema·artifact version 변경 정책이 있습니다.
- [ ] 자동 검사가 보장하지 못하는 범위를 기록합니다.
