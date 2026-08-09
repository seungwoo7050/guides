# failure and recovery plan

## Scope

이 계획은 instance·zone·managed runtime/database/queue/control plane·event delivery·quota·tenant export/deletion·cost anomaly를 다룬다. 목표는 **RPO 15분, RTO 60분**이다. 성공은 component가 다시 `healthy`라고 말하는 순간이 아니라 public invariant가 회복되고 partial state와 orphan resource가 최종 inventory에 수렴한 때다.

| Workload fact / 계산 | 값 | failure·capacity 의미 |
| --- | --- | --- |
| 평상시 처리 concurrency | `2 uploads/s × 평균 4초 = 8` | steady-state worker/database 관찰 기준 |
| 보수적 peak concurrency | `50 uploads/s × p99 40초 = 2,000` | timeout·throttle·downstream stress bound; 보장 용량 아님 |
| 평균 object의 peak ingress | `50/s × 8 MB = 400 MB/s` | 정상 peak network/object/queue metadata 시험 입력 |
| 최대 object stress bound | `50/s × 100 MB = 5,000 MB/s(약 5 GB/s)` | admission·backpressure가 필요한 upper bound |
| invalid / transient | `1% / 2%` | peak에서 각각 0.5/s terminal, 1/s retry 후보 |
| dominant tenant | 전체 workload의 최대 30% | per-tenant fairness와 blast radius 입력 |

평상시에는 invalid가 평균 0.02/s, transient가 0.04/s이며 peak에서는 각각 0.5/s, 1/s다. retry는 transient만 대상으로 하며 duplicate effect를 만들지 않아야 한다. 실제 provider SLA, failover, cold start, throughput, quota, region-wide behavior와 가격은 `unmeasured/unknown`이다.

일반 retry·idempotency·Outbox·DLQ 이론은 `distributed-services`, DB engine 복구 내부는 `database-systems`, credential 공격·incident response는 `cybersecurity`로 넘긴다. 여기서는 그 계약을 각 cloud stage의 소유 책임, failure domain과 evidence에 적용한다.

## Stage 1 — IaaS

두 zone에 application capacity와 health-checked routing을 배치하고 database recovery copy/failover target을 단일 compute failure domain 밖에 둔다. 각 zone은 평상시 2/s를 단독 처리하고, zone 하나를 제거한 시험에서 50/s peak와 backlog recovery를 RTO 안에 만족해야 production peak-ready로 승인한다. 보수적 2,000 concurrency·400 MB/s와 5 GB/s max-object stress bound의 실제 통과 여부는 아직 미측정이므로 admission limit 없이 승인하지 않는다.

| Failure | Detection / public impact | Partial state | Recovery·reconciliation | RPO/RTO evidence |
| --- | --- | --- | --- | --- |
| process/VM loss | health probe, request error·queue age 상승; in-flight request는 결과 불명 | upload reservation, temp object, expired processing lease | healthy zone/VM으로 route, lease 만료 뒤 same operation retry, temp inventory cleanup | alarm→route recovery time, operation trace, error/latency graph |
| zone-a compute loss | zone health와 target loss; 남은 zone에서 latency/throttle 가능 | lost VM local temp만 허용; durable queue/object/DB는 유지 | failed zone target 제거, zone-b scale/admission, backlog drain, replacement inventory | zone-loss start→public invariant recovery ≤60분; lost accepted state ≤15분 |
| database primary loss | connection reset, transaction result ambiguous | commit됐지만 client timeout, replica lag까지의 RPO exposure | operation ID로 outcome 조회, failover 후 write gate·checksum, isolated restore 필요 시 수행 | last durable point와 incident start 차 ≤15분; read/write recovery ≤60분 |
| object write와 metadata commit 분리 | operation deadline·reconciler diff | object만 존재 또는 metadata만 queued | checksum/key로 기존 object 재사용, metadata 수렴; 만료 orphan만 inventory 후 삭제 | before/after DB-object inventory, object checksum, operation terminal reason |
| network partition/egress loss | dependency timeout·flow alarm | accepted request, queued work, delivery 결과 불명 | 신규 admission 제한, bounded timeout, authoritative outcome 조회, route 복구 뒤 drain | dependency/route trace, duplicate effect 0, queue age 회복 |
| image/config/credential 손실 | replacement boot·auth failure | 실행 capacity 감소; durable data 영향 없어야 함 | versioned image/config와 workload identity로 clean rebuild, revoked credential inventory | clean-room rebuild time, digest/policy revision, final binding list |

backup ID 존재는 recovery evidence가 아니다. production과 격리된 environment에 engine/version/config를 복원하고 representative upload·metadata checksum과 tenant counts를 비교한 뒤에만 restore 성공으로 판정한다.

## Stage 2 — Managed platform

managed service가 일부 장애 조치를 수행해도 consumer는 client ambiguity, application health, RPO/RTO acceptance, quota와 exit를 소유한다.

| Managed failure | Provider action / contract | Consumer failure와 partial state | Recovery / acceptance | Unknown to close |
| --- | --- | --- | --- | --- |
| runtime restart/maintenance | instance 교체·배치 primitive | in-flight HTTP 결과 불명, cold capacity·connection churn | operation ID 조회, health/readiness, old revision rollback, backlog drain | restart SLA, minimum capacity, scaling latency |
| database failover | replica promotion·endpoint update primitive | connection reset, commit 결과 불명, replica lag | idempotent operation lookup, pool recycle, read/write/checksum suite | failover time, lag/RPO, transaction semantics |
| queue delay/duplicate/outage | durable delivery·redelivery primitive | queue age 증가, duplicate, ack 결과 불명 | admission/backpressure, same operation effect 재사용, DLQ inventory | retention, delivery guarantee, throughput quota |
| object throttle/outage | retryable API·durability contract | upload/result write 결과 불명, temp object | checksum/head로 outcome 확인, bounded retry, metadata/object reconciliation | throughput/request limit, regional scope |
| control plane unavailable | 기존 data plane이 계속될 수 있음 | deploy, scale, policy/trigger 변경 불가 | stable revision 유지, 자동 변경 중단, data-plane health와 capacity 보호 | control/data plane failure domain, escalation time |
| automated backup restore 실패 | backup 생성·보관 primitive | RPO/RTO 증거 없음, format/key/version mismatch 가능 | isolated restore drill 실패 시 release 차단, alternate export/rebuild runbook | actual restore time, retention, key dependency |

provider failover가 끝났다는 status와 고객 요청이 올바르게 처리된 상태를 구분한다. connection·transaction outcome, queue/event, object checksum, application invariant를 다시 검사한다. provider가 미선정이므로 위 limit·SLA는 모두 현재 unknown이다.

## Stage 3 — FaaS

초기 application contract는 handler timeout 60초, transient 최대 3 attempts, event maximum age 15분이다. 이는 p99 40초에 여유를 두고 RPO 목표 밖의 무한 retry를 막기 위한 시작값이며 provider limit·실측 latency 뒤 versioning한다. invalid input은 retry하지 않고 terminal reason을 기록한다.

| Injection / failure | Public invariant | Durable intermediate state | Retry / terminal rule | Capacity·tenant guard | Evidence |
| --- | --- | --- | --- | --- | --- |
| duplicate event | output·document success·usage는 operation당 한 번 | existing idempotency/result record | 기존 effect 반환 후 ack; 새 usage 금지 | duplicate가 concurrency/cost를 무한 증폭하지 않음 | attempts, duplicate-suppressed, output/usage cardinality |
| result write 뒤 timeout | 같은 deterministic result를 재사용 | result object 존재, document `PROCESSING`, usage 미accept | retry가 checksum 확인→status/usage 수렴; 새 key 금지 | same operation active work 중복 제한 | timeout trace, object checksum, final state |
| invalid file 1% | 명확한 client-visible failure, usage 정책 일관 | terminal `INVALID` + reason; output 없음 | 즉시 terminal, DLQ/retry 금지 | peak 0.5/s가 worker를 점유하지 않음 | invalid count/rate, attempts=1, output 0 |
| transient failure 2% | eventual success 또는 설명 가능한 terminal | attempt/reason/next eligibility | 최대 3 attempts·15분; 초과 시 DLQ | peak base 1/s retry 후보에 backoff+jitter | attempt histogram, age, terminal/DLQ count |
| poison file / DLQ replay | 다른 tenant와 healthy work 진행 | immutable original envelope + disposition | human/automation review 후 same operation replay | tenant별 DLQ·replay rate guard | approver, original/replay ID, before/after |
| concurrency throttle/cold start | admission된 요청의 상태가 유실되지 않음 | queue와 quota reservation 유지 | throttle을 transient로 분류하되 maximum age 적용 | global stress bound 2,000; 한 tenant 최대 30% initial cap | tenant queued/running/throttled, latency, cost units |
| event result 후 usage 실패 | 처리 결과와 billable usage가 eventually 일치 | output/status success, usage pending | same operation usage upsert/reconcile | quota reservation은 outcome까지 유지 | accepted usage 1개, reservation terminal |

`50/s × 40초 = 2,000`은 worst-case admission을 검토하는 보수적 bound이지 function을 무조건 2,000개 열라는 의미가 아니다. database/object/queue limit과 월 budget에 맞춰 낮은 concurrency와 backpressure를 선택할 수 있다. dominant tenant cap은 workload의 30%에서 시작하며 tenant별 latency와 계약을 근거로 조정한다. cold start·provider concurrency와 실제 cost는 미측정이다.

## Stage 4 — SaaS

| SaaS failure | 지켜야 할 invariant | Intermediate / blocked state | Reconciliation / compensation | Deadline·customer evidence |
| --- | --- | --- | --- | --- |
| quota reservation race | starter 100, pro 10,000을 동시 요청에도 초과 승인하지 않음 | `RESERVED`; operation과 billing period에 결합 | atomic compare/reserve, 실패 시 release; usage는 operation당 한 번 commit | ledger equation과 concurrent test trace |
| usage write partial failure | successful billable outcome과 accepted usage가 1:1 | result success, `USAGE_PENDING` | operation ID로 idempotent usage upsert, dashboard reconcile | usage/result diff 0 또는 owner 있는 pending |
| plan/subscription update partial | 한 operation은 하나의 plan version으로 판단 | requested plan, entitlement 적용 전/후 분리 | versioned state machine; billing integration 실패 시 기존 entitlement 유지 | before/after audit와 customer-visible effective time |
| cross-tenant request | tenant B read/write/usage가 0 | authorization에서 terminal deny; background work 생성 금지 | compensation보다 fail-closed, suspected incident는 security handoff | negative test와 B state hash/audit |
| export job failure | authorized snapshot을 24시간 안에 준비하거나 명시 실패·owner | `REQUESTED/SNAPSHOTTED/BUILDING/DELIVERY_PENDING` | step별 retry, immutable manifest/checksum, recipient 재검증 | request→ready ≤24시간, failed-step trace와 customer notice |
| deletion subsystem failure | request 후 7일 안에 active data 0; deleted tenant 접근 금지 | subsystem별 cursor, tombstone, backup-retained notice | idempotent delete·reconcile, deadline alarm, subsystem owner escalation | final DB/object/cache/queue/analytics inventory, backup schedule 고지 |
| budget/cost anomaly | 신규 비용을 제한해도 accepted work·tenant 경계 훼손 금지 | admission reduced, queued work 보존 | concurrency/rate/log guard, orphan cleanup, cost owner review | alarm, resource/usage diff, 변경·rollback record; 가격 unknown |

export 실패를 다른 tenant artifact로 대체하거나 deletion deadline을 backup physical deletion과 혼동하지 않는다. active data 제거와 provider backup retention은 별도 약속이며 후자는 계약 선택 후 고객에게 정확히 고지한다.

## Evidence와 한계

| Drill / test | Injection | Pass criteria | Captured evidence | 증명하지 못하는 것 |
| --- | --- | --- | --- | --- |
| single-zone compute loss | zone-a targets·compute 제거, representative 50/s traffic | public invariant recovery ≤60분, accepted data loss ≤15분, backlog 수렴 | alarm time, error/latency, queue age, operation trace, final inventory | 실제 시험 전 capacity는 `unmeasured` |
| isolated database restore | production과 분리된 target에 목표 시점 restore | selected restore point가 incident 전 15분 이내, usable ≤60분, checksum/count match | backup ID, restore start/end, engine/config, checksum report | managed provider-wide outage 전체 |
| managed failover/reconnect | test profile에서 failover·maintenance | ambiguous operations가 중복 effect 없이 terminal 수렴 | connection error, operation IDs, before/after checksum | provider 미선정이라 현재 local model만 가능 |
| duplicate·timeout·DLQ | 같은 event 반복, result write 뒤 강제 timeout, poison replay | output/status/usage 1개, invalid 1 attempt, bounded transient, replay audit | event/attempt trace, object checksum, DLQ disposition | 실제 provider delivery/cold-start SLA |
| quota race·tenant deny | starter/pro boundary의 concurrent request와 forged tenant context | accepted ≤100/10,000, duplicate usage 0, other-tenant state change 0 | reservation/usage ledger, negative-test before/after | 모든 application path의 formal proof |
| export/deletion reconcile | 각 subsystem step 실패·재시작 | export ready ≤24시간; active deletion inventory 0 ≤7일 | step timestamps, manifest/checksum, final inventory, notice | provider physical backup deletion 시점 |

모든 drill은 alarm 발생 시각, incident start, first detection, mitigation, public recovery, final reconciliation을 분리해 기록한다. restore checksum과 final inventory가 없으면 RTO/RPO 성공으로 표시하지 않는다. local model과 문서 review는 실제 provider zone/control-plane failure, SLA, IAM/network guarantee, capacity와 price를 증명하지 않는다.

## Open risks와 owner

| Risk / unmeasured item | Owner | 닫는 trigger | Required experiment / evidence | 실패 시 rollback·decision |
| --- | --- | --- | --- | --- |
| zone loss 뒤 2,000 concurrency·400 MB/s 처리 | runtime owner | production capacity 승인 전 | provider sandbox zone-loss load test와 backlog/RTO report | admission rate·max size 축소 또는 release defer |
| 5 GB/s max-object stress bound | runtime/cost owner | 100 MB·50/s 지원 주장 전 | ingress/object/downstream throttle·cost test | per-tenant/global rate·size guard 강화 |
| managed DB failover와 restore time | data owner | authoritative production data 수용 전 | failover ambiguity test와 isolated restore checksum | alternate profile 또는 launch defer |
| region/control-plane/provider support failure | runtime owner | provider shortlist 승인 전 | failure-domain/SLA/escalation review와 sandbox evidence | single-region limitation 공개, risky change freeze |
| export 24시간·deletion 7일 대규모 capacity | data/product owner | enterprise tenant onboarding 전 | representative volume rehearsal와 subsystem inventory | tenant size gate·조건부 onboarding |
| 실제 provider 가격·retry 비용 | cost owner | provider 선택·매월 | versioned estimate, budget alarm, billing/usage reconciliation | concurrency·attempt·retention 축소; 현재 unknown |
