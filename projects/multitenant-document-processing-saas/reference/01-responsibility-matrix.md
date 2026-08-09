# responsibility matrix

## Scope

문서 upload·async processing·tenant product state를 대상으로 한다. business owner는 product, runtime owner는 cloud application team, data owner는 product/security, cost owner는 engineering manager다.

## Stage 1 — IaaS

공급자는 physical host와 hypervisor를 관리한다. 소비자는 image·OS patch·network·VM scaling·database 운영·backup·application·data·cost를 관리한다.

## Stage 2 — Managed platform

runtime host, database engine patch, queue infrastructure와 object durability 일부가 공급자에게 이동한다. 소비자는 code, schema, identity, limit, backup restore 검증, client retry와 exit를 소유한다.

## Stage 3 — FaaS

execution environment lifecycle와 invocation scaling이 공급자에게 이동한다. 소비자는 handler, event identity, timeout, concurrency, idempotency, DLQ, downstream capacity와 cost guard를 소유한다.

## Stage 4 — SaaS

공급자는 tenant-facing application 전체를 운영한다. 고객 admin은 membership·sharing·integration을 관리한다. SaaS 공급자는 isolation, entitlement, quota, metering, support access, export와 deletion을 소유한다.

## Evidence와 한계

책임은 task별 official contract, operation log, restore report와 negative test로 확인한다. service label만으로 실제 책임을 확정하지 않는다.

## Open risks와 owner

provider support access, physical deletion, regional control plane scope는 공급자 계약에 의존한다. cloud application owner가 provider 선택 시 닫는다.
