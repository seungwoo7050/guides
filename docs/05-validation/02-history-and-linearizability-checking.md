# History와 linearizability 검사

## 목표

client invocation·completion history를 기록하고 sequential specification에 맞는 linearization이 존재하는지 탐색합니다. 최종 값, replica log 또는 성공률만으로 client-visible consistency를 판정하지 않습니다.

## History 형식

operation을 invocation과 completion으로 나눕니다.

```json
{"type":"invoke","process":"c1","op":"write","key":"x","value":1,"time":10}
{"type":"ok","process":"c1","op":"write","key":"x","value":1,"time":20}
{"type":"invoke","process":"c2","op":"read","key":"x","time":25}
{"type":"ok","process":"c2","op":"read","key":"x","value":1,"time":30}
```

기록할 항목:

- operation ID
- client/process ID
- invocation·completion event
- input과 result
- monotonic local time 또는 event sequence
- target node와 routing epoch
- timeout·fail·unknown 구분
- trace correlation ID

## Pending operation

invocation은 있지만 completion이 없는 operation은 pending입니다.

linearizability 검사에서 선택:

- pending operation을 제거합니다.
- 어떤 return value로 완료됐다고 가정해 볼 수 있습니다.
- 내부 commit evidence로 completion candidate를 제한합니다.

response loss가 있는 분산 시스템에서 pending write를 무조건 실패로 처리하면 실제 적용된 state를 잘못 판정할 수 있습니다.

## Real-time order

operation A의 response가 B의 invocation보다 먼저면 A는 B보다 앞에 linearize되어야 합니다.

겹치는 operation은 어느 순서로 배치해도 될 수 있습니다.

```text
A: |------|
B:    |------|
```

A와 B가 겹치면 sequential specification과 다른 operation constraint를 만족하는 순서를 탐색합니다.

## Sequential model

checker는 object의 sequential transition을 알아야 합니다.

register 예:

```text
state = value
write(v) -> state=v, result=OK
read() -> result=state
```

compare-and-set:

```text
cas(expected, next)
- state == expected이면 state=next, OK
- 아니면 state 유지, MISMATCH
```

queue·set·transaction은 서로 다른 model을 가집니다. API semantics를 checker 안에 숨기지 않고 별도 명세로 둡니다.

## Search

작은 history는 backtracking으로 검사할 수 있습니다.

1. 아직 배치하지 않은 operation 중 real-time predecessor가 모두 배치된 후보를 찾습니다.
2. sequential model에 operation을 적용합니다.
3. observed result와 일치하면 다음 operation을 탐색합니다.
4. 일치하지 않으면 backtrack합니다.
5. 모든 operation을 배치하면 legal linearization입니다.

state memoization과 key별 decomposition으로 탐색을 줄일 수 있습니다.

## Counterexample

위반 결과는 “false” 한 줄이 아니라 최소 history와 이유를 제공해야 합니다.

```text
write(x,1) completed
그 뒤 시작한 read(x)가 0 반환
두 operation은 겹치지 않으므로 read를 write 앞에 배치할 수 없음
sequential model에서 write 뒤 read 결과는 1이어야 함
```

가능한 한 관련 없는 client·key·operation을 제거합니다.

## Multi-key와 transaction

key별 linearizability를 각각 통과해도 multi-key invariant가 맞는 것은 아닙니다.

- transaction history는 strict serializability checker가 필요할 수 있습니다.
- cross-key compare-and-set 또는 transfer는 하나의 operation으로 모델링합니다.
- shard-local history만 보면 global cycle을 놓칠 수 있습니다.

검증 대상 consistency model에 맞는 checker를 선택합니다.

## Workload 생성

좋은 history는 protocol의 약한 지점을 자극합니다.

- read/write register
- compare-and-set register
- monotonic counter
- unique allocation
- bank transfer
- set add/remove
- lock·lease acquisition

단순 write 후 긴 sleep 뒤 read만 반복하면 concurrent ordering bug를 찾기 어렵습니다.

## Nemesis와 workload 분리

workload는 client operation을 생성하고, fault controller는 partition·crash·clock·storage fault를 생성합니다.

각 operation과 fault가 같은 virtual or monotonic timeline에 기록되어야 위반과 원인을 연결할 수 있습니다.

## Unknown과 timeout

client timeout은 completion type `fail`과 다릅니다.

- definite reject: operation이 적용되지 않았음이 protocol로 확정
- unknown: response를 받지 못해 적용 여부 불명
- informational error: 다른 leader·route로 retry 가능

checker input에서 unknown operation을 pending으로 보거나 내부 evidence와 함께 completion candidate로 처리합니다.

## Observability gap

history checker가 통과해도 다음이 남을 수 있습니다.

- 검사하지 않은 key·operation
- 짧은 test 기간
- client library가 잘못된 invocation time 기록
- stale node를 workload가 전혀 읽지 않음
- fault가 실제로 적용되지 않음
- checker model이 API semantics와 다름

checker result와 test coverage를 함께 기록합니다.

## 실패 조건

- final database dump가 맞으면 linearizable하다고 봅니다.
- timeout operation을 definite failure로 제거합니다.
- operation ID 없이 invoke와 completion을 잘못 연결합니다.
- wall clock이 뒤로 가는데 timestamp만으로 real-time order를 만듭니다.
- checker sequential model이 실제 API의 conditional update를 빠뜨립니다.
- key별 검사로 multi-key transaction consistency를 주장합니다.
- violation history를 최소화하지 않습니다.

## 실습과 예제

[linearizable register 예제](../../examples/linearizable-register/README.md)는 작은 register checker를 실행합니다.

[history checking 실습](../../exercises/05-validation/01-linearizability/README.md)은 legal·illegal·pending history를 제공합니다.

검사 항목:

- 겹치지 않는 real-time edge를 보존합니다.
- observed result가 sequential state transition과 일치합니다.
- pending write의 가능한 completion을 다룹니다.
- 최소 counterexample을 설명합니다.

## 완료 조건

- invocation과 completion을 분리해 history를 기록합니다.
- pending·unknown operation을 definite failure와 구분합니다.
- sequential specification과 real-time constraint로 linearization을 탐색합니다.
- multi-key consistency와 single-key linearizability를 구분합니다.
- checker 결과의 workload·fault·관측 한계를 기록합니다.
