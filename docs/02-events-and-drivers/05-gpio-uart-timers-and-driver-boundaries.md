# GPIO, UART, timer와 driver 경계

GPIO, UART와 timer는 입문 예제에서 몇 줄의 API로 보입니다. 실제 driver는 pin·clock·reset·interrupt·buffer·timeout과 error state를 하나의 공개 계약으로 묶습니다. application이 register와 board wiring을 직접 알기 시작하면 portability와 recovery 책임이 빠르게 무너집니다.

## 학습 목표

- application, device-class API, controller driver, board description과 hardware 책임을 구분합니다.
- initialization, ready, busy, error, suspended와 reset 상태를 driver state machine으로 표현합니다.
- polling, interrupt와 asynchronous API의 completion 계약을 비교합니다.
- GPIO, UART와 timer에서 흔한 경계 실패를 분류합니다.

## 계층을 먼저 나눕니다

```text
application policy
→ device-class API
→ device instance/driver state
→ controller register access
→ pin·clock·reset·interrupt resources
→ physical signal/external device
```

예를 들어 “UART로 packet을 보낸다”는 application operation입니다. driver는 baud, framing, FIFO, interrupt, DMA와 error flag를 다루지만 packet retry 정책까지 소유하지 않습니다.

## driver가 소유해야 하는 상태

```text
UNINITIALIZED
→ INITIALIZING
→ READY
   ├─ ACTIVE/BUSY
   ├─ SUSPENDED
   └─ ERROR
→ RESETTING
→ READY 또는 FAILED
```

상태마다 허용 operation을 정합니다.

| 상태 | 허용 예 | 거부 예 |
|---|---|---|
| uninitialized | capability query 일부 | transfer 시작 |
| ready | configure, transfer | 중복 init |
| busy | status, cancel | incompatible reconfigure |
| suspended | resume | register access |
| error | diagnostics, reset | 정상 transfer 반복 |

“함수가 존재한다”는 것과 현재 상태에서 호출 가능하다는 것은 다릅니다.

## GPIO는 pin number만으로 설명되지 않습니다

확인할 상태:

- pin controller와 alternate function
- input/output direction
- pull-up/down
- open-drain/open-source
- drive strength와 slew rate
- active-high/active-low 논리 의미
- debounce 또는 glitch filter
- sleep pin state
- external circuit가 강제하는 level

button이 active-low라면 driver 또는 board description에서 논리 값을 정규화할 수 있습니다. application이 board마다 inversion을 반복하지 않게 합니다.

GPIO interrupt에서는 edge와 현재 level을 구분합니다. edge event가 발생한 뒤 ISR이 읽을 때 level이 이미 바뀔 수 있습니다. debounce는 단순 delay가 아니라 시간과 상태 전이 문제입니다.

## UART는 byte stream과 framing error를 소유합니다

UART driver 경계:

- baud·data bits·parity·stop bits
- TX/RX FIFO
- polling, interrupt, asynchronous/DMA mode
- overrun, framing, parity, break
- partial transfer와 cancellation
- buffer lifetime

`write(buffer, n)`이 반환했다고 모든 bit가 wire로 나갔는지, FIFO에 들어갔는지, driver가 buffer를 더 사용하지 않는지 API마다 다릅니다.

```text
application buffer
→ driver accepted
→ FIFO/DMA
→ shift register
→ physical line
```

“전송 완료”의 기준을 명시합니다.

## timer는 clock source와 wraparound를 숨기지 못합니다

하드웨어 timer driver는 다음을 정합니다.

- input clock와 prescaler
- counter width와 direction
- one-shot/periodic/free-running
- compare/capture channel
- interrupt flag clear
- clock change와 sleep 동작
- read atomicity

application은 duration과 deadline 정책을 소유합니다. timer driver가 tick을 제공한다고 deadline miss가 자동으로 방지되지는 않습니다.

## 동기·비동기 API를 구분합니다

### synchronous

```text
call
→ operation 또는 wait
→ result 반환
```

호출 context에서 block할 수 있는지, timeout이 있는지 확인합니다.

### asynchronous

```text
submit(request, buffer, callback)
→ accepted
→ hardware progress
→ interrupt/DMA completion
→ callback/event
→ buffer 반환
```

반환값은 operation 성공이 아니라 **요청 접수 성공**일 수 있습니다. request identity, cancellation, timeout과 late completion 규칙이 필요합니다.

## initialization dependency를 숨기지 않습니다

GPIO/UART/timer가 ready하려면 다음 자원이 필요할 수 있습니다.

```text
power domain
→ clock
→ reset release
→ pin configuration
→ interrupt controller
→ driver state
```

dependency가 준비되지 않았을 때 driver는 early access를 명확히 거부하거나 initialization 순서를 고정해야 합니다. 우연히 default clock과 pin 상태에서 동작하는 코드는 board 변경에 약합니다.

## error recovery는 API의 일부입니다

- UART overrun 뒤 unread byte와 receiver state
- timer compare가 이미 지난 경우
- GPIO interrupt storm
- peripheral bus fault
- clock loss
- suspend 중 요청 도착

recovery 선택:

1. operation만 실패시키고 state를 ready로 유지합니다.
2. queue와 FIFO를 flush합니다.
3. peripheral block을 reset합니다.
4. dependency까지 재초기화합니다.
5. system safe state 또는 reset으로 escalate합니다.

어떤 error가 어느 단계까지 상태를 오염시키는지 설명해야 합니다.

## driver API review 질문

- hardware instance를 누가 독점합니까?
- configuration은 언제 변경할 수 있습니까?
- buffer ownership은 언제 이동하고 돌아옵니까?
- callback은 어떤 context에서 실행됩니까?
- timeout 뒤 late interrupt는 어떻게 처리합니까?
- cancel이 성공해도 hardware가 이미 byte를 보냈을 수 있습니까?
- suspend/resume 뒤 configuration을 누가 복원합니까?
- reset 뒤 external device state와 어떻게 수렴합니까?

## 실패와 검증

### 첫 실행만 성공

initialization이 peripheral status/FIFO를 완전히 clear하지 않거나 external device가 이전 state를 유지할 수 있습니다.

### logging을 추가하면 오류가 사라짐

UART/logging이 timing, interrupt priority, stack와 clock을 바꿨을 수 있습니다. timing-sensitive race의 신호입니다.

### callback 뒤 buffer 손상

callback이 “hardware completion”인지 “driver accepted”인지 잘못 이해했거나 cache/DMA ownership이 끝나지 않았을 수 있습니다.

## 실습 연결

- [interrupt event 경로](../../exercises/02-interrupt-event-path/README.md)
- [sensor driver 상태 기계](../../exercises/03-sensor-driver-state-machine/README.md)

## 직접 확인할 문제

1. UART API의 `write` 반환과 wire-level completion 사이에 가능한 상태를 나열해 보세요.
2. active-low button logic를 application마다 처리할 때 생기는 portability 문제를 적어 보세요.
3. timer compare deadline이 이미 지난 값으로 설정되면 driver가 선택할 수 있는 정책을 비교해 보세요.
4. driver reset이 external sensor까지 reset하지 못할 때 initialization은 어떤 상태를 처리해야 합니까?

## 이 장이 보장하지 않는 것

GPIO electrical limit, UART clock tolerance, timer capture precision과 pin mux 값은 board·SoC 문서를 확인합니다.
