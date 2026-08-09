# resource and state inventory

## Scope

resource ID, owner, region/zone, stateful 여부, data class, dependency, backup, cost center와 expiry를 관리한다.

## Stage 1 — IaaS

load balancer, VM pool, private database, object storage, public/private network, image, identity, snapshot, log sink가 있다. VM local file은 ephemeral, database·upload는 authoritative, thumbnail은 derived다.

## Stage 2 — Managed platform

VM과 self-managed database를 managed runtime·database·queue로 교체한다. hidden replica·maintenance·quota는 service contract로 추적한다.

## Stage 3 — FaaS

function version, trigger mapping, concurrency, DLQ, result object와 idempotency record를 inventory에 추가한다. execution environment는 resource 정본이 아니다.

## Stage 4 — SaaS

tenant, membership, plan version, subscription, entitlement, quota reservation, usage event, export job와 deletion workflow를 commercial/business state로 추가한다.

## Evidence와 한계

provider inventory export, release manifest, object inventory와 database schema를 대조한다. provider 내부 node는 직접 inventory할 수 없다.

## Open risks와 owner

owner·expiry 없는 shared resource와 provider backup 잔존을 runtime/data owner가 분기별 검토한다.
