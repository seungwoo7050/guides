# debugging, tracing과 crash evidence

임베디드 결함은 debugger를 붙였을 때 사라지거나, 현장에서는 전원만 재시작되고, 한 번의 timing 변화로 재현되지 않을 수 있습니다. 따라서 debug는 breakpoint 사용법이 아니라 **관찰이 시스템에 미치는 영향과 reset 뒤에도 남는 증거를 설계하는 일**입니다.

## 학습 목표

- halt debugger, log, trace, GPIO marker와 crash record의 관찰 효과를 구분합니다.
- fault frame, register, stack, build ID와 reset cause를 하나의 사건으로 연결합니다.
- 현장 crash evidence를 제한된 저장 공간과 privacy 조건 안에서 설계합니다.
- 최적화된 firmware에서 source line과 machine state를 연결합니다.
- 관찰 도구가 timing, power와 peripheral 상태를 바꾸는 경우를 기록합니다.

## 관찰 수단은 서로 다른 상태를 봅니다

| 수단 | 볼 수 있는 것 | 개입 위험 |
|---|---|---|
| breakpoint/step | register, memory, call state | CPU halt, peripheral는 계속 진행할 수 있음 |
| UART/console log | 사건과 application state | blocking, stack, timing, power 증가 |
| RTT/SWO/trace | 낮은 지연 event 또는 instruction 흐름 | probe·target 지원 필요, buffer overflow |
| GPIO pulse | 정확한 외부 timing marker | pin과 analyzer 필요, 표현 가능한 정보 제한 |
| crash record | fault 순간 register와 application metadata | 저장 자체가 fault path를 복잡하게 함 |
| watchdog/reset telemetry | hang와 recovery 결과 | 원인 상세가 부족할 수 있음 |

한 수단의 부재를 사건의 부재로 해석하지 않습니다.

## halt가 위험한 이유

CPU를 멈춰도 다음은 계속될 수 있습니다.

- watchdog counter
- DMA
- peripheral FIFO와 shift register
- external sensor state
- network coprocessor
- motor 또는 actuator
- independent timer와 power manager

반대로 debugger 연결이 watchdog freeze, low-power disable, clock change를 자동 적용할 수도 있습니다. debug build가 production behavior와 같은지 확인합니다.

## fault evidence의 최소 집합

architecture와 RTOS에 따라 다르지만 다음을 연결합니다.

```text
build identity
+ reset cause
+ fault kind/status
+ faulting PC와 return address
+ SP와 stack bounds
+ general register 일부
+ current task/interrupt context
+ recent event ring
+ boot/update state
+ integrity/version
```

주소만 저장하면 exact ELF가 없을 때 해석할 수 없습니다. release마다 다음을 보존합니다.

- ELF with symbols
- map file
- exact configuration와 Devicetree
- compiler/toolchain version
- source commit와 build ID
- image hash

## exception frame을 해석합니다

fault handler에 진입한 뒤 현재 C 함수의 local variable만 보면 원래 fault context를 잃을 수 있습니다. architecture가 stack에 저장한 exception frame과 fault status register를 먼저 보존합니다.

확인 질문:

1. fault가 thread mode입니까 interrupt context입니까?
2. 사용한 stack은 main, process, interrupt 또는 task stack 중 무엇입니까?
3. saved PC가 faulting instruction입니까 다음 instruction입니까?
4. precise fault입니까 delayed/imprecise fault입니까?
5. stack frame 자체가 손상됐습니까?
6. nested fault가 original evidence를 덮었습니까?

## stack unwinding의 한계

backtrace는 다음 조건에 영향을 받습니다.

- optimization과 inlining
- frame pointer 유무
- unwind table
- interrupt/exception frame
- stack corruption
- tail call
- mixed secure/non-secure 또는 multiple stacks

backtrace 한 줄을 절대적인 call history로 보지 않습니다. PC/LR, stack bounds, raw words와 symbolization 조건을 함께 남깁니다.

## 로그는 event stream입니다

좋은 firmware log는 문장보다 구조화된 사건을 남깁니다.

```text
monotonic timestamp
component/event id
request 또는 generation id
state before/after
error class와 raw status
bounded arguments
```

피해야 할 것:

- ISR에서 긴 formatting
- 민감한 key·credential·개인 데이터
- unbounded string
- blocking storage write
- boot마다 의미가 달라지는 임시 event number
- 동일 원인을 서로 다른 문구로만 기록

binary trace를 사용하면 decoder version과 schema도 release artifact입니다.

## ring buffer와 손실 정책

RAM event ring은 crash 직전 사건을 남길 수 있습니다.

설계 항목:

- fixed-size record
- producer context와 synchronization
- wrap sequence
- overflow/drop count
- timestamp source와 wrap
- crash handler에서 snapshot 방법
- reset 뒤 retention 여부

buffer가 가득 찰 때 oldest를 덮을지 newest를 버릴지 정합니다. “로그가 없다”와 “로그가 손실됐다”를 구분할 counter가 필요합니다.

## crash record를 안전하게 저장합니다

fault path에서 flash erase/write를 바로 수행하면 다음 위험이 있습니다.

- corrupted stack와 driver 재진입
- flash operation 중 실행 제한
- power 부족
- nested fault
- 장시간 watchdog timeout

대안:

```text
fault에서 최소 RAM retention record 작성
→ reset
→ early boot가 integrity 확인
→ 정상 driver 초기화 뒤 durable storage로 이동
→ upload/ack 뒤 consumed 표시
```

record에는 magic만 두지 않고 version, length, sequence와 checksum을 포함합니다.

## hang를 조사합니다

crash가 없는 정지는 다음일 수 있습니다.

- deadlock
- interrupts disabled
- priority starvation
- busy loop
- peripheral wait without timeout
- clock stopped
- task stack corruption
- ISR storm

watchdog channel 또는 task heartbeat는 “어느 책임이 진행하지 않았다”를 알려야 합니다. 하나의 global watchdog feed task가 항상 실행되면 다른 task의 hang를 숨길 수 있습니다.

hang evidence:

- task/ISR heartbeat와 last progress timestamp
- queue depth와 owner
- lock/resource owner
- interrupt mask/nesting
- watchdog channel 상태
- last state transition

## timing 문제를 관찰합니다

printf를 추가해 race가 사라지는 것은 흔한 현상입니다. 다음 순서로 관측 강도를 낮춥니다.

1. memory event counter
2. fixed-size ring record
3. GPIO marker와 logic analyzer
4. trace hardware
5. debugger data breakpoint
6. full console log

각 run에서 instrumentation build option을 기록합니다.

## symbolization pipeline

```text
field crash record
→ build ID로 exact ELF 선택
→ address normalization
→ symbol/file/line lookup
→ source commit와 configuration 연결
→ known issue/fixture와 비교
```

PIE, XIP slot offset, bootloader relocation 또는 function pointer tagging이 있다면 주소 보정 규칙을 고정합니다.

## evidence가 충분한 결함 보고서

- target/board revision
- image와 bootloader build ID
- reset cause와 power condition
- reproduction frequency
- expected/actual behavior
- raw crash record
- decoded backtrace와 exact ELF
- recent event sequence
- debugger/logging connected 여부
- 이미 확인한 반증
- 안전하게 재현 가능한 fixture

## 실패와 불변식

- crash record write 중 다시 fault
- retention record checksum failure
- event ring overflow
- timestamp wrap
- wrong ELF로 symbolization
- optimized build에서 inlined frame
- debugger halt 중 watchdog/DMA 진행
- power-loss와 crash reset cause 동시 조건

불변식:

- evidence에는 version과 integrity가 있습니다.
- exact image와 연결할 build identity가 있습니다.
- 수집 실패가 boot를 영구 차단하지 않습니다.
- 민감정보와 장치 고유 secret은 기록하지 않습니다.
- crash upload 실패가 반복 reset loop를 만들지 않습니다.

## 실습 연결

[interrupt event 경로](../../exercises/02-interrupt-event-path/README.md)에 bounded event ring과 overflow counter를 추가하고, [현장 센서 노드 capstone](../../capstone/field-sensor-node/README.md)에서는 reset cause·build ID·last progress를 포함한 crash evidence 계약을 설계합니다.

## 직접 확인할 문제

1. CPU halt 중 DMA가 buffer를 계속 덮을 때 debugger memory view를 어떻게 해석해야 합니까?
2. fault handler에서 flash driver를 호출하지 않고 durable crash report를 남기는 두 단계 경로를 설계해 보세요.
3. build ID가 없는 raw PC만으로 현장 crash를 분석하기 어려운 이유를 적어 보세요.
4. logging을 켰을 때만 결함이 사라지는 경우 관찰 방식을 어떻게 바꾸겠습니까?

## 이 장이 보장하지 않는 것

architecture별 fault register와 trace protocol, vendor probe의 동작은 각각의 공식 문서를 확인합니다. production telemetry의 privacy·보존 정책은 제품과 법적 요구사항의 별도 책임입니다.
