# failure and recovery plan

## Scope

이 문서는 instance·zone·managed control plane·event delivery·quota·tenant lifecycle·cost anomaly의 실패를 공개 상태와 불변식으로 정의한다. 목표 RPO는 15분, RTO는 60분이다. "재시도한다"가 아니라 partial state를 누가 탐지하고 어떤 순서로 수렴시키며 무엇으로 복구 완료를 판정하는지 적는다.

| 입력 / 계산 | 값 | 이 계획에서 검증할 limit |
| --- | --- | --- |
| 평상시 uploads / 평균 처리 | `2/s × 4s = TODO concurrency` | TODO |
| peak uploads / p99 처리 | `50/s × 40s = TODO conservative concurrency` | TODO |
| 평균 object peak ingress | `50/s × 8 MB = TODO` | TODO |
| 최대 object stress bound | `50/s × 100 MB = TODO` | TODO |
| invalid / transient | `1% / 2%` | TODO |
| single enterprise tenant | `30% workload` | TODO |

provider SLA·실제 failover·throughput·price는 아직 `unmeasured/unknown`이다. 일반 분산 retry/idempotency 자체는 인접 소유 가이드로 넘기고 여기서는 cloud stage의 event·failure contract에 적용한다.

## Stage 1 — IaaS

| Failure | Detection / alarm | Public impact | Partial state | Recovery / reconciler | RPO/RTO evidence |
| --- | --- | --- | --- | --- | --- |
| VM process / instance loss | TODO | TODO | TODO | TODO | TODO |
| 한 zone compute loss | TODO | TODO | TODO | TODO | TODO |
| database primary loss | TODO | TODO | TODO | TODO | TODO |
| object write / metadata commit split | TODO | TODO | TODO | TODO | TODO |
| network partition / egress loss | TODO | TODO | TODO | TODO | TODO |
| credential / image loss | TODO | TODO | TODO | TODO | TODO |

두 zone에 둔 capacity가 zone 하나를 잃은 뒤 어느 workload까지 버티는지 TODO로 수치화한다. isolated environment restore, checksum, clean image/config rebuild, DNS·load balancer 전환과 final resource inventory를 복구 단계에 포함한다.

## Stage 2 — Managed platform

| Managed failure | Provider action / contract | Consumer가 해야 할 일 | Ambiguous result | Recovery test | Unknown |
| --- | --- | --- | --- | --- | --- |
| runtime restart / maintenance | TODO | TODO | TODO | TODO | TODO |
| database failover | TODO | TODO | TODO | TODO | TODO |
| queue delay / duplicate / outage | TODO | TODO | TODO | TODO | TODO |
| object service throttling | TODO | TODO | TODO | TODO | TODO |
| control plane unavailable | TODO | TODO | TODO | TODO | TODO |
| backup exists but restore 실패 | TODO | TODO | TODO | TODO | TODO |

자동 backup 생성과 실제 restore 성공을 분리한다. connection reset, transaction 결과 불명, quota exhaustion, regional control-plane scope와 provider escalation 시간을 TODO로 명시한다.

## Stage 3 — FaaS

| Injection / event failure | Expected public behavior | Durable intermediate state | Retry / terminal rule | Capacity·tenant guard | Evidence |
| --- | --- | --- | --- | --- | --- |
| duplicate event | TODO | TODO | TODO | TODO | TODO |
| result write 뒤 timeout | TODO | TODO | TODO | TODO | TODO |
| invalid file 1% | TODO | TODO | TODO | TODO | TODO |
| transient failure 2% | TODO | TODO | TODO | TODO | TODO |
| poison file / DLQ replay | TODO | TODO | TODO | TODO | TODO |
| concurrency throttle / cold start | TODO | TODO | TODO | TODO | TODO |

peak에서 invalid가 초당 `TODO`, transient가 초당 `TODO` 발생하는지 계산한다. duplicate가 output과 usage를 한 번만 만들고, retry가 보수적 2,000 concurrency·downstream limit·30% tenant fairness를 깨지 않도록 maximum attempt·age·timeout·concurrency와 DLQ owner를 TODO로 정한다.

## Stage 4 — SaaS

| SaaS failure | Invariant | Intermediate / blocked state | Reconciliation / compensation | Deadline | Customer evidence |
| --- | --- | --- | --- | --- | --- |
| quota reservation race | TODO | TODO | TODO | TODO | TODO |
| usage write partial failure | TODO | TODO | TODO | TODO | TODO |
| plan/subscription update partial failure | TODO | TODO | TODO | TODO | TODO |
| cross-tenant request | TODO | TODO | TODO | TODO | TODO |
| export job failure | TODO | TODO | TODO | 24시간 | TODO |
| deletion subsystem failure | TODO | TODO | TODO | active data 7일 | TODO |
| budget / cost anomaly | TODO | TODO | TODO | TODO | TODO |

starter 100건/월과 pro 10,000건/월 quota가 race에도 초과 승인되지 않도록 atomic reservation과 idempotent usage의 경계를 TODO로 적는다. deletion은 하나의 boolean이 아니라 subsystem별 상태와 tombstone, retry, backup-retention notice를 가진 workflow로 다룬다.

## Evidence와 한계

| Drill / test | Preconditions | Injected failure | Pass criteria | Captured evidence | 한계 |
| --- | --- | --- | --- | --- | --- |
| single-zone compute loss | TODO | TODO | TODO | TODO | TODO |
| isolated database restore | TODO | TODO | TODO | TODO | TODO |
| managed failover / reconnect | TODO | TODO | TODO | TODO | provider 미선정 |
| duplicate·timeout·DLQ replay | TODO | TODO | TODO | TODO | TODO |
| quota race / cross-tenant deny | TODO | TODO | TODO | TODO | TODO |
| export/deletion reconciliation | TODO | TODO | TODO | TODO | physical deletion unknown |

alarm 발생 시각, incident start/end, error·latency, operation ID, restore checksum, RPO/RTO 계산, event trace와 final inventory를 증거로 남긴다. local model이 실제 zone/control-plane 장애와 provider SLA를 재현하지 못한다는 한계를 TODO로 기술한다.

## Open risks와 owner

| Risk / unmeasured item | Owner | Due / trigger | Required experiment | Rollback / decision effect |
| --- | --- | --- | --- | --- |
| 2,000 concurrency와 400 MB/s / 5 GB/s bound | TODO | TODO | TODO | TODO |
| region-wide / control-plane failure | TODO | TODO | TODO | TODO |
| 실제 database failover와 restore time | TODO | TODO | TODO | TODO |
| export 24시간 / deletion 7일 capacity | TODO | TODO | TODO | TODO |
| provider support와 가격 unknown | TODO | TODO | TODO | TODO |
