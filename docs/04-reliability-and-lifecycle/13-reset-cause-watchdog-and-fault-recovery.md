# reset cause, watchdog와 fault recovery

watchdog가 system을 reset하면 멈춘 장치는 다시 움직일 수 있습니다. 그러나 원인을 잃고 같은 상태로 재진입하면 boot loop가 됩니다. 신뢰성 있는 firmware는 **failure detection, evidence capture, safe action, reset, boot-time diagnosis와 recovery**를 하나의 경로로 설계합니다.

## 학습 목표

- reset cause와 application crash record를 구분합니다.
- watchdog feed 조건을 실제 progress와 연결합니다.
- fault handler에서 보존할 최소 evidence와 안전 제약을 정합니다.
- boot loop, repeated reset와 degraded mode를 설계합니다.
- external device와 actuator의 safe state를 recovery path에 포함합니다.

## reset cause는 출발점입니다

대표 원인:

- power-on/brownout
- external reset pin
- software-requested reset
- watchdog timeout
- lockup/fault escalation
- security violation
- wakeup-related reset

SoC가 지원하는 flag가 다르고 여러 flag가 동시에 남을 수 있습니다. 읽은 뒤 언제 clear되는지 확인합니다.

reset cause만으로 root cause를 알 수 없습니다. “watchdog reset”은 누가 progress를 잃었는지 설명하지 않습니다.

## crash evidence

최소 record 후보:

```text
magic/version/length
boot generation
reset/fault reason
program counter와 return address
stack pointer와 selected registers
fault status registers
current task/ISR identity
last progress markers
active request generations
queue/pool usage
firmware build ID
CRC 또는 integrity field
```

제한:

- fault stack이 손상됐을 수 있습니다.
- flash write는 fault context에서 안전하지 않을 수 있습니다.
- logging과 allocation을 호출하면 재귀 fault가 날 수 있습니다.
- evidence storage 자체가 power loss로 torn될 수 있습니다.

fault handler는 bounded하고 allocation-free해야 하며, retained RAM에 최소 record를 쓰고 다음 boot에서 persistent storage로 옮길 수 있습니다.

## watchdog를 timer처럼 feed하지 않습니다

나쁜 방식:

```text
주기 timer ISR이 무조건 watchdog feed
```

scheduler, main task와 critical service가 모두 멈춰도 timer ISR만 살아 있으면 reset되지 않을 수 있습니다.

더 나은 방식:

```text
각 critical service가 progress generation 갱신
→ supervisor가 deadline와 상태 검사
→ 모든 required condition이 만족될 때만 hardware watchdog feed
```

progress condition 예:

- sensor acquisition generation이 period 내 증가
- storage writer가 bounded backlog 유지
- communication task가 required heartbeat 갱신
- update critical section이 허용 상태
- scheduler latency가 threshold 내

## windowed watchdog

일부 watchdog는 너무 늦은 feed뿐 아니라 너무 이른 feed도 fault로 처리합니다. 이는 runaway loop가 빠르게 feed하는 상황을 찾을 수 있습니다. 실제 window와 clock source, debug freeze 여부를 확인합니다.

## watchdog timeout 선택

```text
timeout
> expected worst critical operation + scheduling/interrupt margin
< 제품이 허용하는 최대 unsafe duration
```

flash erase, update와 low-power state처럼 긴 operation을 고려합니다. timeout을 늘리기만 하면 fault detection이 늦어집니다. operation을 chunk하거나 watchdog-aware protocol을 설계할 수 있습니다.

## safe state는 reset 전후 모두 필요합니다

actuator, motor, heater와 power switch는 MCU reset 동안 pin이 input/default로 바뀔 수 있습니다.

- hardware pull과 external interlock
- reset default pin state
- watchdog reset이 peripheral output을 어떻게 바꾸는지
- startup에서 safe output을 언제 설정하는지
- external device가 이전 command를 계속 수행하는지

software만으로 안전을 보장할 수 없는 영역을 board/hardware contract로 명시합니다.

## boot-time recovery

```text
read reset cause와 retained crash record
→ record integrity 확인
→ boot counter/reset window 갱신
→ 반복 fault 여부 판단
→ normal / degraded / recovery / rollback 선택
→ evidence 보존 뒤 clear
→ external device와 persistent state 재조정
```

동일 image가 짧은 시간 안에 반복 reset되면:

- optional feature disable
- last operation quarantine
- factory/default configuration
- firmware rollback
- maintenance mode
- external communication만 제한적으로 enable

무조건 정상 mode로 들어가 boot loop를 반복하지 않습니다.

## fault handler에서 하지 않을 일

- 일반 logging stack 전체 사용
- lock 획득
- heap allocation
- unbounded flash/filesystem operation
- 실패한 peripheral에 긴 출력
- corrupt pointer를 따라 복잡한 구조 순회

가능하면 raw register와 fixed record만 사용합니다.

## watchdog와 debugger

debug halt 동안 watchdog가 계속 가는지 멈추는지 SoC와 configuration마다 다릅니다. debug 편의를 위해 watchdog를 disable한 build만 시험하면 production hang path를 놓칩니다.

- production-equivalent watchdog test
- debugger freeze setting 기록
- reset 직전 GPIO/trace marker
- HIL에서 intentional hang injection

## reset injection matrix

- idle 중 watchdog
- I2C/SPI transfer 중 reset
- DMA active 중 reset
- flash write/erase 중 reset
- update trial boot 중 reset
- power sleep entry/exit 중 reset
- crash record write 중 power loss

각 경우 다음 boot의 owner, buffer, external device와 persistent state를 확인합니다.

## failure와 검증

### watchdog reset 후 즉시 다시 reset

faulting configuration/request를 그대로 재개하거나 evidence processing 자체가 fault할 수 있습니다.

### reset reason이 항상 power-on

flag clear timing, bootloader 소비, power domain 또는 API 지원 범위를 확인합니다.

### crash log가 가끔 garbage

retained record의 version/CRC와 write ordering이 없거나 해당 reset에서 RAM이 유지되지 않을 수 있습니다.

## 실습 연결

- [power-loss-safe persistence](../../exercises/05-power-loss-persistence/README.md)
- [update와 rollback 모델](../../exercises/06-update-rollback-model/README.md)
- [현장 센서 노드 capstone](../../capstone/field-sensor-node/README.md)

## 직접 확인할 문제

1. timer ISR이 watchdog를 feed할 때 scheduler hang을 놓칠 수 있는 trace를 작성해 보세요.
2. watchdog reset cause와 root cause가 다른 이유를 설명해 보세요.
3. retained crash record에 magic/version/CRC가 필요한 이유를 적어 보세요.
4. MCU reset만으로 external actuator가 safe state가 되지 않는 경우를 설명해 보세요.

## 이 장이 보장하지 않는 것

기능 안전 수준, hazard analysis와 인증 규격을 완료하지 않습니다. 위험한 actuator에는 independent hardware safety mechanism이 필요할 수 있습니다.
