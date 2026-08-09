# event and idempotency contract

## Scope

upload 접수부터 text·thumbnail output, document status, monthly usage 반영까지 하나의 logical operation으로 정의한다. system brief의 초당 2건, peak 50건, 평균 8 MB·최대 100 MB, 평균 처리 4초·p99 40초, invalid 1%·transient failure 2%, 단일 tenant 최대 30% 조건을 사용한다.

| 결정 항목 | 작성할 계약 |
|---|---|
| operation identity | TODO: tenant 범위의 안정된 key와 producer retry 시 재사용 규칙 |
| event identity | TODO: business event ID와 provider delivery ID의 차이 |
| deterministic effect | TODO: result key, document state, usage event의 유일성 |
| terminal state | TODO: 성공, invalid, deleted tenant, exhausted retry의 종결 조건 |

`ACCEPTED → PROCESSING → SUCCEEDED` 정상 전이와 `PROCESSING → RETRY_WAIT → PROCESSING`, `PROCESSING → DEAD_LETTER`, tenant 삭제 중 terminal 전이를 그린다. timeout이나 crash 뒤 어떤 상태가 authoritative인지 TODO로 명시한다.

## Stage 1 — IaaS

직접 운영하는 queue와 worker에서 lease, acknowledgment, processing record의 commit 순서를 작성한다.

| failure injection | 기대 불변식 | 필요한 evidence |
|---|---|---|
| dequeue 직후 worker crash | message와 operation이 유실되지 않는다 | TODO: lease expiry와 재전달 trace |
| output write 뒤 status commit 전 timeout | output과 usage가 중복되지 않는다 | TODO: deterministic key와 dedup record |
| 동일 event ID, 다른 document | partial state 없이 conflict다 | TODO: 상태 전후 snapshot |

TODO: transaction 경계, retry 횟수, poison input 격리와 cleanup owner를 정한다.

## Stage 2 — Managed platform

선택할 managed queue/runtime의 delivery, visibility/acknowledgment, retention, ordering, batch partial failure, DLQ와 replay 계약을 공급자 문서에서 채운다. 제품명이 아닌 공개 행동으로 기록한다.

- TODO: client timeout과 provider processing timeout을 분리한다.
- TODO: service limit, quota increase lead time과 control-plane 장애 시 기존 data-plane 동작을 적는다.
- TODO: provider delivery ID가 불안정해도 유지되는 application operation ID를 증명한다.

## Stage 3 — FaaS

평균 동시성 `2/s × 4s = 8`, 보수적 peak stress `50/s × 40s = 2,000`을 계산하고 downstream capacity보다 invocation이 먼저 늘지 않도록 global·tenant concurrency를 설계한다. peak에서 평균 크기 object ingress는 `50/s × 8 MB = 400 MB/s`, 최대 크기 stress는 `50/s × 100 MB = 5 GB/s`다.

TODO: timeout, maximum event age, maximum attempts, partial batch response, cold start 관측, DLQ replay 절차를 표로 작성한다. 한 tenant가 30% workload를 만들 때 다른 tenant가 굶지 않는 fairness test와, invalid 1%는 retry하지 않고 transient 2%만 bounded retry하는 분류 기준을 포함한다.

## Stage 4 — SaaS

Starter 100건/월, Pro 10,000건/월 quota에 대해 reservation·commit·release 상태를 정의한다. document output과 usage event는 같은 operation ID를 사용하고 duplicate delivery가 두 효과를 각각 한 번만 만들게 한다.

TODO: plan 변경, quota race, deleted tenant의 late event, tenant export 중 재처리, deletion 중 DLQ replay를 정상·경계·실패 사례로 작성한다. tenant별 attempts, output, usage와 quota 잔여량을 content 없이 연결할 audit key를 정한다.

## Evidence와 한계

| 주장 | 자동/수동 evidence | 합격 기준 | evidence가 보장하지 않는 것 |
|---|---|---|---|
| duplicate-safe output | TODO: trace 또는 local model report | 동일 operation의 output 1개 | TODO |
| idempotent usage | TODO | usage effect 1회 | TODO |
| bounded failure | TODO: attempts·DLQ·replay audit | 무한 retry 없음 | TODO |
| tenant fairness | TODO: tenant별 queue age·concurrency | 30% tenant 부하에서 타 tenant 진행 | TODO |

TODO: 실제 provider delivery, concurrent transaction과 crash recovery는 로컬 모델만으로 입증할 수 없음을 기록한다.

## Open risks와 owner

| risk/condition | owner | due date | verification | rollback |
|---|---|---|---|---|
| TODO: 외부 converter의 idempotency 부재 | TODO | TODO: YYYY-MM-DD | TODO | TODO |
| TODO: peak concurrency가 downstream을 압도 | TODO | TODO: YYYY-MM-DD | TODO | TODO |
| TODO: DLQ replay의 tenant 삭제 충돌 | TODO | TODO: YYYY-MM-DD | TODO | TODO |
