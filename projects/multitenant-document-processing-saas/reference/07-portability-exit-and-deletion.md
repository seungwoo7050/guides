# portability exit and deletion

## Scope

source, artifact, runtime, data, identity, operation과 commercial dependency를 lock-in register에 기록한다.

## Stage 1 — IaaS

image·configuration·backup으로 clean environment를 만들고 DNS를 전환한다. volume·snapshot·address·log와 key cleanup을 확인한다.

## Stage 2 — Managed platform

database full/incremental export, queue drain, object inventory, identity·network mapping과 provider backup retention을 계획한다.

## Stage 3 — FaaS

handler code뿐 아니라 trigger schema, retry·ordering, concurrency, DLQ, identity와 observability를 대상 platform에 매핑한다.

## Stage 4 — SaaS

tenant export format, membership·setting·attachment·usage, delivery identity, deletion workflow와 customer notice를 제공한다.

## Evidence와 한계

representative data migration rehearsal로 throughput, checksum, duration과 egress cost를 측정한다. provider physical deletion은 contract evidence에 의존할 수 있다.

## Open risks와 owner

10 TB 이상 data growth와 commitment가 exit cost를 높일 수 있으므로 data/cost owner가 분기별 trigger를 검토한다.
