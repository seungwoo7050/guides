# Capstone B: Event-time 스트림 pipeline

## 목적

모바일/웹 행동 event에서 5분 단위 활동 집계를 만든다. 낮은 latency의 잠정 결과와 late correction을 함께 제공하며 duplicate, out-of-order, restart를 정상 입력으로 처리한다.

## 입력

각 event는 최소 다음 정보를 가진다.

```text
event_id
user_id
session_hint
event_type
occurred_at
observed_at
source_partition
source_offset
schema_version
```

fixture에는 다음이 포함된다.

- 정상 순서 event
- 2분, 20분, 26시간 늦은 event
- 동일 event의 duplicate
- 같은 timestamp의 여러 event
- 미래 timestamp
- partition별 속도 차이
- restart 직전/후 record

## 목표 output

```text
key: user_segment + window_start
window_end
event_count
unique_users
result_version
completeness_state: EARLY | ON_TIME | CORRECTED | CLOSED
watermark_at_emit
published_at
source_coverage
```

unique user 계산은 exact 또는 approximate 중 선택하되 보장과 오차를 명시한다.

## 필수 artifact

1. `event-contract.md`
2. `window-policy.md`
3. `state-and-checkpoint.md`
4. `sink-contract.md`
5. `quality-and-lateness.md`
6. `failure-matrix.md`
7. `reconciliation.md` — batch replay와 stream 결과 비교
8. `runbook.md`
9. `evidence.json` — run/input/code/output identity와 capstone별 필수 시나리오의 관측 파일
10. `submission.json` — 구현 profile, 실행·검증 명령과 알려진 한계

템플릿은 [`exercises/06-capstones/02-event-time-pipeline`](../../exercises/06-capstones/02-event-time-pipeline/README.md)에 있다.

## 누적 evidence 연결

| 높이 | artifact에 남길 evidence |
|---|---|
| contract와 ownership | `event-contract.md`: event/entity identity, producer·operator·consumer owner, schema·time·correction·classification |
| ingestion과 progress | `event-contract.md`: source partition/offset, observed time, replay·retention 범위와 malformed input boundary |
| processing state | `window-policy.md`·`state-and-checkpoint.md`: window/watermark/trigger, dedup horizon, timer, checkpoint와 state schema |
| delivery와 publish | `sink-contract.md`: stable result key/version, pane finality, checkpoint 전후 retry와 consumer update 규칙 |
| orchestration과 recovery | `runbook.md`: job/run/attempt/output identity, backpressure propagation, retry storm, backlog recovery와 batch replay |
| quality와 reconciliation | `quality-and-lateness.md`·`reconciliation.md`: sticky conflict quarantine, late/drop, key/window batch diff |
| lineage·freshness·cost·access | `evidence.json`·`submission.json`·`runbook.md`: input/output/code/state/quality lineage, oldest-event age, source/pipeline delay와 unit cost |
| evolution과 consumer cutover | `failure-matrix.md`·`runbook.md`: state/sink schema shadow restore, canary consumer, rollback/roll-forward와 deprecation |

## 필수 정책

### event time

- timestamp 생성자와 timezone
- invalid/future timestamp 처리
- event time fallback 여부

### window

- fixed/sliding/session 중 선택
- boundary와 key
- batch replay와 동일한 calendar

### watermark

- source/partition progress 반영 방법
- idle partition
- watermark lag 관측

### trigger

- early frequency
- on-time 조건
- late correction debounce
- accumulating/discarding/retraction

### allowed lateness

- state retention
- 자동 correction 기간
- 기간 밖 event의 quarantine/backfill 경로

### sink

- stable output key
- result version 또는 pane ID
- duplicate/retry 처리
- previous result update/retraction

## 필수 실패 시나리오

- `normal`: 고정 offset 범위의 정상 window 계산·checkpoint·sink publish
- `arrival-order-permutation`: 같은 event 집합의 도착 순서와 duplicate 위치를 변경
- `sink-write-before-checkpoint-crash`: sink write 성공 뒤 checkpoint 전 crash
- `checkpoint-before-source-commit-crash`: checkpoint 성공 뒤 source commit 전 crash
- `dedup-ttl-boundary`: duplicate event가 TTL 안/밖에 도착
- `late-window-correction`: 늦은 event가 이미 on-time인 window를 수정
- `late-session-merge`: session window를 사용한다면 late event가 두 session을 merge하고, 사용하지 않으면 선택한 window의 동등한 late 경계를 증명
- `idle-partition-watermark`: 한 partition이 idle하거나 지연돼 watermark를 막음
- `sink-backpressure`: sink가 10분간 느려져 backpressure 발생
- `state-schema-restore`: state schema를 변경한 새 version으로 restore
- `conflicting-event-id`: 같은 event ID에 서로 다른 payload가 도착하고 이후 첫 payload가 다시 전송
- `poison-event-retry-storm`: poison event retry가 한 partition을 막고 retry storm이 sink recovery를 방해
- `insufficient-recovery-capacity`: recovery capacity가 live rate와 같아 backlog와 oldest-event age가 줄지 않음
- `incompatible-result-state-schema`: 새 result/state schema를 old consumer/checkpoint가 읽지 못함
- `batch-reconciliation-mismatch`: 같은 offset 범위의 batch와 closed stream 결과가 key/window별로 어긋남

## 품질과 관측

- partition별 source lag
- event-time lag와 watermark
- early/on-time/late pane 수
- late drop/quarantine count
- duplicate count
- state size와 checkpoint duration
- sink commit latency
- batch replay와 window 결과 diff
- source delay, pipeline delay와 oldest unprocessed event age
- live/recovery rate, retry volume과 million-event당 처리 비용

## batch reconciliation

동일 offset 범위를 bounded input으로 고정해 batch 계산을 수행한다. stream의 `CLOSED` 결과와 비교한다.

불일치가 허용되는 경우:

- approximate algorithm의 문서화된 오차
- correction window 밖 data
- batch와 stream이 다른 reference snapshot을 사용한 경우 — 이는 가능하면 제거해야 한다.

같은 event ID나 같은 entity/version의 conflicting payload는 arrival order로 선택하지 않는다. 해당 identity를 sticky quarantine에 유지하고 conflict가 해결된 새 source/version으로만 repair한다.

## 사람·runtime 검토 evidence

Root validator는 필수 section의 보이는 본문, submission/evidence identity, rubric의 모든 필수 시나리오와 고유한 `evidence/` 파일의 정적 연결을 검사한다. 명령 실행 결과의 진실성과 다음 의미 판단은 선택 runtime과 사람이 별도로 확인한다.

- arrival permutation, duplicate/conflict와 TTL 경계 fixture의 closed result digest
- sink 성공/checkpoint 전 crash와 restore 뒤 source·state·sink 상태
- idle/slow partition, poison event와 sink throttle에서 backpressure 경로와 backlog recovery 계산
- batch replay와 stream `CLOSED` output의 key/window diff
- state schema shadow restore, representative canary consumer와 rollback rehearsal
- approximate algorithm, 실제 broker/processor를 사용하지 않은 경로와 외부 side effect의 비보장

## 완료 판정

- arrival order를 바꿔도 closed 결과가 같다.
- duplicate와 restart가 한 번 반영된 것과 동등한 sink 상태를 만든다.
- early 결과가 consumer에게 잠정임을 표시하고 correction을 적용할 수 있다.
- watermark 정체와 late distribution을 관찰할 수 있다.
- state와 sink failure를 주입한 뒤 checkpoint에서 복구한다.
- batch replay와 차이를 key/window별로 설명한다.
- runtime failure evidence와 사람의 finality·recovery 검토 없이 자동 구조 검사만으로 완료를 주장하지 않는다.

## 범위 밖

- 전역 완전 순서 보장
- 임의의 외부 API를 exactly-once로 호출
- 실제 개인정보 event
- 특정 stream engine의 cluster 운영 전체

## 후속 확장

- sessionization
- streaming join과 temporal dimension
- online feature materialization
- multi-region source
- schema/state migration automation
