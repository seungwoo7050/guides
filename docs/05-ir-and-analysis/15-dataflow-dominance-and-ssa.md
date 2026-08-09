# Data-flow, dominance와 SSA

CFG가 만들어지면 각 program point에서 성립하는 사실을 계산할 수 있습니다. Data-flow analysis는 “코드를 순서대로 훑어 추측”하는 대신 lattice, transfer와 merge를 정의해 loop와 여러 predecessor에서 보수적인 결과를 구합니다.

## 학습 목표

- forward/backward data-flow와 may/must analysis를 구분합니다.
- lattice, transfer function, meet와 fixed point를 compiler fact에 적용합니다.
- dominance와 immediate dominator의 의미를 설명합니다.
- SSA의 single assignment, phi/block parameter와 dominance invariant를 이해합니다.

## Data-flow framework

각 block에 fact를 둡니다.

```text
IN[B]
OUT[B] = transfer(B, IN[B])
```

Predecessor fact를 merge합니다.

```text
IN[B] = meet(OUT[P] for P in predecessors(B))
```

분석마다 direction과 meet가 다릅니다.

| 분석 | 방향 | 의미 | merge 예 |
|---|---|---|---|
| reaching definitions | forward | 이 지점에 도달할 수 있는 정의 | union |
| definite assignment | forward | 모든 경로에서 할당된 변수 | intersection |
| liveness | backward | 이후 사용될 수 있는 값 | union |
| available expressions | forward | 모든 경로에서 이미 계산됨 | intersection |

Union이라고 항상 may, intersection이라고 항상 must인 것은 아니며 fact order 정의에 따라 달라집니다. 분석 의미를 먼저 씁니다.

## Lattice와 종료

Finite fact set의 powerset은 inclusion order로 lattice를 이룹니다. Monotone transfer와 유한 높이가 있으면 worklist가 fixed point에 도달합니다.

```text
worklist = all blocks
while worklist:
    block = pop()
    new = transfer(merge(pred facts))
    if new != old:
        update
        push successors
```

Loop가 있어도 fact가 한 방향으로만 변하고 가능한 상태가 유한하면 종료합니다. Widening이 필요한 infinite domain analysis는 확장 주제입니다.

## Worklist 순서

Reverse postorder는 forward analysis의 수렴을 빠르게 할 수 있지만 결과 의미를 바꾸면 안 됩니다. Hash iteration 순서에 따라 diagnostic이나 dump가 불안정하지 않도록 block order를 고정합니다.

## Liveness

Backward equation:

```text
OUT[B] = union(IN[S] for S in successors(B))
IN[B]  = USE[B] ∪ (OUT[B] - DEF[B])
```

Liveness는 register allocation, dead store와 closure capture lifetime에 사용됩니다. “값이 지금 존재함”과 “앞으로 사용될 수 있음”을 구분합니다.

May-trap/effect instruction의 result가 dead여도 instruction 자체가 dead인지 별도 판단합니다.

## Dominance

Block `A`가 `B`를 dominate한다는 뜻은 entry에서 `B`로 가는 모든 path가 `A`를 지난다는 것입니다.

성질:

- entry는 모든 reachable block을 dominate합니다.
- 각 block은 자신을 dominate합니다.
- unreachable block의 dominance 정책을 별도 처리합니다.

Immediate dominator는 `B`를 strict dominate하는 block 중 가장 가까운 하나입니다. Immediate dominator edge가 dominator tree를 만듭니다.

Dominance frontier는 phi placement와 일부 control dependence 분석에 사용됩니다.

## SSA

Static Single Assignment에서는 각 value가 정확히 한 번 정의됩니다.

```text
x0 = 1
if cond:
    x1 = 2
else:
    x2 = 3
x3 = phi(x1, x2)
```

핵심 invariant:

- definition은 모든 use를 dominate합니다.
- phi operand는 해당 predecessor edge에서 오는 value입니다.
- 각 SSA value의 type이 고정됩니다.

Block parameter 형태:

```text
then: jump merge(x1)
else: jump merge(x2)
merge(x3): ...
```

Phi보다 edge argument가 CFG 변환에서 다루기 쉬운 구현도 있습니다.

## Mutable local에서 SSA로

대표 과정:

1. CFG와 variable definition 위치를 찾습니다.
2. dominance frontier에 phi를 배치합니다.
3. dominator tree를 따라 variable을 rename합니다.
4. 각 use를 현재 version으로 연결합니다.

모든 local을 SSA로 만들 필요는 없습니다. Address-taken variable, captured mutable과 memory는 별도 memory model이 필요합니다. LLVM의 `mem2reg`처럼 stack slot을 승격하는 방식도 있습니다.

## Memory SSA와 alias

Pointer가 있으면 두 store가 같은 location인지 알기 어렵습니다.

```text
*p = 1
*q = 2
load *p
```

`p`와 `q` alias 가능성을 모르면 첫 store value를 그대로 사용할 수 없습니다. Alias analysis, memory SSA와 effect summary가 필요합니다. Mica core는 pointer를 지원하지 않아 local value SSA에 집중합니다.

## Analysis invalidation

CFG를 바꾸는 pass 뒤 dominance와 liveness 결과는 오래될 수 있습니다.

```text
PassResult
  changed
  preserved_analyses
```

모든 analysis를 매번 재계산하면 단순하지만 느립니다. Cache를 쓰면 pass가 무엇을 보존하는지 정확히 선언해야 합니다. 잘못된 preserved claim은 compiler miscompile을 만듭니다.

## Verifier

SSA verifier:

- value definition이 하나입니다.
- use의 function과 value owner가 같습니다.
- definition이 use를 dominate합니다.
- phi/block argument 수가 predecessor와 일치합니다.
- edge argument type과 block parameter type이 같습니다.
- unreachable block 정책이 일관됩니다.

Verifier 실패는 사용자 source error가 아니라 compiler 내부 오류입니다.

## 대표 실패

- loop를 한 번만 방문해 liveness를 계산합니다.
- definite assignment merge에 union을 사용합니다.
- dominance를 source order와 동일시합니다.
- phi operand를 predecessor가 아닌 block 전체 순서로 연결합니다.
- CFG pass 뒤 stale dominance 결과를 재사용합니다.
- dead result라는 이유로 may-trap instruction을 제거합니다.

## 실습 연결

[IR와 pass exercise](../../exercises/05-ir-analysis-and-passes/README.md)에서 definite assignment, liveness와 simple SSA rename을 수행합니다. `examples/dataflow-fixed-point`는 작은 CFG의 fixed point를 출력합니다.

## 점검 질문

1. liveness와 definite assignment가 서로 다른 방향과 meet를 쓰는 이유는 무엇입니까?
2. dominance와 “앞에 나온 block”의 차이는 무엇입니까?
3. SSA definition이 use를 dominate해야 하는 이유는 무엇입니까?
4. pointer/alias가 local SSA보다 어려운 이유는 무엇입니까?
5. pass가 CFG를 바꾼 뒤 어떤 analysis를 무효화해야 합니까?
