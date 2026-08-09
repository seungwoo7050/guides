# superloop, 상태 기계와 event queue

작은 firmware는 RTOS 없이 하나의 `while (1)` loop에서 충분히 동작할 수 있습니다. 문제는 “thread가 없는 것”이 아니라 기능을 blocking call과 암묵적인 global state로 연결하는 것입니다. superloop를 명시적인 상태 기계와 bounded event queue로 만들면 실행 순서, latency와 recovery를 검증할 수 있습니다.

## 학습 목표

- run-to-completion event loop와 blocking control flow를 구분합니다.
- 기능을 상태, event, guard, action으로 표현합니다.
- periodic release, debounce, queue overflow와 backpressure를 설계합니다.
- ISR·driver completion과 foreground state machine의 ownership을 연결합니다.
- RTOS를 도입해야 하는 조건과 도입하지 않아도 되는 조건을 설명합니다.

## 나쁜 superloop

```c
while (1) {
    read_sensor_blocking();
    wait_ms(1000);
    send_packet_blocking();
    if (button_pressed()) {
        do_long_operation();
    }
}
```

한 기능의 wait가 다른 기능의 progress를 막습니다. timeout, cancel, power state와 watchdog 조건도 숨습니다.

## run-to-completion loop

```text
interrupt/driver가 event 생성
→ queue 또는 flag에 기록
→ main loop가 한 event 선택
→ bounded handler가 상태 전이
→ 제어를 loop에 반환
```

handler는 완료될 때까지 다른 foreground handler와 interleave되지 않으므로 shared state reasoning이 단순합니다. 대신 handler가 오래 실행되면 전체 responsiveness가 나빠집니다.

## 상태 기계의 요소

```text
state
input event
optional guard
transition action
next state
output event/command
```

예시 sensor service:

```text
IDLE + SAMPLE_DUE
→ start_conversion
→ WAITING

WAITING + DEVICE_READY
→ read_result
→ IDLE

WAITING + TIMEOUT
→ reset_device
→ RECOVERING
```

함수 이름보다 valid transition과 failure 뒤 state가 중요합니다.

## event type을 구분합니다

- **edge event**: 발생 횟수와 순서가 중요합니다.
- **level state**: 최신 값만 중요할 수 있습니다.
- **command**: 반드시 accept/reject 결과가 필요합니다.
- **completion**: request identity와 generation이 필요할 수 있습니다.
- **timer release**: missed instance policy가 필요합니다.

모든 event를 boolean flag로 표현하면 여러 발생을 잃고, 모든 level을 queue에 넣으면 오래된 상태가 쌓입니다.

## queue는 무한하지 않습니다

queue capacity는 resource budget이자 product policy입니다.

```text
arrival rate > service rate
→ depth 증가
→ full
→ drop/block/coalesce/escalate
```

superloop에서는 producer가 ISR일 수 있으므로 block할 수 없습니다.

정책 예:

- button edge: bounded count와 overflow metric
- temperature state: latest value overwrite
- safety alarm: dedicated slot 또는 fault escalation
- telemetry sample: oldest drop
- actuator command: reject with busy/error

queue depth를 늘리는 것은 지속적인 overload 해결이 아닙니다.

## periodic work를 deadline으로 release합니다

```text
now >= next_sample
→ SAMPLE_DUE event
→ next_sample += period
```

handler 안에서 delay하지 않습니다. missed period가 여러 개면 catch-up 또는 skip policy를 적용합니다. time comparison은 wrap-safe 방식으로 구현합니다.

## debounce도 상태 기계입니다

```text
STABLE_LOW
→ edge high
→ VERIFY_HIGH(deadline)
→ deadline에서 pin high면 STABLE_HIGH + PRESS event
→ 다시 low면 STABLE_LOW
```

ISR에서 긴 delay를 두지 않습니다. hardware filter가 있어도 board와 configured duration을 확인합니다.

## asynchronous driver와 request generation

```text
state IDLE
→ submit request generation 17
→ WAITING(17)

completion generation 16
→ stale, discard

completion generation 17
→ consume, IDLE
```

timeout·cancel 뒤 이전 completion이 오는 상황을 state machine에 포함합니다.

## fairness와 work budget

한 loop iteration에서 특정 source를 모두 drain하면 다른 기능이 굶을 수 있습니다.

대안:

- source별 최대 처리 개수
- priority queue 또는 fixed priority scan
- round-robin
- urgent event 전용 slot
- processing time budget 뒤 반환

priority가 높은 event도 무한히 들어오면 low-priority progress를 막습니다. overload policy가 필요합니다.

## sleep와 event loop

```text
모든 state가 idle인지 확인
→ next deadline 계산
→ interrupt race를 막는 방식으로 sleep 진입
→ wake source 발생
→ event snapshot
→ loop 재개
```

“queue가 비었다 확인한 뒤 interrupt가 오고, 그 다음 sleep”하면 event가 있지만 CPU가 잠들 수 있습니다. architecture/RTOS가 제공하는 atomic idle primitive를 사용합니다.

## watchdog와 progress

main loop가 돌 때마다 watchdog를 feed하면 특정 service가 stuck돼도 loop가 계속 도는 경우를 놓칠 수 있습니다.

더 나은 조건:

- critical state machine별 progress generation
- deadline 내 completion
- queue가 지속적으로 과부하가 아닌지
- storage/update critical section이 안전한지

watchdog feed는 이 조건을 모은 supervisor가 결정합니다.

## 언제 RTOS가 필요한가

RTOS가 유리한 조건:

- 서로 다른 blocking interface를 격리해야 함
- priority와 preemption이 필요함
- 여러 independent stack이 reasoning을 단순하게 함
- vendor/network stack이 task model을 요구함
- CPU sleep와 timer/service integration이 필요함

RTOS를 추가해도 상태 기계, timeout, queue capacity와 ownership 문제는 사라지지 않습니다. task와 mutex 형태로 이동할 뿐입니다.

## 실패와 검증

- event burst에서 queue overflow
- long handler로 deadline miss
- timeout과 completion 동시 발생
- sleep 진입 race
- counter wrap
- recovery 중 새 command
- repeated error event로 starvation

host model에서 event sequence를 고정해 state와 output을 검사할 수 있습니다. 실제 timing은 target에서 별도로 측정합니다.

## 실습 연결

- [interrupt event 경로](../../exercises/02-interrupt-event-path/README.md)
- [deadline과 priority 검토](../../exercises/04-deadline-and-priority-review/README.md)
- [현장 센서 노드 capstone](../../capstone/field-sensor-node/README.md)

## 직접 확인할 문제

1. edge event와 level state를 같은 boolean flag로 표현했을 때 잃는 정보를 비교해 보세요.
2. queue depth를 늘려도 overload가 해결되지 않는 이유를 arrival/service rate로 설명해 보세요.
3. queue empty 확인과 sleep 사이의 race를 trace로 작성해 보세요.
4. watchdog를 loop iteration마다 feed하는 방식이 특정 service hang을 놓치는 예를 적어 보세요.

## 이 장이 보장하지 않는 것

superloop가 RTOS보다 항상 단순하거나 빠르다고 주장하지 않습니다. 기능 수, blocking dependency, latency와 isolation 요구를 기준으로 선택합니다.
