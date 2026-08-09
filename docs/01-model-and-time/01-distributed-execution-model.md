# 분산 실행 모델과 관찰 경계

## 목표

분산 시스템을 “여러 프로세스가 RPC를 호출하는 프로그램”이 아니라 **독립된 상태 기계와 지연 가능한 메시지로 이루어진 실행**으로 표현합니다. 알고리즘을 설명하기 전에 node, message, timer, disk와 client가 어떤 event를 만들 수 있는지 고정합니다.

## 문제

단일 프로세스에서는 함수 호출 전후의 상태를 하나의 debugger와 메모리에서 볼 수 있습니다. 분산 실행에서는 다음이 동시에 일어날 수 있습니다.

```text
node A는 write를 local log에 기록했습니다.
node B는 아직 그 entry를 받지 못했습니다.
client는 응답을 잃어 결과를 모릅니다.
monitor는 A의 마지막 heartbeat가 늦었다고 관찰합니다.
A는 실제로 실행 중이지만 network path가 끊겼습니다.
```

이 상태를 “A가 성공했다”, “B가 stale하다”, “A가 죽었다” 같은 한 문장으로 먼저 요약하면 알고리즘의 보장 범위를 잃습니다. 각 관찰과 실제 상태를 분리해야 합니다.

## 시스템 모델

### Node

node는 local state와 event handler를 가진 결정적 상태 기계로 모델링합니다.

```text
next(local_state, event) -> new_local_state, emitted_effects
```

`event`는 다음 중 하나일 수 있습니다.

- client request
- 다른 node가 보낸 message 수신
- timer 만료
- disk read·write 완료
- crash
- restart
- operator가 적용한 membership·configuration 변경

같은 local state와 같은 event가 항상 같은 결과를 만들도록 핵심 protocol을 작성하면, network와 schedule의 비결정성을 외부 simulator가 통제할 수 있습니다.

### Message

message는 전송 시점과 수신 시점이 분리된 값입니다.

```text
Message {
  id
  sender
  receiver
  kind
  payload
  logical metadata
}
```

모델이 허용하는 network action을 명시합니다.

- 지연
- 재정렬
- 중복
- 유실
- 한 방향만 차단되는 partition
- node별로 다른 지연

TCP를 사용한다고 protocol message가 정확히 한 번 처리되는 것은 아닙니다. TCP 연결이 끊기고 다시 연결되면 application retry가 같은 명령을 다시 보낼 수 있습니다. 이 가이드에서는 packet 수준의 손실 복구보다 protocol message가 node state에 미치는 효과를 다룹니다.

### Timer와 시간

real timer는 event를 생성하는 한 방법입니다. timer 만료는 다른 node의 실제 crash를 증명하지 않습니다.

```text
관찰: election timeout 동안 heartbeat를 받지 못했습니다.
가능한 실제 상태:
- leader crash
- message delay
- partition
- follower pause
- local clock 또는 scheduler 지연
```

결정적 실습에서는 wall clock 대신 virtual time과 명시적인 `advance_time` event를 사용합니다.

### Stable storage

crash-recovery 모델에서는 volatile state와 durable state를 구분합니다.

```text
volatile
- in-memory role
- pending RPC
- next retry time

durable
- term
- vote
- replicated log
- snapshot과 session metadata
```

“disk에 썼다”도 하나의 원자 event라고 가정할지, write와 flush를 분리할지 명시해야 합니다. capstone은 처음에는 durable update를 원자 event로 모델링하고, 선택 확장에서 torn write와 partial persistence를 다룹니다.

### Client

client도 protocol의 일부입니다. 다음 상태를 가질 수 있습니다.

- request ID와 session ID
- 아직 응답을 받지 못한 명령
- retry 대상 node
- 관찰한 leader hint
- operation invocation·completion time

client retry를 모델에서 빼면 duplicate apply와 failover 뒤 결과 조회 문제를 검증할 수 없습니다.

## Global state와 실행 trace

한 시점의 model state는 다음을 포함합니다.

```text
GlobalState {
  nodes: node_id -> LocalState
  messages_in_flight
  timers
  disks
  clients
  configuration
  virtual_time
}
```

실행은 global state 사이의 전이입니다.

```text
S0 --deliver(m1)--> S1
S1 --crash(n2)--> S2
S2 --advance_time(50)--> S3
S3 --restart(n2)--> S4
```

중요한 것은 최종 상태만 아니라 **어떤 event sequence가 그 상태를 만들었는가**입니다. 동일한 최종 key-value map이라도 두 leader가 같은 term에서 서로 다른 값을 commit한 실행은 safety 위반일 수 있습니다.

## 실제 상태와 관찰 상태

분산 시스템에서 node가 아는 것은 관찰 가능한 local evidence뿐입니다.

| 실제 상태 | 관찰 가능한 증거 | 바로 결론 내릴 수 없는 것 |
|---|---|---|
| peer가 느림 | 응답 지연 | crash 여부 |
| 연결 단절 | send 실패·timeout | peer local state |
| 오래된 read | version·term·index | 최신 값의 위치 |
| client timeout | completion 없음 | 명령 적용 여부 |
| heartbeat 없음 | deadline 초과 | 기존 leader 권한의 즉시 소멸 |

알고리즘은 알 수 없는 실제 상태를 추측하는 대신, 충분한 evidence가 생길 때만 state transition을 허용해야 합니다.

## 비결정성을 외부로 이동합니다

protocol code가 직접 random sleep, 현재 시각, OS thread schedule과 network socket에 의존하면 같은 실패를 반복하기 어렵습니다. 다음 경계를 둡니다.

```text
protocol core
- current state와 event만 사용
- 새 state와 effect를 반환

runtime adapter
- 실제 socket·clock·disk를 effect와 event로 변환

simulator
- effect의 전달·지연·유실·중복·crash 순서를 결정
```

이 구조는 production runtime과 simulator가 같은 protocol core를 사용할 수 있게 합니다. 완전히 같은 코드를 공유하지 못하더라도 최소한 state schema와 transition contract는 같아야 합니다.

## 실패 조건

다음 설계는 실행 모델을 숨깁니다.

- timeout을 crash detector의 확정 판정으로 표현합니다.
- network send가 성공하면 receiver가 처리했다고 봅니다.
- node restart 뒤 in-memory state가 그대로 남는다고 가정합니다.
- client를 외부 입력 생성기로만 보고 retry state를 기록하지 않습니다.
- 최종 값만 비교하고 message·term·commit history를 보존하지 않습니다.
- production code 안에서 random과 wall clock을 직접 읽어 schedule 재현을 막습니다.
- “network partition”을 모든 방향과 모든 node에 동일한 하나의 boolean으로만 표현합니다.

## 검증

실행 모델의 첫 검사는 알고리즘 정답이 아니라 **event 재현성**입니다.

```text
seed와 초기 상태를 고정합니다.
→ 같은 fault schedule을 두 번 실행합니다.
→ event ID, state hash와 output이 같습니다.
→ 한 event를 제거해도 위반이 재현되는지 확인합니다.
```

trace에는 최소한 다음을 남깁니다.

- event sequence 번호
- virtual time
- node role·term·commit index
- delivered·dropped message ID
- crash·restart와 durable state hash
- client invocation·completion
- invariant 결과

## 실습

[causality trace 실습](../../exercises/01-model-and-time/01-causality-trace/README.md)은 세 process가 만든 local·send·receive event를 process order, message와 causal edge로 다시 구성합니다.

[deterministic network 예제](../../examples/deterministic-network/README.md)는 동일한 schedule이 같은 trace를 만드는지 확인합니다.

## 완료 조건

- node, message, timer, disk와 client를 독립 state로 표현할 수 있습니다.
- timeout 관찰과 peer crash 사실을 구분합니다.
- volatile state와 durable state를 분리합니다.
- 실행을 최종 값이 아니라 event trace와 global state 전이로 기록합니다.
- protocol core의 비결정성을 외부 simulator로 이동할 수 있습니다.
