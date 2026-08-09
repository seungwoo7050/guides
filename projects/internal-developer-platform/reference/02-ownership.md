# Ownership Contract

## 공통 식별자

공통 연결 키는 `svc-payments`, `env-payments-staging`, `op-payments-staging-v3`, `tenant-checkout`, `sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`, `stateless-http/v3`이다. incident, change, evidence와 support ticket은 이 키를 보존한다.

## Single-writer ownership

| 상태/자원 | authoritative writer | readers | 불변식 |
|---|---|---|---|
| service intent | application owner | platform, security | owner가 spec을 쓰고 controller가 덮어쓰지 않는다 |
| environment spec/status | platform API/controller | developer, support, catalog | spec generation과 observed generation을 분리한다 |
| IaC state/provider resource | IaC reconciler | controller, operator | 사람과 두 controller가 같은 state를 동시에 쓰지 않는다 |
| runtime workload status | Kubernetes controllers | platform status aggregator | aggregator는 관찰하며 workload를 직접 패치하지 않는다 |
| artifact digest/attestation | build pipeline | deploy reconciler, policy | deploy가 artifact를 다시 만들지 않는다 |
| policy decision/exception | policy engine/security approver | controller, auditor | exception은 reason·approver·expiry를 가진다 |

`op-payments-staging-v3`는 여러 writer의 결과를 덮어쓰는 database가 아니라, 각 source의 versioned observation을 모으는 사용자-facing operation이다.

## Failure ownership

| 실패 | 최초 owner | 다음 행동 | platform이 보존할 evidence |
|---|---|---|---|
| invalid request/quota | application owner | payload 또는 사용량 수정 | rejection code, evaluated quota, zero effect |
| IaC/provider partial effect | platform IaC operator | converge 또는 explicit cleanup | state serial, provider IDs, cleanup owner |
| unschedulable/not ready | runtime operator와 service owner | capacity/profile 또는 probe 수정 | scheduler events, condition, generation |
| policy deny | service owner/security owner | compliant config 또는 bounded exception | policy version, rule, decision |
| artifact promotion failure | delivery owner | attestation/compatibility 수정 | immutable digest, provenance, target |
| control-plane outage | platform on-call | restore API/reconciler | queue age, request journal, replay point |

downstream 실패를 application team에게 통째로 넘기지 않는다. 사용자 action과 platform/operator action을 status에 별도 필드로 공개한다.

## 지원과 Escalation

`svc-payments` owner는 catalog의 `env-payments-staging` detail에서 operation을 열고 first-failure code와 runbook을 본다. 15분 SLO가 소진되거나 partial effect 비용이 발생하면 platform on-call로 자동 escalation한다. security deny는 security owner에게, provider-wide outage는 provider liaison에게 전달하되 platform on-call이 사용자-facing update의 single owner다.

handoff에는 `tenant-checkout`, profile, artifact digest, current generation, evidence URI와 last successful reconciliation을 포함한다. secret material은 포함하지 않는다. incident 종료 때 retry/cleanup 결과가 `op-payments-staging-v3`와 audit event에 연결돼야 하며, 지원 ticket만 닫고 resource를 남겨서는 안 된다.
