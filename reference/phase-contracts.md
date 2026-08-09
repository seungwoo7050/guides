# Phase contract 작성표

새 phase나 pass를 추가할 때 다음 표를 채웁니다. Data structure 이름보다 외부 보장과 invalid state를 먼저 적습니다.

| 항목 | 질문 |
|---|---|
| 목적 | 이 phase가 없으면 어떤 질문에 답할 수 없습니까? |
| Input identity | Source/version/module/function 중 무엇을 입력으로 식별합니까? |
| Input invariant | 앞 phase가 반드시 보장해야 하는 구조·type·span은 무엇입니까? |
| Output | 어떤 schema와 identity를 생성합니까? |
| Preserved information | Source span, symbol, type, effect와 evaluation order 중 무엇을 보존합니까? |
| Discarded information | 의도적으로 버리는 trivia·surface distinction은 무엇입니까? |
| User error | 어떤 잘못된 program을 stable diagnostic으로 거부합니까? |
| Recovery | Error node/type/symbol로 어느 정도 계속 진행합니까? |
| Internal invariant | 깨지면 사용자 오류가 아니라 compiler defect인 조건은 무엇입니까? |
| Resource limit | 입력 크기, recursion, worklist, diagnostic budget을 어디서 제한합니까? |
| Determinism | Hash/order/thread/timing에서 결과 순서를 어떻게 고정합니까? |
| Cache key | Incremental 실행에서 어떤 dependency가 바뀌면 무효화합니까? |
| Verification | Unit, property, differential, verifier 중 무엇으로 검사합니까? |
| Known-bad | 어떤 한 줄의 오류가 검사에 반드시 거부돼야 합니까? |
| Compatibility | Schema·diagnostic·artifact를 변경할 때 소비자에게 어떤 영향을 줍니까? |

## 예: name resolution

```text
목적
  NameExpr 문자열을 declaration의 SymbolId에 연결한다.

입력
  recovery AST, top-level signature table

입력 invariant
  모든 node에 valid span과 unique NodeId가 있다.

출력
  NodeId -> SymbolId table, scope tree, resolution diagnostics

보존
  source declaration/reference span, shadowing identity

사용자 오류
  unknown name, same-scope duplicate, immutable assignment target

복구
  unresolved reference에 ErrorSymbol을 연결해 type phase가 crash하지 않게 한다.

internal invariant
  한 NodeId에 서로 다른 SymbolId를 두 번 기록하지 않는다.

검증
  forward call, recursion, nested shadowing, duplicate, invalid AST recovery fixture
```

## Pass pipeline review

두 phase를 합치려 할 때 다음을 확인합니다.

- Parser와 type checker를 합치면 syntax recovery가 semantic table을 오염시키지 않습니까?
- AST를 in-place mutate하면 이전 symbol/type/cache가 stale해지지 않습니까?
- Optimization이 runtime failure와 effect order를 지우지 않습니까?
- Backend adapter가 source language 의미를 target의 undefined behavior로 바꾸지 않습니까?
- LSP adapter가 batch compiler의 core 결과를 다시 해석하지 않습니까?
