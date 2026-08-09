# 실습 2 — interrupt event 경로

## 문제

interrupt handler에서 모든 일을 끝내면 latency와 재진입 위험이 커지고, 아무 일도 하지 않고 signal만 넘기면 status clear, data lifetime과 overflow가 불명확해집니다. 이 실습은 **hardware event → ISR → bounded queue → worker → application state**의 전체 경로를 설계합니다.

## 학습 목표

- pending/status/acknowledge와 application event를 구분합니다.
- ISR의 bounded work와 deferred work를 나눕니다.
- event record의 lifetime, generation와 overflow 정책을 정합니다.
- disable/cancel 뒤 stale interrupt를 처리합니다.
- latency와 loss를 측정 가능한 timestamp·counter로 표현합니다.

## 기본 입력

[`examples/interrupt-event-model`](../../examples/interrupt-event-model/README.md)을 먼저 실행합니다. 그 모델을 수정하거나 host C/RTOS implementation으로 옮깁니다.

## 요구사항

가상의 data-ready peripheral가 다음 상태를 가집니다.

```text
DISABLED
ARMED(generation)
PENDING(status, sample)
QUEUED(event)
PROCESSING(event)
```

입력 사건:

- `ENABLE`
- `RAISE(sample)`
- `ISR`
- `WORK`
- `DISABLE`
- `RESET`

queue capacity는 유한합니다.

## 설계해야 할 계약

### status와 acknowledge

- edge/level-like 동작을 어떤 모델로 선택했는지
- status read와 clear 순서
- 여러 status bit 동시 발생
- spurious interrupt
- clear 뒤 새 event가 들어오는 race

### event record

최소 필드:

```text
generation
sequence
timestamp
raw_status
sample 또는 buffer handle
```

ISR가 stack local data의 pointer를 queue에 넣지 않도록 lifetime을 설명합니다.

### overflow

다음 중 하나를 선택하고 근거를 적습니다.

- newest drop
- oldest overwrite
- hardware backpressure/disable
- coalesce
- fault/safe state

어떤 정책을 선택해도 `dropped` 또는 `overrun` evidence가 필요합니다.

### disable/cancel

```text
ARMED generation 7
→ event pending
→ DISABLE
→ generation 8에 다시 enable
→ 오래된 ISR/completion 도착
```

이전 generation이 새 session state를 바꾸지 못하도록 설계합니다.

## 필수 trace

1. 정상 event 하나
2. ISR 전 event 두 개
3. queue full
4. spurious ISR
5. disable 직전 pending
6. re-enable 뒤 stale generation
7. worker가 느린 동안 event burst
8. reset 뒤 queue와 counter 정책

각 trace에 `state before`, input, `state after`, emitted evidence를 기록합니다.

## 선택 구현

### host/model

- Python 또는 C
- virtual clock
- deterministic event list
- final JSON 또는 table output

### RTOS

- ISR-safe queue/API
- worker task 또는 work queue
- bounded allocation
- interrupt lock/atomic boundary
- instrumentation build

### 실제 보드

- GPIO/timer 또는 sensor data-ready interrupt
- GPIO pulse로 ISR entry/exit와 worker 표시
- logic analyzer로 latency 측정
- burst/overflow stimulus

## 필수 결과물

```text
workspace/
├── design.md
├── state-machine.md
├── fixtures/
├── implementation/
├── evidence/
│   └── traces/
└── report.md
```

## 완료 조건

- ISR의 최대 작업이 input 크기와 무관하게 bounded입니다.
- pending status를 잃거나 무한히 재진입하지 않습니다.
- queue가 가득 찼을 때 정책과 counter가 결정적입니다.
- event record의 lifetime과 owner가 명확합니다.
- stale generation은 application state를 바꾸지 않습니다.
- worker 처리 실패가 interrupt acknowledgement를 되돌리지 않는다는 점을 설명합니다.
- target 측정이 있다면 clock, probe와 instrumentation 조건을 함께 기록합니다.

## 잘못된 완료

- ISR에서 blocking I/O, 동적 할당 또는 긴 formatting 수행
- `volatile bool event` 하나로 여러 event를 표현하면서 loss를 기록하지 않음
- queue 무한 확장
- disable만 하고 pending status/IRQ line을 정리하지 않음
- test에서 `sleep`과 우연한 scheduling에 의존

## 검토 질문

1. status clear가 늦으면 interrupt storm이 생기는 경로를 설명해 보세요.
2. `event_pending = true`가 count를 보존하지 못하는 경우는 언제입니까?
3. queue overflow를 application fault로 올릴 조건과 단순 drop으로 처리할 조건을 비교해 보세요.
4. GPIO pulse 측정이 ISR-to-worker latency를 어떤 오차로 관찰합니까?
