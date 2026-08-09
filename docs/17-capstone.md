# Internal Developer Platform Capstone

최종 과제는 실제 cloud와 Kubernetes platform을 모두 구현하는 프로젝트가 아닙니다. 여러 팀이 서비스를 생성·변경·운영·폐기할 수 있도록 **platform product, API, control plane, delivery, identity, tenancy와 운영 계약을 하나의 검증 가능한 설계**로 묶습니다.

구현할 수 있는 범위를 선택하되, 구현하지 않은 부분도 상태·인터페이스·실패·증거를 문서로 고정합니다.

## 1. 시나리오

가상 조직 `Northstar`는 다음 문제를 가집니다.

```text
개발 팀 3개, 서비스 12개
preview·staging·production 환경
팀마다 다른 build·deployment script
infrastructure 요청은 ticket
소유자·runbook·SLO가 흩어짐
GitOps와 cluster 직접 변경이 혼재
production policy가 배포 마지막에 발견됨
platform team은 반복 ticket과 장애 문의에 묶임
```

목표:

> 표준 HTTP 서비스가 repository 생성부터 production 운영과 폐기까지 self-service 경로를 사용한다. 경로는 versioned API, immutable artifact, GitOps reconciliation, workload identity, tenant guardrail, user journey SLO와 migration 정책을 가진다.

## 2. 범위 선택

### 필수 capability

- service registration과 owner
- preview/staging/production 환경 request
- build artifact와 promotion
- Kubernetes stateless workload profile
- identity·secret reference
- policy와 exception
- catalog/status
- telemetry와 platform SLO
- profile upgrade와 service retirement

### 선택 capability

다음 중 하나 이상을 추가할 수 있습니다.

- managed database
- public endpoint
- scheduled job
- event consumer
- preview TTL와 cleanup
- high-isolation tenant profile
- progressive delivery

### 비범위 예

- business application 전체 구현
- Kubernetes cluster bootstrap 전체
- cloud provider 모든 resource
- database engine과 distributed consensus 구현
- enterprise regulatory certification

비범위가 필수 계약을 숨기는 데 사용되면 안 됩니다.

## 3. 제출물

### A. Platform product brief

- 사용자와 반복 문제
- 현재 journey와 evidence
- 목표 outcome과 guardrail
- 지원/비지원 사용자와 workload
- adoption과 success 측정
- roadmap 첫 capability

### B. Ownership map

- application team
- platform product/control plane
- runtime/cluster operator
- security/policy
- external provider

API, data, identity, deployment, incident와 cost의 single writer와 escalation을 표시합니다.

### C. Platform API

최소 resource:

```text
Service
ServiceEnvironment
Release
CapabilityBinding
PolicyException
Migration
```

각 resource에 다음을 정의합니다.

- identity와 owner
- versioned spec
- status·condition·generation
- validation와 policy
- idempotency
- delete/finalizer
- retry/cancel
- audit event

실제 API server 구현 대신 JSON schema와 예시, 상태 전이 표를 제출할 수 있습니다.

### D. Control plane

```text
request
→ validation
→ policy
→ dependency graph
→ IaC/GitOps desired state
→ observe
→ condition
→ cleanup/finalizer
```

Controller가 관리하는 field와 외부 system의 정본을 표시합니다. Retry budget과 terminal error를 구분합니다.

### E. IaC와 runtime profile

- state partition과 locking
- module/profile version
- Kubernetes workload contract
- network·storage·scheduling
- tenant boundary와 quota
- drift와 destroy
- cluster/platform capacity dependency

실제 IaC를 작성한다면 local/sandbox 자원에 한정하고 state와 cleanup을 검증합니다.

### F. Delivery와 GitOps

- source/build/artifact identity
- evidence bundle
- environment promotion
- desired repository layout
- reconciliation과 drift
- prune guardrail
- progressive delivery 또는 standard rollout
- rollback/roll-forward
- break-glass 종료

### G. Identity·secret·policy

- 사람/workload/automation identity
- short-lived credential
- secret reference·rotation
- policy 단계와 test
- exception/expiry
- audit와 redaction
- compromise containment

### H. Catalog와 developer experience

- component metadata
- owner/repository/runtime/dependency
- self-service request/status
- actionable error
- documentation와 support
- profile version와 upgrade
- portal 비가용 시 API/CLI 경로

### I. Platform operation

- journey SLI/SLO
- alert와 runbook
- capacity/headroom/admission
- cost/showback
- support tier와 escalation
- upgrade/migration/deprecation
- backup/restore와 incident communication

## 4. 최소 repository 구조

```text
capstone/
├── README.md
├── product-brief.md
├── ownership.md
├── api/
│   ├── schemas/
│   └── examples/
├── control-plane/
│   ├── state-machine.md
│   └── reconciliation.md
├── platform/
│   ├── iac-state.md
│   ├── workload-profile.md
│   └── tenancy.md
├── delivery/
│   ├── release-contract.md
│   └── gitops.md
├── security/
│   ├── identity-secrets-policy.md
│   └── threat-model.md
├── operations/
│   ├── slo.md
│   ├── capacity-cost-support.md
│   └── runbooks/
├── migrations/
│   └── profile-v2-to-v3.md
└── evidence/
    └── README.md
```

코드를 구현하지 않는 디렉터리는 문서와 sample object로 계약을 남깁니다.

## 5. 필수 상태 시나리오

### 시나리오 1. 정상 생성

```text
team-checkout이 staging 환경 요청
→ validation/policy 허용
→ IaC와 runtime desired state 생성
→ artifact 배포
→ external smoke
→ catalog Ready
```

증명:

- operation identity
- generation
- artifact digest
- policy version
- external result
- owner와 support link

### 시나리오 2. 중복 요청과 timeout

API 응답이 사라진 뒤 같은 idempotency key로 요청합니다.

기대:

- 새 environment가 중복 생성되지 않습니다.
- 기존 operation 상태를 반환합니다.
- 이미 생성된 외부 resource를 찾습니다.

### 시나리오 3. 부분 provisioning 실패

Database는 생성됐지만 workload 배포가 policy에 거부됩니다.

결정:

- database를 유지하고 수정 대기할지
- rollback/cleanup할지
- 비용과 credential을 누가 소유할지
- condition과 사용자 행동

### 시나리오 4. GitOps drift

Operator가 live workload image를 직접 변경합니다.

기대:

- drift를 탐지합니다.
- 허용되지 않은 변경이면 되돌립니다.
- emergency change였다면 audit와 Git 반영 절차가 실행됩니다.

### 시나리오 5. Tenant resource exhaustion

한 team이 preview environment를 대량 생성합니다.

기대:

- per-tenant quota와 concurrency가 작동합니다.
- production reserve와 다른 tenant journey를 보호합니다.
- actionable denial과 expiry/cleanup 경로를 제공합니다.

### 시나리오 6. Credential 또는 policy failure

Secret broker가 token 발급을 실패하거나 새 policy가 정상 workload를 거부합니다.

기대:

- 원인 계층을 구분합니다.
- 장기 fallback credential을 사용하지 않습니다.
- policy rollout 중단/rollback과 evidence를 남깁니다.

### 시나리오 7. Profile upgrade

`stateless-http/v2` service를 `v3`으로 migration합니다.

기대:

- inventory와 compatibility
- preflight
- canary/wave
- abort/rollback
- old path deprecation
- 완료 뒤 잔여 resource 검사

### 시나리오 8. Service retirement

Production service를 폐기합니다.

기대:

- consumer와 traffic 확인
- data retention/export
- credential·route·resource 폐기
- catalog lifecycle
- cost/orphan 검사
- audit 보존

## 6. 실패 drill

문서만 제출한다면 tabletop 형식으로 다음을 기록합니다.

```text
초기 상태
주입한 사건
첫 관측
가설
허용된 검사
가역 완화
복구 판정
잔여 위험
후속 action
```

권장 drill:

- platform API degraded
- reconciliation queue stuck
- cluster capacity 부족
- invalid policy rollout
- GitOps controller credential 만료
- IaC state lock/stale plan
- supply-chain artifact quarantine
- migration rollback

Runbook은 [`docs/runbooks/`](runbooks/)를 참고해 capstone 환경에 맞게 수정합니다.

## 7. 자동 검증과 사람 검토

### 자동으로 확인할 수 있는 것

- JSON/YAML schema와 required field
- stable ID와 version
- 상태 전이의 terminal condition
- owner·expiry·rollback field
- reference link와 문서 구조
- policy fixture
- sample input/output

### 사람 검토가 필요한 것

- 사용자 문제가 실제로 중요한가
- 추상화가 적절한가
- 책임 경계가 조직 구조와 맞는가
- SLO와 비용이 합리적인가
- isolation과 policy가 risk를 충분히 줄이는가
- migration/incident에서 사람이 수행할 행동이 현실적인가

`verify.sh` 통과를 실제 플랫폼의 안전성과 신뢰성 증명으로 사용하지 않습니다.

이 저장소가 제공하는 실행 가능한 종료 과제는 [`projects/internal-developer-platform/`](../projects/internal-developer-platform/)에 있습니다. 아래 명령은 **가이드 저장소 루트**에서 실행합니다.

```sh
mkdir -p .workspace
cp -R projects/internal-developer-platform/template \
  .workspace/internal-developer-platform
python3 scripts/verify_capstone.py \
  .workspace/internal-developer-platform
```

처음 검사는 의도적으로 미완성 template를 거부합니다. learner control-plane report를 연결하는 전체 절차는 [Capstone README](../projects/internal-developer-platform/README.md#workspace)를 따릅니다. reference 해설은 다음처럼 검증합니다.

```sh
python3 scripts/verify_capstone.py \
  projects/internal-developer-platform/reference
```

## 8. 단계별 구현 순서

### 1단계: Paper platform

Product brief, API schema, state machine와 ownership을 작성합니다.

### 2단계: Deterministic prototype

JSON resource와 작은 controller simulation으로 request→condition을 재현합니다. 외부 system adapter는 fixture로 대체할 수 있습니다.

### 3단계: Local profile

선택적으로 kind/OpenTofu/GitOps 도구 중 일부를 연결합니다. 실제 cloud와 production credential은 사용하지 않습니다.

### 4단계: Failure evidence

중복·timeout·policy deny·drift·quota·migration failure를 주입하고 결과를 기록합니다.

### 5단계: Project transition

실제 오픈소스 platform/controller/catalog/policy 저장소에서 문서·test fixture·작은 controller 변경에 기여합니다.

## 9. 완료 판정

다음 질문에 모두 답해야 합니다.

- 사용자는 무엇을 요청하며 정본은 어디에 있습니까?
- 요청 수락과 실제 Ready를 어떻게 구분합니까?
- 각 controller와 팀이 소유하는 field와 실패는 무엇입니까?
- 같은 요청과 reconcile을 반복해도 중복 effect가 생기지 않습니까?
- Artifact, configuration, secret와 deployment result가 연결됩니까?
- 한 tenant와 하나의 controller 결함이 미치는 blast radius는 어디까지입니까?
- Exception과 break-glass는 어떻게 종료됩니까?
- Platform journey의 SLO·capacity·cost·support가 있습니까?
- Upgrade와 retirement가 생성만큼 자동화돼 있습니까?
- 실제로 검증하지 못한 보장은 무엇입니까?

[`12-capstone-plan`](../exercises/12-capstone-plan/)의 계약을 먼저 완성한 뒤, 선택한 구현 범위와 evidence를 추가합니다.
