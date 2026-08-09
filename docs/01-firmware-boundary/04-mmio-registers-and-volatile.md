# MMIO와 register 의미

Memory-Mapped I/O(MMIO)는 peripheral register를 CPU address space에 배치합니다. C pointer로 읽고 쓸 수 있어 보여도 일반 RAM과 같은 의미가 아닙니다. read 자체가 상태를 지우거나, `1`을 써야 bit가 clear되거나, 접근 폭과 순서가 hardware operation을 결정할 수 있습니다.

## 학습 목표

- register address, access width, field와 side effect를 datasheet에서 읽습니다.
- `volatile`이 보장하는 것과 보장하지 않는 것을 구분합니다.
- read-modify-write, W1C, read-clear, reserved bit와 alias register 문제를 설명합니다.
- compiler ordering, CPU ordering와 device completion을 서로 다른 층으로 구분합니다.

## register contract를 먼저 적습니다

한 register를 사용할 때 다음을 기록합니다.

```text
address/offset:
access width와 alignment:
reset value:
read semantic:
write semantic:
field별 access: RO/RW/WO/W1C/W0C/RC 등
reserved bit 규칙:
동시 hardware update:
operation completion 조건:
required barrier 또는 delay:
```

`RW`라는 표기만으로 충분하지 않습니다. register 전체가 RW여도 field마다 의미가 다를 수 있습니다.

## `volatile`은 필요한 도구지만 완전한 동기화가 아닙니다

C의 volatile access는 해당 abstract machine에서 read/write를 실제 access로 유지하는 데 사용됩니다. 하지만 다음을 자동으로 보장하지 않습니다.

- multi-thread atomicity
- ISR과 foreground 사이의 race-free protocol
- CPU memory ordering 전체
- cache coherence
- DMA buffer ownership
- peripheral operation completion
- register access width가 hardware 요구와 일치하는지

```c
volatile uint32_t *status = (volatile uint32_t *)STATUS_ADDR;
uint32_t value = *status;
```

이 코드는 read를 수행하게 할 수 있지만, read side effect와 이후 순서가 올바른지는 datasheet와 architecture rule이 결정합니다.

## read-modify-write가 위험한 이유

일반적인 C 표현:

```c
REG |= MASK;
```

실제로는 다음 세 단계입니다.

```text
read REG
→ OR MASK
→ write REG
```

사이에 hardware가 status bit를 바꾸거나 register에 W1C field가 있으면 의도하지 않은 bit를 clear할 수 있습니다.

예:

```text
bit 0: ENABLE, RW
bit 1: DONE, W1C
read result: DONE=1
REG |= ENABLE
write result: ENABLE=1, DONE=1
→ DONE이 clear됨
```

대안:

- 전용 SET/CLEAR alias register 사용
- writable field mask만 구성해 write
- W1C status와 configuration register 분리
- critical section 또는 driver-level serialization
- vendor가 제공하는 accessor 사용

## access semantic을 구분합니다

| 표기 | 의미 | 대표 위험 |
|---|---|---|
| RO | read-only | write가 fault 또는 undefined effect |
| WO | write-only | read-modify-write 불가 |
| RW | read/write | hardware 동시 update와 race |
| W1C | 1을 쓰면 clear | 읽은 값을 그대로 쓰면 여러 flag clear |
| W0C | 0을 쓰면 clear | mask 구성 오류 |
| RC | read하면 clear | debugger/watch window가 상태를 소비할 수 있음 |
| self-clearing | write 뒤 hardware가 bit clear | polling timeout과 clock dependency |
| latch-on-read | read sequence가 snapshot 생성 | register read 순서가 계약 |

datasheet 약어가 vendor마다 다를 수 있으므로 legend를 확인합니다.

## reserved bit는 원래 값을 보존한다고 끝나지 않습니다

문서가 “reserved, write zero”라고 하면 반드시 0을 씁니다. “preserve”라고 하면 documented read-modify-write 방식이 필요할 수 있습니다. 미래 silicon revision에서 의미가 생길 수 있으므로 임의의 값이나 struct 전체 copy를 쓰지 않습니다.

C bit-field struct를 register layout에 바로 대응하면 다음 문제가 있습니다.

- implementation-defined bit-field 배치
- endianness와 access width
- compiler가 여러 access를 생성할 가능성
- reserved bit와 side effect 제어 어려움

mask와 shift 또는 검증된 vendor header를 우선합니다.

## 접근 폭과 alignment가 operation의 일부입니다

32-bit register에 byte write를 허용하지 않거나, 64-bit value를 두 번 읽는 사이 hardware가 갱신될 수 있습니다.

multiword counter 읽기 예:

```text
high1 = HIGH
low   = LOW
high2 = HIGH
if high1 != high2: retry
```

또는 hardware가 latch register를 제공할 수 있습니다. 단순히 `uint64_t *` cast로 해결하지 않습니다.

## ordering은 세 층으로 나눕니다

### compiler ordering

compiler가 access를 합치거나 재배치하지 않도록 language와 accessor contract를 사용합니다.

### CPU/bus ordering

architecture barrier가 이전 memory access가 다음 access보다 먼저 관찰되도록 요구될 수 있습니다.

### device completion

write가 interconnect를 통과했다고 peripheral operation이 완료된 것은 아닙니다. status polling, interrupt 또는 explicit acknowledgement가 필요할 수 있습니다.

```text
write START
→ bus accepted
→ device busy
→ operation completes
→ status/interrupt
```

barrier를 넣는 것과 operation completion을 기다리는 것은 같은 일이 아닙니다.

## interrupt와 foreground가 register를 공유할 때

다음 중 하나를 선택합니다.

- 한 context만 register를 소유하고 다른 context는 command/event를 전달합니다.
- atomic SET/CLEAR register를 사용합니다.
- 짧은 interrupt masking으로 read-modify-write를 보호합니다.
- driver lock을 사용하되 ISR에서 blocking lock을 사용하지 않습니다.

register access를 여러 모듈에 흩뜨리면 serialization과 side effect를 추적하기 어렵습니다. raw register access는 driver 내부 한 경계에 모읍니다.

## debugger도 register state를 바꿀 수 있습니다

peripheral view가 주기적으로 RC register를 읽거나, core halt가 timer·bus timeout을 멈추지 않을 수 있습니다. debugger에서 보이는 값이 application이 읽을 값과 같다고 가정하지 않습니다.

관찰 방법:

- side-effect-free mirror/status register 사용
- 한번만 snapshot하고 RAM log에 복사
- logic analyzer 또는 bus trace
- debugger의 peripheral auto-refresh 비활성화

## 안전한 accessor의 형태

```c
uint32_t device_status_snapshot(void);
int device_start(const struct request *req);
void device_ack_events(uint32_t event_mask);
```

application에 raw register pointer를 노출하지 않습니다. driver API는 다음을 함께 고정합니다.

- 유효한 state에서 호출 가능한 operation
- buffer lifetime
- completion 방법
- timeout과 error
- 재시도 가능 여부
- reset/recovery 방법

## 실패와 검증

### 간헐적으로 interrupt가 사라짐

W1C register에 read-modify-write를 수행했거나, flag clear와 event capture 순서가 잘못됐을 수 있습니다.

### polling loop가 끝나지 않음

- clock이 꺼짐
- START write가 잘못된 width
- status가 RC인데 debugger가 소비
- timeout이 없음
- error flag를 무시

### optimization level에 따라 동작 변화

`volatile` 누락, undefined behavior, memory ordering 또는 race를 의심합니다. optimization을 끄는 것은 원인 수정이 아닙니다.

## 실습 연결

[interrupt event 경로](../../exercises/02-interrupt-event-path/README.md)에서 W1C event flag, ISR snapshot과 deferred processing 계약을 설계합니다.

## 직접 확인할 문제

1. W1C와 RW field가 같은 register에 있을 때 `REG |= ENABLE`이 위험한 trace를 작성해 보세요.
2. `volatile` counter를 ISR과 main이 동시에 증가시키면 lost update가 생길 수 있는 이유를 설명해 보세요.
3. memory barrier 뒤에도 peripheral completion을 별도로 기다려야 하는 예를 적어 보세요.
4. debugger watch window가 RC register를 읽을 때 어떤 관측 오류가 생깁니까?

## 이 장이 보장하지 않는 것

구체적인 barrier instruction, bus ordering, register access width와 errata는 target architecture·SoC 문서를 확인합니다. 이 장의 pseudocode를 실제 address에 그대로 사용하지 않습니다.
