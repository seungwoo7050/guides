# memory budget, stack과 allocation

MCU의 memory는 작을 뿐 아니라 종류와 수명이 다릅니다. flash, SRAM, retention RAM, tightly coupled memory, external memory와 DMA-capable region은 같은 byte처럼 사용할 수 없습니다. build가 통과했다는 사실은 runtime peak와 fragmentation, stack collision과 update margin을 보장하지 않습니다.

## 학습 목표

- flash와 RAM 사용량을 static, dynamic, stack, pool과 reserved region으로 나눕니다.
- static allocation, heap, slab/pool과 region allocator의 trade-off를 설명합니다.
- task/interrupt stack budget과 overflow evidence를 설계합니다.
- OOM과 buffer exhaustion을 product state로 처리합니다.
- memory attribute와 DMA·retention 요구를 allocation contract에 포함합니다.

## memory inventory

```text
nonvolatile
- bootloader
- primary/secondary image
- constant data
- settings/log/filesystem
- factory/provisioning data

volatile
- .data/.bss
- .noinit/retention
- main/ISR/task stacks
- heap
- pools/slabs
- driver/DMA/network buffers
- trace/crash records
```

각 region에 다음을 기록합니다.

- address와 size
- read/write/execute
- cacheability
- DMA 접근 가능 여부
- retention/power domain
- alignment
- erase/write 특성
- owner와 lifetime

## static allocation

장점:

- link 또는 boot 시 capacity가 고정됩니다.
- fragmentation이 없습니다.
- ownership과 lifetime이 단순합니다.

비용:

- peak가 동시에 발생하지 않아도 합산 RAM을 예약합니다.
- feature configuration별 낭비가 생길 수 있습니다.
- 동적 workload에 유연하지 않습니다.

static이 항상 안전한 것은 아닙니다. 배열 index와 queue overflow policy가 필요합니다.

## general heap의 위험과 사용 조건

위험:

- fragmentation
- allocation time 변동
- failure가 runtime에 발생
- ownership 누락과 double free
- ISR/critical path에서 사용
- memory corruption이 allocator metadata에 확산

사용할 수 있는 조건:

- boot/init phase에서만 allocate하고 이후 free하지 않음
- noncritical task에서 bounded request
- OOM policy와 metrics 존재
- allocator implementation과 synchronization cost를 이해
- stress와 long-run fragmentation 시험

“동적 할당 금지”도 하나의 policy입니다. 요구와 evidence 없이 교리처럼 사용하지 않습니다.

## pool/slab은 object class와 capacity를 고정합니다

```text
N개의 고정 크기 buffer
FREE → ALLOCATED → IN_FLIGHT → FREE
```

장점:

- allocation cost와 capacity를 제한하기 쉽습니다.
- fragmentation을 줄입니다.
- buffer ownership을 상태로 표현할 수 있습니다.

주의:

- wrong-size object 낭비
- leak가 capacity exhaustion으로 나타남
- ABA/generation 문제
- ISR-safe free list와 ordering
- DMA alignment·cache attribute

pool exhaustion을 무한 wait로 숨기지 않고 drop/reject/backpressure/escalation policy를 정합니다.

## stack budget

각 task의 worst path를 조사합니다.

- call depth
- local arrays/struct
- format/crypto/library temporary
- exception/FPU context
- nested interrupt
- compiler optimization과 inlining
- architecture ABI alignment

방법:

- compiler stack-usage report
- static call graph
- stack fill/watermark
- guard region/MPU
- fault handler의 stack evidence
- stress input와 interrupt load

watermark가 50% 남았다는 한 번의 결과는 unseen path를 보장하지 않습니다. margin과 검사 범위를 함께 기록합니다.

## interrupt stack을 빠뜨리지 않습니다

RTOS에 따라 interrupt가 interrupted task stack을 사용하거나 전용 interrupt stack을 사용할 수 있습니다. nested interrupt와 fault handler가 같은 stack에 추가될 수 있습니다. task별 watermark만 보면 interrupt peak를 놓칠 수 있습니다.

## buffer 크기는 protocol과 backpressure에서 나옵니다

```text
queue depth
= burst size
+ service latency 동안 도착량
+ safety margin
```

무작정 큰 buffer를 만들지 않습니다. 다음을 정합니다.

- maximum frame/record 크기
- burst와 steady-state rate
- producer/consumer worst service time
- drop/coalesce/retry policy
- memory ownership duration
- copy count

zero-copy는 copy를 줄이지만 ownership duration과 pool pressure를 늘릴 수 있습니다.

## memory corruption을 fail-fast하게 만듭니다

- stack canary/guard
- MPU region
- heap hardening
- bounds-checking wrapper
- poisoned freed buffer
- red zone/pattern
- assertion과 fault record
- host sanitizer 경로

production에서 모든 check를 끄는 대신 cost와 recovery policy를 기준으로 선택합니다.

## image와 runtime margin

release gate 예:

```text
primary image <= slot 80%
static RAM <= physical RAM - reserved - stack/heap margin
모든 task stack 관찰 peak + 정해진 margin
buffer pool exhaustion test 통과
update metadata와 future migration 여유
```

숫자는 제품과 project가 정해야 합니다. 이 가이드는 특정 비율을 보편적 기준으로 강제하지 않습니다.

## OOM과 exhaustion은 상태 전이입니다

가능한 정책:

- request reject with explicit error
- low-value telemetry drop
- producer backpressure
- cached object eviction
- degraded mode
- service restart
- safe reset

critical control buffer와 best-effort log buffer를 같은 pool에서 경쟁시키지 않을 수 있습니다.

## memory leak의 embedded 형태

process가 종료되지 않으므로 작은 leak도 장기적으로 capacity를 소진합니다. heap byte뿐 아니라 다음도 leak될 수 있습니다.

- DMA channel
- message object
- queue slot
- reference count
- driver request
- timer/work item
- file/flash handle

long-run test와 generation/accounting metric을 사용합니다.

## failure와 검증

- maximum concurrent requests
- queue/pool full
- repeated timeout/cancel
- reset/reinit 반복
- task stack worst input
- nested interrupt load
- update 직전 largest image
- logging enabled/disabled
- long-run allocation/free pattern

## 실습 연결

[deadline과 priority 검토](../../exercises/04-deadline-and-priority-review/README.md)에 task stack, queue, pool과 overload policy를 포함합니다. [현장 센서 노드 capstone](../../capstone/field-sensor-node/README.md)은 memory budget 표를 필수 artifact로 요구합니다.

## 직접 확인할 문제

1. `.data` object가 flash와 RAM을 모두 소비하는 이유를 설명해 보세요.
2. fixed pool이 fragmentation을 줄여도 exhaustion을 제거하지 않는 이유를 적어 보세요.
3. task stack watermark만으로 전체 interrupt stack 안전을 판단할 수 없는 경우를 설명해 보세요.
4. zero-copy가 오히려 buffer pool pressure를 높이는 trace를 작성해 보세요.

## 이 장이 보장하지 않는 것

특정 allocator의 worst-case time, stack analyzer 정확성, external memory timing과 ECC behavior는 target/tool 문서를 확인합니다.
