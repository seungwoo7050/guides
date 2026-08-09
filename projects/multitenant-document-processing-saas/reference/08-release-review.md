# release review

## Scope

네 stage 중 초기 production은 managed runtime+managed database+queue+object storage와 FaaS worker, SaaS tenant layer 조합을 선택한다.

## Stage 1 — IaaS

제어력은 높지만 작은 팀의 host·database 운영 부담과 image drift가 크다. isolated recovery profile로 유지하되 주 runtime으로 선택하지 않는다.

## Stage 2 — Managed platform

표준 API workload에 적합하다. private access, version lifecycle, restore drill, quota와 export를 조건으로 승인한다.

## Stage 3 — FaaS

bursty document processing에 적합하다. duplicate-safe output, bounded retry, per-tenant concurrency와 cost guard를 필수 조건으로 둔다.

## Stage 4 — SaaS

tenant context, composite key, cache/job isolation, atomic quota, usage deduplication, support audit, export와 deletion evidence가 필요하다.

## Evidence와 한계

local cloud model reference, document reviews, restore rehearsal, zone test, cross-tenant negative test, cost estimate와 migration sample을 사용한다. 실제 provider limit·SLA·price는 선택 뒤 재확인한다.

## Open risks와 owner

`APPROVE_WITH_CONDITIONS`다. provider selection, actual IAM/network test, 100 GB export throughput, database failover와 customer deletion wording을 각각 runtime·security·data·product owner가 닫는다.
