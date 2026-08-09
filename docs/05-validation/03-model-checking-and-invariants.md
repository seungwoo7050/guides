# Model checking과 불변식

## 목표

protocol의 작은 추상 model에서 가능한 state transition을 체계적으로 탐색하고 safety invariant와 liveness property를 검사합니다. 테스트가 실행한 schedule만 보는 한계를 보완하되, model이 production 구현과 같다는 착각을 피합니다.

## Model의 구성

분산 protocol model은 다음을 가집니다.

```text
Variables
- node roles, terms, votes
- logs, commit and applied indexes
- messages
- timers 또는 abstract timeout event
- durable storage
- membership

Init
- 허용된 초기 state

Next
- 한 step에서 가능한 action의 disjunction

Invariant
- 모든 reachable state에서 참이어야 하는 property

Liveness
- fairness와 환경 가정 아래 결국 성립해야 하는 property
```

TLA+ 같은 specification language를 사용할 수 있지만 핵심은 도구 이름이 아니라 state와 transition을 명시적으로 만드는 것입니다.

## 추상화

production value 전체를 model에 넣으면 state space가 폭발합니다. safety에 필요한 구분만 남깁니다.

예:

```text
실제 command payload -> {A, B}
실제 node 수 100 -> 3 또는 5
실제 log 길이 -> 2~4
실제 timeout 값 -> timeout event 발생 가능 여부
```

좋은 추상화는 위반 가능성을 제거하지 않으면서 state 수를 줄입니다.

나쁜 추상화:

- network message를 항상 FIFO로 만들어 reorder bug를 제거
- crash-recovery model에서 durable·volatile state를 합침
- term을 boolean으로 줄여 stale-term path를 잃음
- membership transition을 한 atomic assignment로 만들어 중간 quorum bug를 숨김

## Safety invariant 작성

좋은 invariant는 implementation field에 연결됩니다.

```text
ElectionSafety ==
  forall term:
    Cardinality({n: role[n]=Leader and currentTerm[n]=term}) <= 1

StateMachineSafety ==
  forall n1, n2, index:
    if Applied(n1,index) and Applied(n2,index)
    then Command(n1,index)=Command(n2,index)
```

최종 결과가 아니라 intermediate reachable state에서 검사합니다.

## Inductive invariant

원하는 safety property가 true여도 model checker가 proof를 위해 더 강한 보조 invariant를 필요로 할 수 있습니다.

예:

- vote는 durable term과 함께 저장됨
- committed index 이전 log prefix는 leader마다 일치
- applied entry는 committed임
- snapshot boundary term이 log matching과 일치
- configuration entry는 log order대로 적용됨

보조 invariant는 구현의 숨은 계약을 드러냅니다.

## Liveness와 fairness

message delivery가 영원히 선택되지 않는 schedule을 허용하면 정상 protocol도 progress하지 않습니다. fairness를 정확히 선택합니다.

- weak fairness: action이 계속 enabled면 결국 실행
- strong fairness: action이 반복적으로 enabled면 결국 실행

network partition을 무한히 허용하면서 “모든 command가 결국 commit”을 요구할 수는 없습니다. liveness property에는 stable majority와 delivery 조건을 포함합니다.

## State explosion

줄이는 방법:

- symmetry set으로 node ID 대칭 처리
- small scope
- bounded log·client·key
- derived value 제거
- message multiset의 canonical ordering
- independent action의 partial-order reduction
- refinement 단계별 model 분리

먼저 election만, 그다음 log replication, snapshot, membership을 단계적으로 추가합니다.

## Model과 code 연결

가능한 방식:

- model action과 code handler 이름을 맞춥니다.
- model trace를 simulator schedule로 변환합니다.
- code state를 abstract model state로 projection합니다.
- runtime assertion으로 model invariant 일부를 검사합니다.
- protocol change PR에 model change와 counterexample을 함께 둡니다.

model checker가 통과해도 code가 model과 다르면 보장은 전달되지 않습니다.

## Refinement checking

추상 protocol과 구체 protocol의 behavior 관계를 검사할 수 있습니다.

```text
concrete state
- batched AppendEntries
- snapshot chunks
- retry queues

abstract state
- atomic log append
- atomic snapshot install
```

각 concrete step이 abstract no-op 또는 허용 transition으로 대응해야 합니다.

가이드에서는 완전한 refinement proof보다 mapping과 proof obligation을 문서화하는 수준으로 시작합니다.

## Model counterexample

counterexample은 실행 trace입니다.

```text
Init
→ A timeout, term 1 vote A
→ vote response delayed
→ A crash before durable vote   # 모델이 허용하면 문제
→ A restart
→ B requests vote term 1
→ A votes B
→ two leaders term 1
```

이를 code simulator의 fault schedule과 regression test로 변환합니다.

## Property-based state model

formal tool을 바로 사용하지 않아도 작은 Python model과 generated command sequence로 같은 사고방식을 적용할 수 있습니다.

- reference sequential model
- system-under-test adapter
- generated event sequence
- invariant check
- shrinking

다만 concurrency·message interleaving 전체를 탐색하는 능력은 제한됩니다.

## 실패 조건

- model checker가 통과했다는 사실만으로 production correctness를 주장합니다.
- network FIFO·no-duplicate 같은 가정을 문서화하지 않습니다.
- safety property만 적고 inductive helper invariant를 숨깁니다.
- 무한 partition을 허용하면서 unconditional liveness를 요구합니다.
- state space를 줄이면서 bug 원인이 되는 intermediate state를 atomic 처리합니다.
- model counterexample을 code regression test로 옮기지 않습니다.
- code change 뒤 model mapping을 갱신하지 않습니다.

## 검증

capstone에서 최소한 다음 abstract model을 작성합니다.

```text
nodes = 3
terms = 0..2
log entries = 0..2
commands = {A, B}
network = message multiset
faults = crash, restart, drop, duplicate, reorder
```

검사:

- election safety
- log matching
- leader completeness의 bounded form
- state machine safety
- client effect deduplication

선택 경로는 [TLA+와 proof 도구](../90-optional-paths/01-tla-plus-and-proof-tools.md)를 참고합니다.

## 완료 조건

- variables, Init, Next, invariant와 liveness를 분리합니다.
- safety에 필요한 정보를 보존하며 model을 추상화합니다.
- helper invariant와 fairness 가정을 명시합니다.
- counterexample을 simulator schedule과 regression test로 옮깁니다.
- model과 code 사이의 refinement gap을 기록합니다.
