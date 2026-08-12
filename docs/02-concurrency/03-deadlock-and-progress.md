# 데드락과 진행 보장

## 학습 목표

- 정상 block, deadlock, starvation, livelock과 priority inversion을 관측 기준으로 구분합니다.
- wait-for graph와 다중 인스턴스 자원 축소로 진행 불가능 집합을 찾습니다.
- 예방·회피·탐지·복구 정책의 전제와 비용을 비교합니다.

## 핵심 모델

프로그램이 “멈춘 것처럼 보입니다”라는 관찰만으로 원인을 데드락이라고 부를 수는 없습니다. 작업이 사건을 기다리는 정상 block일 수도 있고, 특정 작업만 계속 밀리는 starvation일 수도 있으며, 상태는 바뀌지만 완료는 만들지 못하는 livelock일 수도 있습니다. 이 장에서는 **누가 무엇을 보유하고 무엇을 기다리는지**를 그래프로 만들고, 시스템 전체와 개별 작업의 진행 보장을 분리합니다.

## 네 가지 상태를 먼저 구분합니다

### 정상 block

작업이 I/O, timer, condition 또는 message를 기다립니다. 필요한 사건이 발생하면 진행할 수 있습니다.

### deadlock

작업 집합이 서로 필요한 자원을 기다려 외부 개입이나 정책 변경 없이는 어떤 작업도 진행할 수 없습니다.

### starvation

시스템의 다른 작업은 계속 완료되지만 특정 작업은 정책상 선택되지 않거나 자원을 얻지 못합니다.

### livelock

작업들이 계속 실행하고 상태를 바꾸지만 서로 양보하거나 충돌을 반복해 유효한 완료를 만들지 못합니다.

진단할 때는 다음을 기록합니다.

```text
CPU를 쓰고 있습니까?
상태가 바뀌고 있습니까?
어떤 작업인가 완료되고 있습니까?
특정 작업만 기다립니까?
기다리는 사건이 외부에서 올 수 있습니까?
```

## 자원 할당 그래프로 기다림을 표현합니다

단일 인스턴스 resource에서는 다음 두 종류의 간선을 사용할 수 있습니다.

```text
작업 → 자원 : 요청하고 기다림
자원 → 작업 : 현재 보유
```

이를 작업 사이의 wait-for graph로 줄이면 다음과 같습니다.

```text
A가 B가 보유한 자원을 기다림 → A → B
B가 C가 보유한 자원을 기다림 → B → C
C가 A가 보유한 자원을 기다림 → C → A
```

단일 인스턴스 자원에서 cycle은 deadlock의 충분한 증거가 될 수 있습니다. 여러 인스턴스가 있는 경우 cycle만으로는 충분하지 않을 수 있으므로 available, allocation과 outstanding request를 함께 계산해야 합니다.

[`deadlock.py`](../../exercises/kernel-model/README.md)는 두 모델을 분리합니다.

- `find_wait_cycle`: 작업 간 wait-for graph의 cycle을 찾습니다.
- `detect_deadlocked`: 여러 인스턴스 자원에서 현재 완료 가능한 작업을 반복 제거하고 남는 집합을 찾습니다.

```sh
make checkpoint-check IMPL=workspace CHECKPOINT=04-deadlock
```

검사를 통과한 뒤에만 `exercises/kernel-model/reference/kernel_model/deadlock.py`의 세 알고리즘과 자신의 상태 표현을 비교합니다.

## Coffman 조건은 진단 체크리스트입니다

전통적으로 deadlock에는 다음 네 조건이 함께 필요합니다.

1. **상호 배제**: 자원을 동시에 하나의 작업만 사용할 수 있습니다.
2. **보유 후 대기**: 이미 가진 자원을 놓지 않은 채 다른 자원을 기다립니다.
3. **강제 회수 불가**: 시스템이 임의로 자원을 빼앗아도 안전하지 않습니다.
4. **순환 대기**: 대기 관계가 cycle을 만듭니다.

이 목록을 암기하는 목적은 모든 문제에 같은 해법을 쓰기 위해서가 아닙니다. 어느 조건을 깨뜨릴 수 있는지 찾는 데 사용합니다.

```text
상호 배제 제거
→ immutable data, copy, lock-free read, resource sharing 방식 변경

보유 후 대기 제거
→ 필요한 자원을 한 번에 요청, 실패하면 모두 반납

강제 회수 가능
→ rollback 가능한 작업, lease, preemptible resource

순환 대기 제거
→ 전역 lock order
```

각 해법에는 비용이 있습니다. 모든 자원을 한 번에 잡으면 concurrency가 줄고, rollback은 보상 상태가 필요하며, 전역 순서는 동적 resource graph에서 어렵습니다.

## 전역 lock order로 cycle을 제거합니다

[`dining-cycle.c`](../../examples/dining-cycle.c)는 각 작업이 필요한 두 lock 중 식별자가 작은 것을 먼저 획득합니다.

```sh
make -C examples build/dining-cycle
./examples/build/dining-cycle 100
```

모든 lock 획득 간선이 같은 방향을 따르면 순환 대기가 만들어지지 않습니다.

```text
항상 낮은 번호 → 높은 번호
```

하지만 이 프로그램이 증명하는 범위는 제한적입니다.

- 모든 작업이 정해진 round를 완료합니다.
- lock order가 cycle을 제거합니다.
- 공정한 대기 시간은 증명하지 않습니다.
- 특정 작업의 starvation이 절대 없다는 보장도 하지 않습니다.

실제 시스템에서는 resource id가 동적으로 생기거나 lock graph가 여러 module에 걸칠 수 있습니다. lock hierarchy를 문서화하고 debug build에서 order 위반을 검사하는 방식이 유용합니다.

## try-lock과 backoff는 deadlock을 livelock으로 바꿀 수 있습니다

다음 전략을 생각합니다.

```text
첫 lock 획득
둘째 lock 획득 실패
첫 lock 반납
즉시 다시 시도
```

두 작업이 같은 박자로 계속 양보하면 상태는 바뀌지만 누구도 완료하지 못합니다. random backoff, priority 또는 중앙 arbiter가 필요할 수 있습니다. 그러나 random delay는 correctness 증명이 아니라 충돌 가능성을 낮추는 정책입니다.

진행 보장을 말할 때는 다음을 구분합니다.

```text
blocking
- 다른 작업이 lock을 반납해야 진행합니다.

lock-free
- 전체 시스템에서 어떤 작업인가는 유한한 단계 안에 진행합니다.
- 특정 작업은 계속 실패할 수 있습니다.

wait-free
- 각 작업이 유한한 단계 안에 완료됩니다.

obstruction-free
- 혼자 실행되면 완료할 수 있습니다.
```

lock-free가 공정성이나 낮은 latency를 자동으로 의미하지 않습니다.

## starvation은 정책과 queue 규칙의 문제입니다

다음 상황에서 starvation이 생길 수 있습니다.

- priority가 낮은 작업이 계속 새 고우선순위 작업에 밀립니다.
- reader-preference RW lock에서 writer가 영원히 못 들어갑니다.
- unfair mutex에서 같은 작업들이 lock을 재획득합니다.
- MLFQ에서 CPU-bound 작업이 계속 낮은 queue에 머뭅니다.
- semaphore가 queue 순서를 보장하지 않습니다.

완화 정책에는 aging, FIFO wait queue, quota, fair scheduling과 priority inheritance가 있습니다. 각 정책은 throughput과 latency 비용을 가집니다.

스케줄링 결과를 평가할 때 평균만 보지 않습니다.

```text
최대 대기 시간
상위 percentile latency
각 작업의 service share
연속으로 선택되지 않은 기간
특정 class의 완료 여부
```

## priority inversion은 deadlock이 아니지만 진행을 심각하게 지연합니다

낮은 우선순위 작업 L이 mutex를 보유하고, 높은 우선순위 H가 기다리는 동안 중간 우선순위 M이 L을 선점하면 H는 M보다 간접적으로 낮은 우선순위가 됩니다.

```text
L: resource 보유
H: L을 기다림
M: L을 계속 선점
```

cycle이 없으므로 deadlock은 아닙니다. 그러나 실시간 또는 latency-sensitive 시스템에서는 deadline을 놓칠 수 있습니다.

priority inheritance는 L이 H의 priority를 잠시 상속하게 합니다. 이 정책을 사용할 때도 다음을 확인해야 합니다.

- nested lock에서 상속이 전파됩니까?
- lock 반납 뒤 priority가 정확히 복원됩니까?
- 여러 waiter의 priority를 어떻게 결합합니까?
- interrupt와 scheduler lock의 우선순위 관계는 무엇입니까?

## 여러 인스턴스 자원과 안전 상태

현재 deadlock 탐지는 지금 보유한 자원과 현재 요청만 봅니다. 회피 알고리즘은 각 작업의 최대 요구량까지 알아야 합니다.

```text
available
allocation[task]
maximum[task]
need = maximum - allocation
```

현재 available로 완료 가능한 작업을 찾고, 완료했다고 가정해 그 allocation을 돌려받는 과정을 반복합니다. 모든 작업을 제거할 수 있으면 safe sequence가 존재합니다.

중요한 구분은 다음입니다.

```text
unsafe
- 앞으로 어떤 요청 순서가 오면 deadlock이 될 수 있습니다.
- 현재 이미 deadlock이라는 뜻은 아닙니다.

deadlocked
- 현재 상태에서 완료 가능한 진행 경로가 없습니다.
```

Banker 계열 회피는 최대 요구량을 미리 알아야 하고 자원 이용률을 낮출 수 있어 모든 시스템에 적합하지 않습니다.

## timeout은 해결책이 아니라 복구 정책의 시작입니다

lock이나 원격 요청에 timeout을 두면 영원한 대기를 제한할 수 있습니다. 그러나 timeout 뒤에는 다음 질문이 남습니다.

- 작업이 실제로 자원을 얻지 못한 것이 확실합니까?
- 중간 상태를 rollback할 수 있습니까?
- 이미 일어난 side effect를 보상합니까?
- 같은 요청을 재시도해도 안전합니까?
- timeout된 waiter를 queue에서 정확히 제거했습니까?

커널 내부 mutex를 시간 초과로 포기할 수 없는 경우도 많습니다. timeout은 deadlock의 원인을 제거하지 않으며, 잘못 설계하면 부분 효과와 중복 실행을 추가합니다.

## deadlock 탐지와 복구

탐지를 선택한 시스템은 cycle을 찾은 뒤 희생 작업을 골라야 합니다.

선택 기준의 예는 다음과 같습니다.

```text
rollback 비용
이미 사용한 CPU·I/O 시간
보유한 resource 수
사용자 우선순위
다른 작업이 기다리는 정도
다시 시작할 수 있는지
데이터 손실 가능성
```

복구 방법은 작업 중단, transaction rollback, resource preemption과 process restart가 될 수 있습니다. 같은 작업만 반복 희생하면 starvation이 생기므로 희생 이력도 상태로 관리해야 합니다.

## 진단은 snapshot 하나보다 시간 흐름이 필요합니다

thread dump 한 번에서 cycle이 보이면 강한 증거가 됩니다. 반면 작업이 같은 위치에 있었다는 사실만으로는 정상적인 긴 I/O와 deadlock을 구분하기 어렵습니다.

다음 정보를 함께 수집합니다.

```text
시간별 wait graph 변화
각 lock의 owner와 wait duration
작업 상태와 CPU 사용량
I/O completion 유무
queue 길이와 throughput
최근 lock acquisition/release 사건
priority와 scheduler 상태
```

운영 환경의 실제 명령과 관찰 방법은 Unix 시스템 가이드가 담당합니다. 이 가이드에서는 관찰값을 어떤 상태 모델로 해석할지에 집중합니다.

## failure fixture로 모순을 거부합니다

`kernel-model`의 failure fixture는 다음과 같은 상태를 허용하지 않습니다.

- 같은 작업이 ready queue와 running 위치에 동시에 존재합니다.
- `BLOCKED` 작업이 어떤 wait queue에도 없습니다.
- request가 pending과 completion queue에 동시에 있습니다.

이 오류들은 모두 “한 객체는 동시에 하나의 상태 위치만 가진다”는 공통 불변식을 어깁니다.

```sh
make checkpoint-check IMPL=workspace CHECKPOINT=04-deadlock
```

## 연결 실습

[`deadlock-cycle.json`](../../exercises/kernel-model/fixtures/deadlock-cycle.json)과 [`dining-cycle.c`](../../examples/dining-cycle.c)를 서로 다른 진행 모델로 비교합니다.

다음 상황을 각각 deadlock, starvation, livelock, 정상 block 또는 정보 부족으로 분류하고 필요한 추가 증거를 적습니다.

1. 두 thread가 서로 상대가 보유한 mutex를 기다립니다.
2. 낮은 priority 작업이 10분 동안 CPU를 받지 못하지만 다른 요청은 계속 완료됩니다.
3. 두 worker가 충돌할 때마다 둘 다 즉시 rollback하고 같은 시점에 재시도합니다.
4. disk read를 기다리는 thread가 `BLOCKED`이고 장치 queue에는 요청이 있습니다.
5. queue 길이는 계속 늘지만 모든 worker는 CPU를 사용 중입니다.
6. thread dump 한 번에서 여러 작업이 같은 condition variable을 기다립니다.

## 완료 기준

- cycle fixture와 safe fixture의 work vector 변화를 단계별로 기록합니다.
- 여섯 관측 상황을 진행 문제로 분류하고 부족한 증거를 명시합니다.
- 선택한 예방 또는 복구 정책이 어떤 Coffman 조건과 소유권을 바꾸는지 설명합니다.

## 실패 조건

- thread dump 한 번의 대기 상태를 곧바로 deadlock이라고 단정합니다.
- 단일 인스턴스 cycle 규칙을 다중 인스턴스 자원에 그대로 적용합니다.
- timeout을 사용하면서 rollback, 중복 실행과 자원 회수 계약을 정의하지 않습니다.

## 자기 설명

- 정상 block, deadlock, starvation과 livelock을 관찰 기준으로 구분할 수 있습니까?
- 단일 인스턴스와 여러 인스턴스 resource에서 cycle의 의미가 다른 이유를 설명할 수 있습니까?
- 네 Coffman 조건 중 어떤 조건을 깨뜨리는 설계인지 말할 수 있습니까?
- lock ordering이 deadlock을 줄이지만 공정성까지 보장하지 않는 이유를 설명할 수 있습니까?
- lock-free, wait-free와 fairness를 구분할 수 있습니까?
- timeout 이후 rollback·소유권·재시도 계약을 설계할 수 있습니까?
