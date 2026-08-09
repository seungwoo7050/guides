# cost quota and metering

## Scope

cost per 1000 successful documents와 active tenant를 핵심 unit으로 사용한다. provider bill과 SaaS usage를 분리한다.

## Stage 1 — IaaS

VM, database, load balancer, storage, backup, log와 egress의 idle·variable cost를 계산한다. owner·expiry 없는 resource를 거부한다.

## Stage 2 — Managed platform

minimum capacity, request/throughput unit, managed backup와 private network premium을 포함한다. service limit와 quota increase lead time을 기록한다.

## Stage 3 — FaaS

invocation·duration·memory·retry·DLQ·log·egress와 provisioned warm capacity를 계산한다. maximum concurrency·attempt로 비용 폭주를 제한한다.

## Stage 4 — SaaS

starter/pro entitlement, atomic quota reservation, idempotent usage event와 tenant storage·egress attribution을 구현한다. billing price rule은 raw metering과 분리한다.

## Evidence와 한계

billing export, resource inventory, usage event와 outcome count를 대조한다. estimate는 pricing·traffic 변화 때문에 정기적으로 갱신한다.

## Open risks와 owner

shared database·support cost allocation rule은 finance/product와 함께 versioning한다.
