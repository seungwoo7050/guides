# clock, timeout, deadline과 wraparound

임베디드 시스템의 시간은 하나가 아닙니다. CPU cycle counter, peripheral timer, RTOS tick, low-power RTC와 external time source가 서로 다른 frequency, precision, drift와 power-state behavior를 가집니다. “10ms마다 실행한다”는 요구는 어떤 clock에서 언제부터 언제까지를 재는지 정하지 않으면 검증할 수 없습니다.

## 학습 목표

- clock source, counter, tick, duration, timeout, deadline, latency와 jitter를 구분합니다.
- wrapping counter에서 안전한 elapsed-time 비교를 설계합니다.
- periodic task의 drift와 release policy를 설명합니다.
- power·frequency transition과 timekeeping의 경계를 검토합니다.
- 평균과 worst-case 관찰을 분리합니다.

## 시간 용어를 구분합니다

| 용어 | 질문 |
|---|---|
| clock source | 어떤 oscillator나 counter가 시간을 만듭니까? |
| frequency | 초당 몇 cycle입니까? 실제 오차는 얼마입니까? |
| resolution | 구분할 수 있는 최소 단위는 무엇입니까? |
| precision | 반복 측정이 얼마나 세밀합니까? |
| accuracy | 실제 기준 시간과 얼마나 가깝습니까? |
| monotonic time | reset이나 wrap 전까지 뒤로 가지 않습니까? |
| wall time | 달력·UTC와 연결됩니까? |
| duration | 두 시점 사이의 길이는 얼마입니까? |
| timeout | 기다림을 언제 포기합니까? |
| deadline | 결과가 언제까지 완료돼야 합니까? |
| latency | 사건에서 응답까지 얼마나 걸립니까? |
| jitter | 반복 latency 또는 release time이 얼마나 변합니까? |

RTOS tick 1ms라고 실제 event가 정확히 1ms 간격으로 실행된다는 뜻은 아닙니다. tick resolution, scheduler latency, interrupt mask와 clock drift가 모두 영향을 줍니다.

## time source를 선택할 때 상태를 기록합니다

```text
source:
frequency와 tolerance:
width:
wrap period:
read cost와 atomicity:
power state에서 계속 동작하는가:
clock change의 영향:
reset 뒤 유지되는가:
다른 core/device와 공유되는가:
```

CPU cycle counter는 고해상도지만 frequency scaling이나 sleep에서 멈출 수 있습니다. RTC는 저전력에서 계속 동작하지만 resolution과 drift가 다를 수 있습니다.

## counter에서 duration을 계산합니다

unsigned wrapping counter에서 `now - start`는 차이가 counter range 절반보다 작다는 전제에서 wrap을 자연스럽게 처리할 수 있습니다.

```c
uint32_t elapsed = now - start;
if (elapsed >= timeout_ticks) {
    /* timed out */
}
```

위 방식은 다음 조건이 필요합니다.

- 같은 unsigned width를 사용합니다.
- 비교 대상 duration이 표현 가능한 안전 범위 안에 있습니다.
- `start + timeout`의 단순 대소 비교를 사용하지 않습니다.
- counter frequency가 구간 중 바뀌지 않거나 conversion을 보정합니다.

wall clock처럼 뒤로 갈 수 있는 값에 같은 방식을 쓰지 않습니다.

## absolute deadline과 relative delay를 구분합니다

### 상대 delay

```text
작업 완료
→ 100ms sleep
→ 다음 작업
```

작업 시간이 period에 누적돼 drift가 생깁니다.

### 절대 release schedule

```text
next_release = initial + n × period
작업 완료
→ next_release까지 wait
```

작업 시간이 period보다 짧다면 장기 drift를 줄일 수 있습니다. deadline을 놓쳤을 때 정책이 필요합니다.

- missed instance를 건너뜁니다.
- 즉시 한 번 실행하고 다음 절대 release로 돌아갑니다.
- backlog를 모두 처리합니다.
- fault/degraded mode로 전환합니다.

sensor sampling, control loop와 telemetry에 같은 정책을 사용할 필요는 없습니다.

## deadline에는 execution budget이 필요합니다

```text
end-to-end response
= interrupt latency
+ ISR service
+ queue wait
+ task execution
+ bus/DMA wait
+ downstream completion
```

deadline `D`만 적지 말고 각 구간의 budget과 measurement point를 정합니다.

```text
period P = 10ms
release jitter J <= 100us
execution budget C <= 1.5ms
end-to-end deadline D = 5ms
queue depth = 2
miss policy = newest sample replaces pending sample
```

이 수치는 실제 target과 load에서 검증해야 합니다.

## WCET와 관찰된 최댓값을 구분합니다

benchmark에서 가장 큰 값은 관찰된 maximum입니다. Worst-Case Execution Time(WCET)을 주장하려면 가능한 path, cache·interrupt·bus contention과 measurement/proof method를 정의해야 합니다.

실무 입문 단계에서는 다음을 기록합니다.

- 입력과 configuration
- compiler optimization
- target clock
- interrupt load
- warm/cold cache 또는 flash wait state
- sample count와 분포
- 관찰된 min/median/p95/p99/max
- 검사하지 않은 path

“평균 200us”로 500us deadline을 보장하지 않습니다.

## timeout은 cancellation이 아닙니다

```text
operation 시작
→ caller timeout
→ caller는 실패로 진행
→ hardware operation은 계속 진행
→ 늦은 completion
```

시간이 지났다는 사실과 resource가 정리됐다는 사실을 분리합니다. timeout path는 abort, drain, generation change와 buffer ownership 반환을 수행해야 할 수 있습니다.

## timer interrupt와 callback context

timer expiry callback이 ISR context에서 실행되는지 RTOS thread에서 실행되는지 확인합니다. ISR context이면 짧고 non-blocking이어야 합니다. 긴 작업은 workqueue나 task로 넘깁니다.

여러 timer callback이 같은 system workqueue를 공유하면 하나의 긴 callback이 다른 deadline을 지연할 수 있습니다.

## clock change와 power state

frequency scaling 또는 oscillator switch에서 다음이 바뀔 수 있습니다.

- cycle-to-time conversion
- UART/SPI baud
- timer compare value
- RTOS tick compensation
- busy-wait duration
- peripheral timeout

RTOS가 monotonic uptime을 보정해도 raw peripheral timer는 보정되지 않을 수 있습니다. sleep에서 멈추는 counter와 계속 가는 RTC의 차이를 wakeup path에서 수렴시킵니다.

## 여러 clock domain 사이의 timestamp

sensor, radio와 CPU가 각자 counter를 사용하면 timestamp를 단순 비교할 수 없습니다.

필요한 것:

- clock domain 식별자
- frequency와 epoch
- synchronization sample
- conversion error bound
- reset/wrap generation

분산 clock synchronization 전체를 다루지는 않지만, 같은 숫자 단위가 같은 시간축을 뜻하지 않는다는 점을 고정합니다.

## 실패와 검증

### 약 49일 뒤 timeout failure

32-bit millisecond counter를 signed 또는 absolute timestamp로 잘못 비교했을 수 있습니다.

### sleep 뒤 대량 event 실행

relative/absolute schedule과 missed-release policy가 정의되지 않았을 수 있습니다.

### debug build만 deadline 통과

optimization, logging, debugger halt가 timing을 바꿉니다. release configuration과 실제 load를 사용합니다.

### clock 변경 뒤 UART와 timeout 모두 실패

clock tree 변경을 peripheral divisor와 time conversion에 반영하지 않았을 수 있습니다.

## 실습 연결

[deadline과 priority 검토](../../exercises/04-deadline-and-priority-review/README.md)에서 task period, execution budget, priority, queue와 miss policy를 설계합니다.

## 직접 확인할 문제

1. 16-bit 1kHz counter의 wrap period와 안전하게 직접 비교할 수 있는 duration 범위를 계산해 보세요.
2. “작업 후 100ms sleep”이 장기적으로 drift하는 trace를 작성해 보세요.
3. timeout 뒤 hardware operation이 계속 진행될 때 buffer 재사용 문제를 설명해 보세요.
4. 평균 latency와 deadline 보장의 차이를 evidence 관점에서 적어 보세요.

## 이 장이 보장하지 않는 것

특정 RTOS scheduler가 hard real-time deadline을 보장한다고 주장하지 않습니다. safety-critical WCET, schedulability proof와 clock calibration은 별도 전문 과정과 도구가 필요합니다.
