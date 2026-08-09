# release review

## Scope

IaaS, managed platform, FaaS와 SaaS tenant layer를 책임·실패·비용·가용성·portability·evidence로 비교해 하나의 release 결정을 내린다. system brief의 2/s·50/s, 8 MB·100 MB, 평균 4초·p99 40초, invalid 1%·transient 2%·단일 tenant 30%, RPO 15분·RTO 60분, Starter 100·Pro 10,000건/월, export 24시간·active deletion 7일을 acceptance input으로 사용한다.

최종 줄은 정확히 하나만 작성한다: `Decision: APPROVE`, `Decision: APPROVE_WITH_CONDITIONS`, `Decision: DEFER`, `Decision: REJECT`.

## Stage 1 — IaaS

| review axis | finding | evidence | remaining responsibility |
|---|---|---|---|
| control/portability | TODO | TODO | TODO |
| zone failure/RTO·RPO | TODO | TODO | TODO |
| patch/scaling/cost | TODO | TODO | TODO |

TODO: 작은 팀이 host·database를 직접 운영할 때 얻는 제어와 image drift, patch, backup restore, capacity 책임을 비교한다.

## Stage 2 — Managed platform

TODO: managed runtime, database, queue와 object storage로 이동한 책임과 여전히 소비자가 소유하는 schema, identity, limit, restore, client retry, cost와 exit를 적는다. 공급자를 선택하지 않았다면 SLA·limit·price는 unmeasured/unknown으로 표시한다.

## Stage 3 — FaaS

평균 동시성 8, 보수적 peak 2,000, 평균 크기 peak ingress 400 MB/s, 최대 크기 5 GB/s stress를 기준으로 timeout, cold start, bounded retry, downstream capacity, tenant별 30% fairness와 cost guard를 판정한다.

TODO: invalid 1%와 transient 2%를 분리한 failure injection, duplicate-safe output·usage와 DLQ replay evidence가 없으면 승인 조건으로 올린다.

## Stage 4 — SaaS

TODO: request/DB/object/cache/queue/function/analytics/support/export/deletion의 tenant context, membership/role, Starter 100·Pro 10,000 quota, idempotent usage, export 24시간과 active deletion 7일 evidence를 검토한다. control plane과 data plane owner도 분리한다.

## Evidence와 한계

| required evidence | 상태 | 무엇을 입증 | 입증하지 못하는 것 |
|---|---|---|---|
| local cloud model report | TODO | state/isolation/quota/event/delete 공개 행동 | 실제 IAM·network/provider SLA |
| restore/zone rehearsal | TODO | RPO 15분·RTO 60분 | region-wide failure |
| tenant negative test | TODO | 관찰한 경로의 격리 | 모든 application query |
| cost/export sample | TODO | 측정 sample | 실제 월 가격·성장률 |

TODO: 자동 검사 통과가 architecture의 기술적 타당성이나 교육적 완료를 자동 승인하지 않음을 명시한다.

## Open risks와 owner

결정 조건은 각각 owner, 유효한 ISO due date, verification과 rollback을 가져야 한다.

| condition/risk | owner | due date | verification | rollback |
|---|---|---|---|---|
| TODO | TODO | TODO: YYYY-MM-DD | TODO | TODO |
| TODO | TODO | TODO: YYYY-MM-DD | TODO | TODO |
| TODO | TODO | TODO: YYYY-MM-DD | TODO | TODO |

Decision: TODO
