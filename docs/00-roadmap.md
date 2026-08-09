# 플랫폼 엔지니어링 가이드 학습 지도

이 가이드는 이미 한 서비스를 배포하고 운영할 수 있는 개발자가, 그 능력을 여러 팀이 반복해서 사용할 수 있는 **내부 개발자 플랫폼(Internal Developer Platform)**으로 확장하는 과정입니다.

최종적으로 다음 흐름을 설계하고 검증할 수 있어야 합니다.

```text
개발자가 서비스 또는 환경을 요청
→ platform API가 입력과 정책을 검증
→ control plane이 infrastructure와 runtime desired state를 생성
→ IaC·GitOps controller가 현재 상태를 수렴
→ build artifact가 환경 사이를 승격
→ identity·secret·policy가 최소 권한을 강제
→ catalog와 status가 소유자·현재 상태·증거를 노출
→ SLO·capacity·cost·support가 플랫폼 자체를 운영
→ upgrade·migration·deprecation으로 경로를 진화
```

## 1. 대상 독자

다음 경험을 전제로 합니다.

- 작은 서비스를 공개 환경에 배포하고 log·metric·backup·rollback을 다뤄 본 적이 있습니다.
- Git과 CI에서 변경이 어떤 artifact를 만들었는지 추적할 수 있습니다.
- HTTP API, JSON, process, network endpoint와 access control의 기본 개념을 압니다.
- 장애가 발생했을 때 증상과 최초 실패를 구분하려고 시도할 수 있습니다.

Kubernetes, Terraform/OpenTofu, GitOps controller, developer portal 사용 경험은 필수가 아닙니다. 핵심 과정은 특정 제품의 설치가 아니라 상태와 책임의 경계를 먼저 구축합니다.

## 2. 선행 브랜치와 소유권

### 직접 기준선

[`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra)는 다음 능력을 소유합니다.

- 한 서비스의 host·container·DNS·TLS·release·secret·observability·backup·incident response
- exact artifact 배포와 rollback
- 공개 운영 환경의 위협 모델과 복구 계약

이 가이드는 같은 내용을 다시 설명하지 않습니다. 대신 여러 팀이 그 능력을 공통 인터페이스로 소비할 때 생기는 문제를 다룹니다.

### 권장 연결

- [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services): platform API와 controller의 timeout·retry·idempotency·부분 실패
- [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks): cluster·service·gateway·DNS 경로의 실패 분리
- [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems): process·file·permission·socket 관찰
- [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity): 위협 모델, 공격 경로, hardening과 사고 대응
- [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems): control plane의 복제·합의·failure detector를 더 깊게 이해할 때

## 3. 학습 시나리오

문서와 reference는 다음 가상 조직을 공통 배경으로 사용합니다.

```text
조직: Northstar
개발 팀: checkout, catalog, identity
서비스: 12개
환경: preview, staging, production
기존 방식:
- infrastructure 요청은 ticket과 수동 승인
- 팀마다 다른 CI·배포 스크립트
- 소유자와 runbook이 흩어짐
- cluster 직접 변경과 GitOps 변경이 혼재
- 정책 위반이 배포 마지막 단계에서 발견됨
- platform team이 반복 ticket과 장애 문의에 묶임
```

목표는 모든 팀을 같은 언어와 framework에 강제하는 것이 아닙니다. 서비스가 공통으로 필요로 하는 결과를 안정적인 platform contract로 제공합니다.

## 4. 읽는 순서

### Part I. 플랫폼 제품과 제어 모델

| 장 | 핵심 질문 | 대응 실습 |
|---|---|---|
| [01 플랫폼을 제품으로 정의하기](01-platform-as-product.md) | 누구의 어떤 반복 문제를 줄이며, 결과를 무엇으로 측정합니까? | [`01-platform-product`](../exercises/01-platform-product/) |
| [02 플랫폼 계약과 책임 경계](02-platform-contracts-and-ownership.md) | 사용자가 요청한 결과와 플랫폼·서비스 팀의 책임은 어디서 나뉩니까? | [`02-platform-contract`](../exercises/02-platform-contract/) |
| [03 Control plane과 reconciliation](03-control-planes-and-reconciliation.md) | 비동기 작업을 재시도해도 같은 desired state로 수렴합니까? | [`03-reconciliation`](../exercises/03-reconciliation/) |

Part I을 마치면 플랫폼을 tool collection이 아니라 사용자·API·control loop·support boundary를 가진 제품으로 설명할 수 있어야 합니다.

### Part II. Infrastructure와 runtime substrate

| 장 | 핵심 질문 | 대응 실습 |
|---|---|---|
| [04 Infrastructure as Code와 state](04-infrastructure-as-code-state-and-drift.md) | 선언, state와 원격 자원의 identity를 누가 소유합니까? | [`04-iac-state`](../exercises/04-iac-state/) |
| [05 Kubernetes API와 workload](05-kubernetes-api-workloads-and-controllers.md) | API object와 controller가 workload를 어떤 계약으로 유지합니까? | [`05-workload-contract`](../exercises/05-workload-contract/) |
| [06 Kubernetes network·storage·scheduling](06-kubernetes-network-storage-and-scheduling.md) | 통신·저장·자원·disruption 책임이 platform과 workload 사이에서 어떻게 나뉩니까? | [`05-workload-contract`](../exercises/05-workload-contract/) |

Part II는 Kubernetes 명령을 외우는 구간이 아닙니다. platform API가 기반 자원의 상태를 어떻게 표현하고, runtime이 어떤 실패를 platform 사용자에게 노출하는지 확인합니다.

### Part III. Self-service 전달 경로

| 장 | 핵심 질문 | 대응 실습 |
|---|---|---|
| [07 Self-service platform API와 catalog](07-self-service-platform-apis-and-catalogs.md) | portal이 없어도 자동화 가능한 안정적인 요청·상태 인터페이스가 있습니까? | [`06-self-service`](../exercises/06-self-service/) |
| [08 Golden path와 service lifecycle](08-golden-paths-and-service-lifecycle.md) | 지원되는 경로와 escape hatch를 어떻게 함께 운영합니까? | [`06-self-service`](../exercises/06-self-service/) |
| [09 Delivery platform과 artifact promotion](09-delivery-platform-and-artifact-promotion.md) | 같은 artifact가 환경 사이에서 어떤 증거와 gate를 거쳐 이동합니까? | [`07-delivery-gitops`](../exercises/07-delivery-gitops/) |
| [10 GitOps reconciliation과 긴급 변경](10-gitops-reconciliation-and-emergency-changes.md) | desired state, live drift와 emergency change가 충돌할 때 정본은 무엇입니까? | [`07-delivery-gitops`](../exercises/07-delivery-gitops/) |
| [11 Identity·secret·policy](11-identity-secrets-and-policy.md) | 사람·workload·automation 권한과 예외를 어떻게 짧고 추적 가능하게 만듭니까? | [`08-identity-policy`](../exercises/08-identity-policy/) |

Part III을 마치면 저장소 생성에서 배포·관측·폐기까지의 golden path를 하나의 service lifecycle로 설계할 수 있어야 합니다.

### Part IV. 공유 플랫폼 운영과 진화

| 장 | 핵심 질문 | 대응 실습 |
|---|---|---|
| [12 관측·감사·개발자 피드백](12-observability-audit-and-developer-feedback.md) | 내부 component 상태와 개발자 여정 실패를 어떻게 연결합니까? | [`10-platform-slo`](../exercises/10-platform-slo/) |
| [13 Multi-tenancy·quota·isolation](13-multitenancy-quotas-and-isolation.md) | 한 tenant의 권한·부하·오류가 다른 tenant로 번지는 범위를 어떻게 제한합니까? | [`09-multitenancy`](../exercises/09-multitenancy/) |
| [14 Platform SLO·capacity·cost·support](14-platform-slo-capacity-cost-and-support.md) | 플랫폼을 누가 어느 수준으로 운영하고 비용·용량을 어떻게 배분합니까? | [`10-platform-slo`](../exercises/10-platform-slo/) |
| [15 Upgrade·migration·deprecation](15-upgrades-migrations-and-deprecation.md) | 기반과 API를 바꾸면서 기존 workload의 안전한 이동을 어떻게 증명합니까? | [`11-migration`](../exercises/11-migration/) |
| [16 Supply chain과 platform security](16-supply-chain-and-platform-security.md) | source에서 runtime까지 어떤 주체와 artifact를 신뢰합니까? | [`08-identity-policy`](../exercises/08-identity-policy/) |

### Part V. 통합 과제

| 장 | 핵심 질문 | 대응 실습 |
|---|---|---|
| [17 Internal Developer Platform Capstone](17-capstone.md) | service 생성·변경·실패·복구·폐기 전체를 하나의 contract로 연결할 수 있습니까? | [`12-capstone-plan`](../exercises/12-capstone-plan/) |

## 5. 문서와 실습 사용법

1. 장의 첫 부분에서 소유 상태와 실패 조건을 확인합니다.
2. 예시를 읽기 전에 자신의 조직 또는 가상 조직에 적용한 초안을 작성합니다.
3. 대응 실습의 `skeleton/submission.json`을 `.workspace/`로 복사합니다.
4. `verify_submission.py`로 누락된 계약을 확인합니다.
5. 통과한 뒤 `reference`와 비교합니다.
6. 답이 다르다면 어떤 위험과 trade-off 때문에 다른지 기록합니다.

```sh
mkdir -p .workspace/platform-contract
cp exercises/02-platform-contract/skeleton/submission.json \
  .workspace/platform-contract/submission.json

python3 scripts/verify_submission.py \
  exercises/02-platform-contract/contract.json \
  .workspace/platform-contract/submission.json
```

검사 통과는 설계가 실제 조직에서 옳다는 뜻이 아닙니다. 필수 질문을 빠뜨리지 않았다는 최소 조건입니다. 실제 채택, 운영 비용과 장애 결과는 사용자 인터뷰, deployment record와 incident evidence로 검증해야 합니다.

## 6. 세 종류의 상태

플랫폼 설계에서 다음을 섞지 않습니다.

### 요청 상태

사용자가 platform API에 선언한 목표입니다. 예: `checkout` 서비스의 `staging` 환경을 생성하고 release digest `sha256:...`를 배포합니다.

### 제어 상태

platform control plane이 reconciliation을 위해 저장하는 generation, condition, dependency와 retry 정보입니다.

### 실행 상태

cloud resource, Kubernetes object, workload process와 외부 dependency가 실제로 가진 상태입니다.

요청이 저장됐다고 실행이 완료된 것은 아닙니다. controller가 성공을 기록했다고 사용자 요청이 실제로 통과한 것도 아닙니다. 외부 smoke, workload SLI와 audit evidence가 별도로 필요합니다.

## 7. 핵심 과정과 선택 실습의 경계

핵심 과정은 문서·JSON 계약과 상태 모델만으로 완료할 수 있습니다. 다음 도구는 선택 profile입니다.

- Kubernetes local cluster: `kind` 또는 동등 환경
- Infrastructure as Code: OpenTofu 또는 Terraform
- Software catalog와 portal: Backstage 또는 동등 구현
- GitOps controller: Flux 또는 Argo CD
- Admission policy: Kubernetes CEL, Kyverno, Gatekeeper 또는 동등 구현

선택 실습은 [`90-optional-labs/00-index.md`](90-optional-labs/00-index.md)에서 시작합니다. 특정 도구 하나를 설치했다고 플랫폼 엔지니어링을 완료한 것으로 보지 않습니다.

## 8. 완료 기준

다음 결과물을 독립적으로 만들 수 있어야 합니다.

- 사용자와 outcome이 명확한 platform product brief
- versioned platform API contract와 reconciliation state machine
- IaC state partition·locking·drift·migration 정책
- workload contract와 tenant isolation profile
- service catalog metadata와 golden path lifecycle
- artifact promotion·GitOps·emergency change workflow
- identity·secret·policy·exception 계약
- platform journey SLI·SLO·capacity·cost·support model
- upgrade·migration·deprecation plan
- 실패 drill과 runbook을 포함한 capstone 설계

가이드 이후에는 실제 플랫폼 또는 오픈소스 저장소에서 작은 controller, template, policy, observability 또는 문서 변경으로 기여를 시작합니다.
