# IaC and Runtime Contract

## 공통 식별자

`svc-payments` / `env-payments-staging` / `op-payments-staging-v3` / `tenant-checkout` / `sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa` / `stateless-http/v3`를 plan, state, runtime label과 evidence에 동일하게 사용한다.

## IaC State와 Drift

desired configuration, rendered module input, IaC state serial, provider object, observed runtime을 서로 다른 상태로 취급한다. plan에는 resource ID, destructive flag, policy result와 예상 비용 delta가 있고 apply 전에 immutable evidence로 저장된다. state backend writer는 reconciler 하나이며 lock timeout은 retryable failure로 operation에 보인다.

provider effect 뒤 state write가 실패하면 성공으로 재시도하지 않는다. provider ID를 partial effect inventory에 남기고 import/converge 또는 cleanup 중 하나를 owner가 선택한다. 일반 drift는 `stateless-http/v3` desired input으로 되돌리고 before/after diff를 남긴다. break-glass drift는 approver·reason·expiry·evidence가 모두 유효할 때만 잠시 유지되며 expiry 뒤 reconciliation 대상이다.

## Kubernetes Runtime

profile은 namespace, workload class, resource bounds, service account, network/storage policy와 최소 availability를 versioned contract로 만든다. `sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa` digest를 workload spec에 고정하며 mutable tag는 evidence가 아니다. readiness probe 성공만으로 platform `Ready`가 되지 않고 scheduler, rollout, endpoint와 외부 smoke observation이 같은 generation에 있어야 한다.

unschedulable은 application code failure로 숨기지 않는다. requested/available capacity와 blocking constraint를 runtime operator에게 보낸다. disruption budget, storage migration과 CNI failure는 각 owner와 rollback/roll-forward action을 가진다. 실제 Kubernetes가 없는 이 dossier에서는 enforcement를 주장하지 않고 필요한 observation과 owner를 설계한다.

## Tenant Isolation과 Cleanup

`tenant-checkout` quota 2는 admission에서 atomic하게 예약하고 failed request가 slot을 소비하지 않게 한다. tenant별 queue에 최소 service share를 두어 한 tenant의 provider backoff가 다른 tenant의 `Ready` 진행을 막지 않게 한다. production reserve는 staging burst와 별도 pool이며 quota는 물리 capacity를 만든다는 뜻이 아니다.

retirement/rollback cleanup은 environment tag만 지우지 않는다. provider objects, namespace/workloads, DNS/traffic, volumes/data decision, service account bindings, exceptions, queue reservations와 cost inventory를 확인한다. 삭제가 확인되지 않은 항목은 tombstone의 pending cleanup에 남고 `Retired`를 발행하지 않는다.
