# 멀티코어, 캐시 일관성과 거짓 공유

여러 코어가 같은 물리 메모리를 공유해도 각 코어의 전용 캐시에는 같은 라인의 복사본이 있을 수 있습니다. 한 코어가 값을 쓰면 다른 코어가 오래된 값을 계속 사용하지 않도록 일관성 프로토콜이 소유권과 무효화를 조정합니다. 통신 단위가 변수보다 큰 캐시 라인이기 때문에 서로 다른 변수를 쓰는 스레드도 거짓 공유로 경쟁할 수 있습니다.

## 학습 목표

- MESI stable state의 read·write·invalidation 전이를 추적합니다.
- coherence, consistency와 언어 memory model이 답하는 질문을 구분합니다.

## 선행 개념

cache line, write-back과 ISA memory ordering의 기본 개념을 알아야 합니다.

## 공유 메모리 모델의 층을 나눕니다

다중 스레드 프로그램을 이해하려면 다음 층을 구분해야 합니다.

```text
programming language memory model
→ 컴파일러 변환
→ ISA atomic/fence semantics
→ cache coherence와 interconnect
→ cache/memory controller
```

C/C++의 data race가 있는 program은 hardware cache coherence가 있어도 올바르지 않습니다. 반대로 language atomic을 사용해 correctness가 맞아도 cache line contention으로 느릴 수 있습니다.

## 캐시 일관성은 한 위치의 최신 값을 관리합니다

core 0과 core 1이 같은 line을 read하면 둘 다 copy를 가질 수 있습니다. core 0이 write하려면 다른 copy를 무효화하거나 update해야 합니다.

대표 방식은 다음과 같습니다.

- snooping protocol은 shared bus 또는 broadcast domain에서 transaction을 감시합니다.
- directory protocol은 line sharer와 owner 정보를 directory에 두고 필요한 node에 메시지를 보냅니다.

core 수가 커질수록 모든 request를 broadcast하기 어려워 directory와 계층형 coherence가 중요해질 수 있습니다.

## MESI는 캐시 라인별 네 상태를 사용하는 단순 모델입니다

### Modified

이 cache만 최신 copy를 가지며 memory보다 새 값일 수 있습니다. eviction 또는 다른 core의 read에 write-back이나 data 전달이 필요할 수 있습니다.

### Exclusive

이 cache만 clean copy를 가집니다. write할 때 다른 sharer가 없으므로 bus transaction 없이 Modified로 바꿀 수 있습니다.

### Shared

여러 cache가 clean copy를 가질 수 있습니다. write하려면 다른 Shared copy를 무효화해야 합니다.

### Invalid

사용할 수 없는 entry입니다.

실제 processor는 MESIF, MOESI와 더 많은 transient state를 사용할 수 있습니다. 이 가이드의 simulator는 stable MESI state만 다룹니다.

## 읽기 실패의 상태 전이

core 0이 line을 read하고 다른 cache에 copy가 없으면 다음처럼 Exclusive를 받을 수 있습니다.

```text
core0: I --BusRd--> E
```

core 1이 같은 line을 read하면 core 0은 Shared로 내려가고 core 1도 Shared를 가집니다.

```text
core0: E → S
core1: I → S
```

Modified owner가 있을 때 다른 core가 read하면 owner가 최신 data를 제공하거나 memory에 반영하고 Shared로 내려갈 수 있습니다.

## 쓰기는 독점 소유권을 요구합니다

core 0이 Shared line을 쓰려면 다른 sharer를 invalidate합니다.

```text
core0: S --BusUpgr--> M
core1: S → I
```

Invalid 상태에서 write miss가 나면 read-exclusive transaction으로 data와 ownership을 함께 요청할 수 있습니다.

```text
core0: I --BusRdX--> M
other copies → I
```

Exclusive 상태에서는 다른 sharer가 없으므로 local `E → M` 전이가 가능합니다.

## 거짓 공유는 같은 캐시 라인의 다른 값을 경쟁하게 만듭니다

다음 계수기 배열에서 스레드 0과 스레드 1은 서로 다른 원소만 씁니다.

```c
counters[0] += 1;
counters[1] += 1;
```

두 element가 같은 cache line에 있으면 write할 때마다 line ownership이 core 사이를 오갈 수 있습니다.

```text
core0 writes offset 0  → core1 copy invalid
core1 writes offset 8  → core0 copy invalid
core0 writes offset 0  → core1 copy invalid
```

program의 논리적 공유 단위는 8바이트 counter지만 coherence 단위는 64바이트 line일 수 있습니다. 이를 false sharing이라고 합니다.

```sh
python3 exercises/processor-model/reference/processor-model.py coherence \
  exercises/processor-model/fixtures/traces/coherence-false-sharing.trace \
  --cores 2 --line-size 64
```

`address 0`과 `address 8`이 같은 block으로 계산되고 invalidation이 반복되는지 확인하세요.

## 실제 공유와 거짓 공유를 구분합니다

### 실제 공유

여러 thread가 같은 logical value를 읽고 쓰며 synchronization이 필요합니다.

### 거짓 공유

서로 다른 logical value를 쓰지만 같은 cache line에 배치되어 coherence traffic이 생깁니다.

padding은 false sharing을 줄일 수 있지만 true sharing의 serialization은 없애지 못합니다. lock counter 하나를 line에 따로 놓아도 모든 thread가 같은 lock을 갱신하면 ownership은 계속 이동합니다.

## 여백 추가는 근거가 있을 때만 사용합니다

[false-sharing 예제](../../examples/false-sharing/README.md)는 compact counter와 64바이트 간격 counter를 비교합니다.

```sh
make -C examples/false-sharing benchmark
```

검사는 각 counter가 정확한 횟수만큼 증가했는지만 확인합니다. padded version의 고정 speedup을 요구하지 않습니다.

padding의 비용은 다음과 같습니다.

- memory footprint 증가
- cache와 TLB working set 증가
- structure serialization/ABI 변경
- 더 많은 memory bandwidth

thread별 hot write field가 실제로 같은 line에서 invalidation을 만드는지 profile과 layout으로 확인한 뒤 적용하세요.

## 원자 연산은 캐시 라인 소유권과 연결됩니다

atomic read-modify-write는 read와 write 사이에 다른 core가 끼어들지 못하도록 하나의 operation으로 수행합니다. hardware는 line ownership, reservation 또는 locked operation을 사용해 구현할 수 있습니다.

다음 increment는 일반 load/add/store 세 단계라 race가 생깁니다.

```text
load counter
add 1
store counter
```

atomic increment는 lost update를 막지만 모든 thread가 같은 counter를 갱신하면 line이 병목이 됩니다. correctness와 scalability는 별도 문제입니다.

대안은 다음과 같습니다.

- 스레드별 계수기를 주기적으로 합산
- sharded counter
- batch update
- ownership을 한 thread에 두고 message 전달

최종 정확성, 읽기 freshness와 merge 비용을 함께 설계해야 합니다.

## 잠금 경합은 임계 구역 밖에서도 비용이 생깁니다

lock variable 하나를 acquire하려고 여러 core가 반복 write하면 line이 ping-pong할 수 있습니다. spin lock은 짧은 대기에는 context switch를 피하지만 긴 대기에서는 CPU와 interconnect를 낭비합니다.

잘 설계된 lock은 다음을 고려합니다.

- critical section 길이
- waiter 수
- fairness
- preemption
- NUMA 위치
- backoff 또는 queue lock
- blocking 전환

“mutex는 kernel call이므로 항상 느립니다”라고 단정할 수 없습니다. uncontended fast path가 user space atomic으로 끝나는 구현도 있고 contention에서만 sleep할 수 있습니다.

## 메모리 일관성은 여러 캐시 라인의 순서를 정합니다

coherence가 line A와 line B 각각의 write order를 유지해도 다른 core가 두 line의 write를 같은 순서로 볼지 별도 규칙이 필요합니다.

```text
core0: data = 42; ready = 1
core1: if (ready == 1) use(data)
```

올바른 message passing에는 release/acquire 같은 language-level ordering이 필요할 수 있습니다. [out-of-order 문서](08-superscalar-out-of-order-and-speculation.md)의 store buffer와 fence를 함께 확인하세요.

coherence protocol trace만으로 lock-free algorithm의 correctness를 증명할 수 없습니다.

## 캐시 사이 전송과 메모리 통신량

한 core가 Modified line을 가지고 있을 때 다른 core가 읽으면 최신 data가 owner cache에서 직접 전달될 수 있습니다. implementation에 따라 memory controller와 shared cache가 경로에 참여합니다.

performance counter에서 memory bandwidth가 낮다고 coherence traffic이 없는 것은 아닙니다. cache-to-cache transfer와 invalidation은 별도 interconnect event일 수 있습니다.

processor별 counter를 사용할 때 event definition과 scope를 확인해야 합니다.

## NUMA는 메모리 접근 거리까지 다르게 만듭니다

여러 socket 또는 NUMA node에서는 core와 memory controller의 거리가 다릅니다.

```text
local node memory
remote node memory
```

첫 접근 정책으로 페이지가 어느 노드에 배치되는지, 스레드가 다른 CPU로 이동하는지에 따라 지연 시간과 대역폭이 달라질 수 있습니다. 스레드의 CPU만 고정하고 메모리 배치를 보지 않거나, 반대로 메모리만 고정하고 스레드를 이동시키면 결과를 해석하기 어렵습니다.

NUMA optimization은 다음을 함께 다룹니다.

- 스레드 배치
- page placement
- shard ownership
- remote read/write 비율
- cross-node synchronization

작은 single-socket workload에는 복잡성만 늘릴 수 있으므로 topology와 profile을 먼저 확인하세요.

## 확장성은 직렬 실행 비율과 경합을 함께 봅니다

core 수를 늘릴 때 speedup이 선형이 아닌 이유는 다음이 섞입니다.

- serial section
- load imbalance
- lock/atomic contention
- coherence traffic
- memory bandwidth saturation
- shared cache capacity
- scheduler와 runtime overhead

Amdahl의 법칙은 serial fraction 상한을 보여 주고, coherence·bandwidth 측정은 parallel 부분의 비용 증가를 보여 줍니다.

```text
parallel time(N)
= useful work / N
+ synchronization
+ communication
+ imbalance
```

스레드 수만 늘려 벤치마크 한 점을 보고 확장성을 판단하지 말고 1, 2, 4, 8...개 스레드의 추세선을 그리세요.

## 공유 상태를 줄이는 설계

가장 빠른 coherence transaction은 필요하지 않은 transaction입니다. 다음 구조를 검토할 수 있습니다.

- immutable data 공유
- 스레드·코어별 분할
- single-writer ownership
- message passing
- append-only log 뒤 merge
- read-mostly snapshot

공유를 없애면 merge, latency, memory duplication 또는 consistency model이 달라집니다. “자원을 공유하지 않습니다”는 무료 해결책이 아니라 architecture 선택입니다.

## 거짓 공유를 찾는 절차

1. thread별 hot write address를 찾습니다.
2. object offset과 실제 address를 기록합니다.
3. cache line 크기 기준으로 같은 line인지 계산합니다.
4. thread가 다른 core에서 동시에 실행되는지 확인합니다.
5. coherence/cache-to-cache counter가 있다면 관찰합니다.
6. padding 또는 partition을 한 가지 적용합니다.
7. correctness, memory footprint와 전체 workload를 다시 측정합니다.

struct source만 보고 allocator alignment와 array stride를 확인하지 않으면 실제 line 배치를 틀릴 수 있습니다.

## 직접 구현하기

`skeleton/processor_model/coherence.py`에서 stable MESI state를 구현하세요.

- read miss의 `I→E` 또는 `I→S`
- 다른 reader가 왔을 때 `E/M→S`
- `S→M`의 invalidation
- `I→M`의 read-exclusive
- Modified owner의 write-back count

```sh
cd exercises/processor-model
EXERCISE_IMPL=skeleton python3 -m unittest \
  tests.test_processor_model.CoherenceTests -v
```

transient state와 network timing은 생략되어 있으므로 simulator를 실제 CPU protocol 검증기로 사용하면 안 됩니다.

## 직접 확인할 문제

1. 두 core가 같은 line을 read한 뒤 한 core가 write할 때 MESI state를 순서대로 적어 보세요.
2. `E→M` 전이에 bus transaction이 필요하지 않을 수 있는 이유를 설명해 보세요.
3. false sharing padding이 memory footprint와 TLB miss를 늘릴 수 있는 이유를 적어 보세요.
4. 원자 계수기 하나를 스레드별 계수기로 나눌 때 최신성과 합산 규칙이 어떻게 달라지는지 설명해 보세요.
5. coherence가 올바른데도 release/acquire가 필요한 message-passing 예제를 설명해 보세요.

## 연결 실습

[`processor-model` stage-10](../../exercises/processor-model/README.md)에서 MESI와 false-sharing trace를 구현합니다.

## 완료 기준

- 두 core의 read/write sequence에서 MESI state를 순서대로 적을 수 있습니다.
- true sharing과 false sharing을 cache line 주소로 구분할 수 있습니다.
- `make stage-10 EXERCISE_IMPL=workspace`가 통과합니다.
