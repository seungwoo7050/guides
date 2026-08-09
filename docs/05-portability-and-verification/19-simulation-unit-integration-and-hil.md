# simulation, unit, integration과 HIL

펌웨어 테스트는 실제 보드에서 한 번 실행하는 것으로 끝나지 않습니다. host unit test는 빠르지만 register timing을 보지 못하고, emulator는 CPU와 일부 peripheral를 실행하지만 실제 전기적 특성을 재현하지 않으며, hardware-in-the-loop(HIL)는 현실적이지만 느리고 실패 원인이 복잡합니다. 각 층이 **어떤 계약을 증명하고 어떤 결함을 놓치는지** 먼저 정합니다.

## 학습 목표

- pure logic, driver state, RTOS integration와 physical hardware 검증을 계층화합니다.
- fake, mock, simulator, emulator와 HIL의 차이를 설명합니다.
- 시간·interrupt·power loss와 bus failure를 결정적으로 주입합니다.
- flakiness를 제품 결함과 test infrastructure 결함으로 분리합니다.
- board farm과 release test의 evidence·reset·resource ownership을 설계합니다.

## 테스트 층

| 층 | 대표 대상 | 잘 찾는 결함 | 놓치기 쉬운 결함 |
|---|---|---|---|
| 정적 검사 | type, config, linker/map, stack estimate | 잘못된 조합·초과 budget | runtime timing·전기적 문제 |
| host unit | parser, state machine, CRC, policy | 경계값·상태 전이·오류 처리 | MMIO·alignment·ISR context |
| native simulation | RTOS/application logic | thread·queue·timer interaction | 실제 ISA·peripheral timing |
| ISA/board emulation | startup, exception, driver 일부 | vector·memory map·CPU semantics | analog·real bus·실제 DMA/cache 특성 |
| target integration | 실제 MCU와 peripheral | driver·clock·interrupt·timing | 장기 환경·생산 편차 |
| HIL/system | sensor·power·network·actuator | end-to-end와 physical interaction | 모든 조합·희귀 장기 결함 |
| field telemetry | 실제 workload | 현실 분포와 장기 결함 | 통제된 재현·정밀 내부 상태 |

한 층을 “더 현실적”이라는 이유로 모든 검사에 사용하지 않습니다.

## testable seam을 설계합니다

application logic이 raw register와 global time을 직접 사용하면 host test가 어렵습니다. 다음 boundary를 둡니다.

```text
application policy
├── clock interface
├── sensor operation interface
├── persistent record interface
├── update/boot state interface
└── event output interface
```

interface를 무조건 객체 지향 추상화로 만들 필요는 없습니다. C function table, handle, compile-time backend 또는 small adapter도 가능합니다. 목적은 hardware effect와 pure decision을 분리하는 것입니다.

## fake와 mock을 구분합니다

- fake는 작지만 실제 상태를 가진 대체 구현입니다. 예: byte array flash, virtual clock, queued sensor.
- mock은 예상 호출 순서·인수를 검사합니다.
- stub은 고정 응답을 돌려줍니다.
- simulator는 대상의 상태와 사건을 더 넓게 모델링합니다.

호출 순서 mock만 많으면 내부 구현을 바꿀 때 의미 없는 실패가 늘어납니다. 가능한 경우 외부 상태와 불변식을 검사합니다.

## 시간은 주입 가능한 입력입니다

실제 sleep을 사용하는 테스트는 느리고 경계 재현이 어렵습니다.

```text
virtual_now = 0
schedule event at 100
advance to 99   → not expired
advance to 100  → exactly one transition
advance across wrap → same ordering rule
```

검사할 것:

- deadline 직전·정확히 같은 시각·직후
- timestamp wrap
- timer 취소와 stale callback
- 여러 event가 같은 tick
- long pause 후 catch-up/drop policy

## interrupt를 사건으로 모델링합니다

host unit에서 ISR machine instruction을 재현할 필요는 없습니다. 다음 계약을 모델링합니다.

```text
hardware status set
→ interrupt event
→ ISR reads/acknowledges status
→ bounded record enqueue
→ worker consumes generation
```

주입 사례:

- interrupt before enable
- event during critical section
- duplicate/spurious interrupt
- status bit 여러 개 동시
- queue full
- stale completion after timeout

실제 priority와 nesting은 emulator 또는 target integration에서 추가합니다.

## register와 bus fake

register fake는 access semantic을 보존해야 합니다.

- read-only
- write-one-to-clear
- read-to-clear
- self-clearing command
- reserved bit
- reset value

일반 dictionary에 값을 대입하는 fake는 잘못된 read-modify-write를 통과시킬 수 있습니다.

bus fake는 다음을 주입합니다.

- NACK/no response
- timeout
- partial/short transfer
- corrupted frame
- busy/stuck condition
- identity mismatch
- reset/retry 뒤 회복

## power loss 테스트

persistent/update 실습은 operation 사이 cut point를 열거합니다.

```text
for cut in every_write_boundary:
    start from known image
    execute until cut
    remove power/reset process
    recover from stored bytes only
    assert last or new complete state
```

random cut만 사용하지 않고 모든 의미 있는 transition을 결정적으로 검사합니다. 실제 flash에서는 erase unit, program alignment와 1→0 transition 같은 device 제약도 target test에서 확인합니다.

## emulator와 simulator의 계약

사용 전에 확인합니다.

- CPU architecture와 privilege/exception 지원
- modeled peripheral 목록
- clock/time advancement 방식
- flash persistence
- interrupt timing
- DMA/cache behavior
- unsupported register access 처리
- host I/O와 target I/O 연결

emulator가 구현하지 않은 register를 0으로 반환하거나 성공 처리하면 driver bug가 숨을 수 있습니다.

## 실제 보드 테스트

target integration의 최소 fixture:

- board revision과 serial identity
- programmer/debug probe
- controllable power
- serial capture
- optional logic analyzer/bus analyzer
- sensor/device fixture 또는 loopback
- known firmware image와 recovery path

각 test는 다음 lifecycle을 소유합니다.

```text
reserve board
→ recover/flash known baseline
→ reset and wait for readiness
→ execute stimulus
→ collect logs/artifact
→ classify result
→ return board to known state
→ release lease
```

실패 뒤 board를 다음 test에 그대로 넘기면 연쇄 오판이 생깁니다.

## HIL failure를 분류합니다

```text
PRODUCT_FAIL       기대한 firmware contract 위반
FIXTURE_FAIL       cable, sensor, relay, probe 문제
INFRA_FAIL         runner/network/artifact 문제
INCONCLUSIVE       필요한 evidence 부족
```

모든 timeout을 product failure로 기록하지 않습니다. 그러나 자동 retry로 결함을 숨기지도 않습니다. 첫 실패 artifact를 보존하고 retry는 분류 보조로 사용합니다.

## flakiness를 다룹니다

- 실패율과 조건을 기록합니다.
- random seed, firmware build, board identity와 fixture version을 남깁니다.
- 무조건 재실행해 green으로 만들지 않습니다.
- race/timing 문제라면 virtual time 또는 event trace로 낮은 층 fixture를 만듭니다.
- board-specific이면 hardware batch·temperature·voltage와 상관을 봅니다.

## coverage의 의미

line coverage는 실행된 code를 보여 줄 뿐 다음을 보장하지 않습니다.

- interrupt ordering
- timing deadline
- stack worst case
- power-loss atomicity
- physical signal quality
- correct peripheral reset state
- production configuration 조합

요구사항·상태 전이·failure matrix를 기준으로 검사를 매핑합니다.

## release verification matrix

| 변경 | 최소 검사 |
|---|---|
| pure parser/state machine | host unit + boundary/property cases |
| driver register logic | semantic register fake + emulator/target |
| interrupt/deferred work | deterministic event test + target timing |
| Kconfig/Devicetree | build matrix + generated artifact inspection |
| flash persistence | exhaustive cut-point model + target power cut sample |
| boot/update | state model + emulator + actual bootloader trial/revert |
| power management | state model + wake-source target test + current measurement |

## 자동 검증의 한계

이 가이드의 `./verify.sh`는 문서와 작은 Python 상태 모델만 확인합니다. 다음은 사용자가 선택한 target에서 별도 evidence를 남겨야 합니다.

- interrupt latency
- actual bus waveform
- DMA/cache coherence
- flash endurance와 power cut
- current consumption
- bootloader image swap
- environmental range

## 실습 연결

[실습 전체 안내](../../exercises/README.md)는 각 과제를 `host model → optional Zephyr/native_sim → QEMU/board`로 확장하는 방법을 설명합니다. capstone의 [완료 기준](../../capstone/field-sensor-node/acceptance.md)은 검사 층마다 주장 가능한 범위를 분리합니다.

## 직접 확인할 문제

1. register mock가 write-one-to-clear 의미를 구현하지 않으면 어떤 잘못된 driver가 통과할 수 있습니까?
2. power-loss test에서 random cut만으로 충분하지 않은 이유를 설명해 보세요.
3. 실제 보드 timeout을 product, fixture, infrastructure failure로 나누기 위해 어떤 evidence가 필요합니까?
4. line coverage가 높아도 deadline과 stack 안전을 보장하지 않는 이유를 적어 보세요.

## 이 장이 보장하지 않는 것

특정 board farm 제품, 계측기 제어 framework와 인증 시험 절차를 정하지 않습니다. 제품 위험과 규제 요구에 따라 별도 validation plan을 만들어야 합니다.
