# 관측·감사·개발자 피드백

플랫폼 내부 component의 CPU와 오류율이 정상이어도 개발자가 환경을 만들지 못하면 플랫폼 여정은 실패한 것입니다. 반대로 controller log에 error가 있어도 자동 retry로 사용자 결과가 정상이라면 즉시 장애로 분류할 필요는 없습니다.

이 장은 플랫폼의 **내부 상태**, **사용자 여정**과 **변경 책임**을 같은 근거로 연결합니다.

## 1. 세 가지 관측 관점

### 사용자 여정

- 서비스 생성
- 첫 artifact build
- preview 환경 생성
- staging/production promotion
- secret 또는 capability 추가
- incident 진단
- profile upgrade
- 환경과 서비스 폐기

### Control plane 내부

- API request
- queue와 reconcile
- IaC plan/apply
- GitOps sync
- policy decision
- secret broker
- catalog ingestion
- cluster·cloud dependency

### Governance와 audit

- 누가 무엇을 요청·승인·변경했는가
- 어떤 policy와 version이 결정했는가
- 어떤 artifact와 configuration이 배포됐는가
- exception과 break-glass가 언제 종료됐는가

세 관점을 request, operation, resource와 release identity로 연결합니다.

## 2. Correlation model

최소 식별자:

- `request_id`: 한 API 요청
- `operation_id`: 비동기 provisioning 또는 promotion 작업
- `resource_id`: service/environment/capability의 안정적 ID
- `generation`: desired state 세대
- `release_id`: source·artifact·environment 연결
- `tenant_id`: team 또는 isolation unit
- `policy_decision_id`: 적용된 판단
- `trace_id`: 여러 component 실행 연결

하나의 ID를 모든 의미로 재사용하지 않습니다. 같은 operation에 retry request가 여러 개 있을 수 있고, 한 resource에는 여러 generation이 존재합니다.

## 3. Signal 설계

### Trace

사용자 요청이 여러 controller와 외부 API를 통과하는 경로를 연결합니다.

중요 span:

```text
platform.api.validate
platform.policy.evaluate
platform.reconcile
terraform.plan
terraform.apply
kubernetes.apply
release.observe
catalog.update
```

Retry마다 새 trace만 생성하면 전체 operation을 잃을 수 있으므로 operation identity를 attribute로 유지합니다.

### Metric

집계와 경향을 봅니다.

- journey success/latency
- condition 체류 시간
- queue depth와 oldest age
- dependency error rate
- policy deny/warn
- profile/version adoption
- tenant별 usage와 saturation
- orphan와 cleanup backlog

Label cardinality를 제한합니다. Service ID나 request ID를 metric label로 무제한 넣지 않습니다.

### Log

상태 전이와 진단 context를 기록합니다.

좋은 log:

```json
{
  "event": "reconcile_blocked",
  "resource_id": "checkout-staging",
  "generation": 4,
  "operation_id": "op-...",
  "condition": "Blocked",
  "reason": "QuotaExceeded",
  "owner": "team-checkout",
  "retryable": false
}
```

Stack trace만 남기거나 secret·manifest 전체를 출력하지 않습니다.

### Event와 audit

사용자에게 의미 있는 변경과 권한 행동을 append-only event로 남깁니다.

- request accepted/rejected
- approval
- desired state changed
- deployment promoted/rolled back
- policy exception
- break-glass
- ownership change
- deletion requested/completed

Audit은 운영 log와 retention·access·무결성 요구가 다를 수 있습니다.

## 4. Platform journey SLI

Component별 availability만으로는 플랫폼 가치를 측정하지 못합니다.

예:

```text
환경 생성 성공률
= 정해진 시간 안에 Ready condition과 external smoke를 만족한 요청
  / 유효하고 정책상 허용된 환경 생성 요청
```

사용자 입력 오류와 platform 실패를 분리합니다. 그러나 입력 오류가 지나치게 많다면 API와 문서의 usability 문제일 수 있으므로 별도 지표로 추적합니다.

대표 SLI:

- valid request acceptance latency
- environment Ready latency
- deployment observation latency
- platform-caused failure rate
- self-service completion rate
- actionable error rate
- rollback/restore success rate
- profile upgrade completion
- portal/catalog freshness

SLO와 alert는 [`14 Platform SLO·capacity·cost·support`](14-platform-slo-capacity-cost-and-support.md)에서 다룹니다.

## 5. Actionable feedback

개발자가 platform team에게 문의하기 전에 스스로 다음 행동을 알 수 있어야 합니다.

오류 메시지에 포함할 내용:

- 어떤 단계가 실패했는가
- 사용자의 요청이 저장됐는가
- 자동 retry 중인가
- 영향을 받는 resource와 generation
- stable error code
- owner: application/platform/security/vendor
- 가능한 remediation
- 상태와 상세 evidence link
- retry/cancel/escalate 방법

잘못된 예:

```text
Internal error. Contact administrator.
```

개선:

```text
Environment는 생성됐지만 workload가 15분 안에 Ready가 되지 않았습니다.
Reason: ImagePullDenied
Action: release digest와 registry policy를 확인하세요.
Owner: team-checkout
Evidence: operation/op-123/events
```

## 6. Status page와 portal

Portal의 상태 화면은 실제 status API의 소비자입니다. 다음을 구분합니다.

- global platform incident
- 특정 capability 장애
- 특정 cluster/region 장애
- tenant quota 또는 정책 문제
- 하나의 resource reconcile 실패
- application workload 실패

모든 문제를 “platform degraded”로 표시하면 신뢰를 잃습니다. 반대로 component 일부가 실패해도 사용자 impact가 없다고 숨기면 용량과 잔여 위험을 놓칩니다.

## 7. Audit evidence

중요한 변경은 다음 질문에 답해야 합니다.

```text
누가 요청했는가?
무엇이 바뀌었는가?
어떤 source·artifact·configuration인가?
어떤 policy version이 허용했는가?
누가 승인했는가?
어느 resource와 environment에 적용됐는가?
실제 결과는 무엇인가?
rollback 또는 cleanup은 완료됐는가?
```

Audit record의 접근과 retention도 정책으로 관리합니다. 운영자가 자신의 행동 기록을 삭제할 수 없게 분리할 수 있습니다.

## 8. Telemetry privacy와 비용

플랫폼 telemetry는 repository 이름, team, service, environment와 정책 사유 같은 민감 metadata를 포함할 수 있습니다.

- secret과 payload redaction
- tenant 간 query isolation
- audit 접근 제한
- retention과 삭제
- sampling이 중요한 사건을 누락하지 않는지
- high-cardinality 비용
- debug mode의 자동 만료

모든 trace를 영구 보관하지 않습니다. 사건 종류와 risk에 맞는 retention을 둡니다.

## 9. Feedback loop

관측은 dashboard 제작으로 끝나지 않습니다.

```text
사용자 journey 실패 수집
→ 반복 원인 분류
→ platform/API/document 개선 후보
→ 우선순위와 owner
→ 변경 배포
→ 같은 journey 지표 비교
```

Support ticket, chat와 incident에 stable category와 resource identity를 연결하면 정성 피드백과 telemetry를 함께 볼 수 있습니다.

대표 분류:

- discoverability
- invalid default
- permission/policy
- quota/capacity
- dependency outage
- platform defect
- application defect
- documentation gap
- unsupported use case

## 10. 운영 dashboard의 계층

### 제품 dashboard

- adoption과 active users
- journey 성공률과 시간
- manual ticket 감소
- profile upgrade와 exception

### Reliability dashboard

- SLO와 error budget
- API/controller dependency
- queue와 saturation
- failed/stuck operation

### Tenant dashboard

- usage와 quota
- deployment·environment 상태
- policy violation
- cost와 efficiency

### Incident dashboard

- 현재 impact
- 최초 실패 시점
- change/release correlation
- operation backlog
- mitigation 상태

한 dashboard에 모든 metric을 넣지 않습니다.

## 11. Runbook 연결

Alert에는 진단 순서와 안전한 완화가 있어야 합니다.

이 가이드의 runbook:

- [`provisioning stuck`](runbooks/01-provisioning-stuck.md)
- [`reconciliation drift`](runbooks/02-reconciliation-drift.md)
- [`workload unschedulable`](runbooks/03-workload-unschedulable.md)
- [`tenant resource exhaustion`](runbooks/04-tenant-resource-exhaustion.md)
- [`platform API degraded`](runbooks/05-platform-api-degraded.md)
- [`credential or policy failure`](runbooks/06-credential-or-policy-failure.md)
- [`upgrade rollback`](runbooks/07-upgrade-rollback.md)

Runbook은 원인을 단정하지 않고 관측·가설·가역 완화·복구 검증 순서로 작성합니다.

## 12. 실습

[`10-platform-slo`](../exercises/10-platform-slo/)에서 다음을 정의합니다.

- 핵심 platform journey
- request/operation/resource/release identity
- trace·metric·log·audit event
- user-visible condition과 remediation
- platform/user/dependency failure 분류
- privacy·retention
- feedback loop와 owner

## 13. 검토 질문

- Component health와 user journey success가 분리돼 있습니까?
- 하나의 operation을 여러 retry와 dependency call 사이에서 추적할 수 있습니까?
- 오류가 다음 행동·owner·retryability를 알려 줍니까?
- Metric label이 무제한 cardinality를 만들지 않습니까?
- Audit가 source·policy·승인·결과를 연결합니까?
- Telemetry가 secret과 tenant metadata를 과도하게 노출하지 않습니까?
- Support와 incident 결과가 플랫폼 개선 backlog로 돌아옵니까?

다음 장에서는 여러 tenant가 같은 플랫폼을 사용할 때 권한·자원·네트워크·장애를 어디까지 공유할지 결정합니다.
