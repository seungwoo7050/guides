# 사건 순서, causality와 logical clock

## 목표

공통 wall clock 없이도 message와 local execution이 만드는 causal order를 표현합니다. Lamport clock, vector clock, version vector와 physical clock의 역할을 구분하고, timestamp를 consistency 보장의 대체물로 사용하지 않습니다.

## 전체 순서가 항상 존재하지 않습니다

서로 다른 node에서 발생한 두 event 사이에 message 경로가 없다면 어느 것이 먼저인지 protocol 관점에서 결정할 근거가 없을 수 있습니다.

```text
A: local write x
B: local write y

두 node 사이에 message가 없으면 x와 y는 concurrent할 수 있습니다.
```

log 파일의 수집 시각이 `x=10:00:00.100`, `y=10:00:00.090`이라고 보여도 clock offset과 수집 지연 때문에 causality가 바뀌지 않습니다.

## Happened-before 관계

`a -> b`는 다음 규칙으로 정의합니다.

1. 같은 process에서 `a`가 `b`보다 먼저 발생했습니다.
2. `a`가 message send이고 `b`가 그 message receive입니다.
3. `a -> b`, `b -> c`이면 `a -> c`입니다.

`a -> b`도 `b -> a`도 아니면 두 event는 concurrent합니다.

이 관계는 physical time이 아니라 정보가 이동할 수 있었는지를 표현합니다.

## Lamport clock

각 process가 정수 counter를 유지합니다.

```text
local event 또는 send 전: counter += 1
send: message에 counter 포함
receive(ts): counter = max(counter, ts) + 1
```

보장:

```text
a -> b 이면 L(a) < L(b)
```

역은 성립하지 않습니다.

```text
L(a) < L(b)라고 해서 a -> b는 아닙니다.
```

Lamport timestamp와 node ID를 묶으면 event를 결정적으로 total order할 수 있지만, 그 order가 실제 causality를 더 많이 알아낸 것은 아닙니다. concurrent event 사이에 임의의 tie-break를 추가한 것입니다.

### 사용할 곳

- deterministic event ordering
- total-order broadcast 구현의 일부
- trace 정렬과 reproducible scheduler
- logical sequence를 부여하는 coordinator

### 사용하지 말아야 할 곳

- elapsed time 측정
- lease 만료
- concurrent update 탐지
- message가 실제로 최신이라는 증명

## Vector clock

각 participant별 counter를 가진 vector를 유지합니다.

```text
A: [2, 0, 0]
B: [1, 3, 0]
C: [1, 2, 4]
```

모든 component가 `<=`이고 하나 이상 `<`이면 앞 version이 causally before입니다. 어느 쪽도 component-wise `<=`가 아니면 concurrent입니다.

vector clock은 causality를 더 정확히 표현하지만 participant 수와 membership change에 따라 metadata가 커집니다.

### Version vector

replica별 version progress를 표현하는 데 사용합니다. 객체별 sibling이나 replica state의 causal 관계를 비교할 수 있습니다.

주의:

- client와 replica가 어떤 component를 증가시키는지 정해야 합니다.
- node ID 재사용은 오래된 version과 새 incarnation을 혼동시킬 수 있습니다.
- pruning은 단순 삭제가 아니라 causality 정보 손실을 의미합니다.
- vector가 concurrent하다고 conflict를 자동으로 merge할 수 있는 것은 아닙니다.

## Physical clock

physical clock은 실제 시간과 가까운 값을 제공하지만 다음 오차가 있습니다.

- node 간 offset
- drift
- NTP step 또는 slew
- VM pause와 scheduler delay
- leap second 처리

따라서 timestamp 비교로 “항상 최신 write”를 선택하면 clock skew에 의해 새 값이 사라질 수 있습니다.

### Clock uncertainty

시간 기반 순서를 safety에 사용하려면 오차 범위를 model에 포함해야 합니다. 예를 들어 clock API가 `[earliest, latest]` 구간을 제공하고 불확실성이 사라질 때까지 commit을 지연하는 설계가 가능합니다. 단순한 `now()` 호출과는 다른 계약입니다.

### Hybrid logical clock

physical time의 대략적인 순서와 logical counter를 결합할 수 있습니다. 운영 추적과 causality-preserving timestamp에 유용하지만, 다음을 자동 보장하지 않습니다.

- linearizability
- unique leader
- transaction serializability
- network partition 중 안전한 write 승인

보장은 HLC 자체가 아니라 HLC를 사용하는 protocol에서 나옵니다.

## Consistent cut와 global state

분산 trace의 일부 event를 선택해 global snapshot을 만들 때 message receive를 포함하면서 그 send를 제외하면 causal inconsistency가 생깁니다.

consistent cut의 직관:

```text
cut 안에 event b가 있고 a -> b라면 a도 cut 안에 있어야 합니다.
```

이 개념은 Chandy–Lamport snapshot, distributed checkpoint와 trace 분석의 기반입니다.

## Commit order와 causality

replicated log는 명령에 하나의 commit order를 부여할 수 있습니다. 이 순서는 client가 본 모든 physical time을 반영하는 것이 아니라 protocol이 선택한 serialization order입니다.

서로 다른 key나 shard에서 독립적으로 commit한 명령에는 전역 total order가 없을 수 있습니다. 전역 order가 필요하면 추가 coordination과 비용이 필요합니다.

## 실패 조건

- log 수집 timestamp를 happened-before 관계로 사용합니다.
- Lamport clock의 숫자 비교로 concurrency를 판정합니다.
- vector clock이 있으면 conflict merge가 자동 해결된다고 봅니다.
- node ID를 재사용하면서 version metadata를 유지합니다.
- last-write-wins를 사용하면서 clock skew와 data loss를 문서화하지 않습니다.
- HLC를 도입했다는 이유만으로 linearizability를 주장합니다.
- snapshot에서 receive를 포함하고 causal send를 제외합니다.

## 검증

[logical clock 예제](../../examples/logical-clocks/README.md)는 같은 event trace에 Lamport clock과 vector clock을 적용합니다.

[causality trace 실습](../../exercises/01-model-and-time/01-causality-trace/README.md)에서는 다음을 제출합니다.

- happened-before edge 목록
- concurrent event pair
- Lamport timestamp
- vector timestamp
- consistent하지 않은 cut와 수정한 cut

검사는 특정 숫자보다 관계를 봅니다.

```text
모든 causal edge에서 timestamp order가 보존됩니까?
concurrent pair를 vector가 incomparable하게 표현합니까?
cut가 causal predecessor를 모두 포함합니까?
```

## 완료 조건

- wall clock order와 happened-before를 구분합니다.
- Lamport clock이 제공하는 단방향 보장을 설명합니다.
- vector clock으로 causality와 concurrency를 판정합니다.
- version metadata의 node identity와 pruning 문제를 설명합니다.
- consistent cut를 trace와 snapshot에 적용합니다.
- timestamp가 consensus나 consistency protocol을 대체하지 않음을 설명합니다.
