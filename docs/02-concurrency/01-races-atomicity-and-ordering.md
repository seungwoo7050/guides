# 경쟁, 원자성과 순서

## 학습 목표

- 경쟁 조건, 언어 수준 data race, 원자성, 가시성과 순서를 분리합니다.
- 복합 갱신을 깨는 실행 교차를 결정론적 trace로 재현합니다.
- atomic operation이 해결하지 않는 수명·소유권·복합 불변식을 식별합니다.

## 핵심 모델

동시에 실행되는 두 작업이 같은 메모리를 사용한다고 해서 곧바로 오류가 생기는 것은 아닙니다. 오류는 **여러 작업이 관찰하거나 바꾸는 상태에 대한 계약이 없고, 결과가 보장되지 않은 사건 순서에 의존할 때** 생깁니다. 이 장에서는 경쟁 조건, 데이터 경쟁, 원자성, 가시성과 순서를 서로 구분하고, 운영체제가 어떤 메커니즘을 제공하더라도 상위 계층이 지켜야 할 불변식이 남는 이유를 설명합니다.

## 동시성과 병렬성은 같은 말이 아닙니다

```text
동시성
- 여러 작업의 진행 구간이 겹칩니다.
- 하나의 CPU에서도 선점과 block 사이에 실행이 교차할 수 있습니다.

병렬성
- 여러 CPU 또는 실행 장치가 실제 같은 시간에 명령을 수행합니다.
- cache coherence와 메모리 순서 문제가 더 직접적으로 드러날 수 있습니다.
```

하나의 CPU에서는 한 순간에 한 명령만 실행하더라도 `read → 계산 → write` 사이에 다른 작업이 들어올 수 있습니다. 따라서 “CPU가 하나이므로 공유 상태는 안전합니다”라는 결론은 성립하지 않습니다.

## 경쟁 조건과 데이터 경쟁을 구분합니다

경쟁 조건은 결과의 정확성이 사건 순서에 의존하는 더 넓은 개념입니다.

```text
잔액 확인
→ 충분하다고 판단
→ 다른 요청이 먼저 인출
→ 첫 요청도 인출
```

각 접근이 잠금으로 보호되어 데이터 경쟁이 없더라도 “확인과 변경”이 하나의 계약으로 묶이지 않았다면 업무 경쟁 조건은 남습니다.

데이터 경쟁은 언어 메모리 모델이 정의하는 더 좁은 오류입니다. 보통 같은 메모리 위치에 대한 상충 접근 중 적어도 하나가 쓰기이고, 두 접근 사이에 필요한 동기화 관계가 없을 때 발생합니다. C와 C++에서는 데이터 경쟁이 정의되지 않은 동작을 만들 수 있으므로 “가끔 잘못된 값” 정도로 제한해 생각해서는 안 됩니다.

이 가이드가 집중하는 질문은 다음입니다.

```text
어떤 상태가 공유됩니까?
한 연산의 논리적 경계는 어디까지입니까?
어떤 사건이 먼저 보여야 합니까?
중간 상태를 누가 관찰할 수 있습니까?
실패하거나 선점돼도 어떤 불변식이 유지돼야 합니까?
```

언어별 atomic API의 정확한 문법과 모든 memory order 규칙은 C, C++와 Java 가이드가 담당합니다.

## 원자성은 연산의 경계를 말합니다

하나의 load와 store가 각각 원자적이어도 복합 갱신은 원자적이지 않을 수 있습니다.

```text
초기값 counter = 0

작업 A: load counter → 0
작업 B: load counter → 0
작업 A: 0 + 1 계산
작업 B: 0 + 1 계산
작업 A: store 1
작업 B: store 1

예상값 2, 실제값 1
```

[`lost-update.c`](../../examples/lost-update.c)는 이 실행 교차를 sleep이나 우연한 scheduler 순서에 맡기지 않습니다. 두 작업이 같은 값을 읽은 뒤 함께 저장하도록 barrier로 순서를 고정합니다.

```sh
make -C examples build/lost-update
./examples/build/lost-update split 100
./examples/build/lost-update fetch-add 100
```

`split` 경로는 원자적 load와 원자적 store를 따로 사용하지만 복합 증가를 하나로 묶지 않습니다. `fetch-add` 경로는 읽기-수정-쓰기를 하나의 원자적 연산으로 만듭니다.

여기서 얻어야 할 결론은 “항상 atomic을 쓰면 됩니다”가 아닙니다. 한 변수의 증가처럼 상태 전이가 작은 경우에는 원자적 읽기-수정-쓰기가 충분할 수 있습니다. 여러 변수의 관계, queue의 head·tail·count, 소유권 이전처럼 불변식이 넓으면 mutex나 더 높은 수준의 직렬화가 필요합니다.

## 가시성과 순서는 원자성과 별개의 질문입니다

다음 두 값을 생각해 봅니다.

```text
data = 준비할 실제 값
ready = data가 준비됐다는 표시
```

생산자가 `data`를 쓴 뒤 `ready`를 설정하고, 소비자가 `ready`를 본 뒤 `data`를 읽고 싶어 합니다. 하지만 compiler와 CPU는 독립적이라고 판단한 접근을 재배치할 수 있고, 각 CPU의 store buffer와 cache가 관찰 시점을 달리 만들 수 있습니다.

따라서 필요한 계약은 다음 두 가지입니다.

1. `ready` 자체의 읽기와 쓰기가 찢어지지 않아야 합니다.
2. 소비자가 준비 상태를 본 경우, 그보다 앞선 `data` 쓰기도 관찰해야 합니다.

두 번째가 순서와 공개의 문제입니다. 흔히 생산자의 release와 소비자의 acquire가 연결돼 이 관계를 만듭니다.

```text
생산자
일반 data 쓰기
release publish

소비자
acquire observe
일반 data 읽기
```

이 도식은 공통 직관만 보여 줍니다. 어떤 연산이 synchronize-with 관계를 만드는지, 실패한 compare-exchange에 어떤 순서를 써야 하는지 같은 정확한 규칙은 사용하는 언어의 memory model을 따라야 합니다.

## barrier와 memory fence를 섞지 않습니다

`barrier`라는 단어는 문맥에 따라 두 가지를 가리킬 수 있습니다.

### 실행 참가자 barrier

여러 thread가 같은 단계에 도착할 때까지 다음 단계로 넘어가지 않게 합니다. `lost-update.c`의 사용자 정의 barrier는 실행 교차를 결정적으로 만들기 위해 사용됩니다.

### memory fence

한 실행 주체 안의 메모리 접근 순서와 다른 주체가 관찰할 수 있는 순서를 제약합니다. CPU 명령, compiler fence와 언어 atomic 규칙이 서로 다른 계층에 존재합니다.

두 메커니즘은 함께 쓰일 수 있지만 같은 기능은 아닙니다. 참가자 barrier를 통과했다고 해서 언어가 요구하는 메모리 동기화가 자동으로 생기는지, 그 구현이 어떤 mutex·condition variable·atomic을 사용하는지 확인해야 합니다.

## 임계 구역은 코드 줄보다 불변식의 범위로 정합니다

다음 queue 상태가 있다고 가정합니다.

```text
0 <= count <= capacity
head와 tail은 배열 범위 안에 있음
count == 0이면 pop 불가
count == capacity이면 push 불가
저장된 항목 수 == count
```

`head`만 잠그고 `tail`만 따로 잠그면 각 변수의 개별 값은 안전해 보일 수 있습니다. 그러나 `count`, slot 내용과 종료 상태가 함께 바뀌면 전체 불변식이 중간에 깨질 수 있습니다.

임계 구역을 정할 때는 다음 순서가 좋습니다.

```text
1. 항상 참이어야 하는 관계를 적습니다.
2. 그 관계를 읽거나 바꾸는 모든 연산을 찾습니다.
3. 중간 상태를 다른 작업이 볼 수 있는지 확인합니다.
4. 실패·취소·예외 경로도 같은 보호를 거치는지 확인합니다.
5. 필요한 최소 범위를 하나의 동기화 계약으로 묶습니다.
```

잠금 범위를 단순히 줄이는 것은 목표가 아닙니다. 먼저 정확한 경계를 만든 뒤 측정으로 contention이 문제인지 확인해야 합니다.

## interrupt context도 동시 실행 주체입니다

커널에서는 사용자 thread끼리만 경쟁하지 않습니다. 다음 실행 주체가 같은 상태를 만질 수 있습니다.

- process 또는 thread context
- interrupt handler
- deferred work 또는 worker thread
- timer callback
- 다른 CPU의 kernel path

interrupt를 잠시 비활성화하는 것은 현재 CPU에서 해당 interrupt 경로가 끼어드는 것을 막을 수 있지만, 다른 CPU의 접근이나 process context의 모든 경쟁을 자동으로 막지 않습니다. 반대로 sleep 가능한 mutex는 interrupt context에서 사용할 수 없는 경우가 있습니다.

따라서 동기화 도구는 이름보다 실행 문맥과 block 가능성을 함께 봐야 합니다.

```text
이 문맥은 잠들 수 있습니까?
같은 상태를 다른 CPU가 바꿀 수 있습니까?
interrupt handler가 같은 lock을 잡습니까?
lock을 잡은 채 장치 완료를 기다리지는 않습니까?
```

## 원자적 상태 기계는 유용하지만 수명 문제를 없애지 않습니다

요청 상태를 다음처럼 원자적으로 바꾼다고 가정합니다.

```text
PENDING → COMPLETED
PENDING → CANCELLED
```

compare-and-swap으로 둘 중 하나만 성공하게 하면 double completion을 막을 수 있습니다. 그러나 다음 질문은 남습니다.

- 완료 결과를 저장하는 buffer는 언제 해제합니까?
- 실패한 경쟁자가 보유한 참조는 누가 반납합니까?
- 상태가 `COMPLETED`가 됐지만 사용자에게 아직 전달되지 않은 결과는 어디에 있습니까?
- late interrupt가 이미 재사용된 request id를 만날 수 있습니까?

원자적 상태 전이는 **누가 승자인지** 결정하는 도구입니다. 자원 수명, queue 위치와 회수 책임은 별도 불변식으로 모델링해야 합니다. [`device_io.py`](../../exercises/kernel-model/README.md)는 요청 상태와 pending·in-flight·completion 위치가 서로 모순되지 않는지 함께 검사합니다.

## 성능 최적화 전에 실패를 결정적으로 재현합니다

동시성 버그를 `sleep(0.01)`과 반복 횟수로 재현하면 machine load와 scheduler에 따라 결과가 달라집니다. 우선 다음 도구를 사용해 문제 순서를 고정합니다.

```text
barrier
latch
명시적 event
fixture로 제공된 state transition
단일 thread가 여러 작업의 step을 교대로 호출하는 모델
```

결정적 재현이 만들어진 뒤에만 실제 병렬 실행으로 확장합니다. 상태 모델은 hardware timing을 재현하지 않지만, 어떤 순서가 불변식을 깨뜨리는지 검증하기에 적합합니다.

## 흔히 잘못 내리는 결론

### “정수 읽기와 쓰기는 원자적이므로 안전합니다”

복합 연산, 순서와 수명은 별개입니다.

### “volatile을 쓰면 thread-safe합니다”

대부분의 일반 언어에서 `volatile`은 mutex나 atomic의 대체물이 아닙니다. 정확한 의미는 언어와 구현 계약을 확인해야 합니다.

### “mutex가 있으므로 경쟁 조건이 없습니다”

모든 참여자가 같은 mutex와 같은 predicate를 공유해야 합니다. 확인과 변경이 서로 다른 임계 구역에 있으면 논리 경쟁은 남습니다.

### “테스트를 여러 번 통과했으므로 동시성 버그가 없습니다”

관찰되지 않았다는 뜻일 뿐입니다. 잘못된 실행 교차를 의도적으로 만들고 불변식을 검사해야 합니다.

### “강한 memory order를 쓰면 설계가 옳습니다”

강한 순서는 일부 가시성 문제를 줄일 수 있지만 잘못된 소유권, duplicate queue entry와 use-after-free를 고치지 않습니다.

## 연결 실습

[`lost-update.c`](../../examples/lost-update.c)와 [`bounded-buffer.c`](../../examples/bounded-buffer.c)를 빌드해 아래 관찰 계약을 확인합니다.

1. `lost-update split 10`의 한 round를 종이에 두 작업의 단계로 나눕니다.
2. load와 store가 각각 원자적이어도 왜 결과 하나가 사라지는지 설명합니다.
3. `fetch-add`가 하나의 counter 불변식에는 충분한 이유를 설명합니다.
4. `bounded-buffer.c`의 `head`, `tail`, `count`, 합계와 종료 상태 중 어떤 값을 같은 mutex가 보호하는지 적습니다.
5. request cancellation에서 원자적 상태 전이만 있고 completion queue가 없다면 어떤 결과가 유실되는지 적습니다.

## 완료 기준

- `lost-update split`에서 두 load와 두 store의 실행 순서를 표로 재현합니다.
- `fetch-add`가 보장하는 단일 counter 원자성과 보장하지 않는 상위 계약을 나눕니다.
- bounded buffer의 mutex가 함께 보호해야 하는 field와 predicate를 모두 표시합니다.

## 실패 조건

- 개별 load/store가 atomic이라는 이유로 read-modify-write 전체가 안전하다고 결론 냅니다.
- `volatile` 또는 강한 memory order를 소유권·수명 설계의 대체로 사용합니다.
- 여러 번 통과한 비결정적 테스트를 잘못된 interleaving 부재의 증명으로 취급합니다.

## 자기 설명

- 경쟁 조건과 언어 수준 데이터 경쟁을 구분할 수 있습니까?
- 개별 load·store의 원자성과 복합 상태 전이의 원자성을 구분할 수 있습니까?
- 가시성, ordering과 lifetime이 원자성과 별개의 계약인 이유를 설명할 수 있습니까?
- 보호해야 할 code line이 아니라 불변식을 기준으로 임계 구역을 정할 수 있습니까?
- interrupt, timer와 다른 CPU를 동시 실행 주체로 포함해 분석할 수 있습니까?
- 우연한 반복이 아니라 결정적 실행 교차로 오류를 재현할 수 있습니까?
