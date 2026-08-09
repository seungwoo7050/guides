# 현장 센서 노드 failure matrix

각 행은 구현 전 설계하고, 실행 뒤 실제 evidence와 판정을 추가합니다. `기대 상태`는 제품 선택에 따라 바꿀 수 있지만 변경 이유를 기록합니다.

| ID | 실패 주입 | 관찰 지점 | 금지 상태 | 기대 상태/복구 | 필수 evidence |
|---|---|---|---|---|---|
| F01 | sensor dependency not ready | boot/self-test | 정상 운영 표시 | degraded 또는 safe mode | dependency result, build ID |
| F02 | wrong sensor identity | probe | 임의 sample 사용 | unavailable, bounded retry 없음/제한 | raw identity, semantic error |
| F03 | bus NACK transient | sampling | 무한 retry | bounded retry 후 success/fault | attempt count, bus status |
| F04 | bus stuck/timeout | transaction | task 영구 block | timeout, controller/device recovery | deadline, recovery result |
| F05 | conversion exact deadline | driver | run마다 다른 판정 | 명시한 `<=`/`<` 규칙 | virtual timestamp trace |
| F06 | late data-ready after timeout | ISR/worker | 새 request 완료 | stale generation drop | generation, stale counter |
| F07 | interrupt burst | event queue | memory 무한 증가 | drop/coalesce/backpressure | depth watermark, drop count |
| F08 | spurious interrupt | ISR | fake sample 생성 | ack/ignore 또는 fault policy | raw status, event count |
| F09 | ISR queue full | ISR handoff | blocking wait | bounded overflow handling | ISR duration, overflow counter |
| F10 | record queue full | acquisition | committed sample silent loss | explicit drop/pause/safe policy | record/sample sequence gap |
| F11 | flash erase 중 power loss | persistence | 모든 record invalid | previous complete record | flash bytes, recovery selection |
| F12 | payload program 중 power loss | persistence | partial payload valid | old/new complete only | cut point, integrity result |
| F13 | commit marker torn | persistence | incomplete record valid | marker invalid, previous 사용 | raw metadata |
| F14 | sequence wrap | recovery | older record 선택 | 정의한 modular ordering | sequence fixture |
| F15 | storage full | persistence | overwrite unacked record | pause/drop/reclaim policy | capacity, record states |
| F16 | uploader offline 장기화 | upload/storage | unbounded memory | persistent backlog와 pressure policy | backlog age/depth |
| F17 | upload applied, response lost | uploader | silent duplicate/삭제 | UNKNOWN, stable id retry | request/record ID, attempt |
| F18 | ack 수신 뒤 metadata write power loss | uploader/store | record silent delete | resend 가능 또는 durable ack | ack/commit trace |
| F19 | communication task burst | scheduler | sampling deadline miss 무관측 | priority/backpressure policy | task trace, deadline counter |
| F20 | low task lock + medium preemption | RTOS | unbounded priority inversion | inheritance/ceiling 또는 구조 변경 | lock owner, response time |
| F21 | stack near/over budget | runtime | random corruption | detection/reset/safe state | watermark/fault frame |
| F22 | allocation/pool exhaustion | runtime | null dereference | explicit terminal error/pressure | pool counters |
| F23 | supervisor task alive, sensor task hung | watchdog | 계속 feed | sensor channel expiry와 reset | per-channel heartbeat |
| F24 | watchdog reset 반복 | boot/supervisor | boot loop 무한 반복 | threshold 뒤 safe/recovery mode | retained reset count |
| F25 | crash record checksum invalid | early boot | garbage upload | reject + diagnostic counter | record version/checksum |
| F26 | sleep entry 직전 interrupt | power/event | event loss | abort sleep 또는 wake pending | interrupt/sleep trace |
| F27 | wake 뒤 peripheral config lost | resume | stale config로 운영 | readiness/reconfigure | reset/config readback |
| F28 | clock source fallback | timing | old frequency로 timeout 계산 | clock state 반영 또는 fault | actual/configured frequency |
| F29 | invalid candidate image | bootloader | candidate 실행 | reject, confirmed 유지 | validation reason |
| F30 | wrong hardware candidate | bootloader | boot 후 register fault | compatibility reject | hardware/image metadata |
| F31 | trial image immediate fault | boot | 반복 trial 무한 | attempt 증가, revert | boot state/reset cause |
| F32 | trial image late watchdog | supervisor/update | 이미 confirm됨 | confirmation 전이면 revert | confirmation timing |
| F33 | confirmation write power loss | metadata | no bootable image | trial/revert의 결정적 선택 | metadata copies |
| F34 | revert 중 power loss | bootloader | both slots unusable | confirmed/recovery path | slot/status state |
| F35 | previous image + new schema | app/storage | old image corrupts data | rollback blocked/recovery/migration policy | schema ranges |
| F36 | both images invalid | boot | random jump | recovery mode | validation report |
| F37 | event log overflow | telemetry | “사건 없음”으로 해석 | overflow counter와 partial trace | ring sequence/drop count |
| F38 | wrong ELF symbolization | analysis | 잘못된 root cause 확정 | build ID mismatch 거부 | crash/image build IDs |
| F39 | test fixture cable failure | HIL | product regression 판정 | FIXTURE_FAIL/INCONCLUSIVE | probe/power/loopback evidence |
| F40 | brownout/noisy reset | system | reset cause 소실 | retained cause + boot policy | power/reset capture |

## 작성 방법

각 구현은 표에 다음 열을 추가해도 됩니다.

```text
fixture path
execution command
actual result
status: PASS / FAIL / NOT TESTED / INCONCLUSIVE
verified environment
remaining risk
```

`NOT TESTED`와 `INCONCLUSIVE`를 실패처럼 숨기지 않습니다. 실제 hardware가 없는 행은 state/model 수준에서 검증하고 전기적·timing behavior는 별도 한계로 남깁니다.
