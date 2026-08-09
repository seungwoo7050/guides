# identity network and tenant boundaries

## Scope

human, workload, automation, customer와 support identity를 분리한다. control plane과 application data plane을 별도 policy로 관리한다.

## Stage 1 — IaaS

public ingress는 load balancer만 허용한다. VM·database는 private이며 VM workload identity는 tenant object와 database operation에 필요한 최소 권한만 가진다.

## Stage 2 — Managed platform

runtime identity와 managed service resource policy를 연결한다. admin·migration·backup identity는 application runtime과 분리한다.

## Stage 3 — FaaS

function identity는 source read, result write, status·usage update만 허용한다. trigger disable과 concurrency 변경은 deployment automation만 수행한다.

## Stage 4 — SaaS

request tenant context는 membership에서 만들고 body의 tenant ID를 신뢰하지 않는다. cache key·queue payload·object prefix·export·support session에 tenant를 포함한다.

## Evidence와 한계

cross-tenant negative test, public endpoint scan, policy simulation, audit event와 support access log를 사용한다. policy simulation은 runtime application bug를 증명하지 않는다.

## Open risks와 owner

metadata credential, support impersonation과 analytics export는 security owner가 threat model과 test를 유지한다.
