# 공식 자료 색인

이 가이드는 특정 제품의 명령을 정본으로 복사하지 않습니다. 개념의 정의, 현재 API와 설치 절차는 각 프로젝트의 공식 문서를 확인합니다. 아래 링크는 2026-08-09에 확인한 시작점이며, 실제 실습 전에는 지원 version과 변경 사항을 다시 확인합니다.

<a id="platform-product"></a>
## 플랫폼을 제품으로 운영하기

- [DORA: Platform engineering](https://dora.dev/capabilities/platform-engineering/) — 내부 플랫폼을 자동화·self-service·반복 가능한 workflow와 사용자 중심 제품으로 보는 출발점
- [Backstage Software Catalog](https://backstage.io/docs/features/software-catalog/) — component·owner·system·resource metadata와 catalog 모델
- [Backstage Software Templates](https://backstage.io/docs/features/software-templates/) — repository와 component 시작 구조를 생성하는 template 기능

Portal과 catalog 제품의 기능을 platform API·control plane의 소유권과 동일시하지 않습니다.

<a id="control-loop"></a>
## Kubernetes API와 제어 루프

- [Kubernetes Concepts](https://kubernetes.io/docs/concepts/) — cluster, workload, service, storage와 configuration 개요
- [Controllers](https://kubernetes.io/docs/concepts/architecture/controller/) — desired state와 control loop
- [Kubernetes API](https://kubernetes.io/docs/reference/kubernetes-api/) — object schema와 API reference
- [Workload management](https://kubernetes.io/docs/concepts/workloads/controllers/) — Deployment, StatefulSet, Job 등 controller가 관리하는 workload

<a id="kubernetes"></a>
## Kubernetes runtime 경계

- [Services, Load Balancing, and Networking](https://kubernetes.io/docs/concepts/services-networking/) — Service, network와 traffic 경계
- [Storage](https://kubernetes.io/docs/concepts/storage/) — volume, persistent volume와 storage class
- [Scheduling, Preemption and Eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/) — scheduler와 배치 계약
- [Resource Quotas](https://kubernetes.io/docs/concepts/policy/resource-quotas/) — namespace 단위 resource 제한
- [Multi-tenancy](https://kubernetes.io/docs/concepts/security/multi-tenancy/) — namespace·cluster 등 tenant isolation 선택
- [Pod Security Admission](https://kubernetes.io/docs/concepts/security/pod-security-admission/) — Pod security standard 적용 경계

<a id="kubernetes-disruption"></a>
## 중단과 가용성

- [Disruptions](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/) — voluntary/involuntary disruption과 PodDisruptionBudget

PDB가 workload 전체 availability를 자동 보장하거나 cluster capacity를 생성하는 것은 아닙니다.

<a id="iac-state"></a>
## Infrastructure as Code와 state

- [Terraform state](https://developer.hashicorp.com/terraform/language/state) — configuration address와 remote object mapping
- [Terraform backends](https://developer.hashicorp.com/terraform/language/state/backends) — state 저장과 locking 경계
- [OpenTofu state](https://opentofu.org/docs/language/state/) — OpenTofu의 state 모델과 관련 문서

Provider와 backend별 locking·encryption·migration 동작은 사용하는 version의 공식 문서를 추가로 확인합니다.

<a id="gitops"></a>
## GitOps와 reconciliation

- [OpenGitOps principles](https://opengitops.dev/) — declarative, versioned/immutable, pulled automatically, continuously reconciled 원칙
- [Flux concepts](https://fluxcd.io/flux/concepts/) — source와 reconciliation, controller 구성
- [Argo CD automated sync](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/) — automated sync, prune와 self-heal 경계

구현 제품을 고르기 전에 desired state owner, drift, prune와 break-glass 계약을 먼저 정의합니다.

<a id="observability"></a>
## 관측성

- [OpenTelemetry signals](https://opentelemetry.io/docs/concepts/signals/) — traces, metrics, logs와 baggage의 역할

Platform journey identity, audit와 high-cardinality 정책은 조직 설계가 별도로 필요합니다.

<a id="identity"></a>
## Workload identity

- [SPIFFE overview](https://spiffe.io/docs/latest/spiffe-about/overview/) — workload identity와 trust domain의 기본 모델

SPIFFE/SPIRE 사용 여부와 무관하게 workload identity의 발급 근거, audience, TTL, rotation과 revocation을 설계합니다.

<a id="supply-chain"></a>
## Software supply chain

- [SLSA Provenance](https://slsa.dev/spec/v1.2/provenance) — artifact가 어떤 input과 build process에서 생성됐는지 표현하는 provenance 모델
- [SLSA tracks](https://slsa.dev/spec/v1.2/tracks) — build와 source 등 supply-chain 보장 범주

SLSA level 또는 badge 자체보다 실제 threat와 검증 policy가 무엇을 보장하는지 확인합니다.

## 자료 사용 규칙

- 공식 문서의 현재 version을 우선합니다.
- 한 제품의 동작을 플랫폼 엔지니어링 일반 원리로 확장하지 않습니다.
- deprecated/experimental 기능은 support status를 표시합니다.
- 외부 문구를 긴 분량으로 복사하지 않고 개념을 자신의 상태·실패·검증 언어로 다시 설명합니다.
- 예제 version을 올릴 때 문서, 실습, 검사와 migration 설명을 함께 갱신합니다.
