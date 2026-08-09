# RTOS task, queue와 priority inversion

RTOS는 thread, scheduler, timer와 synchronization primitive를 제공하지만 application 상태의 정확성을 대신 설계하지 않습니다. task를 기능마다 하나씩 만들고 mutex를 추가하면 초기 동작은 쉬워 보여도 priority inversion, deadlock, unbounded queue와 shutdown failure가 생길 수 있습니다.

## 학습 목표

- task lifecycle, ready/block/running state와 preemption을 설명합니다.
- queue, semaphore, mutex, event와 notification의 의미를 구분합니다.
- priority inversion과 inheritance/ceiling의 조건을 분석합니다.
- ISR-to-task handoff, workqueue와 dedicated task를 비교합니다.
- startup, cancellation, shutdown와 reset path를 설계합니다.

## task 상태

```text
CREATED
→ READY
→ RUNNING
   ├─ preempted → READY
   ├─ wait/receive/sleep → BLOCKED
   └─ exit → TERMINATED
BLOCKED + event/timeout → READY
```

priority가 높아도 blocked task는 실행되지 않습니다. low-priority task가 resource를 쥐고 있으면 high-priority task의 progress에 영향을 줄 수 있습니다.

## primitive의 의미를 섞지 않습니다

### queue

payload와 순서를 전달합니다. capacity와 overflow policy가 필요합니다.

### semaphore

event count 또는 resource count를 전달합니다. payload는 별도 state에 있을 수 있습니다.

### mutex

shared state의 exclusive ownership을 전달합니다. 일반적으로 owner task가 unlock해야 하며 priority inheritance를 제공할 수 있습니다.

### event flags/notification

여러 상태 bit 또는 task-specific signal을 저비용으로 전달할 수 있지만 event count와 payload를 잃을 수 있습니다.

### condition variable와 predicate

wake event 자체보다 protected predicate가 중요합니다. RTOS마다 제공 방식이 다릅니다.

어떤 primitive를 사용할지 “API가 편하다”가 아니라 전달해야 하는 state로 결정합니다.

## priority를 기능 중요도만으로 정하지 않습니다

priority는 다음을 반영합니다.

- deadline과 period
- worst-case execution 또는 budget
- blocking dependency
- interrupt/deferred work 관계
- shared resource와 critical section
- overload behavior

“network task가 중요하므로 최고 priority”처럼 정하면 sensor acquisition이나 watchdog supervisor를 굶길 수 있습니다.

## priority inversion

```text
L: mutex M 획득
H: 실행되어 M 요청 → block
M: 중간 priority task가 계속 실행
L: 실행하지 못해 M 반환 지연
H: 간접적으로 M보다 낮은 progress
```

대응:

- critical section을 짧고 bounded하게 만듭니다.
- priority inheritance를 사용합니다.
- priority ceiling 또는 resource server를 고려합니다.
- high-priority path에서 공유하지 않는 message passing으로 바꿉니다.
- lock 안에서 slow bus·logging·allocation을 수행하지 않습니다.

inheritance는 deadlock과 긴 critical section을 제거하지 않습니다.

## deadlock과 lock ordering

여러 mutex가 있으면 global order를 정합니다.

```text
항상 A → B 순서로 획득
B를 가진 채 A 요청 금지
```

callback이 내부에서 다른 lock을 얻거나 driver가 user callback을 lock 안에서 호출하면 보이지 않는 cycle이 생길 수 있습니다. public API의 callback/lock contract를 문서화합니다.

## ISR에서 task로 넘기기

ISR-safe API만 사용하고 wakeup이 즉시 context switch를 만들 수 있는지 확인합니다.

```text
ISR snapshot
→ queue/send/give
→ higher-priority task ready
→ ISR return
→ scheduler selects task
```

이 경로는 낮은 latency를 제공할 수 있지만 task가 burst를 처리할 capacity와 buffer pool을 가져야 합니다.

## system workqueue와 dedicated task

### shared workqueue

장점:

- task/stack 수 감소
- 짧은 deferred work에 적합

위험:

- 한 긴 work가 다른 work를 막음
- blocking call이 전체 queue를 정지
- priority와 stack budget 공유

### dedicated task

장점:

- 독립 priority·stack·blocking
- state ownership이 명확할 수 있음

비용:

- RAM과 context switch
- task 간 queue/lock 증가
- startup·shutdown 복잡성

work의 blocking·deadline·state ownership을 기준으로 선택합니다.

## one task per feature는 자동 설계가 아닙니다

다음 질문을 먼저 답합니다.

- feature가 독립적으로 block해야 합니까?
- 다른 feature와 어떤 state를 공유합니까?
- task가 없으면 어떤 deadline을 못 지킵니까?
- stack worst case를 감당할 수 있습니까?
- queue capacity와 overload policy는 무엇입니까?
- task failure를 누가 감지하고 복구합니까?

하나의 state owner task가 여러 command를 직렬화하는 편이 여러 task가 mutex로 공유 state를 만지는 것보다 단순할 수 있습니다.

## startup과 dependency readiness

```text
kernel start
→ driver dependency ready
→ storage/config load
→ service task start
→ external communication enable
→ normal operation
```

모든 task를 동시에 생성하고 각자 retry loop로 dependency를 기다리게 하면 boot order와 fault handling이 분산됩니다. supervisor 또는 explicit init phase를 사용합니다.

## cancellation과 shutdown

embedded system도 update, power-off, mode change에서 controlled shutdown이 필요합니다.

- 새 request 수락 중지
- active operation cancel 또는 drain
- queue 처리/폐기 정책
- persistent state commit
- device suspend
- task acknowledgment
- watchdog window와 deadline

강제 task delete는 lock, buffer와 peripheral ownership을 남길 수 있습니다.

## stack과 task-local state

각 task stack은 별도 RAM budget입니다. callback depth, formatting, library call와 interrupt stack 구조를 포함합니다. stack watermark는 관찰된 workload의 근거이며 모든 path의 proof가 아닙니다.

## failure와 검증

- high-priority task CPU hog
- low-priority owner + medium task로 inversion 재현
- lock order 반전
- queue full에서 producer behavior
- workqueue handler가 block
- startup dependency failure
- cancellation과 completion race
- task stack 부족

scheduler trace, thread analyzer, GPIO marker와 event timestamp를 함께 사용합니다.

## 실습 연결

[deadline과 priority 검토](../../exercises/04-deadline-and-priority-review/README.md)에서 task set, resource graph와 queue budget을 작성합니다.

## 직접 확인할 문제

1. binary semaphore와 mutex가 같은 “1/0” 상태처럼 보여도 owner와 priority 의미가 다른 이유를 설명해 보세요.
2. priority inheritance가 deadlock을 해결하지 못하는 trace를 작성해 보세요.
3. system workqueue에서 긴 I2C transfer를 수행하면 어떤 다른 기능이 지연될 수 있습니까?
4. task 강제 삭제가 driver와 buffer ownership을 깨뜨릴 수 있는 이유를 적어 보세요.

## 이 장이 보장하지 않는 것

특정 RTOS API 이름과 scheduler policy는 release마다 다릅니다. hard real-time schedulability와 SMP memory model은 별도 전문 영역입니다.
