# 블록, 깨우기와 IPC

## 학습 목표

- predicate 검사, wait 등록, block과 wakeup을 하나의 원자적 계약으로 연결합니다.
- generation을 이용해 prepare와 commit 사이의 lost wakeup을 방지합니다.
- 정상 완료·timeout·cancel 중 마지막 cleanup 소유자를 정합니다.

## 핵심 모델

작업이 I/O, timer, lock 또는 다른 process의 message를 기다릴 때 CPU를 계속 점유하며 반복 확인하면 자원을 낭비합니다. 운영체제는 진행 조건이 충족되지 않은 작업을 `BLOCKED`로 옮기고, 조건을 바꾼 사건이 발생했을 때 다시 `READY`로 깨웁니다. 이 장의 핵심은 “sleep과 wakeup 함수”가 아니라 **조건 검사, 대기 등록, 사건 기록과 취소 수명**을 하나의 상태 전이로 연결하는 것입니다.

## block은 CPU를 포기하는 상태 전이입니다

일반적인 경로는 다음과 같습니다.

```text
1. 작업이 진행 조건을 검사합니다.
2. 조건이 거짓이면 자신을 특정 wait queue에 등록합니다.
3. RUNNING에서 BLOCKED로 전환합니다.
4. scheduler가 다른 READY 작업을 실행합니다.
5. 장치·timer·다른 작업이 조건을 바꾸고 wakeup을 요청합니다.
6. 대기 작업은 BLOCKED에서 READY로 이동합니다.
7. scheduler가 다시 선택한 뒤 조건을 재검사합니다.
```

wakeup이 작업을 즉시 `RUNNING`으로 만드는 것은 아닙니다. CPU가 없거나 더 높은 우선순위 작업이 있으면 READY queue에서 기다릴 수 있습니다.

## wait queue가 소유해야 하는 정보

wait queue는 단순한 thread 목록보다 많은 계약을 가집니다.

```text
대기 주체 식별자
대기 이유와 predicate
어떤 object 또는 channel에 연결됐는지
cancel·timeout 가능 여부
등록 세대 또는 event sequence
깨울 때 전달할 결과와 오류
queue에서 제거할 책임
```

한 작업이 둘 이상의 queue에 동시에 들어가거나, wakeup 뒤에도 blocked 상태가 남거나, timeout과 정상 completion이 모두 소유권을 회수하면 상태가 깨집니다.

## 깨우기 손실이 생기는 창

다음 순서는 잘못될 수 있습니다.

```text
consumer: queue가 비었는지 검사 → 비어 있음
producer: item 추가 → wakeup 호출, 아직 waiter 없음
consumer: wait queue 등록 → sleep
```

조건은 이미 참인데 consumer는 이후 사건이 없으면 영원히 잠들 수 있습니다. 문제는 wakeup을 기억하지 않는 것이 아니라 **조건 검사와 대기 등록이 하나의 원자적 전이로 연결되지 않은 것**입니다.

해결 방법은 구현마다 다르지만 공통 원리는 다음 중 하나입니다.

- predicate를 보호하는 lock을 가진 채 wait queue 등록과 sleep 준비를 연결합니다.
- event generation이나 sequence를 기록하고, 등록 직전에 세대가 바뀌었는지 확인합니다.
- message queue 자체가 데이터를 보존해 늦은 수신자가 읽게 합니다.

[`synchronization.py`](../../exercises/kernel-model/README.md)의 `ConditionChannel`은 세대 번호를 사용합니다.

```text
prepare_wait에서 generation=4를 관찰
그 사이 notify가 generation=5로 변경
commit_wait가 generation 불일치를 확인
→ 작업은 sleep하지 않고 predicate를 다시 확인
```

## 왜 조건을 `while`로 다시 검사합니까?

condition variable에서 깨어났다는 사실은 predicate가 현재 참이라는 보장이 아닙니다.

- 여러 waiter 중 다른 작업이 먼저 자원을 소비할 수 있습니다.
- broadcast로 predicate 하나에 많은 작업이 깨어날 수 있습니다.
- 구현이 spurious wakeup을 허용할 수 있습니다.
- cancellation·timeout과 정상 사건이 경쟁할 수 있습니다.

따라서 안전한 구조는 다음과 같습니다.

```text
lock
while predicate가 거짓:
    wait(lock과 wait queue 등록을 원자적으로 연결)
predicate가 참인 상태에서 공유 상태 변경
unlock
```

## timeout과 cancellation은 또 하나의 completion입니다

대기 중인 요청을 취소하거나 timeout 처리할 때도 소유권 경쟁이 생깁니다.

```text
정상 completion이 먼저 발생
→ cancel은 이미 완료된 결과를 보존해야 합니다.

cancel이 먼저 대기 상태를 제거
→ 이후 늦은 completion이 같은 buffer를 다시 해제하면 안 됩니다.

in-flight 장치 요청
→ 사용자 요청은 취소됐어도 DMA가 끝날 때까지 buffer를 유지해야 할 수 있습니다.
```

“timeout이 났다”는 사실은 원래 작업이 실행되지 않았다는 뜻이 아닙니다. request state를 `QUEUED`, `IN_FLIGHT`, `COMPLETED`, `CANCEL_PENDING`처럼 명시하면 누가 마지막 cleanup을 수행하는지 결정할 수 있습니다.

## IPC를 상태와 복사 경계로 보기

Inter-process communication은 하나의 기능이 아니라 여러 소유권 모델입니다.

### byte stream과 pipe

송신자는 byte를 kernel buffer에 쓰고, 수신자는 순서대로 읽습니다. message boundary가 보존되지 않을 수 있으며 buffer가 가득 차면 writer가 block됩니다. 모든 write end가 닫혀야 reader가 EOF를 볼 수 있습니다.

### message queue

kernel 또는 runtime이 message boundary와 queue를 보존합니다. queue depth, message size, ordering, delivery와 backpressure 계약이 필요합니다.

### shared memory

data copy를 줄일 수 있지만 공유 상태의 동기화와 수명은 참여자가 직접 설계합니다. memory mapping이 공유된다는 사실만으로 visibility와 atomicity가 보장되지는 않습니다.

### signal·event notification

작은 사건을 알리는 데 적합하지만 payload와 누적 방식이 제한될 수 있습니다. 여러 번의 같은 사건이 하나로 합쳐지는지, queue되는지 확인해야 합니다.

### local socket

stream 또는 datagram 계약을 제공하고 credential 전달과 namespace를 사용할 수 있습니다. 구체적인 API는 C·Unix·network 가이드가 담당합니다.

## backpressure는 정상 상태입니다

producer가 consumer보다 빠르면 queue는 무한히 커질 수 없습니다. 운영체제와 애플리케이션은 다음 중 하나를 선택합니다.

```text
producer block
새 요청 거부
낡은 항목 버리기
우선순위별 제한
속도 조절 신호 전달
spill to disk
```

정책을 명시하지 않으면 memory exhaustion이나 latency 폭증이 backpressure 역할을 대신하게 됩니다. bounded buffer의 `not_full` condition은 공간이 생길 때까지 producer를 block하는 정책입니다.

## block/wakeup과 scheduler 연결

wait queue에서 깨워도 CPU를 즉시 주는 것은 scheduler 정책입니다. 우선순위가 높은 작업을 preempt할지, 현재 quantum이 끝날 때까지 기다릴지, 어느 CPU의 ready queue에 넣을지 결정해야 합니다.

여기서 메커니즘과 정책을 분리합니다.

```text
메커니즘
- 작업을 wait queue에 등록합니다.
- 사건을 기록합니다.
- BLOCKED를 READY로 바꿉니다.

정책
- 한 명만 깨울지 모두 깨울지 선택합니다.
- 어느 CPU queue에 넣을지 선택합니다.
- 즉시 선점할지 선택합니다.
```

`notify_all`을 무조건 사용하면 thundering herd가 생길 수 있습니다. 반대로 한 작업만 깨우면 여러 자원이 동시에 생겼을 때 처리량을 놓칠 수 있습니다.

## 연결 실습

`01-lifecycle`을 workspace에서 통과시킨 뒤 실행 수명 fixture를 확인합니다.

```sh
make checkpoint-check IMPL=workspace CHECKPOINT=01-lifecycle
python3 exercises/kernel-model/workspace/kernel-model.py \
  lifecycle exercises/kernel-model/fixtures/lifecycle.json
```

이어서 `02-synchronization`을 구현하고 깨우기 손실 창을 확인합니다.

```sh
make checkpoint-check IMPL=workspace CHECKPOINT=02-synchronization
python3 exercises/kernel-model/workspace/kernel-model.py \
  condition exercises/kernel-model/fixtures/condition.json
```

`outcomes`에서 첫 `commit`은 `slept=false`가 되어야 합니다. notify가 prepare와 commit 사이에 발생했기 때문입니다. 두 번째 등록은 같은 generation에서 commit되고, 이후 broadcast가 대기자를 깨웁니다.

각 checkpoint를 통과한 뒤에만 대응하는 `exercises/kernel-model/reference/kernel_model/lifecycle.py`와 `synchronization.py`의 설계 선택을 비교합니다.

## 설계 점검표

대기 경로를 설계할 때 다음 질문에 답합니다.

- predicate는 어떤 lock 또는 상태 object가 보호합니까?
- predicate 검사와 wait queue 등록 사이에 사건을 잃을 창이 있습니까?
- wakeup은 한 명입니까, 모두입니까? 그 정책의 근거는 무엇입니까?
- timeout, cancel과 정상 completion 중 누가 최종 결과를 소유합니까?
- queue가 가득 찼을 때 producer는 block, reject, drop 중 무엇을 합니까?
- 종료할 때 waiter를 어떻게 깨우고 queue를 회수합니까?

## 완료 기준

- condition fixture에서 첫 commit이 잠들지 않는 generation 변화를 trace합니다.
- block된 작업의 channel·reason·queue 위치가 일치함을 snapshot으로 검사합니다.
- queue full, timeout, cancel과 shutdown 각각의 결과와 소유자를 표로 작성합니다.

## 실패 조건

- predicate를 검사한 뒤 보호 없이 별도로 wait queue에 등록합니다.
- wakeup을 완료 보장으로 취급하고 깨어난 뒤 조건을 다시 검사하지 않습니다.
- timeout을 반환한 즉시 장치나 다른 실행 주체가 buffer를 사용하지 않는다고 가정합니다.

## 자기 설명

- condition variable이 상태 자체를 저장하지 않는다는 말은 무엇을 뜻합니까?
- `notify_all`이 correctness에는 안전해도 thundering herd를 만들 수 있는 이유는 무엇입니까?

## 다음 장으로 가져갈 모델

이 장을 마쳤다면 block은 단순한 함수 호출이 아니라 작업 위치와 소유권을 바꾸는 전이라는 점을 설명할 수 있어야 합니다. 다음 장에서는 여러 실행 주체가 같은 상태를 갱신할 때 어떤 interleaving이 잘못된 결과를 만들고, atomicity와 ordering이 어떤 역할을 하는지 살펴봅니다.
