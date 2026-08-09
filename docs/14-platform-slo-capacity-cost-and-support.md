# Platform SLO·capacity·cost·support

플랫폼은 다른 팀의 전달 경로에 들어가는 제품이므로 “best effort automation”으로만 운영할 수 없습니다. 그러나 모든 capability를 24시간 최고 수준으로 지원하는 것도 비용과 조직 규모에 맞지 않습니다.

이 장은 사용자 여정별 신뢰성 목표, capacity와 비용, 지원 책임을 하나의 운영 계약으로 연결합니다.

SLI/SLO와 Kubernetes workload·node autoscaling의 공식 기준은 [source index의 SLO와 capacity](../reference/source-index.md#slo-capacity)를 확인합니다. Autoscaler가 provider capacity, queue fairness나 platform journey SLO를 자동 보장한다고 가정하지 않습니다.

## 1. Platform SLO의 대상

SLO는 component보다 사용자 결과에 둡니다.

가능한 journey:

- valid platform API request 수락
- preview 환경 생성
- verified artifact promotion
- production desired state reconciliation
- secret credential 발급
- catalog ownership 조회
- policy decision
- profile upgrade operation

예:

```text
Preview environment provisioning
- 대상: 정책상 허용된 유효 요청
- 성공: 15분 안에 Ready와 smoke 통과
- 목표: 30일 window 99%
- 제외: user cancellation, external provider declared outage
```

제외 조건을 넓게 잡아 플랫폼 실패를 숨기지 않습니다.

## 2. SLI 분모와 실패 분류

요청 결과를 분류합니다.

| 분류 | SLO 실패인가 | 별도 추적 |
|---|---:|---|
| platform API internal error | 예 | defect |
| dependency timeout budget 초과 | 보통 예 | provider dependency |
| invalid user input | 아니요 | usability/error rate |
| policy deny | 아니요 | policy friction |
| quota deny | 정책에 따라 | capacity/friction |
| application workload crash | 보통 아니요 | workload quality |
| platform default 때문에 crash | 예 | profile defect |
| user cancellation | 아니요 | journey abandonment |

분류가 애매하면 owner와 remediation을 찾기 어렵습니다. Stable error taxonomy를 사용합니다.

## 3. Error budget

Error budget은 실패를 허용하기 위한 핑계가 아니라 reliability와 변화 속도를 조정하는 신호입니다.

사용 예:

- budget 충분: 새로운 profile과 migration 진행
- 빠른 burn: risky rollout 중단, defect 수정 우선
- budget 소진: release 제한, reliability work 실행

모든 platform change를 완전히 freeze할 필요는 없습니다. 복구·보안·관측 개선은 계속할 수 있습니다. 정책을 capability와 risk에 맞게 정합니다.

## 4. Alert 설계

Alert는 사람이 행동할 수 있어야 합니다.

좋은 alert:

- 영향받는 journey와 tenant/environment
- burn rate 또는 stuck operation 수
- 최초 발생과 최근 change
- dependency와 platform failure 구분
- runbook
- 안전한 첫 검사

피해야 할 것:

- controller error 한 번마다 paging
- 사용자 impact 없는 retry를 high severity로 알림
- platform-wide 장애와 한 resource 오류를 같은 채널로 보냄
- owner 없는 alert

빠른 burn과 느린 burn을 다른 window로 탐지할 수 있습니다.

## 5. Support model

Capability별 support level을 명시합니다.

| 수준 | 예 | 지원 |
|---|---|---|
| production critical | production delivery, identity | on-call, SLO, incident process |
| supported | standard profiles, staging | business-hours + escalation |
| preview | 새 profile 또는 add-on | 제한된 사용자, 빠른 변화 |
| community/experimental | 선택 plugin | best effort, 자체 운영 가능 |
| deprecated | old version | migration 지원, 신규 사용 금지 |

사용자는 어떤 경로가 어떤 support를 받는지 생성 전에 알아야 합니다.

## 6. Ownership과 escalation

다음 역할을 분리합니다.

- platform capability owner
- runtime/cluster operator
- security/policy owner
- application service owner
- external provider owner
- incident commander
- communication owner

모든 platform issue를 중앙 팀이 직접 해결하지 않습니다. 하지만 사용자가 owner를 찾는 비용은 플랫폼이 줄여야 합니다.

Escalation에는 다음이 필요합니다.

- resource/operation identity
- impact와 urgency
- 이미 확인한 evidence
- application/platform/dependency 분류
- 임시 완화
- 다음 update 시점

## 7. Capacity model

Capacity는 현재 평균 사용량이 아니라 성장, burst, failure와 upgrade를 감당하는 여유를 포함합니다.

계층:

- platform API rate와 worker queue
- controller concurrency
- cluster compute·memory·storage
- IP·load balancer·volume 같은 provider quota
- CI runner와 artifact storage
- telemetry ingestion와 cardinality
- secret/policy service
- support 인력과 change capacity

### Headroom

```text
available capacity
- expected growth
- failure reserve
- upgrade surge
- tenant burst
= allocatable headroom
```

모든 resource를 100% 채우면 node drain, zone failure와 rolling upgrade가 불가능해집니다.

## 8. Saturation과 admission

Capacity 부족을 무한 queue로 숨기지 않습니다.

- request rate limit
- per-tenant concurrency
- priority class
- preview TTL와 maximum count
- production reserve
- queue age alert
- admission reject와 명확한 retry-after
- provider quota preflight

중요한 작업과 대량 low-priority preview 생성이 같은 queue에서 경쟁하지 않게 합니다.

## 9. 비용 모델

Platform 비용은 cloud invoice뿐 아니라 개발·지원·upgrade 비용을 포함합니다.

구분:

```text
직접 usage
+ shared runtime overhead
+ reliability headroom
+ security·observability service
+ platform engineering와 support
```

비용 지표:

- tenant/service/environment별 직접 비용
- idle·orphan resource
- preview environment 평균 수명
- log/trace/cardinality 비용
- profile별 단위 비용
- 수동 ticket 처리 비용
- migration/deprecation 지연 비용

단가만 줄여 개발자 lead time과 reliability를 악화시키지 않습니다. 비용 변화가 사용자 outcome에 미치는 영향을 함께 봅니다.

## 10. Showback와 chargeback

처음에는 showback으로 visibility를 제공합니다.

- 현재 usage
- budget 대비 trend
- 큰 비용 driver
- 선택한 profile의 trade-off
- 절약 가능한 safe action
- shared overhead 기준

Chargeback은 ownership을 높일 수 있지만 팀이 필요한 reliability reserve를 제거하거나 label gaming을 할 수 있습니다. 목적과 행동 변화를 먼저 정합니다.

## 11. Platform roadmap와 운영 부채

사용자 feature만 만들고 upgrade·capacity·support automation을 미루면 platform team이 ticket과 사고에 묶입니다.

운영 backlog:

- 반복 incident
- 오래된 profile/version
- manual approval와 repair
- flaky workflow
- missing telemetry
- unsupported exception
- capacity risk
- orphan resource
- security debt

Product roadmap에서 feature와 운영 부채의 trade-off를 같은 기준으로 검토합니다.

## 12. Incident와 communication

Platform incident에서는 application team이 영향을 빠르게 판단할 수 있어야 합니다.

상태 communication:

- 영향받는 capability·environment·region
- 기존 workload와 새 change 중 무엇이 영향받는지
- 우회 경로와 위험
- 다음 update 시점
- 복구 뒤 backlog 처리
- 후속 action owner

복구 후 queued operation이 한꺼번에 실행돼 2차 부하를 만들 수 있습니다. Rate와 priority를 조정하며 drain합니다.

## 13. 실습

[`10-platform-slo`](../exercises/10-platform-slo/)에서 다음을 만듭니다.

- 두 개 이상의 user journey SLI/SLO
- 실패 분류와 분모
- error budget action
- alert와 runbook
- support tier와 owner
- capacity unit·headroom·admission
- cost allocation와 showback
- incident communication

Template은 [`reference/platform-slo-template.md`](../reference/platform-slo-template.md)를 사용할 수 있습니다.

## 14. 검토 질문

- SLO가 component uptime보다 사용자 결과를 측정합니까?
- Invalid input·policy deny·platform defect를 구분합니까?
- Error budget 소진 때 구체적인 변화 정책이 있습니까?
- Capability별 support level과 시간대가 명확합니까?
- Capacity가 failure와 upgrade surge를 포함합니까?
- Queue가 무한히 늘기 전에 admission과 priority가 작동합니까?
- 비용 절감이 reliability와 lead time에 미치는 영향도 측정합니까?
- Incident communication이 기존 workload와 새 변경의 영향을 구분합니까?

다음 장에서는 플랫폼 자체의 API, profile, cluster와 add-on을 안전하게 upgrade하고 이전 version을 폐기하는 방법을 다룹니다.
