# 실습 4 — deadline과 priority 검토

## 문제

평균 실행 시간이 짧다는 이유로 deadline을 보장할 수 없습니다. interrupt masking, 높은 priority의 실행, lock blocking, queue 대기, cache/flash stall와 같은 최악 조건을 함께 계산하고 실제 trace와 비교해야 합니다. 이 실습에서는 작은 RTOS workload의 **응답 시간·blocking·jitter budget**을 설계 검토합니다.

## workload

다음 기본 workload를 사용하거나 실제 프로젝트의 축소판을 만듭니다.

| 작업 | trigger | period/min gap | deadline | 자원 |
|---|---|---:|---:|---|
| sensor task | timer/data-ready | 10 ms | 4 ms | I2C mutex |
| communication task | event | 20 ms min | 15 ms | buffer pool, SPI |
| storage task | batch | 100 ms | 80 ms | flash mutex |
| supervisor | periodic | 50 ms | 10 ms | heartbeat table |
| logging | background | aperiodic | best effort | ring/transport |

숫자는 출발점일 뿐입니다. 선택한 target의 측정과 요구사항으로 바꿉니다.

## 학습 목표

- period, deadline, execution time, response time와 jitter를 구분합니다.
- interrupt와 critical section의 blocking을 budget에 포함합니다.
- fixed-priority scheduling의 interference를 설명합니다.
- priority inversion과 inheritance/ceiling의 적용 조건을 검토합니다.
- 분석값과 measured trace의 차이를 근거로 설명합니다.

## 입력 표

각 task/ISR에 다음을 기록합니다.

```text
activation condition
priority
minimum inter-arrival/period
relative deadline
WCET estimate source
shared resource와 max critical section
queue capacity와 overflow policy
stack budget
```

WCET를 한 번 실행한 최대값으로 단정하지 않습니다. 초기에는 보수적 estimate와 불확실성을 표시합니다.

## 응답 경로를 분해합니다

예: sensor event

```text
hardware event
+ interrupt latency
+ ISR execution
+ queue handoff
+ ready queue interference
+ shared bus blocking
+ driver transaction
+ processing
= end-to-end response
```

각 항목의 owner와 관찰 방법을 적습니다.

## priority inversion trace

최소 다음 trace를 작성합니다.

```text
low-priority storage가 mutex 획득
→ high-priority sensor가 mutex에서 block
→ medium-priority communication이 low를 preempt
→ high의 blocking 연장
```

- inheritance가 있을 때/없을 때
- lock hold 안에서 blocking I/O가 있을 때
- timeout/cancel 시 owner cleanup
- interrupt가 같은 resource를 접근할 때

를 비교합니다.

## 계산

정교한 formal schedulability 분석을 요구하지 않지만, 각 high/medium priority task에 대해 다음을 반복합니다.

```text
R_i = C_i + B_i + higher-priority interference during R_i
```

- `C_i`: 해당 task의 실행 비용
- `B_i`: 낮은 priority resource blocking의 상한
- interference: 더 높은 priority task/ISR가 response window 안에 실행되는 비용

iteration과 가정, 단위를 표에 남깁니다. sporadic task는 minimum inter-arrival를 사용합니다.

이 디렉터리에는 실행 가능한 `starter/`, 비교 기준인 `reference/`와 세
종류의 결정론적 fixture가 있습니다. response-time fixture는 blocking과 ISR
interference를 포함하고, queue fixture는 유한 capacity의 drop과 deadline
miss를 남기며, priority-inversion fixture는 inheritance 유무의 per-tick
reference trace를 비교합니다.

```sh
python3 exercises/04-deadline-and-priority-review/check.py \
  --submission exercises/04-deadline-and-priority-review/reference
python3 exercises/04-deadline-and-priority-review/check.py \
  --submission exercises/04-deadline-and-priority-review/starter --json
```

checker는 통과 시 `0`, 공개 계산·trace 계약 위반 시 `1`, submission 경로나
checker 입력을 읽을 수 없으면 `2`를 반환합니다. `starter/analysis.py`를
학습자 workspace로 복사해 함수의 공개 반환 모양을 유지하며 완성합니다.

## failure scenario

- communication burst
- storage erase의 긴 critical section
- interrupt storm
- logging transport block
- tick/clock frequency change
- task overrun
- queue full
- priority 잘못 설정
- mutex inheritance 미지원

각 scenario에서 어떤 deadline이 먼저 깨지고 어떤 counter/trace가 이를 보여야 하는지 적습니다.

## 실제 측정 선택 경로

- GPIO pulse: event, ISR, task start/end
- RTOS trace: ready/running/block state
- cycle counter/timer
- queue depth watermark
- execution-time histogram
- stack watermark

측정 시 instrumentation, compiler optimization, clock와 power state를 기록합니다.

## 필수 결과물

```text
workspace/
├── workload.md
├── resource-graph.md
├── response-time.md
├── priority-inversion.md
├── failure-scenarios.md
├── evidence/                 선택 측정
└── report.md
```

## 완료 조건

- 모든 deadline에 end-to-end 시작과 종료 사건이 정의돼 있습니다.
- shared resource마다 최대 blocking source를 찾습니다.
- interrupt disabling과 ISR interference를 포함합니다.
- queueing delay와 execution time을 구분합니다.
- priority assignment의 근거와 반례가 있습니다.
- 분석이 사용하는 가정과 미측정 구간을 표시합니다.
- measured max를 WCET 보장으로 확대하지 않습니다.

자동 checker는 주어진 정수 시간 모델에서의 보수적 반복, queue 사건 순서와
단순 priority-inheritance trace만 판정합니다. 실제 RTOS의 scheduling point,
context-switch 비용, multicore, cache·flash stall, interrupt controller와 WCET를
증명하지 않습니다. target 측정은 별도 raw trace와 clock·optimization·power
조건을 보존하고, fixture 결과보다 강한 보장으로 확대하지 않습니다.

## 잘못된 완료

- CPU utilization 합계만 계산
- 평균 latency로 deadline 주장
- mutex hold 안의 I/O와 preemption을 무시
- ISR를 0 cost로 처리
- best-effort logging이 critical task와 같은 resource를 block
- 실제 clock/power state를 기록하지 않음

## 검토 질문

1. utilization이 낮아도 deadline miss가 가능한 trace를 작성해 보세요.
2. priority inheritance가 모든 deadlock과 긴 blocking을 해결하지 못하는 이유는 무엇입니까?
3. event timestamp를 ISR entry에서 찍을 때 hardware event부터의 latency 중 무엇을 놓칩니까?
4. storage erase를 높은 priority에서 수행하지 않고도 data loss를 막는 구조를 제안해 보세요.
