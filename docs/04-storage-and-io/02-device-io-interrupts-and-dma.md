# 장치 I/O, interrupt와 DMA

## 학습 목표

- request의 queued·in-flight·completed·reaped 위치와 소유권을 추적합니다.
- DMA pin, interrupt completion, cancel과 timeout의 수명 경쟁을 설명합니다.
- queue depth·polling·coalescing 정책을 correctness 제약 안에서 비교합니다.

## 핵심 모델

장치 요청은 함수 호출처럼 호출 stack 안에서 즉시 완료되지 않을 수 있습니다. kernel이 요청을 queue에 넣고 장치에 제출한 뒤 현재 thread를 block하면, 실제 data transfer와 completion은 나중 interrupt에서 일어납니다. 이 장의 핵심은 장치 register 사용법이 아니라 **요청 상태, buffer pin, 취소, interrupt completion과 사용자 회수 사이의 수명**입니다.

## I/O 경로를 상태 기계로 봅니다

단순한 block device 또는 network device 요청을 다음 상태로 표현할 수 있습니다.

```text
NEW
→ QUEUED
→ IN_FLIGHT
→ COMPLETED
→ REAPED
```

취소가 있으면 다음 경로가 추가됩니다.

```text
QUEUED → CANCELLED → REAPED
IN_FLIGHT → CANCEL_PENDING → CANCELLED → REAPED
```

중요한 점은 `COMPLETED`와 `REAPED`를 분리하는 것입니다.

- `COMPLETED`: 장치와 kernel이 결과를 만들었고 buffer를 더 이상 DMA에 사용하지 않습니다.
- `REAPED`: 요청 소유자가 결과를 받아 마지막 참조를 정리했습니다.

completion 직후 request object를 즉시 해제하면 user 또는 waiting thread가 결과를 읽기 전에 사라질 수 있습니다.

[`device_io.py`](../../exercises/kernel-model/README.md)는 pending queue, in-flight set, owner별 completion queue와 request state가 서로 모순되지 않는지 검사합니다.

## 제출 전에 필요한 상태

요청 제출에는 최소한 다음 정보가 필요합니다.

```text
request id
owner 또는 completion 대상
operation 종류와 device 위치
buffer 또는 page 목록
전송 길이
queue와 priority 정보
timeout·cancel 상태
완료 결과를 저장할 위치
```

요청 수명 동안 owner가 사라질 수 있다면 process exit, file close와 device removal에서 누가 request를 취소하고 결과를 폐기할지 정해야 합니다.

## queue depth와 backpressure

장치는 동시에 처리할 수 있는 요청 수가 제한됩니다. kernel과 driver는 software queue와 hardware submission queue를 둘 수 있습니다.

queue가 가득 찼을 때 정책은 다음 중 하나입니다.

```text
호출자 block
즉시 busy 오류
상위 queue에 보관
낮은 priority 요청 거부
요청 병합 또는 재정렬
```

queue를 무한히 키우면 throughput이 늘기보다 latency와 memory 사용이 폭증할 수 있습니다. queue depth는 device parallelism과 tail latency를 함께 측정해 정해야 합니다.

`DeviceQueue(queue_depth=N)` 실습은 active request 수가 제한을 넘으면 제출을 거부합니다.

## programmed I/O와 DMA

### programmed I/O

CPU가 device register 또는 port를 통해 data를 직접 옮깁니다. 작은 control transfer에는 적합할 수 있지만 큰 data 이동에 CPU를 많이 사용합니다.

### DMA

device가 memory와 직접 data를 주고받습니다. CPU는 descriptor를 준비하고 completion을 처리합니다.

```text
CPU: buffer와 descriptor 준비
CPU: device에 제출
device: memory transfer
interrupt 또는 polling: completion 확인
CPU: 결과 공개와 cleanup
```

DMA가 CPU를 완전히 배제하는 것은 아닙니다. mapping, cache consistency, IOMMU, descriptor 관리, interrupt와 completion 처리가 필요합니다.

## DMA buffer는 완료 전까지 살아 있어야 합니다

장치가 physical page를 사용 중인데 process가 buffer를 해제하거나 COW·reclaim으로 page가 다른 용도로 바뀌면 data corruption이 생길 수 있습니다.

따라서 in-flight request의 page는 pin하거나 device-visible mapping의 수명을 보장해야 합니다.

```text
QUEUED
- 아직 DMA pin이 필요 없을 수 있음

IN_FLIGHT 또는 CANCEL_PENDING
- device가 접근할 수 있으므로 pinned

COMPLETED 또는 CANCELLED after completion
- device 접근 종료, unpin 가능

REAPED
- 사용자 결과 전달과 request object 회수 완료
```

`device_io.py`는 `pinned == in_flight set membership` 불변식을 검사합니다. `failure-fixtures/04-device-double-location.json`은 요청이 둘 이상의 queue 위치를 동시에 가지는 상태를 거부합니다.

## virtual address를 device에 그대로 줄 수 없습니다

device가 보는 주소는 CPU process virtual address와 다를 수 있습니다. 다음 계층이 존재할 수 있습니다.

```text
process virtual address
→ kernel page mapping
→ physical page
→ IOMMU를 통한 device-visible address
→ scatter-gather descriptor
```

연속된 user buffer가 physical memory에서는 여러 page에 흩어질 수 있습니다. scatter-gather list는 여러 segment를 하나의 요청으로 기술합니다.

IOMMU는 device가 접근할 수 있는 memory 범위를 제한하고 address translation을 제공할 수 있습니다. 정확한 architecture와 API는 컴퓨터 구조·플랫폼 문서의 범위이며, 운영체제 관점에서는 mapping 생성과 해제 수명이 request 상태와 일치해야 합니다.

## cache coherence와 DMA direction

CPU cache와 device가 memory를 함께 사용할 때 platform이 hardware coherent인지, software가 cache maintenance를 해야 하는지 확인해야 합니다.

```text
CPU → device
- CPU가 작성한 descriptor와 data가 device에 보여야 함

device → CPU
- device write가 끝난 뒤 CPU가 stale cache가 아닌 새 data를 봐야 함
```

memory barrier, DMA mapping API와 cache flush/invalidate 규칙은 architecture와 kernel API에 따라 다릅니다. 일반 pointer write와 compiler `volatile`만으로 해결할 수 없습니다.

## interrupt는 completion 후보를 알립니다

장치는 요청 하나마다 interrupt를 발생시키거나 여러 completion을 묶을 수 있습니다. interrupt handler의 일반적인 역할은 다음처럼 작게 유지됩니다.

```text
장치 상태 확인
interrupt 원인 acknowledge
완료 descriptor 수집 또는 표시
추가 처리를 worker·softirq·completion queue에 예약
```

handler에서 큰 복사, 복잡한 allocation과 장시간 lock 보유를 피합니다. 실제 이름과 계층은 운영체제마다 다르지만 “빠른 acknowledge”와 “지연 가능한 후속 처리”를 분리하는 원리는 공통입니다.

## interrupt coalescing과 polling

요청마다 interrupt를 만들면 고속 장치에서 CPU overhead가 커질 수 있습니다.

### interrupt coalescing

여러 completion을 묶거나 일정 시간 뒤 interrupt를 발생시킵니다.

```text
장점: interrupt rate 감소, throughput 향상
비용: 개별 요청 latency 증가 가능
```

### polling

CPU가 completion queue를 반복 확인합니다.

```text
장점: 높은 부하에서 interrupt 전환 비용 감소
비용: 유휴 상태에서도 CPU 사용 가능
```

hybrid 정책은 낮은 부하에서는 interrupt, 높은 부하에서는 제한된 polling을 사용할 수 있습니다. 선택은 throughput만이 아니라 tail latency, CPU budget과 power를 포함해야 합니다.

## completion과 wakeup

장치 완료 뒤 일반적인 경로는 다음과 같습니다.

```text
interrupt 또는 polling이 descriptor 완료 확인
→ request를 in-flight에서 제거
→ bytes transferred와 error 기록
→ buffer unpin 또는 DMA mapping 해제
→ completion queue에 결과 추가
→ 기다리는 thread wakeup
→ thread READY
→ scheduler 선택
→ result reap
```

wakeup은 즉시 사용자 코드 실행을 뜻하지 않습니다. scheduler가 CPU를 줄 때까지 READY에서 기다립니다.

completion을 먼저 알리고 결과 필드를 나중에 쓰면 waiter가 불완전한 결과를 볼 수 있습니다. 결과 상태 공개와 wakeup 사이의 ordering 계약이 필요합니다.

## partial completion과 오류

I/O 요청은 전체 길이보다 적게 완료될 수 있습니다.

```text
일부 byte 전송
장치 오류
medium error
connection reset
cancel과 completion 경쟁
```

request 결과에는 최소한 다음을 구분해야 합니다.

```text
요청 길이
실제 전송 길이
완료 상태
재시도 가능한 오류인지
부분 data가 유효한지
재시도 offset과 idempotency
```

read와 write의 상위 API가 short operation을 허용하는 경우 호출자가 반복해야 합니다. 장치 driver가 임의로 같은 write를 재시도하면 중복 side effect가 생기는 장치도 있으므로 operation 의미를 확인해야 합니다.

## cancellation은 device 실행을 되돌리지 않을 수 있습니다

### queued request 취소

hardware에 제출 전이라면 pending queue에서 제거하고 결과를 `CANCELLED`로 만들 수 있습니다.

### in-flight request 취소

장치가 이미 buffer를 사용 중이면 즉시 free할 수 없습니다.

```text
IN_FLIGHT → CANCEL_PENDING
→ 장치 abort를 시도하거나 completion을 기다림
→ interrupt에서 CANCELLED 결과 생성
→ unpin
→ owner가 reap
```

cancel 요청이 성공했다는 API 결과가 “device가 한 byte도 처리하지 않았습니다”를 뜻하는지 확인해야 합니다. 일부 operation은 side effect가 이미 일어났을 수 있습니다.

### completion과 cancel 경쟁

정상 completion이 먼저 state를 바꿨다면 cancel은 완료 결과를 보존해야 합니다. cancel이 먼저 `CANCEL_PENDING`으로 바꿨다면 late completion이 cleanup을 마치고 한 번만 cancellation 결과를 queue에 넣어야 합니다.

원자적 상태 전이와 queue 불변식을 함께 사용해 double completion을 막습니다.

## timeout도 cancellation과 같은 수명 문제를 가집니다

호출자가 timeout됐어도 장치 요청은 계속 in-flight일 수 있습니다. 다음 전략 중 하나를 선택합니다.

```text
호출자만 기다림 중단, request는 background에서 완료
request cancel 시도 후 실제 completion까지 buffer 유지
request를 detached owner로 이전
process 종료에서 kernel이 orphan result 정리
```

사용자 관점 timeout과 device 관점 completion을 같은 상태로 합치면 use-after-free와 결과 중복이 생깁니다.

## device reset과 hot removal

장치가 reset되거나 사라지면 in-flight request 전부에 결과를 만들어야 합니다.

```text
새 submission 중단
hardware queue 상태 격리
각 request를 실패 또는 retry 상태로 전환
DMA 중단과 mapping 안전성 확인
waiter wakeup
resource 회수
장치 재초기화 뒤 stale completion 거부
```

request id에 generation을 포함하면 reset 전 늦은 completion이 새 request로 오인되는 것을 막을 수 있습니다.

## I/O scheduler와 request merge

block I/O에서는 인접 요청을 병합하고 device 특성에 따라 순서를 바꿀 수 있습니다. 목표는 다음 사이의 균형입니다.

```text
throughput
seek 또는 command 효율
read latency
write batching
priority와 fairness
barrier·flush ordering
```

요청 재정렬은 durability barrier와 dependency를 넘어서는 안 됩니다. 특정 device 구현 세부보다 “정책이 correctness constraint 안에서 후보를 선택합니다”라는 원리가 중요합니다.

## 관찰값의 한계

application에서 read latency가 길다는 사실만으로 device가 느리다고 결론 내릴 수 없습니다.

```text
ready queue 대기
lock contention
page fault
filesystem lookup
page cache miss
I/O queue 대기
device service time
interrupt coalescing
completion worker 지연
```

각 계층의 timestamp와 queue depth가 필요합니다. 실제 추적 명령은 Unix 시스템 가이드에서 다룹니다.

## 연결 실습

다음 명령으로 reference test와 I/O fixture를 실행합니다.

```sh
make -C exercises/kernel-model reference-test
cd exercises/kernel-model
python3 reference/kernel-model.py io fixtures/io.json
```

그리고 다음 상황의 최종 state와 buffer pin 여부를 적습니다.

1. queued request를 즉시 cancel합니다.
2. in-flight request를 cancel한 뒤 interrupt가 도착합니다.
3. completion 뒤 owner가 아직 reap하지 않았습니다.
4. 같은 request에 interrupt completion이 두 번 옵니다.
5. queue depth를 넘겨 새 request를 제출합니다.
6. owner가 아닌 process가 결과를 reap하려 합니다.

## 완료 기준

- 여섯 요청 상황의 최종 state, queue 위치와 pinned 여부를 작성합니다.
- I/O fixture의 partial completion 4096 bytes가 owner에게 한 번 전달됨을 검사합니다.
- double completion과 queue-depth failure fixture가 선언한 이유로 거부됨을 확인합니다.

## 실패 조건

- cancel 반환을 장치 side effect와 DMA가 즉시 끝났다는 보장으로 해석합니다.
- in-flight request의 buffer를 completion 전에 unpin 또는 free합니다.
- interrupt 도착과 사용자 결과 회수를 하나의 상태로 합쳐 중복 완료를 허용합니다.

## 자기 설명

- queued, in-flight, completed와 reaped 상태를 구분할 수 있습니까?
- DMA buffer가 request completion 전까지 살아 있어야 하는 이유를 설명할 수 있습니까?
- cancel과 timeout이 실제 장치 side effect를 자동으로 되돌리지 않는 이유를 설명할 수 있습니까?
- interrupt handler와 지연 가능한 completion 작업을 분리할 수 있습니까?
- partial I/O, error와 retry의 소유권을 추적할 수 있습니까?
- queue depth, coalescing과 polling을 throughput뿐 아니라 latency와 CPU 비용으로 비교할 수 있습니까?
