# 결정적 시뮬레이션

## 목표

실제 thread·socket·wall clock의 비결정성을 virtual event scheduler로 바꿔 같은 장애 실행을 반복하고 최소화합니다. random fault test를 “가끔 실패하는 장시간 테스트”가 아니라 seed·schedule·state hash를 가진 재현 가능한 근거로 만듭니다.

## 왜 일반 통합 테스트만으로 부족합니까?

분산 bug는 매우 짧은 ordering 차이에 의존할 수 있습니다.

```text
AppendEntries ack
leader crash
client retry
new election
old response delivery
```

실제 network와 thread로 이 순서를 만들면 다음 문제가 생깁니다.

- 재현이 어렵습니다.
- 실패를 기다리느라 느립니다.
- 같은 test가 환경에 따라 다르게 동작합니다.
- 위반을 만든 정확한 event를 찾기 어렵습니다.
- sleep을 늘리면 bug가 사라지거나 test가 불안정해집니다.

결정적 simulator는 모든 external nondeterminism을 event 선택으로 이동합니다.

## Simulator state

```text
Simulation {
  virtual_time
  nodes
  durable_stores
  messages_in_flight
  timers
  clients
  faults
  random_seed
  event_log
}
```

한 step은 enabled event 중 하나를 선택해 적용합니다.

```text
deliver(message_id)
drop(message_id)
duplicate(message_id)
fire(timer_id)
crash(node_id)
restart(node_id)
partition(link)
heal(link)
complete_disk(op_id)
client_invoke(request)
```

protocol core는 실제 sleep·socket·random을 사용하지 않고 simulator가 event로 전달한 값만 사용합니다.

## Virtual time

virtual time은 다음 timer까지 즉시 이동할 수 있습니다.

```text
advance_to(next_timer.deadline)
```

장점:

- 수 시간의 expiry·retry를 즉시 실행합니다.
- 같은 deadline의 tie-break를 결정적으로 정합니다.
- process pause와 clock jump를 별도 event로 모델링합니다.

주의:

- virtual time이 physical clock 오차를 자동 모델링하지 않습니다.
- node별 monotonic clock과 wall clock이 다르면 별도 state를 둡니다.
- CPU starvation이나 long handler는 execution delay event로 표현합니다.

## Seeded random schedule

상태에서 가능한 event 중 seeded PRNG로 하나를 선택할 수 있습니다.

기록:

```text
seed
initial configuration
software version
step count
selected event IDs
invariant results
final state hash
```

seed만 기록하는 것으로 충분하지 않을 수 있습니다. code change로 enabled event 집합과 PRNG 호출 수가 바뀌면 같은 seed가 다른 schedule을 만듭니다. 따라서 실패 schedule의 explicit event list도 함께 저장합니다.

## Exhaustive exploration

작은 model은 모든 event order를 탐색할 수 있습니다.

state explosion을 줄이는 방법:

- node·message·key 수 제한
- symmetry reduction
- equivalent state hash deduplication
- bounded step 수
- partial-order reduction
- 불필요한 payload 추상화

capstone의 unit model은 node 3개, key 1~2개, outstanding request 1~2개로 시작합니다.

## Fault injection

fault는 “node를 죽입니다”라는 하나의 action이 아닙니다.

### Network

- 특정 message drop
- 방향성 partition
- message duplication
- reorder
- delay spike
- stale message delivery

### Node

- handler 전·후 crash
- timer pause
- restart with durable state
- process incarnation 변경

### Storage

- append 전·후 crash
- flush delay
- read error
- checksum mismatch
- snapshot install interruption

### Client

- response loss
- retry to another node
- duplicate request
- client pause·restart

fault는 protocol이 지원한다고 주장하는 model 안에서 먼저 사용합니다. Byzantine corruption을 crash-only protocol의 일반 검증에 섞고 “실패했다”고 평가하지 않습니다.

## Invariant checking

각 step 뒤 값싼 invariant를 실행합니다.

```text
- one leader per term
- commit index monotonic
- applied index <= commit index
- same index applied command equal
- durable vote at most one per term
- one shard write authority per epoch
```

비싼 history 검사와 full state comparison은 일정 간격이나 run 종료 뒤 수행할 수 있습니다.

invariant failure에는 첫 위반 step과 이전 state를 보존합니다.

## Trace shrinking

실패 schedule이 수천 step이면 이해하기 어렵습니다. 다음 방식으로 줄입니다.

- event chunk 제거
- fault 수 감소
- node·client·key 제거
- delay 값을 줄임
- duplicate 횟수 감소
- 동일 state에 도달하는 prefix 축약

줄인 trace가 같은 invariant를 같은 의미로 위반하는지 확인합니다. 단순히 최종 error 문자열이 같은지만 보지 않습니다.

## Simulator와 production 차이

simulation은 model에 넣은 failure만 찾습니다.

빠지기 쉬운 것:

- kernel·filesystem 실제 durability
- memory model과 data race
- serialization bug
- packet fragmentation·MTU
- resource exhaustion
- clock implementation 차이
- operator·upgrade behavior

따라서 simulation을 실제 integration, fuzzing, crash test와 결합합니다.

## Reproducibility contract

실패 artifact 예:

```text
artifacts/failures/raft-commit-current-term/
├── metadata.json
├── schedule.json
├── initial-state.json
├── trace.jsonl
├── final-state.json
└── invariant.txt
```

source commit과 simulator version도 포함합니다.

## 실패 조건

- test에서 real sleep으로 election order를 만듭니다.
- random seed만 남기고 실제 event schedule을 보존하지 않습니다.
- fault를 run 시작 전에만 넣고 state transition 사이 crash를 검사하지 않습니다.
- final value만 검사하고 매 step invariant를 보지 않습니다.
- simulator에 없는 failure까지 지원한다고 주장합니다.
- 긴 실패 trace를 최소화하지 않고 flaky test로 남깁니다.
- virtual time과 node local clock을 같은 값으로 고정합니다.

## 실습

[deterministic network 예제](../../examples/deterministic-network/README.md)는 message delay·drop·duplicate와 virtual timer를 같은 schedule로 재현합니다.

[simulation plan 실습](../../exercises/05-validation/02-simulation-plan/README.md)은 capstone의 event type, fault matrix, invariant와 artifact format을 설계합니다.

## 완료 조건

- protocol core에서 network·clock·disk 비결정성을 분리합니다.
- seed와 explicit schedule을 함께 저장합니다.
- every-step invariant와 end-of-run history 검사를 구분합니다.
- crash point를 state update 사이에 배치합니다.
- 실패 trace를 최소화하고 source version과 함께 보존합니다.
- simulation의 model gap을 실제 integration test로 보완합니다.
