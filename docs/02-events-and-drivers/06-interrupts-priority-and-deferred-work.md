# interrupt, priority와 deferred work

Interrupt Service Routine(ISR)은 hardware event에 빠르게 반응하지만 일반 thread와 같은 실행 환경이 아닙니다. ISR에서 모든 일을 끝내려 하면 latency와 nesting이 커지고, 너무 적게 처리하면 event를 잃거나 interrupt storm이 생깁니다. 핵심은 **hardware state를 안정화하는 최소 작업**과 **나중에 수행할 정책 작업**을 분리하는 것입니다.

## 학습 목표

- interrupt pending, active, enable, mask와 priority 상태를 구분합니다.
- ISR의 최소 책임과 deferred work 경계를 설계합니다.
- event coalescing, queue overflow, lost wakeup와 late completion을 처리합니다.
- interrupt latency와 response time을 측정 가능한 구간으로 나눕니다.

## interrupt path

```text
hardware condition
→ peripheral status/flag
→ interrupt controller pending
→ priority·mask 판단
→ CPU exception entry
→ ISR
→ flag acknowledge/clear
→ event snapshot·enqueue
→ exception return
→ worker/task/application policy
```

각 단계가 지연되거나 상태를 잃을 수 있습니다.

## pending, active와 enabled를 구분합니다

- peripheral flag가 set돼도 controller line이 disabled면 CPU가 ISR에 들어오지 않습니다.
- controller pending을 clear해도 peripheral condition이 남으면 즉시 다시 pending될 수 있습니다.
- ISR이 active인 동안 같은 interrupt가 재진입 가능한지는 controller와 priority 설정에 따라 다릅니다.
- global mask와 per-line mask는 다릅니다.

“interrupt를 clear했다”는 표현은 어느 층의 어떤 bit를 clear했는지 적어야 합니다.

## ISR의 최소 책임

일반적인 ISR은 다음만 수행합니다.

1. source와 status를 snapshot합니다.
2. hardware가 요구하는 순서로 acknowledge/clear합니다.
3. data loss를 막기 위해 FIFO 또는 capture register를 제한적으로 비웁니다.
4. bounded event 또는 buffer reference를 queue에 넣습니다.
5. 필요한 worker를 깨웁니다.
6. 빠르게 반환합니다.

ISR에서 피해야 할 작업:

- unbounded loop
- blocking mutex/semaphore wait
- 일반 heap allocation
- 긴 formatting과 logging
- 느린 bus transaction
- 파일·network·복잡한 protocol 처리
- failure가 끝나지 않는 retry

RTOS가 일부 ISR-safe API를 제공하더라도 context와 worst-case cost를 확인합니다.

## flag clear 순서는 event loss를 결정합니다

대표적인 두 패턴:

```text
snapshot status
→ clear observed flags
→ process snapshot
```

또는 hardware가 요구하면:

```text
read data register
→ status automatically clears
```

clear를 먼저 하고 data를 나중에 읽으면 새로운 event와 이전 event를 구분하지 못할 수 있습니다. 반대로 clear를 늦추면 interrupt가 계속 assertion돼 storm이 생길 수 있습니다. datasheet의 sequence와 errata를 확인합니다.

## deferred work는 state transfer입니다

ISR에서 worker로 넘기는 것은 “함수 호출을 나중에 한다”가 아니라 state와 ownership을 이동하는 일입니다.

```text
ISR owns hardware snapshot
→ queue push 성공
→ worker owns event
→ processing 완료
→ buffer 또는 slot 반환
```

queue push가 실패하면 선택해야 합니다.

- newest event drop
- oldest event drop
- coalesce/count only
- overwrite latest state
- hardware flow control
- fault escalation

어떤 정책도 자동으로 안전하지 않습니다. 제품 의미에 맞게 loss semantics를 정합니다.

## edge event와 level state를 구분합니다

- “button edge 3회”처럼 모든 event 개수가 중요할 수 있습니다.
- “현재 temperature threshold 초과”처럼 최신 level만 중요할 수 있습니다.
- “UART RX byte”는 FIFO capacity까지 sequence가 중요합니다.

level state를 매 event queue에 넣으면 불필요하게 폭주할 수 있고, edge count를 단일 boolean으로 coalesce하면 사건을 잃습니다.

## priority는 숫자가 아니라 선점 관계입니다

architecture와 RTOS마다 높은 우선순위를 작은 숫자로 표현할 수도 있습니다. 숫자 자체보다 다음을 기록합니다.

- 누가 누구를 preempt합니까?
- 같은 priority에서 순서는 무엇입니까?
- ISR이 kernel API를 호출할 수 있는 priority 범위는 어디입니까?
- critical section이 어떤 interrupt까지 mask합니까?
- nested interrupt가 stack에 추가하는 worst-case frame은 얼마입니까?

## latency를 구간으로 나눕니다

```text
hardware event time
→ interrupt request asserted       device latency
→ ISR first instruction            interrupt latency
→ event snapshot complete          ISR service time
→ worker scheduled                 scheduling latency
→ application action complete      end-to-end response time
```

GPIO pulse, cycle counter, trace와 logic analyzer를 이용해 구간을 측정할 수 있습니다. 한 구간의 평균을 전체 worst-case response로 사용하지 않습니다.

## shared state와 memory visibility

ISR과 foreground가 같은 object를 사용할 때 `volatile`만으로 compound operation과 ordering이 안전해지지 않습니다.

대안:

- single-producer/single-consumer ring의 명확한 index protocol
- RTOS ISR-safe queue
- architecture atomic operation
- 짧은 interrupt mask
- immutable buffer descriptor와 ownership handoff

producer가 payload를 쓰기 전에 ready flag를 공개하거나 consumer가 반환하기 전에 DMA가 다시 사용하면 corruption이 생깁니다.

## timeout과 late interrupt

```text
request A 시작
→ timeout
→ driver가 A를 실패로 반환
→ request B가 같은 hardware/buffer 시작
→ A의 늦은 completion interrupt 도착
```

request generation 또는 identity가 없으면 A completion을 B 결과로 오인할 수 있습니다. timeout은 hardware operation을 자동으로 중단하지 않습니다. abort, drain, generation increment와 stale completion discard가 필요할 수 있습니다.

## interrupt storm와 recovery

원인:

- source flag를 clear하지 못함
- level condition이 계속 active
- floating input 또는 bounce
- error flag 반복
- driver가 dependency를 reset하지 않음

대응:

1. source를 snapshot합니다.
2. line 또는 source를 제한적으로 mask합니다.
3. event count와 first/last time을 기록합니다.
4. worker에서 root cause를 처리합니다.
5. 안전한 조건에서 unmask합니다.
6. 반복되면 degraded mode 또는 reset으로 escalate합니다.

ISR 안에서 무한히 log하지 않습니다.

## 실습 연결

[interrupt event 경로](../../exercises/02-interrupt-event-path/README.md)는 다음을 설계합니다.

- W1C status snapshot
- capacity가 제한된 queue
- overflow policy
- worker wakeup
- timeout 뒤 stale completion
- latency measurement point

작은 host model은 [`examples/interrupt-event-model`](../../examples/interrupt-event-model/README.md)에서 실행합니다.

## 직접 확인할 문제

1. level-triggered interrupt에서 controller pending만 clear하면 왜 바로 재진입할 수 있습니까?
2. ISR queue가 full일 때 sensor alarm과 UART byte에 같은 drop policy를 사용하면 안 되는 이유를 설명해 보세요.
3. timeout 뒤 late completion이 새 request를 완료시킬 수 있는 trace를 작성해 보세요.
4. ISR execution time과 end-to-end response time의 차이를 측정 지점으로 표현해 보세요.

## 이 장이 보장하지 않는 것

정확한 exception entry cost, priority bit 수, tail chaining, interrupt mask instruction과 memory barrier는 architecture·RTOS 문서를 확인합니다.
