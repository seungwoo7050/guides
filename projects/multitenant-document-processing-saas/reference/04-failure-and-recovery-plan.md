# failure and recovery plan

## Scope

instance·zone·managed service·event·quota·tenant deletion·cost anomaly를 포함한다. 목표는 RPO 15분, RTO 60분이다.

## Stage 1 — IaaS

두 zone에 application capacity를 배치하고 zone 하나 제거 뒤 peak를 처리한다. database backup을 isolated environment에 restore하고 image·configuration으로 clean rebuild한다.

## Stage 2 — Managed platform

provider failover와 maintenance 중 client connection·transaction 결과를 검사한다. automated backup과 실제 restore를 분리한다.

## Stage 3 — FaaS

duplicate, result-write 뒤 timeout, poison file, throttle와 DLQ replay를 주입한다. idempotency와 bounded retry로 상태를 수렴시킨다.

## Stage 4 — SaaS

quota race, subscription update partial failure, tenant export failure와 deletion retry를 다룬다. subsystem별 deletion status와 reconciliation을 둔다.

## Evidence와 한계

alarm time, error·latency, operation ID, restore checksum, event trace, final inventory와 RTO/RPO report를 보존한다. local model은 provider outage를 재현하지 못한다.

## Open risks와 owner

region-wide failure와 provider support dependency는 runtime owner가 선택 profile에서 검토한다.
