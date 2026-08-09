# event and idempotency contract

## Scope

upload 접수부터 원본 object, text·thumbnail output, document status와 monthly usage까지 하나의 logical operation으로 추적한다. operation identity는 `(tenant_id, upload_id)`이고 event schema의 `event_id`는 같은 `upload_id`다. producer retry는 이를 재사용한다. provider delivery ID는 전송 시도일 뿐 business identity로 쓰지 않는다. output key는 `tenants/{tenant_id}/documents/{document_id}/operations/{upload_id}/{kind}`로 결정적이다. `dead-letter`는 재시도가 끝난 terminal state를 뜻한다.

authoritative state는 application processing record다. 정상 전이는 `ACCEPTED → PROCESSING → SUCCEEDED`, 일시 실패는 `PROCESSING → RETRY_WAIT → PROCESSING`, invalid file이나 exhausted retry는 각각 `REJECTED_INVALID`, `DEAD_LETTER`로 끝난다. 성공 operation은 output 생성과 usage commit을 각각 정확히 한 번 관찰할 수 있어야 하며, 재전달은 이미 기록된 effect를 반환한다.

평상시 2건/s와 평균 4초 처리에서 평균 동시성은 `2 × 4 = 8`이다. 보수적 peak stress는 peak 50건/s와 p99 40초를 곱한 `2,000`이며, 평균 크기 object를 peak로 받으면 `50 × 8 MB = 400 MB/s`, 모두 최대 크기라면 `50 × 100 MB = 5 GB/s`다. 이는 capacity 상한이 아니라 반드시 throttle·queue·downstream test가 필요한 stress input이다.

## Stage 1 — IaaS

worker는 queue message를 lease한 뒤 operation record를 compare-and-set으로 `PROCESSING`으로 바꾼다. 원본은 tenant-scoped key로 읽고, 결과는 위 deterministic key에 쓰며, status·usage commit 뒤에만 message를 acknowledge한다. output write 후 status commit 전에 crash하면 재시도는 같은 key의 checksum을 비교하고 기존 output을 재사용한다. usage는 `(tenant_id, upload_id, "document_processed")` unique key로 upsert한다.

| 주입 실패 | 공개 결과 | 불변식/evidence |
|---|---|---|
| dequeue 직후 worker crash | lease 만료 후 같은 operation 재전달 | message 유실 없음, attempts 증가 |
| output write 뒤 timeout | 기존 checksum 재사용 후 status 수렴 | output 1개, usage 1회 |
| 동일 upload ID와 다른 document | `EVENT_CONFLICT` terminal | output·usage·queue 추가 없음 |
| invalid file | `REJECTED_INVALID`, retry 없음 | brief의 예상 1%를 별도 집계 |
| transient converter failure | `RETRY_WAIT`, 최대 3회 뒤 DLQ | brief의 예상 2%와 attempts 비교 |

retry 대상은 timeout, connection reset 같은 명시적 transient class뿐이다. permission, tenant inactive, schema/plan unsupported와 payload conflict는 재시도하지 않는다. queue와 database 사이 원자 transaction은 없으므로 reconciliation worker가 `PROCESSING` lease expiry, orphan output과 uncommitted usage를 operation ID로 수렴시킨다.

## Stage 2 — Managed platform

managed queue/runtime를 선택할 때 at-least-once delivery 허용 여부, visibility/acknowledgment timeout, retention, payload size, ordering, batch partial response, DLQ retention·redrive와 control-plane 장애 중 data-plane 동작을 공식 계약에 기록한다. 공급자가 아직 선택되지 않아 실제 limit과 보장 값은 `unknown/unmeasured`다.

visibility timeout은 p99 40초에 cold start·network·commit margin을 더한 실측값보다 길게 설정하되, 긴 lease가 recovery를 늦추지 않는지 failure injection으로 결정한다. application client timeout은 provider processing timeout과 분리한다. queue가 부여하는 delivery ID나 receive count가 달라져도 `(tenant_id, upload_id)` dedup record는 유지한다. DLQ redrive는 새 operation을 만들지 않고 원래 operation ID와 attempt history를 보존한다.

## Stage 3 — FaaS

function invocation 성공은 business completion과 같지 않다. handler는 tenant·document·upload ID를 검증하고 processing record를 선점한 뒤 deterministic output, status, usage를 commit한다. 같은 batch의 invalid 1%는 terminal response로 분리하고 transient 2%만 재전달한다. maximum attempts는 3이며 그 이후 원래 payload hash·tenant·attempt history와 함께 DLQ로 보낸다. maximum event age는 product가 허용하는 처리 지연을 측정한 뒤 정하며 현재 값은 `unknown`이다.

평균 동시성 8은 정상 기준선이고, 보수적 2,000 invocation 및 400 MB/s·5 GB/s ingress stress가 database·converter·object store를 압도하지 않도록 reserved/global concurrency와 queue backpressure를 둔다. global concurrency의 정확한 수치는 load test 전 `unmeasured`다. 한 enterprise tenant가 전체 workload의 30%를 만들 수 있으므로 tenant별 active concurrency와 dispatch share를 30% 목표로 제한하고, 남는 capacity만 work-conserving 방식으로 빌려준다. 30% tenant 부하 중 다른 tenant의 queue age와 completion이 계속 진행되는지를 검증한다.

cold start, timeout 직전 output write, partial batch, throttle, poison payload와 DLQ replay를 주입한다. replay 전 tenant가 `ACTIVE`인지 확인하며 deletion이 시작됐으면 output·usage를 만들지 않고 deletion audit에 terminal 사유를 남긴다.

## Stage 4 — SaaS

Starter는 100건/월, Pro는 10,000건/월이다. upload 수락 시 versioned plan에 대해 quota를 `AVAILABLE → RESERVED`로 원자 전이하고 성공하면 `COMMITTED`, invalid나 최종 실패면 명시한 정책에 따라 `RELEASED`로 전이한다. 이 reference에서는 성공한 document만 usage에 반영하고 invalid 1%와 최종 transient failure는 reservation을 release한다. retry는 새 reservation이나 usage를 만들지 않는다.

plan 변경은 이미 reserved된 operation의 plan version을 바꾸지 않는다. quota 마지막 한 건을 동시에 예약하면 정확히 하나만 성공한다. deleted tenant의 late event, 다른 tenant의 document를 가리키는 event와 unsupported plan/schema는 partial output 없이 terminal이다. export는 usage event와 quota state의 snapshot을 포함하고 24시간 내 준비하며, deletion은 active data를 7일 내 제거하는 동안 새 event와 DLQ replay를 차단한다. tombstone과 aggregate usage처럼 남기는 evidence의 retention은 customer notice에 별도로 기록한다.

## Evidence와 한계

| 주장 | 제출 evidence | 합격 기준 | 한계 |
|---|---|---|---|
| duplicate-safe output | operation trace, output key·checksum | 동일 operation output 1개 | object store 실제 consistency 미검증 |
| idempotent usage/quota | reservation·usage unique key와 전후 snapshot | retry 뒤 commit 1회 | 실제 concurrent DB transaction 미검증 |
| bounded failure | attempts, terminal class, DLQ·redrive audit | invalid retry 0, transient 최대 3회 | 실제 provider delivery 미검증 |
| tenant fairness | tenant별 concurrency, queue age, completion | 30% producer 중 다른 tenant 진행 | stress 수치별 provider limit 미측정 |
| lifecycle 연결 | export/deletion 중 late-event trace | 삭제 tenant output·usage 0 | physical deletion 미검증 |

local cloud model report는 tenant-scoped identity, duplicate, conflict, retry, DLQ, usage-once와 deletion 공개 행동을 결정적으로 검사한다. 실제 process crash, distributed transaction, cold start, 400 MB/s·5 GB/s data path, provider delivery guarantee는 integration·load test가 필요하며 자동 검사가 architecture 타당성을 승인하지 않는다.

## Open risks와 owner

| risk/condition | owner | due date | verification | rollback |
|---|---|---|---|---|
| 외부 converter가 idempotency key를 지원하지 않음 | application owner | 2026-09-15 | timeout-after-write test에서 checksum 기반 reconcile과 invocation count 확인 | converter 호출을 single-flight worker로 제한 |
| provider limit 전 보수적 peak 2,000이 downstream을 압도 | runtime owner | 2026-09-22 | 400 MB/s와 별도 5 GB/s stress를 throttle한 load report, queue age·error 기록 | FaaS concurrency를 last-known-safe 값으로 낮춤 |
| deletion tenant의 DLQ가 replay됨 | data owner | 2026-09-15 | deletion 시작 뒤 redrive negative test에서 output·usage 0 확인 | redrive disable 후 tenant queue quarantine |
| provider delivery·event-age contract 미확정 | runtime owner | 2026-09-29 | 선택 provider 공식 계약과 failure-injection 결과 검토 | provider adapter를 비활성화하고 local/managed queue 경로 유지 |
