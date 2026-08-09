# identity network and tenant boundaries

## Scope

이 문서는 human, workload, deployment automation, customer admin/member, support identity를 분리하고 cloud control plane과 application data plane의 권한을 독립적으로 검토한다. 모든 request·database row·object·cache·queue·function·analytics·support·export·deletion 흐름에서 tenant context가 어디서 만들어지고 어디서 다시 검증되는지 추적한다.

tenant는 B2B organization이며 한 사용자는 여러 tenant에 속할 수 있다. 따라서 client가 보낸 tenant ID만 신뢰해서는 안 된다. 인증 프로토콜·공격 기법 전체와 관계 스키마 설계는 인접 소유 가이드로 넘기고, 이 문서는 cloud resource policy와 tenant isolation 적용만 TODO로 완성한다.

| Identity class | 발급자 / source | 허용 동작 | 금지 동작 | Credential lifetime | Audit evidence |
| --- | --- | --- | --- | --- | --- |
| customer member | TODO | TODO | TODO | TODO | TODO |
| customer admin | TODO | TODO | TODO | TODO | TODO |
| application workload | TODO | TODO | TODO | TODO | TODO |
| processing function | TODO | TODO | TODO | TODO | TODO |
| deployment / migration automation | TODO | TODO | TODO | TODO | TODO |
| support operator | TODO | TODO | TODO | TODO | TODO |

## Stage 1 — IaaS

| Flow / boundary | Public ingress | Private hop | Identity / policy decision | Tenant context source | Negative test |
| --- | --- | --- | --- | --- | --- |
| upload request | TODO | TODO | TODO | TODO | TODO |
| metadata read/write | TODO | TODO | TODO | TODO | TODO |
| object put/get | TODO | TODO | TODO | TODO | TODO |
| async queue publish/consume | TODO | TODO | TODO | TODO | TODO |
| admin / SSH / break-glass | TODO | TODO | TODO | TODO | TODO |

public endpoint를 TODO로 한정하고 VM·database·object access가 private 또는 resource policy로 제한되는지 적는다. application runtime identity와 human admin identity를 공유하지 않는다. tenant A token으로 tenant B metadata, guessed object key, cache key, queue operation을 읽는 대표 실패를 설계한다.

## Stage 2 — Managed platform

managed runtime/database/queue/object storage 사이의 service identity와 private attachment를 채운다. "같은 provider account"나 "managed service"는 신뢰 경계가 아니다.

| Managed connection | Calling identity | Resource policy / network gate | Data-plane tenant check | Control-plane owner | Evidence |
| --- | --- | --- | --- | --- | --- |
| runtime → database | TODO | TODO | TODO | TODO | TODO |
| runtime → object storage | TODO | TODO | TODO | TODO | TODO |
| runtime → queue | TODO | TODO | TODO | TODO | TODO |
| migration → database | TODO | TODO | TODO | TODO | TODO |
| backup / restore | TODO | TODO | TODO | TODO | TODO |

admin·migration·backup identity를 runtime에서 분리하고, secret rotation·service attachment·audit log의 owner를 TODO로 정한다. provider가 실제로 보장하는 private path, IAM propagation, control-plane regionality는 미선정이므로 `unmeasured/unknown`이다.

## Stage 3 — FaaS

function은 source object read, deterministic result write, status·usage update에 필요한 권한만 가진다. trigger enable/disable, concurrency 변경, function 배포는 runtime identity가 아니라 automation identity가 소유한다.

| Event field / action | Trusted source | 재검증 | Function permission | Cross-tenant / abuse failure | Guard |
| --- | --- | --- | --- | --- | --- |
| operation ID | TODO | TODO | TODO | TODO | TODO |
| tenant context | TODO | TODO | TODO | TODO | TODO |
| source object key | TODO | TODO | TODO | TODO | TODO |
| result object key | TODO | TODO | TODO | TODO | TODO |
| usage·quota update | TODO | TODO | TODO | TODO | TODO |
| DLQ replay | TODO | TODO | TODO | TODO | TODO |

enterprise tenant 하나가 workload의 30%를 만들 수 있을 때 다른 tenant가 굶지 않도록 global·per-tenant concurrency 정책과 관측 증거를 TODO로 정한다. 실제 provider의 concurrency·cold start·IAM limit은 `unmeasured/unknown`이다.

## Stage 4 — SaaS

| Surface | Tenant context derivation | Isolation key / policy | Customer admin 권한 | SaaS provider 의무 | Representative deny test |
| --- | --- | --- | --- | --- | --- |
| API request | TODO | TODO | TODO | TODO | TODO |
| database | TODO | TODO | TODO | TODO | TODO |
| object / download | TODO | TODO | TODO | TODO | TODO |
| cache | TODO | TODO | TODO | TODO | TODO |
| queue / function | TODO | TODO | TODO | TODO | TODO |
| analytics / usage | TODO | TODO | TODO | TODO | TODO |
| support session | TODO | TODO | TODO | TODO | TODO |
| export / deletion | TODO | TODO | TODO | TODO | TODO |

membership lookup으로 active tenant context를 만든 뒤 모든 downstream key에 전파하고 다시 검증하는 흐름을 TODO로 그린다. 고객 admin은 자기 tenant의 member·role·sharing만 바꿀 수 있고, SaaS 공급자는 isolation, support audit, export 24시간, active deletion 7일과 backup retention 고지를 책임진다.

## Evidence와 한계

| Claim | Test / observation | Expected result | Evidence | 이 증거의 한계 |
| --- | --- | --- | --- | --- |
| tenant A는 tenant B metadata를 읽지 못한다 | TODO | TODO | TODO | TODO |
| guessed object/cache key도 경계를 우회하지 못한다 | TODO | TODO | TODO | TODO |
| queue/function에 tenant context가 보존된다 | TODO | TODO | TODO | TODO |
| support access가 승인·시간 제한·감사된다 | TODO | TODO | TODO | TODO |
| public endpoint가 allowlist와 같다 | TODO | TODO | TODO | TODO |
| least privilege가 실제 provider policy에 적용된다 | TODO | TODO | TODO | provider 미선정 |

로컬 negative test, policy simulation, public endpoint scan, audit event를 구분한다. policy simulation은 application의 누락된 tenant predicate를 증명하지 않고, local test는 실제 provider network/IAM 보장을 증명하지 않는다.

## Open risks와 owner

| Risk / unknown | Owner | Due / trigger | Verification | Containment / handoff |
| --- | --- | --- | --- | --- |
| provider identity·private network 동작 unknown | TODO | TODO | TODO | TODO |
| metadata credential / SSRF 경계 | TODO | TODO | TODO | 보안 전문 가이드로 handoff |
| support impersonation과 break-glass | TODO | TODO | TODO | TODO |
| analytics/export tenant leakage | TODO | TODO | TODO | TODO |
| 30% enterprise tenant의 fairness | TODO | TODO | TODO | TODO |
