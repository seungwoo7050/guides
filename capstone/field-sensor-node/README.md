# Capstone — 현장 센서 노드

## 문제

배터리로 동작하는 센서 노드가 일정 주기로 환경 값을 측정하고, 유효한 기록을 flash에 보존하며, 연결 가능한 시점에 외부 수집기로 전송합니다. 장치는 장시간 unattended 상태로 운영되며 sensor·bus·storage·communication 오류, reset, 전원 손실과 firmware update를 견뎌야 합니다.

이 capstone의 목적은 완성 제품이나 특정 보드 firmware를 제공하는 것이 아닙니다. 문서에서 배운 다음 계약을 **하나의 제한된 시스템 설계와 검증 계획**으로 연결합니다.

```text
boot와 image
→ hardware description과 driver readiness
→ periodic sampling과 interrupt
→ bounded queue와 deadline
→ persistent record
→ upload와 acknowledgement
→ watchdog·crash evidence
→ sleep/wakeup
→ trial update와 rollback
```

## 결과물 형태

다음 두 경로 중 하나를 선택합니다.

### 설계·상태 모델 경로

hardware 없이도 완료할 수 있습니다.

- architecture와 state machine
- deterministic fixture
- interrupt/update/persistence model 확장
- failure matrix와 invariant checker
- resource·timing·energy budget
- verification plan과 미검증 범위

### 구현 경로

설계 결과의 일부를 Zephyr/native simulation/QEMU/실제 보드로 옮깁니다. 모든 기능을 구현할 필요는 없습니다. 한 개의 end-to-end slice를 강하게 검증하는 것이 좋습니다.

추천 slice:

- interrupt-driven sampling + bounded queue
- power-loss-safe record
- watchdog + crash evidence
- trial image + rollback
- sleep/wakeup + current measurement

## 제품 요구사항

### 기본 기능

1. 부팅 뒤 exact image/build ID와 reset cause를 식별합니다.
2. sensor와 storage dependency를 초기화하고 readiness를 판정합니다.
3. configurable interval로 sample request를 시작합니다.
4. data-ready interrupt 또는 timer event를 bounded ISR path로 전달합니다.
5. sample에 sequence, monotonic timestamp, quality/status를 붙입니다.
6. 유효 record를 persistent storage에 기록합니다.
7. 연결 가능할 때 아직 acknowledge되지 않은 record를 전송합니다.
8. acknowledge된 record를 안전하게 reclaim합니다.
9. idle 기간에는 low-power state로 들어가고 예정된 사건에 깨어납니다.
10. critical responsibility가 진행하지 않으면 watchdog recovery를 수행합니다.
11. candidate image를 trial boot하고 self-test 뒤 confirm하거나 revert합니다.

### 비기능 계약

- RAM, flash, stack, queue와 storage budget이 bounded입니다.
- sample deadline과 허용 jitter가 정의돼 있습니다.
- reset/power loss 뒤 record duplication 또는 omission policy가 명시돼 있습니다.
- 모든 external operation에는 timeout와 terminal result가 있습니다.
- crash/update report를 exact build와 연결할 수 있습니다.
- simulator와 실제 hardware가 증명하는 범위를 분리합니다.

## 의도적인 비범위

- 실제 radio/TCP stack 구현
- cloud backend
- production cryptographic key provisioning
- PCB, battery charger와 analog sensor 회로
- 산업별 안전 인증
- 전체 MCUboot port 또는 custom RTOS
- 모든 peripheral를 위한 generic driver framework

communication은 abstract uploader interface 또는 loopback/fake로 충분합니다.

## system boundary

```text
                   +----------------------+
 hardware event -->| sensor driver        |
                   +----------+-----------+
                              | sample event
                              v
+-------------+    +----------+-----------+    +------------------+
| clock/power |--->| acquisition service  |--->| bounded record Q |
+-------------+    +----------+-----------+    +---------+--------+
                              |                          |
                              v                          v
                   +----------+-----------+    +---------+--------+
                   | persistent store     |<-->| upload service   |
                   +----------+-----------+    +------------------+
                              |
                    durable records/metadata

+------------------+  +------------------+  +--------------------+
| supervisor/WDT   |  | crash evidence   |  | boot/update state  |
+------------------+  +------------------+  +--------------------+
```

각 box는 interface와 state owner를 가져야 합니다. global variable로 암묵적으로 결합하지 않습니다.

## 정본 상태

### sample request

```text
IDLE
→ REQUESTED(generation, deadline)
→ WAITING_DEVICE
→ READY(raw status)
→ READING
→ VALIDATED
→ COMMITTED(record sequence)
→ IDLE

terminal failure:
REJECTED / TIMEOUT / DEVICE_FAULT / STORAGE_FAULT
```

### record

```text
FREE
→ BUILDING
→ QUEUED
→ DURABLE
→ PENDING_UPLOAD
→ IN_FLIGHT(attempt)
→ ACKNOWLEDGED
→ RECLAIMABLE
→ FREE
```

`IN_FLIGHT` 중 reset되면 remote acknowledgement를 모를 수 있습니다. record ID와 idempotent receiver 또는 at-least-once policy를 정합니다.

### device lifecycle

```text
BOOTING
→ SELF_TEST
→ OPERATIONAL
↔ DEGRADED
→ RECOVERING
→ SAFE_MODE
```

### firmware lifecycle

```text
CONFIRMED
→ CANDIDATE
→ TRIAL
  ├─ confirm → CONFIRMED
  └─ fail/reset limit → REVERT
```

## module contract

### clock/power

- monotonic time와 wrap-safe comparison
- wake source와 sleep depth
- clock transition 뒤 timer/peripheral 재설정
- sleep 동안 시간 연속성 여부

### sensor driver

- init/probe/configure
- start/cancel sample with generation
- data-ready/status
- timeout/recovery
- suspend/resume

### acquisition service

- sample cadence
- skipped/late sample policy
- queue pressure
- quality/status 판정
- storage handoff

### persistent store

- record format/version/integrity
- append/commit/recover
- power-loss cut point
- capacity와 reclaim
- schema compatibility

### uploader

- batch selection
- request/record identity
- timeout/retry/backoff
- unknown result
- acknowledge와 durable cursor

### supervisor

- responsibility별 heartbeat/progress
- deadline와 escalation
- safe output
- watchdog feed 조건
- reset loop detection

### crash evidence

- build ID
- reset/fault reason
- last progress와 state
- queue/storage/update summary
- integrity와 consume lifecycle

### boot/update

- candidate validation
- compatibility
- trial self-test
- confirmation deadline
- revert/recovery

## 개발 단계

### Milestone 1. 계약과 정본 상태

- target profile와 비범위
- module/interface diagram
- state owner 표
- end-to-end sample trace
- resource inventory
- failure matrix 초안

이 단계에서 구현을 시작하지 않습니다.

### Milestone 2. 결정론적 host model

- virtual clock
- scripted sensor/bus
- bounded event/record queues
- byte-array persistence
- abstract uploader
- reset/reboot
- update state

fixture가 같은 입력에서 같은 final state와 evidence를 내야 합니다.

### Milestone 3. 정상 경로

```text
boot
→ readiness
→ sample
→ persistent commit
→ upload
→ ack
→ reclaim
→ sleep
```

각 transition의 timestamp, generation와 record sequence를 확인합니다.

### Milestone 4. 실패와 복구

[failure matrix](failure-matrix.md)의 필수 행을 구현합니다. 오류를 단순 예외로 종료하지 않고 reboot 뒤 durable state를 검사합니다.

### Milestone 5. RTOS/target slice

선택한 한 경로를 실제 API로 옮깁니다.

- final Devicetree/Kconfig artifact
- ELF/map와 resource budget
- target trace/log
- host model과 다른 behavior
- 미검증 항목

### Milestone 6. release/update

- build identity
- candidate/trial/confirm/revert fixture
- persistent schema compatibility
- rollback report

## 필수 artifact

```text
capstone-workspace/
├── README.md
├── requirements.md
├── architecture.md
├── state/
│   ├── device.md
│   ├── sampling.md
│   ├── records.md
│   └── update.md
├── budgets/
│   ├── memory.md
│   ├── timing.md
│   └── energy.md
├── model-or-implementation/
├── fixtures/
├── evidence/
├── verification.md
├── failure-matrix.md
└── limitations.md
```

## 핵심 불변식

1. 같은 generation의 sample은 terminal result 하나만 가집니다.
2. queue와 storage는 capacity를 넘지 않으며 overflow 정책을 기록합니다.
3. committed record는 integrity가 확인되기 전까지 valid로 사용하지 않습니다.
4. power loss 뒤 complete record만 복구합니다.
5. acknowledge되지 않은 record를 silent delete하지 않습니다.
6. timeout/cancel 뒤 late completion이 새 operation을 완료하지 않습니다.
7. watchdog feed는 모든 critical responsibility의 progress를 전제로 합니다.
8. trial image confirmation 전 previous bootable image를 보존합니다.
9. crash/update evidence는 exact build와 연결됩니다.
10. sleep/wakeup 뒤 driver와 time state가 명시적으로 복원됩니다.

## 완료 판정

정확한 기준은 [acceptance.md](acceptance.md)를 사용합니다. 최소한 다음을 만족해야 합니다.

- 모든 필수 artifact가 있습니다.
- 정상 trace와 필수 failure trace가 자동 또는 반복 가능하게 실행됩니다.
- final state를 외부 checker 또는 명시적 assertion이 판정합니다.
- hardware 없이 보장한 것과 target에서 확인한 것을 분리합니다.
- resource/timing/energy 주장에는 입력과 측정 또는 계산 근거가 있습니다.
- production-ready, secure, real-time 같은 표현을 근거 없이 사용하지 않습니다.

## 가이드 이후 확장

capstone을 거대한 제품으로 계속 확장하지 않습니다. 다음 중 하나를 선택합니다.

- Zephyr sensor driver/sample에 작은 기여
- board description 또는 binding 개선
- persistent storage library의 cut-point test
- watchdog/crash telemetry module
- MCUboot sample의 trial/revert test
- low-power measurement project
- embedded open-source issue 재현과 patch

같은 하위 시스템에서 반복 기여하며 실제 전문성을 만듭니다.
