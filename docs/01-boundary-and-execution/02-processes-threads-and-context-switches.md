# 프로세스, 스레드와 문맥 전환

## 학습 목표

- program, process, address space, thread와 CPU context를 분리합니다.
- `NEW`, `READY`, `RUNNING`, `BLOCKED`, `TERMINATED` 위치 불변식을 추적합니다.
- mode switch와 context switch의 원인·저장 상태·비용을 구분합니다.

## 핵심 모델

프로세스와 스레드는 단순히 “실행 중인 코드”가 아닙니다. 커널이 중단했다가 다시 이어서 실행하고, 다른 실행 주체와 자원을 공유하거나 분리할 수 있도록 관리하는 상태 묶음입니다. 이 장에서는 program, process, address space, thread와 CPU context를 분리하고, 상태 전이와 context switch를 같은 말로 사용하지 않도록 모델을 세웁니다.

## 실행 객체를 분리하기

```text
program
- 저장장치에 있는 code와 초기 data

process
- 하나의 address space
- 자격 정보와 resource limit
- file descriptor table과 kernel object 참조
- 하나 이상의 thread

thread
- program counter와 일반 register
- stack pointer와 thread stack
- scheduling state와 priority
- signal mask와 thread-local kernel state 일부
```

같은 program을 두 번 실행하면 서로 다른 process가 됩니다. 같은 process의 thread들은 보통 code, global data, heap과 열린 file을 공유하지만 register와 stack은 별도로 가집니다. 주소 공간을 공유한다는 사실은 동시 접근이 안전하다는 뜻이 아닙니다.

## 최소 상태 기계

운영체제와 교재마다 이름은 다르지만 다음 상태는 공통 모델로 사용할 수 있습니다.

```text
NEW --admit--> READY --dispatch--> RUNNING --exit--> TERMINATED
                    ^                 |
                    |                 | block / wait
                    |                 v
                    +---- wake ---- BLOCKED

RUNNING --preempt 또는 yield--> READY
```

각 전이의 주체와 원인을 분리합니다.

| 전이 | 누가 일으킵니까? | 대표 원인 |
|---|---|---|
| `NEW → READY` | kernel admission 경로 | 생성이 끝나 실행 후보가 됩니다. |
| `READY → RUNNING` | scheduler와 dispatcher | CPU를 배정합니다. |
| `RUNNING → READY` | timer·scheduler 또는 작업 자신 | 선점, time slice 만료, 자발적 yield입니다. |
| `RUNNING → BLOCKED` | system call·fault·동기화 경로 | I/O, timer, page-in, lock이나 condition을 기다립니다. |
| `BLOCKED → READY` | interrupt·timer·다른 작업 | 기다리던 사건이 발생해 다시 실행 가능해집니다. |
| `RUNNING → TERMINATED` | 작업 또는 kernel | 정상 종료나 복구 불가능한 사건입니다. |

핵심 불변식은 한 작업이 동시에 두 실행 위치에 존재하지 않는 것입니다.

```text
READY 작업은 정확히 한 ready queue에 있습니다.
RUNNING 작업은 정확히 한 CPU에서 실행합니다.
BLOCKED 작업은 정확히 한 대기 이유와 wait queue에 연결됩니다.
TERMINATED 작업은 scheduling과 wait queue에서 제거됩니다.
```

[`kernel-model/lifecycle.py`](../../exercises/kernel-model/README.md)는 이 관계를 직접 검사합니다. 작업 객체의 `state`만 맞고 queue 위치가 틀려도 오류입니다.

## 상태 전이와 context switch는 다릅니다

상태 전이는 작업의 논리적 위치가 바뀌는 사건입니다. context switch는 현재 CPU register state를 저장하고 다른 작업의 state를 복원하는 메커니즘입니다.

다음 세 경로를 비교합니다.

```text
사용자 모드 → 커널 모드 → 같은 thread
- system call이 즉시 끝납니다.
- 모드는 바뀌지만 실행 주체는 같습니다.

사용자 모드 → 커널 모드 → 다른 thread
- 현재 작업이 block되거나 preempt됩니다.
- mode switch와 context switch가 함께 발생합니다.

kernel thread A → kernel thread B
- 사용자 모드로 돌아가지 않고 실행 주체만 바뀝니다.
```

따라서 system call 횟수와 context switch 횟수를 동일시할 수 없습니다. 성능 문제에서는 실제로 어떤 작업이 `RUNNING`에서 나갔고, 원인이 I/O·lock·page fault·time slice 중 무엇인지 확인해야 합니다.

## 커널이 보존하는 문맥

정확한 구조체와 필드는 운영체제와 ISA마다 다릅니다. 일반적으로 다음 상태가 필요합니다.

```text
CPU 실행 상태
- program counter
- stack pointer
- 일반 register와 상태 flag
- 필요할 때 vector/FPU state

scheduling 상태
- READY, RUNNING, BLOCKED
- policy별 priority, virtual runtime와 time slice
- CPU affinity와 최근 실행 CPU
- block reason과 wait channel

process 연결
- address space를 식별하는 참조
- credential과 resource limit
- file table 등 process-level object

kernel 실행 상태
- kernel stack
- 중단된 system call 진행 상태
- 참조 중인 kernel object와 cleanup 책임
```

모든 상태를 매 switch마다 같은 비용으로 저장하지는 않습니다. 같은 process의 thread switch는 address space를 유지할 수 있고, 일부 register state는 lazy 방식으로 관리할 수 있습니다. 하드웨어 TLB와 cache 비용은 컴퓨터 구조 가이드의 영역이며, 여기서는 “다른 address space로 바뀌면 이후 memory locality가 달라질 수 있다”는 경계만 사용합니다.

## process와 thread가 공유하는 것

공유 범위를 설계할 때는 “함께 보인다”와 “같이 갱신해도 안전하다”를 구분합니다.

| 자원 | process 사이 | 같은 process의 thread 사이 |
|---|---|---|
| virtual address space | 기본적으로 분리됩니다. | 공유합니다. |
| register와 stack | 분리됩니다. | thread마다 분리됩니다. |
| heap·global data | IPC나 shared mapping 없이는 분리됩니다. | 공유합니다. |
| file descriptor table | 생성·전달 방식에 따라 공유 참조가 생깁니다. | 보통 process 수준에서 공유합니다. |
| credential·resource limit | process 모델에 속합니다. | 같은 process 안에서 대체로 공유합니다. |
| scheduling state | 실행 주체마다 별도입니다. | thread마다 별도입니다. |

같은 file descriptor 번호를 공유해도 offset과 underlying open file state가 어떤 객체에 속하는지는 API에 따라 확인해야 합니다. 이 구체적 POSIX 계약은 C·Unix 가이드가 담당합니다.

## 생성, 교체와 종료의 소유권

process 생성과 종료를 단순한 함수 호출로만 보면 zombie, orphan과 자원 회수 문제를 놓칩니다.

```text
생성
- 새 process/thread 객체를 누가 할당합니까?
- address space와 file table을 복사합니까, 공유합니까?
- READY로 공개되기 전에 초기화가 끝났습니까?

실행 이미지 교체
- process identity와 PID는 유지합니까?
- 기존 address space와 thread는 어떻게 정리합니까?
- 열린 file과 signal 상태 중 무엇을 유지합니까?

종료
- exit status를 누가 보관합니까?
- parent가 아직 결과를 회수하지 않았다면 어떤 최소 상태가 남습니까?
- 마지막 참조가 사라질 때 누가 kernel object를 해제합니까?
```

운영체제마다 세부 계약은 다르지만, **종료한 실행 주체의 메모리 해제**와 **상위 주체가 결과를 회수하는 시점**이 분리될 수 있다는 모델은 중요합니다.

## context switch 비용을 분해하기

비용은 register 저장·복원만이 아닙니다.

- scheduler 자료구조를 갱신하고 후보를 선택합니다.
- kernel stack과 작업별 상태를 교체합니다.
- address space 전환이 필요하면 translation state에 영향을 줄 수 있습니다.
- 새 작업의 code와 data가 cache에 없으면 이후 miss가 늘어납니다.
- 공유 cache line과 lock이 CPU 사이를 이동할 수 있습니다.
- 너무 짧은 time slice는 응답성을 높이지만 유효 작업 비율을 낮춥니다.

반대로 switch가 비싸다는 이유만으로 thread나 process를 피할 수는 없습니다. I/O 대기 중 다른 작업을 실행하는 이익, 병렬성, 장애 격리와 구현 복잡성을 함께 비교합니다.

## 다중 CPU에서 추가되는 상태

CPU가 여러 개면 단일 ready queue 모델에 다음 문제가 추가됩니다.

```text
한 작업은 동시에 두 CPU에서 RUNNING이면 안 됩니다.
CPU별 ready queue의 부하를 언제 옮길지 결정해야 합니다.
최근 CPU에 남겨 cache locality를 얻을지, 빈 CPU로 보내 latency를 줄일지 선택합니다.
작업과 interrupt affinity가 특정 CPU에 집중될 수 있습니다.
동일 kernel object를 갱신하는 lock과 cache line 경쟁이 생깁니다.
```

이 가이드의 상태 모델은 CPU 하나로 시작합니다. 다중 CPU는 같은 불변식에 “CPU별 위치와 이동”이 추가된 확장으로 이해합니다.

## 관측값을 해석하는 주의점

`ps`, profiler와 tracing 도구는 서로 다른 단위를 보여 줍니다.

- 한 글자 상태가 `RUNNING`과 `READY`를 함께 표시할 수 있습니다.
- `BLOCKED`는 효율적인 I/O 대기일 수도 있고 풀리지 않는 lock 대기일 수도 있습니다.
- thread 수가 많다고 context switch가 항상 많은 것은 아닙니다.
- switch 횟수만으로 원인이 time slice인지 I/O인지 lock인지 알 수 없습니다.
- sample profiler는 전체 사건을 기록하는 trace와 다릅니다.

관측할 때는 수집 기간, process/thread 단위, 빠진 사건과 상태 정의를 함께 기록합니다.

## 연결 실습

다음 명령은 작업 A가 disk를 기다리는 동안 B가 실행되고, B 종료 뒤 A가 깨어나 완료되는 흐름을 재현합니다.

```sh
python3 exercises/kernel-model/reference/kernel-model.py \
  lifecycle exercises/kernel-model/fixtures/lifecycle.json
```

출력에서 확인할 항목은 다음과 같습니다.

- `running`, `ready`, `wait_queues`에 같은 작업이 중복되지 않습니다.
- block된 작업은 channel과 reason을 소유합니다.
- wakeup은 작업을 바로 `RUNNING`으로 만들지 않고 `READY`로 보냅니다.
- 종료한 작업은 ready와 wait queue에서 사라집니다.

## 완료 기준

- lifecycle fixture의 모든 전이를 이전 상태·사건·다음 상태 표로 작성합니다.
- 같은 작업이 running, ready, wait, completed 중 정확히 한 위치에 있음을 검사합니다.
- process가 공유하는 상태와 thread별로 보존하는 문맥을 예제로 나눕니다.

## 실패 조건

- `RUNNING`과 scheduler가 선택할 수 있는 `READY`를 같은 상태로 취급합니다.
- block reason과 wait queue 없이 작업 상태만 `BLOCKED`로 바꿉니다.
- context switch 횟수만으로 원인이 선점·I/O·lock 중 무엇인지 단정합니다.

## 자기 설명

- wakeup이 작업을 즉시 `RUNNING`이 아니라 `READY`로 옮기는 이유는 무엇입니까?
- 같은 process의 thread가 address space를 공유해도 register와 stack은 분리되는 이유는 무엇입니까?

## 다음 장으로 가져갈 모델

이 장을 마쳤다면 program, process, address space와 thread를 구분하고, mode switch와 context switch의 차이를 설명할 수 있어야 합니다. 다음 장에서는 여러 `READY` 작업 중 어떤 작업을 선택할지, 그 정책이 latency·throughput·fairness에 어떤 trade-off를 만드는지 비교합니다.
