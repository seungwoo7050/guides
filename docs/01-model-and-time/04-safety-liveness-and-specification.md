# Safety, liveness와 분산 명세

## 목표

구현 전에 허용되는 state와 history를 명세합니다. “데이터가 일관됩니다”, “항상 사용 가능합니다” 같은 문구를 safety invariant, liveness 조건과 client-visible specification으로 바꿉니다.

## Safety와 liveness

### Safety

나쁜 일이 발생하지 않는 성질입니다. 유한한 trace prefix에서 위반을 발견할 수 있습니다.

예:

- 같은 log index에 서로 다른 committed command가 존재하지 않습니다.
- 한 term에서 한 voter가 서로 다른 candidate 두 명에게 vote하지 않습니다.
- state machine은 같은 committed prefix를 같은 순서로 적용합니다.
- shard epoch가 같은 동안 두 owner가 write를 승인하지 않습니다.
- 완료된 client request가 restart 뒤 다시 적용되지 않습니다.

### Liveness

좋은 일이 결국 발생하는 성질입니다. 유한 실행에서 아직 발생하지 않았다는 사실만으로 위반을 확정하기 어렵습니다.

예:

- 안정적인 majority가 연결되면 leader가 결국 선출됩니다.
- committed log entry가 실행 중인 replica에 결국 적용됩니다.
- partition이 끝나고 anti-entropy가 계속 실행되면 replica가 수렴합니다.
- shard transfer가 필요한 participant와 storage가 정상이라면 결국 완료됩니다.

liveness는 fairness와 시간 가정을 함께 적어야 합니다.

## Sequential specification

replicated object의 의미를 먼저 단일 상태 기계로 정의합니다.

```text
State: Map<Key, Value>

put(key, value):
  state[key] = value
  return OK

get(key):
  return state.get(key)

compare_and_set(key, expected, next):
  if state[key] != expected:
    return MISMATCH
  state[key] = next
  return OK
```

분산 구현의 목표는 network와 replica가 존재해도 client history가 이 specification의 허용 history에 속하도록 만드는 것입니다.

## State invariant

invariant는 모든 reachable state에서 참이어야 합니다.

Raft 예:

```text
Election Safety
한 term에 최대 한 leader만 존재합니다.

Log Matching
두 log가 같은 index와 term의 entry를 가지면 그 index까지 prefix가 같습니다.

Leader Completeness
어떤 term에 commit된 entry는 이후 모든 leader의 log에 존재합니다.

State Machine Safety
어떤 server도 같은 index에 서로 다른 command를 apply하지 않습니다.
```

설명용 이름만 적지 말고 실제 state field에 연결합니다.

```text
forall i, j, index:
  if applied[i][index] and applied[j][index]:
    command(i, index) == command(j, index)
```

## History specification

client-visible consistency는 내부 state가 아니라 invocation과 completion history로 표현하는 편이 좋습니다.

```text
invoke client1 put(x, 1)
complete client1 OK
invoke client2 get(x)
complete client2 1
```

operation이 겹치지 않는 real-time order, process order와 sequential object semantics를 기준으로 legal ordering이 존재하는지 검사합니다.

내부 replica가 잠시 달라도 client history가 specification을 만족할 수 있고, 내부 값이 최종적으로 같아도 이미 반환한 잘못된 read 때문에 history가 위반될 수 있습니다.

## Refinement

구현의 복잡한 state를 abstract specification의 state에 대응시키는 mapping을 둡니다.

예:

```text
implementation state
- logs
- commit index
- applied index
- snapshots
- session table

abstract state
- key-value map
- completed request results
```

refinement 질문:

- 어떤 구현 event가 abstract operation을 완료시킵니까?
- uncommitted log entry는 abstract state에 포함됩니까?
- snapshot은 어떤 log prefix와 같은 abstract state입니까?
- duplicate request response는 새 transition입니까, 이전 결과 재생입니까?

## Linearization point

linearizability를 주장하는 operation은 invocation과 response 사이 어딘가에서 원자적으로 적용된 것처럼 보이는 지점을 가져야 합니다.

분산 시스템에서 code line 하나와 정확히 일치하지 않을 수 있습니다.

- write가 current-term quorum에 복제되어 commit 가능해진 순간
- leader가 read barrier를 통과해 leadership과 commit position을 확인한 순간
- compare-and-set 명령이 replicated state machine에서 적용된 순간

linearization point를 정했다고 proof가 끝나는 것은 아닙니다. 모든 concurrent history에서 그 지점을 일관된 sequential order로 배치할 수 있어야 합니다.

## Safety proof obligation

문서 수준의 proof는 다음 구조를 사용합니다.

1. 초기 state에서 invariant가 참입니다.
2. 각 event handler가 invariant를 보존합니다.
3. crash·restart와 message duplicate도 event 종류에 포함합니다.
4. snapshot·membership 같은 optimization이 기존 invariant를 약화시키지 않습니다.
5. client-visible response가 abstract specification과 대응합니다.

복잡한 protocol은 수학적 proof나 model checking이 필요할 수 있습니다. 이 가이드의 목표는 proof 전체를 대체하는 것이 아니라 구현자가 검증할 obligation을 빠뜨리지 않도록 만드는 것입니다.

## Liveness proof obligation

liveness는 조건부 문장으로 적습니다.

```text
if
- majority가 실행 중이고
- majority 사이 message가 반복적으로 전달되며
- election timer가 계속 만료되고
- storage operation이 완료된다면
then
- 어떤 node가 결국 leader가 되고
- 새 client command가 결국 commit됩니다.
```

안정 기간의 길이, retry가 계속 시도되는지, scheduler fairness와 client routing도 포함합니다.

## Availability와 progress를 분리합니다

- request가 빠르게 거절되는 것은 termination이지만 업무 availability는 아닐 수 있습니다.
- stale read를 반환하면 응답 availability는 높아지지만 consistency가 달라집니다.
- minority가 read-only snapshot을 제공할 수 있어도 최신 write는 받을 수 없을 수 있습니다.

API별로 허용 응답을 적습니다.

## 실패 조건

- safety와 liveness를 “정상 동작”이라는 한 항목으로 묶습니다.
- final state만 검사하고 client-visible history를 보지 않습니다.
- liveness를 무한 retry나 timeout 증가로만 설명합니다.
- implementation state와 abstract state의 대응을 정의하지 않습니다.
- snapshot이나 compaction 뒤 session metadata가 빠져 refinement가 깨집니다.
- “linearizable”이라는 용어를 operation 범위와 read protocol 없이 사용합니다.

## 검증

각 실습에서 다음 세 파일을 작성하는 방식을 권장합니다.

```text
spec.md
- operation과 sequential semantics

invariants.md
- 모든 reachable state에서 참이어야 할 조건

liveness.md
- 진행에 필요한 환경·시간·fairness 조건
```

[linearizability 실습](../../exercises/05-validation/01-linearizability/README.md)은 같은 final value를 가진 여러 history 중 legal history와 위반 history를 구분합니다.

## 완료 조건

- safety와 liveness를 유한 trace 위반 가능성으로 구분합니다.
- sequential specification을 protocol 구현 전에 작성합니다.
- internal invariant와 client-visible history property를 분리합니다.
- refinement mapping과 operation completion 지점을 설명합니다.
- liveness 주장을 환경·시간·fairness 조건과 함께 적습니다.
