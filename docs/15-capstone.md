# 멀티테넌트 문서 처리 SaaS Capstone

Capstone은 하나의 문서 처리 서비스를 다음 네 단계로 재설계하며 책임·실패·비용의 변화를 누적 기록합니다.

```text
Stage 1  IaaS
Stage 2  Managed platform
Stage 3  Event-driven FaaS
Stage 4  Multi-tenant SaaS
```

완성 application 전체를 구현하는 것이 필수는 아닙니다. 그러나 architecture 문서가 추상적인 그림에 머물지 않도록 local cloud model의 불변식과 구체적인 failure evidence를 포함해야 합니다.

## 1. System brief

사용자는 문서를 업로드하고 변환 결과를 받습니다.

기능:

- upload
- metadata 저장
- async processing
- result download
- organization membership
- plan과 monthly quota
- usage report
- export와 tenant deletion

비기능:

- 두 zone 중 하나의 compute loss를 견딥니다.
- 같은 upload event가 중복돼도 결과와 usage가 하나입니다.
- 다른 tenant의 document·result·export를 읽을 수 없습니다.
- quota 초과는 부분 document를 남기지 않습니다.
- tenant 종료 뒤 active data와 pending job이 남지 않습니다.
- resource owner·budget·cleanup evidence가 있습니다.

자세한 입력은 [`projects/multitenant-document-processing-saas/inputs/system-brief.md`](../projects/multitenant-document-processing-saas/inputs/system-brief.md)에 있습니다.

## 2. Stage 1 — IaaS

예시 구성:

```text
public load balancer
→ application VM pool across zones
→ private database
→ object storage
→ worker VM
```

필수 결정:

- image와 bootstrap
- network route와 public/private 경계
- stateful·ephemeral 분류
- zone loss
- backup·restore
- scaling trigger
- workload identity
- resource inventory와 cost

증거:

- VM 하나와 zone 하나 제거 시나리오
- replacement bootstrap
- private database negative access
- restore result
- orphan resource 검사

## 3. Stage 2 — Managed platform

application runtime과 database·queue 일부를 managed service로 옮깁니다.

작성:

- 사라진 운영 작업
- 공급자에게 이동한 작업
- 남은 consumer responsibility
- maintenance·version·quota
- network와 identity 변화
- backup·restore 변화
- observability gap
- export와 exit
- cost curve

“managed라서 운영이 줄었다”가 아니라 task와 evidence를 비교합니다.

## 4. Stage 3 — FaaS

문서 처리 worker를 event-driven function으로 바꿉니다.

```text
upload accepted
→ event
→ function
→ result object
→ status update
→ usage event
```

필수 failure:

- duplicate event
- result 저장 뒤 timeout
- missing object
- poison document
- tenant 삭제 중 retry
- concurrency가 database 또는 external converter limit 초과
- dead-letter replay

작성:

- event identity
- attempt와 deadline
- idempotency state
- output key
- retry classification
- maximum age·attempt
- DLQ owner
- per-tenant concurrency
- cost per useful result

## 5. Stage 4 — SaaS

다음 상태를 추가합니다.

```text
tenant
membership
role
plan version
subscription
entitlement
quota reservation
usage event
export job
deletion workflow
```

필수 isolation path:

- request
- database
- object storage
- cache
- queue
- function
- analytics
- support
- export
- backup·restore
- deletion

필수 commercial failure:

- duplicate billing webhook
- upgrade provisioning partial failure
- downgrade below current usage
- quota race
- late usage event
- invoice dispute

## 6. 공통 산출물

Capstone workspace는 다음 파일을 완성합니다.

```text
01-responsibility-matrix.md
02-resource-and-state-inventory.md
03-identity-network-and-tenant-boundaries.md
04-failure-and-recovery-plan.md
05-event-and-idempotency-contract.md
06-cost-quota-and-metering.md
07-portability-exit-and-deletion.md
08-release-review.md
```

각 파일의 목적은 project README와 rubric에 정의돼 있습니다.

## 7. Local model 연결

[`exercises/07-local-cloud-model`](../exercises/07-local-cloud-model/README.md)의 reference가 보여 주는 외부 불변식을 Capstone에 적용합니다.

- cross-tenant access deny
- duplicate event suppression
- atomic quota
- private stateful resource
- tenant cleanup

실제 provider profile을 선택했다면 같은 불변식을 provider resource와 integration test로 어떻게 검증할지 추가합니다.

## 8. 선택 provider profile

실제 계정 실험은 한 provider만 선택해도 됩니다.

필수 evidence:

- experiment charter
- account/project
- identity
- budget
- resource prefix/tag
- exact CLI/IaC version
- created inventory
- failure test
- destroy log
- final inventory
- billing delay note

실제 provider 실험이 local model을 대체하지는 않습니다. provider-specific behavior를 추가로 확인합니다.

## 9. 리뷰 기준

### Scope와 ownership

- workload와 tenant가 명확합니다.
- resource·data·cost owner가 있습니다.

### Responsibility

- 각 stage에서 provider와 consumer task가 달라집니다.
- 숨겨진 관리형 상태와 limit가 기록됩니다.

### Failure

- instance·zone·control plane·event·quota·tenant failure를 구분합니다.
- partial state와 compensation이 있습니다.

### Evidence

- architecture 주장마다 test·metric·audit·restore·cost evidence가 있습니다.
- evidence의 한계가 기록됩니다.

### SaaS

- tenant context가 모든 path에 전달됩니다.
- entitlement·quota·metering·billing이 분리됩니다.
- export와 deletion이 subsystem 전체에 전파됩니다.

### Exit

- data·identity·configuration·log·key를 회수합니다.
- migration duration·cost와 trigger가 있습니다.

## 10. 완료 판정

자동 contract 통과는 필수 파일과 미완성 token이 없음을 확인할 뿐입니다. 사람 리뷰어가 다음을 승인해야 합니다.

```text
APPROVE
APPROVE_WITH_CONDITIONS
DEFER
REJECT
```

조건에는 owner, due date, verification과 rollback이 필요합니다.

## 11. Capstone 이후

다음 프로젝트 중 하나로 이동합니다.

- 실제 provider에서 IaaS와 managed runtime 비교
- FaaS worker와 DLQ 운영
- 기존 앱의 organization·quota·usage·export 구현
- cloud cost anomaly와 orphan cleanup tool
- managed database migration rehearsal
- self-service platform의 초기 golden path
