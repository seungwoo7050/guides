# CPU 스케줄링

## 학습 목표

- workload와 tick 사건 순서를 고정한 뒤 scheduling 정책을 비교합니다.
- response, waiting, turnaround, throughput과 fairness의 충돌을 계산합니다.
- 정책 선택과 작업 위치 불변식을 서로 독립적으로 검증합니다.

## 핵심 모델

CPU scheduling은 “가장 빠른 알고리즘 하나”를 찾는 문제가 아닙니다. workload의 도착 패턴, CPU burst와 I/O wait, 응답 목표와 fairness에 따라 서로 다른 정책이 필요합니다. 이 장에서는 scheduler가 사용할 수 있는 상태, 정책별 선택 기준과 metric의 충돌을 분리합니다.

## 먼저 workload를 명시하기

정책을 비교하기 전에 작업이 어떤 형태인지 적습니다.

```text
arrival time
CPU burst 목록
burst 사이의 I/O wait
priority 또는 deadline
interactive인지 batch인지
CPU-bound인지 I/O-bound인지
작업 수와 CPU 수
```

CPU burst만 있고 I/O wait가 없는 표는 실제 시스템의 중요한 전이를 숨깁니다. 작업이 I/O를 요청하면 `RUNNING → BLOCKED`가 되고, completion 뒤 `BLOCKED → READY`가 됩니다. scheduler는 block된 작업을 선택할 수 없습니다.

## metric은 서로 충돌합니다

| metric | 의미 | 최적화할 때 생길 수 있는 비용 |
|---|---|---|
| turnaround time | 도착부터 완료까지의 시간 | 짧은 작업을 우선하면 긴 작업이 밀릴 수 있습니다. |
| response time | 도착부터 첫 실행까지의 시간 | 자주 선점하면 switch 비용이 늘 수 있습니다. |
| waiting time | READY 상태에서 기다린 시간 | I/O wait와 혼동하면 정책을 잘못 평가합니다. |
| throughput | 단위 시간에 완료한 작업 수 | 개별 작업의 tail latency가 나빠질 수 있습니다. |
| fairness | 작업이나 사용자에게 배분된 CPU의 균형 | 전체 처리량이나 cache locality와 충돌할 수 있습니다. |
| deadline miss | 정해진 시점까지 완료하지 못한 수 | 일반-purpose fairness와 다른 정책이 필요할 수 있습니다. |

평균만 보면 긴 지연을 숨길 수 있습니다. interactive workload에서는 median뿐 아니라 높은 percentile과 starvation 가능성을 함께 봅니다.

## 기본 정책을 같은 상태로 비교하기

### FCFS

도착 순서대로 실행하며, 한 CPU burst가 끝나거나 block될 때까지 유지합니다.

장점:

- 정책이 단순하고 선택 비용이 작습니다.
- 도착 순서가 명확합니다.

위험:

- 긴 CPU burst가 앞에 오면 짧은 작업이 오래 기다리는 convoy effect가 생깁니다.
- interactive response가 나쁠 수 있습니다.

### SJF와 SRTF

SJF는 예측된 CPU burst가 가장 짧은 작업을 비선점으로 선택합니다. SRTF는 남은 시간이 더 짧은 작업이 도착하면 선점합니다.

이론적으로 평균 waiting time을 줄일 수 있지만 미래 burst를 정확히 알기 어렵습니다. 실제 시스템은 과거 사용량을 이용한 추정과 workload class를 사용합니다. 추정 오류와 긴 작업의 starvation을 별도로 다뤄야 합니다.

### priority scheduling

숫자나 class로 중요도를 표현합니다. 같은 priority 안에서 FCFS나 RR를 결합할 수 있습니다.

우선순위가 낮은 작업이 계속 밀릴 수 있으므로 aging이 필요할 수 있습니다. 높은 우선순위 작업이 낮은 우선순위 작업의 lock을 기다리는 priority inversion은 단순 scheduler 선택만으로 해결되지 않습니다.

### Round Robin

한 작업에 quantum만큼 CPU를 주고 아직 끝나지 않았다면 ready queue 뒤로 보냅니다.

```text
quantum이 너무 큼
→ FCFS와 비슷해지고 response가 느려집니다.

quantum이 너무 작음
→ response는 빨라질 수 있지만 context switch와 locality 비용이 커집니다.
```

quantum은 고정된 마법의 값이 아니라 workload와 switch 비용을 함께 고려하는 정책 변수입니다.

### MLFQ

여러 priority queue와 서로 다른 quantum을 사용합니다. 짧게 CPU를 쓰고 자주 block되는 interactive 작업을 높은 queue에 유지하고, CPU를 오래 쓰는 작업을 낮은 queue로 내릴 수 있습니다.

다음 정책을 명시해야 합니다.

- 새 작업의 시작 queue
- quantum 소진 시 demotion
- I/O block 뒤 promotion 여부
- 일정 시간 뒤 전체 boost
- 각 queue 안의 ordering

규칙이 없으면 “MLFQ”라는 이름만으로 실행 결과를 결정할 수 없습니다.

## 한 tick의 처리 순서가 결과를 바꿉니다

결정론적 시뮬레이터는 같은 시각에 여러 사건이 발생할 때 순서를 고정해야 합니다. 이 가이드의 `scheduler.py`는 다음 순서를 사용합니다.

```text
1. 현재 시각까지 도착한 작업을 READY로 넣습니다.
2. I/O wait가 끝난 작업을 READY로 깨웁니다.
3. CPU가 비어 있으면 정책으로 한 작업을 선택합니다.
4. 현재 tick의 RUNNING·READY·BLOCKED 상태를 기록합니다.
5. READY 작업의 waiting time을 늘립니다.
6. RUNNING 작업을 한 tick 실행합니다.
7. burst 완료, block, 종료 또는 quantum 만료를 처리합니다.
```

도착과 quantum 만료를 반대 순서로 처리하면 같은 입력에서도 timeline이 달라질 수 있습니다. 정책 비교에서는 이런 tie-breaking 규칙을 숨기지 않습니다.

## I/O-bound와 CPU-bound의 상호작용

I/O-bound 작업은 짧은 CPU burst 뒤 자주 block됩니다. CPU-bound 작업은 긴 burst를 사용합니다. 한 정책이 interactive 작업을 빠르게 깨우면서도 CPU-bound 작업을 굶기지 않으려면 다음 상태가 필요합니다.

- 최근 CPU 사용량
- ready queue에서 기다린 시간
- block 빈도
- priority와 queue level
- time slice 사용량

I/O 작업이 block된 동안 CPU가 idle일 필요는 없습니다. scheduler는 다른 ready 작업을 실행합니다. 이것이 multiprogramming이 장치 대기 시간을 숨기는 핵심입니다.

## 다중 CPU의 정책 질문

CPU가 여러 개면 “다음 작업”뿐 아니라 “어느 CPU의 어느 queue에 둘지”를 선택합니다.

```text
global queue
- 부하 균형이 단순합니다.
- queue lock 경쟁이 커질 수 있습니다.

per-CPU queue
- 선택 경로와 locality가 좋아질 수 있습니다.
- imbalance를 교정하는 migration이 필요합니다.
```

CPU affinity는 cache locality를 보존할 수 있지만 한 CPU에 부하가 몰릴 수 있습니다. NUMA에서는 memory 위치까지 고려해야 하지만 이 가이드의 기본 범위에서는 per-CPU queue와 migration trade-off까지만 다룹니다.

## 정책과 불변식을 분리하기

어떤 정책을 사용해도 다음은 깨지면 안 됩니다.

```text
한 작업은 동시에 두 CPU에서 RUNNING이면 안 됩니다.
BLOCKED 작업은 ready queue에 있으면 안 됩니다.
종료한 작업은 다시 선택되면 안 됩니다.
ready queue의 한 항목은 존재하는 작업을 참조해야 합니다.
metric은 같은 시간 정의와 event order로 계산해야 합니다.
```

정책을 바꾸는 실험과 불변식 검사를 같은 함수에 섞으면 한 정책의 bug가 상태 오염으로 번질 수 있습니다. `kernel-model`은 작업 상태와 policy 선택을 분리해 검사합니다.

## 연결 실습

기준 fixture를 실행합니다.

```sh
python3 exercises/kernel-model/reference/kernel-model.py \
  schedule exercises/kernel-model/fixtures/schedule.json
```

출력에서 다음을 비교합니다.

- 각 tick의 `running`, `ready`, `blocked`
- 작업별 response, waiting, turnaround
- completion order
- CPU가 idle인 구간

`policy`를 `fcfs`, `sjf`, `priority`, `rr`, `mlfq`로 바꾸고 다음 질문에 답합니다.

1. 평균 waiting time이 줄어도 가장 오래 기다린 작업은 어떻게 바뀝니까?
2. I/O에서 돌아온 작업의 queue level은 어떤 정책을 반영합니까?
3. quantum을 절반으로 줄였을 때 timeline과 switch 횟수는 어떻게 달라집니까?
4. 같은 시각에 도착한 작업의 tie-breaker를 바꾸면 결과가 안정적으로 재현됩니까?

## 실제 관측을 정책 증명으로 오해하지 않기

한 번 실행한 process의 CPU 사용률이나 context switch 수만으로 scheduler 정책을 증명할 수 없습니다. 실제 시스템에는 다음 변수가 있습니다.

- 다른 process와 interrupt load
- CPU frequency와 thermal state
- affinity와 cgroup·priority 설정
- filesystem·network wait
- kernel version과 scheduler implementation

실제 관측은 모델을 반증하는 근거로 사용하되, 정책 자체를 확인하려면 공식 문서와 trace가 필요합니다.

## 완료 기준

- 같은 fixture에서 FCFS·SJF·RR 정책의 timeline과 세 metric을 비교합니다.
- 도착, I/O wakeup, 선택, 실행, 완료의 한 tick 순서를 명시합니다.
- tie-break와 quantum을 바꾼 결과가 재현 가능하도록 입력과 정책을 기록합니다.

## 실패 조건

- I/O 대기를 ready waiting time에 포함해 정책 metric을 왜곡합니다.
- 평균값 하나만 보고 starvation과 tail latency를 무시합니다.
- 실제 시스템 한 번의 CPU 사용률로 scheduler 정책을 증명합니다.

## 자기 설명

- SJF가 평균 대기를 줄여도 starvation 위험을 만들 수 있는 이유는 무엇입니까?
- RR quantum을 줄일 때 response와 context-switch 비용이 반대 방향으로 움직일 수 있는 이유는 무엇입니까?

## 다음 장으로 가져갈 모델

이 장을 마쳤다면 scheduler가 `READY` 후보만 선택하고, block·wakeup이 workload를 계속 바꾼다는 점을 설명할 수 있어야 합니다. 다음 장에서는 작업이 사건을 기다릴 때 wait queue 등록과 wakeup을 어떻게 연결해야 알림을 잃지 않는지 살펴봅니다.
