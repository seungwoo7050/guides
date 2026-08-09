# Consistency model과 client history

## 목표

“강한 일관성”, “최종 일관성” 같은 넓은 표현을 client operation history의 허용 규칙으로 바꿉니다. linearizability, sequential consistency, causal consistency, session guarantee와 eventual convergence를 서로 다른 계약으로 구분합니다.

## Consistency model은 허용 history의 집합입니다

history는 operation invocation과 completion을 기록합니다.

```text
1 invoke  c1 write(x, 1)
2 complete c1 OK
3 invoke  c2 read(x)
4 complete c2 0
```

write가 완료된 뒤 시작한 read가 이전 값을 반환했습니다. final state가 나중에 `1`로 수렴해도 이 history가 linearizable해지는 것은 아닙니다.

분산 시스템의 consistency를 검증할 때 internal log만 보지 않고 client-visible history를 기록해야 합니다.

## Linearizability

각 operation이 invocation과 response 사이의 한 순간에 원자적으로 실행된 것처럼 보이며, 겹치지 않는 operation의 real-time order를 보존합니다.

예:

```text
write(x, 1)가 완료된 뒤 read(x)가 시작했다면
read는 1 또는 그 뒤 write의 값을 반환해야 합니다.
```

특징:

- single-object specification과 잘 결합합니다.
- client가 wall clock을 직접 공유하지 않아도 invocation·completion 순서로 real-time 제약을 표현합니다.
- availability와 latency 비용이 커질 수 있습니다.
- leader write가 linearizable하다고 follower read도 자동 linearizable하지 않습니다.

## Sequential consistency

모든 operation을 각 process의 program order를 보존하는 하나의 sequential order로 배치할 수 있습니다. 그러나 서로 다른 process 사이의 real-time order를 반드시 보존하지 않습니다.

따라서 완료된 write 뒤 다른 client가 시작한 read가 이전 값을 볼 수 있어도, 어떤 global sequential order로 설명 가능하면 허용될 수 있습니다.

linearizability보다 약하지만 reasoning 방식은 여전히 하나의 total order를 사용합니다.

## Causal consistency

causally related operation의 순서를 모든 observer가 보존합니다. concurrent operation은 서로 다른 순서로 보일 수 있습니다.

```text
c1: write(x, 1)
c1: x=1을 읽은 뒤 write(y, 1)

다른 client가 y=1을 본다면 x=1보다 먼저 보이면 안 됩니다.
```

필요한 metadata와 delivery rule:

- dependency 또는 causal context
- session의 observed version
- causally ready한 update만 적용하는 buffer
- metadata pruning과 membership 처리

## Session guarantee

global consistency가 약해도 한 client session에 다음을 제공할 수 있습니다.

- read-your-writes
- monotonic reads
- monotonic writes
- writes-follow-reads

예를 들어 follower read 시스템에서 client가 이전에 본 version token을 보내고 그 이상을 apply한 replica로 routing할 수 있습니다.

session guarantee는 모든 client 사이의 global order를 제공하지 않습니다.

## Eventual convergence

새 update가 멈추고 replica 사이 통신과 repair가 계속되면 replica가 같은 state로 수렴합니다.

이 계약에 포함되지 않는 것:

- 언제 수렴하는지에 대한 finite bound
- 수렴 전 어떤 값을 읽는지
- conflict가 의도한 업무 결과로 merge되는지
- 완료된 write가 영원히 보존되는지
- session order

“eventual consistency”를 사용할 때 최소한 다음을 추가로 적습니다.

- conflict 표현 방식
- merge 함수의 성질
- anti-entropy 주기와 대상
- tombstone 보존과 garbage collection 조건
- client-visible stale bound 또는 session guarantee

## Read consistency의 구체화

API별로 계약을 나눕니다.

| API | 가능한 계약 예시 |
|---|---|
| account balance | linearizable 또는 strict serializable transaction |
| product catalog | bounded-stale 또는 eventual read |
| user preferences | read-your-writes session |
| analytics dashboard | snapshot time이 표시된 stale read |
| coordination metadata | linearizable compare-and-set |

한 시스템 안에서도 operation마다 다를 수 있습니다. “우리 DB는 strongly consistent”보다 어떤 API가 어떤 history를 허용하는지 적습니다.

## Transaction consistency와의 관계

linearizability는 주로 개별 object operation의 real-time behavior를 설명합니다. serializability는 여러 object를 포함한 transaction이 어떤 serial execution과 같은지 설명합니다.

`strict serializability`는 serializability와 real-time order를 함께 요구합니다.

다음은 서로 자동으로 따라오지 않습니다.

- 각 key가 linearizable하다고 multi-key transaction이 serializable한 것은 아닙니다.
- transaction이 serializable하다고 transaction 사이 real-time order가 보존되는 것은 아닙니다.
- snapshot isolation은 write skew 같은 anomaly를 허용할 수 있습니다.

관계형 isolation의 상세는 `database-systems`가 소유하며, 이 브랜치는 shard와 replica를 넘는 coordination 경계를 다룹니다.

## Staleness를 수치로 표현합니다

stale read를 허용한다면 관찰 기준을 정합니다.

- version lag: leader commit index와 follower applied index 차이
- time lag: source timestamp와 replica apply time 차이
- bounded staleness: 최대 version 또는 시간 차이
- explicit snapshot: client가 읽는 snapshot ID 또는 timestamp

wall clock lag를 사용할 때 clock uncertainty를 포함합니다.

## Consistency와 availability 선택

partition 중 다음 API 동작을 명시합니다.

```text
write:
- minority에서 거절
- local accept 후 conflict 허용
- queue만 하고 commit하지 않음

read:
- 최신 보장을 위해 거절
- stale 표시와 함께 local value 반환
- session token을 만족하는 replica가 없으면 대기·거절
```

응답 여부만이 아니라 반환 값의 의미를 contract에 포함합니다.

## 실패 조건

- final value가 같으면 consistency가 맞다고 판단합니다.
- linearizability와 serializability를 같은 뜻으로 사용합니다.
- leader write protocol만 보고 follower read를 검증하지 않습니다.
- causal consistency를 timestamp 정렬만으로 구현합니다.
- session token 없이 임의 follower에 read-your-writes를 주장합니다.
- eventual convergence에 conflict·repair·tombstone 계약이 없습니다.
- stale read를 제공하면서 stale 정도와 source version을 숨깁니다.

## 검증

[consistency history 실습](../../exercises/02-replication-and-consistency/01-consistency-history/README.md)은 같은 operation 집합을 서로 다른 invocation·completion order로 제공합니다.

학습자는 각 history에 대해 다음을 제출합니다.

- sequential specification
- real-time constraint
- process order
- 가능한 linearization 또는 불가능한 이유
- causal dependency
- 허용할 consistency model

[linearizable register 예제](../../examples/linearizable-register/README.md)는 작은 read/write register history를 탐색합니다.

## 완료 조건

- consistency model을 허용 history의 집합으로 설명합니다.
- linearizability와 sequential consistency의 real-time 차이를 판정합니다.
- causal dependency와 concurrent update를 구분합니다.
- global consistency와 session guarantee를 분리합니다.
- eventual convergence의 추가 계약을 명시합니다.
- multi-object transaction consistency와 single-object consistency를 혼동하지 않습니다.
