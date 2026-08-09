# power, clock, sleep와 wakeup

저전력 동작은 `sleep()` 한 줄이 아닙니다. CPU, memory, clock, peripheral와 external device가 서로 다른 power domain과 wakeup 조건을 가집니다. 진입 중 event가 도착하거나 wakeup 뒤 clock·pin·driver state가 복원되지 않으면 간헐 failure가 생깁니다.

## 학습 목표

- system power state와 device runtime power state를 구분합니다.
- sleep 진입 전 quiesce와 wakeup 뒤 restore 순서를 설계합니다.
- wake source, pending interrupt와 event loss race를 설명합니다.
- clock source 전환이 timer·serial·deadline에 미치는 영향을 추적합니다.
- energy 측정을 state와 workload에 연결합니다.

## power state inventory

```text
CPU: active / idle / sleep / deep sleep / off
RAM: active / retention / lost
flash: active / low-power / inaccessible
peripheral: active / suspended / off
clock: high-speed / low-speed / stopped
external device: own active/sleep/reset state
```

이름은 platform마다 다릅니다. state 이름보다 다음을 기록합니다.

- 어떤 domain이 꺼집니까?
- 어떤 memory가 유지됩니까?
- wake latency와 source는 무엇입니까?
- resume는 reset path입니까, instruction resume입니까?
- clock frequency와 timer continuity는 어떻게 됩니까?

## system PM과 device PM

- **system power management**는 CPU와 전체 platform state를 선택합니다.
- **device runtime PM**은 사용하지 않는 peripheral을 독립적으로 suspend/resume합니다.

application이 UART를 사용 중인데 system이 deep sleep을 선택하거나, usage count가 남아 device가 suspend되지 않으면 power와 correctness가 모두 깨질 수 있습니다.

## sleep 진입 protocol

```text
새 작업 수락 제한
→ active transaction drain/cancel
→ persistent state 필요 시 commit
→ device별 suspend
→ pin/wakeup source 설정
→ pending event 재확인
→ atomic idle/sleep instruction
```

queue empty 확인과 sleep instruction 사이에 interrupt가 발생하는 race를 막아야 합니다. RTOS 또는 architecture가 제공하는 idle primitive를 사용합니다.

## wakeup protocol

```text
wakeup source latch
→ core resumes/reset
→ required clock 안정화
→ power domain restore
→ pin/device resume
→ elapsed time와 expired deadline 계산
→ wake event 처리
→ normal policy 복귀
```

wakeup source를 너무 일찍 clear하면 원인을 잃고, 너무 늦게 clear하면 재진입할 수 있습니다.

## external device state

MCU가 sleep해도 sensor, radio와 external flash가 계속 active일 수 있습니다.

- sleep command와 response 확인
- interrupt pin이 wake source인지
- power rail이 꺼지는지
- wake 뒤 reset 또는 context restore가 필요한지
- bus line이 back-powering을 만들지

electrical behavior는 schematic와 datasheet가 소유합니다. firmware는 device state machine과 timeout을 소유합니다.

## clock source transition

고속 oscillator를 끄고 저속 clock으로 이동할 때:

- CPU/peripheral frequency 변경
- UART/SPI baud divisor 변경
- busy wait와 cycle counter 의미 변경
- timer source continuity
- PLL lock timeout
- flash wait state

clock switch 실패에 fallback이 필요합니다. “clock ready flag가 올 때까지 무한 대기”하면 watchdog reset만 반복할 수 있습니다.

## elapsed time와 deadline 복구

sleep에서 system tick이 멈추면 RTC를 사용해 elapsed time을 계산할 수 있습니다.

```text
before_sleep_monotonic
before_sleep_rtc
→ sleep
→ after_wake_rtc
→ elapsed estimate
→ timer queue 보정
```

RTC wrap, drift와 reset generation을 처리합니다. wall time 동기화가 바뀌어도 monotonic deadline을 뒤로 돌리지 않습니다.

## pin state와 leakage

pin configuration은 기능뿐 아니라 power에 영향을 줍니다.

- floating input
- pull-up/down과 external resistor 충돌
- output level로 external device에 역전류
- analog input leakage
- debug pin 활성화
- wake pin polarity

software state와 board electrical state를 함께 검토합니다.

## energy budget

평균 current만 적지 않고 state residence를 계산합니다.

```text
energy per cycle
= active current × active time
+ sleep current × sleep time
+ radio/sensor transaction energy
+ transition overhead
```

측정 조건:

- supply voltage
- board revision와 regulator
- debugger 연결 여부
- LED·USB·serial bridge
- firmware build/config
- workload와 radio environment
- measurement bandwidth/sample rate

개발 board 전체 소비를 MCU data-sheet sleep current와 직접 비교하지 않습니다.

## failure와 검증

- sleep entry 직전 event injection
- wake source 여러 개 동시 발생
- clock startup failure
- device suspend 중 request
- DMA/flash active 상태에서 deep sleep 요청
- long sleep 뒤 counter wrap
- external device가 sleep command NACK
- wake 뒤 first transaction failure

## 실습 연결

[현장 센서 노드 capstone](../../capstone/field-sensor-node/README.md)은 sleep eligibility, wake source와 first-operation-after-wake 검증을 요구합니다.

## 직접 확인할 문제

1. queue empty 확인 뒤 interrupt가 오고 CPU가 sleep에 들어가는 race를 설명해 보세요.
2. CPU가 sleep해도 external sensor가 power를 소비할 수 있는 경로를 적어 보세요.
3. frequency scaling 뒤 cycle-based timeout이 달라질 수 있는 이유를 설명해 보세요.
4. 개발 board 전류와 MCU datasheet current를 직접 비교하면 안 되는 이유를 나열해 보세요.

## 이 장이 보장하지 않는 것

board-level power integrity, battery chemistry, regulator efficiency와 EMC를 다루지 않습니다. 실제 제품 energy budget은 hardware 측정이 필요합니다.
