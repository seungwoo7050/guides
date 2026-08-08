# 동기화 도구와 조건 대기

## 학습 목표

- mutex, spinlock, semaphore, condition과 barrier를 저장 상태와 소유권으로 구분합니다.
- 도구 이름보다 보호할 predicate와 실행 문맥에서 선택합니다.
- cancellation·shutdown·priority inversion을 정상 경로와 함께 설계합니다.

## 핵심 모델

동기화 도구는 공유 변수를 “안전하게 만드는 마법”이 아닙니다. 각 도구는 **누가 동시에 들어갈 수 있는지, 조건이 거짓일 때 어디서 기다리는지, 사건이 발생하면 누구를 깨우는지, 취소와 종료에서 소유권을 누가 회수하는지**를 정합니다. 올바른 도구 선택은 이름을 암기하는 일이 아니라 보호할 불변식과 실행 문맥을 명시하는 일입니다.

## 먼저 보호할 predicate를 적습니다

bounded queue를 예로 들면 다음 관계가 핵심입니다.

```text
0 <= count <= capacity
head와 tail은 유효한 slot을 가리킴
count == 0이면 consumer는 꺼낼 수 없음
count == capacity이면 producer는 넣을 수 없음
producer_done && count == 0이면 consumer가 종료할 수 있음
```

이 관계를 적지 않고 “mutex 하나와 condition variable 두 개를 씁니다”라고 시작하면 다음 오류를 놓치기 쉽습니다.

- `count`는 잠갔지만 종료 flag는 잠그지 않습니다.
- condition wait 전후에 다른 mutex를 사용합니다.
- signal이 predicate 변경보다 먼저 발생합니다.
- 오류 경로에서 lock을 반납하지 않습니다.
- 마지막 producer 종료를 consumer가 알 수 없습니다.

[`bounded-buffer.c`](../../examples/bounded-buffer.c)는 `head`, `tail`, `count`, 통계와 `producer_done`을 하나의 mutex로 보호하고 `not_empty`, `not_full`은 각각 predicate가 바뀔 가능성을 알립니다.

## mutex: 소유권이 있는 상호 배제

mutex는 일반적으로 한 실행 주체가 획득하고 같은 소유자가 해제합니다. 핵심 계약은 다음입니다.

```text
lock 획득 성공
→ 보호 상태에 접근할 독점 권한을 얻음

unlock
→ 보호 상태를 공개하고 소유권을 반납함
```

mutex를 선택할 때 확인할 질문은 다음과 같습니다.

- 잠든 채 기다려도 되는 문맥입니까?
- 임계 구역이 얼마나 오래 걸립니까?
- lock을 가진 채 I/O나 다른 thread completion을 기다립니까?
- 같은 lock을 획득하는 순서가 전체 시스템에서 일관됩니까?
- 실패와 조기 반환에서도 반드시 해제됩니까?

잠금의 수를 늘리면 병렬성이 높아질 수 있지만, 불변식이 여러 잠금에 걸치면 lock ordering과 snapshot 일관성이 더 어려워집니다.

## spinlock: 잠들 수 없는 짧은 경로

spinlock은 획득에 실패한 동안 CPU에서 반복합니다. 따라서 다음 조건이 중요합니다.

```text
임계 구역이 매우 짧음
현재 문맥에서 sleep이 허용되지 않음
lock 소유자가 다른 CPU에서 곧 실행될 가능성이 있음
선점·interrupt와의 관계가 정의됨
```

하나의 CPU에서 lock 소유자가 선점된 채 다른 작업이 같은 lock을 spin하면 진행하지 못할 수 있습니다. 실제 kernel spinlock은 선점, interrupt mask와 memory barrier를 함께 다룰 수 있으므로 사용자 공간 busy loop와 같은 것으로 보면 안 됩니다.

“spin이 mutex보다 빠릅니다”는 일반적인 규칙이 아닙니다. 대기 시간, CPU 수, contention과 scheduler 상태를 측정해야 합니다.

## semaphore: 제한된 허가 수를 모델링합니다

counting semaphore는 동시에 사용할 수 있는 허가의 수를 나타냅니다.

```text
초기 permit = N
acquire 성공 → permit 하나 소비
permit 없음 → waiter 등록 또는 실패
release → waiter에게 직접 양도하거나 permit 증가
```

mutex와 다른 점은 소유권 모델입니다. semaphore는 반드시 같은 작업이 반환해야 하는 mutex와 달리, 어떤 사건이 허가를 반납할 수 있습니다. 이 때문에 resource pool, producer-consumer의 item·space 수와 동시 작업 제한에 적합합니다.

하지만 semaphore count만으로 queue 내용, 종료 상태와 항목 소유권이 모두 보호되는 것은 아닙니다. count와 실제 자료구조가 어긋나지 않도록 추가 mutex 또는 원자적 상태 기계가 필요할 수 있습니다.

[`synchronization.py`](../../exercises/kernel-model/README.md)의 `CountingSemaphore`는 기다리는 작업이 있으면 `release`가 permit을 단순 증가시키지 않고 다음 waiter에게 직접 허가를 넘깁니다. 이 차이는 “permit 수”와 “이미 선택된 소유자”를 구분하게 합니다.

## condition variable: 상태를 저장하지 않고 변화 가능성을 알립니다

condition variable은 item이나 permit을 저장하는 queue가 아닙니다. 공유 predicate를 다시 검사해야 할 이유를 알리는 메커니즘입니다.

올바른 기본형은 다음과 같습니다.

```text
lock(mutex)
while predicate가 거짓:
    condition_wait(condition, mutex)
predicate가 참인 상태에서 공유 상태 변경
unlock(mutex)
```

`condition_wait`는 개념적으로 다음을 원자적으로 연결해야 합니다.

```text
wait queue 등록
mutex 해제
현재 작업 block
```

깨어난 뒤에는 mutex를 다시 획득하고 predicate를 재검사합니다.

### signal과 broadcast

`signal`은 보통 waiter 하나를 깨울 가능성을 만듭니다. `broadcast`는 모든 waiter를 깨웁니다. 선택 기준은 “작업이 몇 개인가”보다 predicate 변화가 몇 작업의 진행을 허용하는가입니다.

- item 하나가 추가됐다면 consumer 하나만 진행할 수 있습니다.
- shutdown flag가 설정됐다면 모든 waiter가 종료 조건을 확인해야 합니다.
- 여러 slot이 한꺼번에 생겼다면 여러 producer를 깨울 수 있지만 과도한 wakeup 비용도 고려합니다.

깨울 대상의 공정성은 condition variable 자체가 보장하지 않을 수 있습니다.

## event와 generation: 사건을 놓치지 않는 방법

단순 notification은 waiter가 아직 등록되지 않았을 때 유실될 수 있습니다. 해결은 사건의 의미에 따라 다릅니다.

```text
상태 기반 predicate
→ 상태 자체를 저장하고 lock 아래에서 다시 검사합니다.

누적 permit
→ semaphore처럼 개수를 저장합니다.

message
→ queue에 payload를 보존합니다.

변경 세대
→ generation 또는 sequence를 증가시켜 늦은 waiter가 변화 사실을 감지합니다.
```

`ConditionChannel` 실습은 `prepare_wait`에서 관찰한 generation과 `commit_wait` 시점의 generation을 비교합니다. 사이에 notification이 있었다면 실제 sleep을 하지 않고 호출자에게 predicate 재검사를 요구합니다.

```sh
make -C exercises/kernel-model reference-test
```

이 모델은 실제 condition variable API를 복제하려는 것이 아니라 깨우기 손실을 막기 위해 어떤 상태가 필요할 수 있는지 보여 줍니다.

## reader-writer lock과 seqlock은 읽기 비율만 보고 선택하지 않습니다

### reader-writer lock

여러 reader를 동시에 허용하고 writer는 독점합니다. 읽기가 많을 때 유리할 수 있지만 다음 문제가 있습니다.

- writer starvation 또는 reader starvation 정책
- read에서 write로 upgrade할 때 deadlock
- 읽기 구간이 길면 writer latency 증가
- cache line contention과 관리 비용

### seqlock 계열

writer가 sequence를 바꾸며 갱신하고 reader는 lock 없이 snapshot을 읽은 뒤 sequence가 변했는지 확인해 재시도합니다. reader가 매우 짧고 재시도 가능한 경우에 유용하지만 다음 제약이 있습니다.

- reader가 pointer를 따라가며 해제된 object에 접근하면 안 됩니다.
- writer가 길면 reader 재시도가 폭증합니다.
- 일관되지 않은 중간 값을 읽어도 안전한 자료형이어야 합니다.
- memory ordering 규칙이 정확해야 합니다.

도구 이름보다 데이터 수명과 재시도 가능성을 먼저 확인합니다.

## barrier와 latch: 단계의 참가자를 조정합니다

barrier는 정해진 참가자가 한 세대에 모두 도착할 때까지 기다립니다. 다음 세대로 재사용하려면 generation이 필요합니다. 참가자가 중간에 실패하거나 빠졌을 때 영원히 기다리지 않도록 broken 상태나 cancellation 정책도 필요합니다.

latch는 보통 count가 0이 될 때 한 번 열립니다. 작업 시작 gate, 여러 worker 완료 대기와 결정적 test에 유용합니다.

운영 코드보다 test에서 barrier를 사용하면 특정 실행 교차를 안정적으로 재현할 수 있습니다. 그러나 barrier를 추가해 버그를 가리는 일이 없도록, test 동기화와 제품 동기화를 구분합니다.

## read-copy-update와 hazard 계열은 수명 회수가 핵심입니다

읽기를 막지 않는 자료구조에서는 pointer를 교체한 뒤 옛 object를 즉시 해제할 수 없습니다. 기존 reader가 아직 참조할 수 있기 때문입니다.

```text
publish new version
→ 새 reader는 new version 사용
→ 기존 reader가 quiescent state를 지날 때까지 대기
→ old version 회수
```

RCU, epoch reclamation, hazard pointer는 세부 방식이 다르지만 “공개”보다 “안전한 회수 시점”이 핵심입니다. 이 영역은 후속 과정이며, 여기서는 lock-free라는 말이 memory reclamation 문제를 없애지 않는다는 점만 고정합니다.

## priority inversion과 mutex protocol

낮은 우선순위 작업 L이 lock을 보유하고, 높은 우선순위 H가 그 lock을 기다리는 동안 중간 우선순위 M이 L을 계속 밀어낼 수 있습니다.

```text
L: lock 보유
H: lock 대기
M: L보다 우선순위가 높아 계속 실행
→ H가 간접적으로 M보다 뒤로 밀림
```

priority inheritance는 L이 H의 우선순위를 일시적으로 상속하게 해 lock을 빨리 반납하도록 돕습니다. priority ceiling은 resource마다 상한을 두는 다른 정책입니다. 어떤 protocol도 긴 임계 구역과 잘못된 lock graph를 자동으로 고치지는 않습니다.

## 오류와 취소 경로를 첫 설계에 포함합니다

동기화 코드는 정상 경로보다 종료 경로에서 자주 깨집니다.

```text
thread 생성 일부 실패
producer가 오류로 조기 종료
waiter가 timeout
process가 shutdown 요청
lock 획득 뒤 함수가 예외 또는 오류 반환
condition broadcast 중 일부 작업이 이미 취소됨
```

다음 계약을 명시합니다.

- 누가 shutdown predicate를 설정합니까?
- 누가 모든 waiter를 깨웁니까?
- queue에 남은 항목을 처리합니까, 폐기합니까?
- 대기자는 어떤 오류를 받습니까?
- 마지막 사용자가 object를 파괴하는 시점을 어떻게 압니까?

`bounded-buffer.c`는 생산 완료 flag를 mutex 아래서 설정하고 모든 consumer가 종료 predicate를 다시 보도록 broadcast합니다.

## 도구 선택표

| 문제 | 우선 검토할 도구 | 확인할 위험 |
|---|---|---|
| 짧은 공유 불변식 | mutex | 긴 임계 구역, lock order |
| sleep 불가한 짧은 kernel path | spinlock 계열 | CPU 낭비, 선점·interrupt 관계 |
| N개의 동시 자원 | counting semaphore | count와 실제 소유권 불일치 |
| predicate 변화 대기 | condition variable | lost wakeup, spurious wakeup |
| 단계 참가자 조정 | barrier/latch | 참가자 실패, generation |
| 읽기 많은 snapshot | RW lock 또는 sequence 계열 | writer starvation, 수명 회수 |
| 단일 변수 상태 경쟁 | atomic state machine | 복합 불변식과 cleanup |

이 표는 정답이 아니라 첫 질문입니다. 실행 문맥, 공정성, timeout, cancellation과 수명까지 포함해 결정합니다.

## 연결 실습

[`bounded-buffer.c`](../../examples/bounded-buffer.c)를 읽고 다음을 작성합니다.

1. mutex가 보호하는 모든 필드를 나열합니다.
2. `not_empty`와 `not_full` 각각의 predicate를 식으로 적습니다.
3. `if` 대신 `while`이 필요한 실행 순서를 하나 만듭니다.
4. 마지막 item을 소비한 뒤 `producer_done`이 거짓이면 왜 종료할 수 없는지 설명합니다.
5. producer가 중간 실패했는데 완료 flag를 설정하지 않으면 어떤 waiter가 영원히 남는지 적습니다.
6. buffer를 파괴하기 전에 모든 thread가 종료했음을 어떻게 보장하는지 확인합니다.

## 완료 기준

- bounded buffer의 `not_empty`·`not_full` predicate와 보호 lock을 식으로 적습니다.
- semaphore 허가가 대기자에게 직접 전달되는 상태 전이를 검사합니다.
- signal/broadcast, mutex/spinlock 선택을 실행 문맥·공정성·수명으로 설명합니다.

## 실패 조건

- condition wait를 predicate 없이 event queue처럼 사용합니다.
- 잠들 수 있는 경로에서 대기 시간이 긴 spinlock을 사용합니다.
- 정상 completion과 shutdown이 경쟁할 때 같은 자원을 두 번 회수할 수 있습니다.

## 자기 설명

- mutex, semaphore와 condition variable을 소유권과 저장하는 상태의 차이로 구분할 수 있습니까?
- condition wait가 predicate 검사와 queue 등록을 어떻게 연결해야 하는지 설명할 수 있습니까?
- signal과 broadcast를 깨우는 작업 수가 아니라 진행 가능한 predicate 수로 선택할 수 있습니까?
- spinlock을 sleep 가능한 일반 코드에 기계적으로 사용하지 않을 수 있습니까?
- atomic state machine과 자원 회수 계약을 별도로 설계할 수 있습니까?
- 정상 completion, timeout과 shutdown이 경쟁할 때 마지막 cleanup 책임을 정할 수 있습니까?
