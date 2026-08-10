# 현장 센서 노드 완료 기준

이 문서는 capstone의 합격 조건을 고정합니다. 화면 출력이나 정상 실행 한 번이 아니라 **상태·실패·복구·검증 근거**를 판정합니다.

## 1. 범위와 재현성

- [ ] target 또는 model profile, source revision와 tool version이 기록돼 있습니다.
- [ ] 구현 범위와 의도적 비범위가 분리돼 있습니다.
- [ ] 한 명령 또는 명확한 절차로 fixture를 다시 실행할 수 있습니다.
- [ ] 생성 artifact와 raw evidence의 위치가 문서화돼 있습니다.
- [ ] debug/release 또는 test/production configuration을 혼동하지 않습니다.

## 2. architecture와 소유권

- [ ] hardware description, driver, service, persistence, uploader, supervisor와 boot/update의 책임이 분리돼 있습니다.
- [ ] module interface마다 input, result, timeout와 owner가 있습니다.
- [ ] sample generation, record sequence와 image build identity가 서로 다른 식별자임을 설명합니다.
- [ ] buffer, queue entry, persistent record와 callback의 lifetime이 있습니다.
- [ ] ISR, worker/task와 boot context에서 허용되는 operation을 구분합니다.

## 3. boot와 image

- [ ] reset cause와 selected image/build ID를 기록합니다.
- [ ] vector/startup/memory layout 또는 선택 RTOS의 equivalent를 설명합니다.
- [ ] flash, static RAM, stack, queue와 storage budget이 있습니다.
- [ ] boot dependency가 ready하지 않을 때 fail/degraded/safe 정책이 있습니다.
- [ ] crash record를 초기화 전에 보존하는 순서를 설명합니다.

## 4. sampling과 event path

- [ ] sample request에 generation와 deadline가 있습니다.
- [ ] ISR work가 bounded이며 deferred work 경로가 있습니다.
- [ ] event queue capacity와 overflow 정책이 있습니다.
- [ ] duplicate/spurious/stale event fixture가 있습니다.
- [ ] timeout/cancel 뒤 late completion이 새 request를 바꾸지 않습니다.
- [ ] sample timestamp, unit, quality/status가 있습니다.

## 5. persistent record

- [ ] record format에 version, length, sequence와 integrity가 있습니다.
- [ ] commit 전 partial record를 valid로 해석하지 않습니다.
- [ ] power-loss cut point 검사가 있습니다.
- [ ] reboot 뒤 old/new complete 중 하나만 선택합니다.
- [ ] capacity, reclaim와 wear/write-frequency 정책이 있습니다.
- [ ] schema migration와 firmware rollback compatibility가 기록돼 있습니다.

## 6. upload와 unknown result

- [ ] record ID가 retry에서도 안정적입니다.
- [ ] request timeout와 retry budget가 bounded입니다.
- [ ] response를 못 받았지만 remote effect가 있었을 수 있는 `UNKNOWN` 상태를 다룹니다.
- [ ] acknowledgement가 durable하게 반영되기 전 record를 삭제하지 않습니다.
- [ ] duplicate upload를 receiver idempotency 또는 명시적 policy로 처리합니다.
- [ ] offline 기간의 queue/storage pressure 정책이 있습니다.

## 7. timing과 power

- [ ] sample deadline의 시작/종료 사건과 허용 jitter가 정의돼 있습니다.
- [ ] ISR, queue, task interference와 shared resource blocking을 분석합니다.
- [ ] 측정값과 worst-case 보장을 구분합니다.
- [ ] sleep entry 조건과 wake source가 있습니다.
- [ ] wake 뒤 clock, driver와 time continuity를 복원합니다.
- [ ] energy estimate 또는 측정은 workload와 instrument 조건을 포함합니다.

## 8. watchdog와 crash evidence

- [ ] critical responsibility별 progress/heartbeat가 있습니다.
- [ ] global feed task가 다른 hang를 숨기지 않습니다.
- [ ] watchdog/reset-loop escalation과 safe mode 조건이 있습니다.
- [ ] crash evidence에 build ID, reset/fault reason, last progress가 있습니다.
- [ ] record integrity/version과 consume lifecycle이 있습니다.
- [ ] evidence 기록 실패가 영구 boot block을 만들지 않습니다.

## 9. update와 rollback

- [ ] candidate completeness, validity와 hardware compatibility를 검사합니다.
- [ ] trial image와 previous confirmed image를 구분합니다.
- [ ] self-test 항목과 confirmation deadline가 있습니다.
- [ ] repeated reset/timeout 뒤 bounded revert가 있습니다.
- [ ] confirm/revert metadata power loss fixture가 있습니다.
- [ ] binary rollback와 persistent data compatibility를 별도로 판정합니다.
- [ ] both-image failure 시 recovery behavior가 있습니다.

## 10. 검증 층

- [ ] pure state와 policy는 host/model test가 있습니다.
- [ ] interrupt/time/power loss를 결정적으로 주입합니다.
- [ ] simulator/emulator가 지원하지 않는 behavior를 기록합니다.
- [ ] target 결과가 있다면 board revision, configuration와 raw trace가 있습니다.
- [ ] HIL timeout를 product/fixture/infra/inconclusive로 분류합니다.
- [ ] test coverage를 timing·power·safety 보장으로 확대하지 않습니다.

## 필수 시나리오

다음은 모두 결과가 결정적이어야 합니다.

1. cold boot → 정상 sample → commit → upload → ack → sleep
2. sensor identity mismatch
3. data-ready burst와 event queue overflow
4. conversion timeout 뒤 late interrupt
5. persistence program 중 power loss
6. storage full과 uploader offline
7. upload result unknown 뒤 retry
8. task hang와 watchdog reset
9. sleep 진입 직전 event
10. candidate trial crash와 revert
11. confirmation write 중 power loss
12. new schema 때문에 previous image가 읽지 못하는 경우

### 실행 fixture 추적표

각 fixture는 위 번호와 [failure matrix](failure-matrix.md)의 행을 동시에 고정합니다. checker는 이 매핑 자체도 검사하므로 fixture 이름만 바꿔 결과를 우회할 수 없습니다.

| 시나리오 | fixture ID와 파일 | failure matrix | 자동 판정의 핵심 |
|---:|---|---|---|
| 1 | `S01` — [normal cycle](fixtures/S01-normal-cycle.json) | F07, F12, F17, F26 | W1C, DMA handoff, commit, durable ACK/reclaim, sleep |
| 2 | `S02` — [identity mismatch](fixtures/S02-identity-mismatch.json) | F02 | raw identity 불일치, degraded, request 거부 |
| 3 | `S03` — [burst overflow](fixtures/S03-burst-overflow.json) | F07, F09 | capacity 2, high-water 2, explicit drop 1 |
| 4 | `S04` — [timeout/late IRQ](fixtures/S04-timeout-late-interrupt.json) | F04, F06 | deadline 뒤 generation 7 stale drop, commit 없음 |
| 5 | `S05` — [persistence power loss](fixtures/S05-persistence-power-loss.json) | F12, F13 | staging discard, partial record 미복구 |
| 6 | `S06` — [storage full/offline](fixtures/S06-storage-full-offline.json) | F15, F16 | unacked 2개 보존, 세 번째 거부, bounded backlog |
| 7 | `S07` — [upload UNKNOWN](fixtures/S07-upload-unknown-retry.json) | F17, F18 | 같은 `R1`로 2회, UNKNOWN 뒤 보존, ACK 뒤만 reclaim 가능 |
| 8 | `S08` — [watchdog/crash](fixtures/S08-watchdog-crash.json) | F23, F24, F25 | hung service가 feed를 막고 build-linked crash record를 먼저 기록 |
| 9 | `S09` — [sleep race](fixtures/S09-sleep-entry-race.json) | F26, F27 | wake latch, sleep abort, driver readiness 복원 |
| 10 | `S10` — [trial crash/revert](fixtures/S10-trial-crash-revert.json) | F31, F34 | self-test 뒤 v2 confirm, 다음 v3 trial crash에서 v2 revert |
| 11 | `S11` — [confirm power loss](fixtures/S11-confirm-power-loss.json) | F33 | torn confirm을 success로 확대하지 않고 v1 선택 |
| 12 | `S12` — [schema rollback](fixtures/S12-schema-rollback.json) | F35 | schema 2를 못 읽는 v1 rollback 차단, recovery 선택 |

전체 suite는 다음 누적 연결이 한 번 이상 실제 trace에 나타나는지도 검사합니다.

```text
driver → MMIO/W1C → DMA ownership → bounded queue
→ persistent commit → upload UNKNOWN/ACK
→ sleep/wakeup → watchdog/crash → update trial/confirm/revert
```

자동 판정 결과의 `required_evidence`는 실제 target evidence의 **요구 목록**이지 그 evidence 자체가 아닙니다. JSON 출력의 `human_review.status=NOT_TESTED`는 board trace, timing, power-cut, current와 HIL 판정이 남았음을 뜻합니다.

## 합격 수준

### 설계·모델 완료

- 위 체크 항목을 문서와 deterministic fixture로 만족합니다.
- target-specific timing/electrical/power 주장은 `미검증`으로 표시합니다.

### emulator/RTOS 완료

- 설계·모델 조건을 만족합니다.
- final configuration, ELF/map와 runtime trace가 있습니다.
- emulator가 빠뜨린 peripheral 특성을 적습니다.

### 실제 보드 slice 완료

- 선택한 end-to-end slice가 실제 board에서 반복됩니다.
- logic/bus/current/debug evidence와 측정 조건이 있습니다.
- 한 board의 결과를 전체 지원 범위로 확대하지 않습니다.

어느 수준을 선택했는지 `README.md`에 명시합니다.

## 불합격 예

- 정상 demo만 실행되고 failure fixture가 없음
- 무한 queue/heap으로 pressure를 숨김
- 모든 오류를 reset으로 처리하고 원인·loop 제어가 없음
- test가 exception 발생만 보고 성공 처리
- update 뒤 old image를 즉시 지움
- simulator 통과를 real-time/power/production 보장으로 표현
- exact build와 연결되지 않는 crash 주소만 저장
