# 플랫폼 엔지니어링 가이드

플랫폼 엔지니어링은 Kubernetes, Terraform과 CI/CD 도구를 한데 모으는 일이 아닙니다. 여러 개발 팀이 서비스를 만들고 변경하고 운영할 때 반복해서 겪는 어려움을 **제품처럼 관리되는 공통 인터페이스와 자동화된 경로**로 줄이는 일입니다.

이 가이드는 단일 공개 서비스를 운영하는 [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra)의 기준선에서 시작합니다. 그 운영 능력을 여러 팀과 서비스가 공유할 수 있도록 다음 문제로 확장합니다.

- 플랫폼의 사용자와 해결할 문제를 정합니다.
- 개발 팀과 플랫폼 팀의 책임 경계를 계약으로 만듭니다.
- 선언한 상태와 실제 상태를 제어 루프로 수렴시킵니다.
- Infrastructure as Code의 설정·state·원격 자원·drift를 구분합니다.
- Kubernetes API, workload, network, storage와 scheduling 경계를 이해합니다.
- self-service API, software catalog와 golden path를 설계합니다.
- 한 번 만든 artifact를 여러 환경으로 안전하게 승격합니다.
- GitOps의 desired state, reconciliation과 긴급 변경 경계를 운영합니다.
- 사람·workload·automation identity와 정책 적용 지점을 분리합니다.
- 여러 tenant의 권한·자원·네트워크·blast radius를 제한합니다.
- 플랫폼 사용자 여정의 SLO, 용량, 비용과 지원 모델을 운영합니다.
- 플랫폼 자체를 upgrade·migration·deprecation 가능한 제품으로 관리합니다.

처음에는 [`docs/00-roadmap.md`](docs/00-roadmap.md)를 읽으세요. 선행 지식, 문서 순서, 실습 방식과 완료 기준을 한 문서에서 확인할 수 있습니다.

## 과정이 만드는 능력

과정을 마치면 다음 작업을 수행할 수 있어야 합니다.

- 플랫폼을 내부 인프라 티켓 처리 조직이 아니라 개발자를 위한 제품으로 정의합니다.
- 사용자 여정과 실제 마찰 근거에서 platform capability의 우선순위를 정합니다.
- platform API의 입력·출력·상태·오류·취소·소유권을 명시합니다.
- 비동기 provisioning을 desired state, observed state와 condition으로 모델링합니다.
- IaC state의 소유자, locking, sensitive data, drift와 migration 경계를 설계합니다.
- Kubernetes workload가 요청한 자원, readiness, network, storage와 disruption 계약을 검토합니다.
- portal, catalog, template와 platform control plane을 서로 다른 구성요소로 구분합니다.
- golden path의 지원 범위, escape hatch와 deprecation 정책을 정합니다.
- build, artifact, environment configuration과 deployment result를 추적 가능한 release로 연결합니다.
- GitOps reconciliation이 실패하거나 긴급 변경과 충돌할 때 복구 순서를 설명합니다.
- short-lived workload identity, secret delivery, admission policy와 예외 수명을 설계합니다.
- tenant trust 수준에 맞춰 account·cluster·namespace·node 경계를 선택합니다.
- 플랫폼 내부 상태와 개발자 경험을 trace·metric·log·audit event로 연결합니다.
- 플랫폼 여정별 SLI·SLO, 지원 책임, 용량 headroom과 비용 배분 기준을 만듭니다.
- cluster, add-on, policy, template와 platform API를 중단 가능성을 관리하며 upgrade합니다.
- 최종 과제에서 서비스 생성부터 폐기까지의 self-service 경로와 실패 복구를 검증합니다.

## 범위

이 과정의 기준선은 다음과 같습니다.

```text
여러 개발 팀
+ 여러 애플리케이션 저장소
+ 공통 build·artifact·deployment 경로
+ 선언형 infrastructure와 runtime state
+ Kubernetes를 사용한 대표 runtime profile
+ self-service platform API와 software catalog
+ GitOps reconciliation
+ workload identity·policy·telemetry
+ platform SLO·capacity·cost·upgrade 계약
```

Kubernetes는 이 가이드의 중요한 구현 profile이지만 플랫폼 엔지니어링의 정의 자체는 아닙니다. 조직에 따라 VM, serverless, managed data service와 SaaS를 같은 platform API 뒤에 둘 수 있습니다. 핵심은 도구 이름이 아니라 **사용자가 요청한 결과, 현재 상태, 실패와 복구 책임을 일관된 계약으로 제공하는가**입니다.

다음은 이 과정의 기본 범위가 아닙니다.

- 한 대의 Linux 호스트에 공개 서비스를 처음 배포하는 방법
- 애플리케이션의 API·DB·업무 로직 구현
- 서비스 간 Saga, Outbox와 업무 정합성의 전체 설명
- consensus, replicated log와 분산 저장소 구현
- 특정 cloud provider의 모든 제품과 자격증 범위
- Kubernetes control plane을 처음부터 구축하는 방법
- 조직 전체의 보안 감사, 규제 인증과 침투 테스트
- 모든 팀을 하나의 template에 강제하는 조직 정책

이 영역은 각각 `web-infra`, `web-app`, `distributed-services`, `distributed-systems`, `cybersecurity`와 실제 조직의 전문 과정이 주로 소유합니다.

### `main`의 소유 계약

이 브랜치는 최신 `main`에서 `specialization`으로 분류됩니다. 아래 문구는 구현 범위를 임의로 넓히거나 줄이지 않기 위한 정본입니다.

| 구분 | 계약 |
|---|---|
| 직접 필수 | `web-infra` |
| 권장 기반 | `distributed-services`, `cybersecurity`, `computer-networks`, `cloud-computing`, `data-engineering` |
| 인접 연결 | `agentic-systems`, `machine-learning`, `distributed-systems`, `cloud-computing`, `game-development` |
| 정해진 후속 브랜치 | 없음. 완료 뒤 실제 플랫폼·도구 저장소에 기여하고, 프로젝트 목적에 맞는 인접 브랜치를 선택합니다. |

이 브랜치가 주로 소유하는 범위는 다음 다섯 가지입니다.

1. 플랫폼 사용자와 golden path
2. Infrastructure as Code와 drift
3. 컨테이너 오케스트레이션
4. 재사용 가능한 CI/CD·GitOps
5. identity·secret·관측·catalog·multi-tenancy

단일 서비스 공개 운영 재교육, 애플리케이션 도메인 로직, 조직 문화 일반론만의 DevOps와 특정 클라우드 자격증 범위는 명시적으로 소유하지 않습니다.

## 선행 지식

### 필수 기준선

- [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra)의 공개 운영 경계를 이해합니다.
- Git 저장소의 branch, commit, review와 CI 결과를 읽을 수 있습니다.
- HTTP API와 비동기 작업의 기본 구조를 이해합니다.
- Linux process, file permission, network endpoint를 관찰할 수 있습니다.

### 권장 기반

- [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks): DNS·TLS·routing·service path 진단
- [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services): timeout·retry·idempotency·부분 실패
- [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity): threat model·least privilege·사고 대응
- [`cloud-computing`](https://github.com/seungwoo7050/guides/tree/cloud-computing): 공급자·소비자 책임, failure domain, 비용과 관리 경계
- [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering): 여러 팀의 pipeline workload가 요구하는 자원·품질·lineage 계약

모든 권장 브랜치를 먼저 완료할 필요는 없습니다. 각 문서가 요구하는 경계를 이해하지 못할 때 해당 가이드의 필요한 장으로 이동합니다.

`unix-systems`는 아래 직무 트랙에서 플랫폼에 진입하기 전의 운영 관찰 기반입니다. `distributed-systems`는 복제·합의 자체를 구현하려는 후속 심화이며, 이 브랜치의 직접 필수나 권장 선행으로 강제하지 않습니다.

## 업무 트랙에서의 위치

`platform-engineering`이 실제 선형 경로에 포함되는 핵심 트랙은 두 개입니다.

| 트랙 | 권장 선형 경로 |
|---|---|
| `infrastructure-platform` — host platform | `git → unix-systems → computer-networks → web-infra → cybersecurity → platform-engineering` |
| `infrastructure-platform` — cloud platform | `git → unix-systems → computer-networks → web-infra → cloud-computing → cybersecurity → platform-engineering` |
| `game-tools-platform` | `git → python → unix-systems → game-development → web-infra → platform-engineering` |

`data-engineering`과 `distributed-systems` 트랙에서는 권장 인접 지식이고, 웹·SaaS·cloud·보안·ML·agent·게임 서버/데이터 트랙에서는 핵심 경로 뒤의 심화 선택입니다. 트랙의 위치는 브랜치 자체의 엄밀한 직접 의존성과 같지 않습니다.

## 읽는 순서

| Part | 문서 | 종료 능력 |
|---|---|---|
| I | [플랫폼을 제품으로 정의하기](docs/01-platform-as-product.md) | 사용자와 문제를 근거로 platform outcome을 정합니다. |
| I | [플랫폼 계약과 책임 경계](docs/02-platform-contracts-and-ownership.md) | 팀·API·지원·escape hatch의 소유권을 고정합니다. |
| I | [Control plane과 reconciliation](docs/03-control-planes-and-reconciliation.md) | desired state를 반복 가능한 제어 루프로 수렴시킵니다. |
| II | [Infrastructure as Code와 state](docs/04-infrastructure-as-code-state-and-drift.md) | configuration·state·원격 자원·drift를 안전하게 관리합니다. |
| II | [Kubernetes API와 workload](docs/05-kubernetes-api-workloads-and-controllers.md) | API object와 controller가 workload를 유지하는 계약을 이해합니다. |
| II | [Kubernetes network·storage·scheduling](docs/06-kubernetes-network-storage-and-scheduling.md) | 통신·저장·배치·disruption의 플랫폼 경계를 검토합니다. |
| III | [Self-service platform API와 catalog](docs/07-self-service-platform-apis-and-catalogs.md) | portal과 무관하게 작동하는 비동기 platform API를 설계합니다. |
| III | [Golden path와 service lifecycle](docs/08-golden-paths-and-service-lifecycle.md) | 생성부터 폐기까지 지원되는 경로와 예외를 관리합니다. |
| III | [Delivery platform과 artifact promotion](docs/09-delivery-platform-and-artifact-promotion.md) | build once와 environment promotion을 release 계약으로 만듭니다. |
| III | [GitOps reconciliation과 긴급 변경](docs/10-gitops-reconciliation-and-emergency-changes.md) | desired state, drift, prune와 break-glass 변경을 운영합니다. |
| III | [Identity·secret·policy](docs/11-identity-secrets-and-policy.md) | 사람과 workload 권한, secret 수명과 정책 단계를 분리합니다. |
| IV | [관측·감사·개발자 피드백](docs/12-observability-audit-and-developer-feedback.md) | 플랫폼 내부 동작과 사용자 여정을 같은 근거로 연결합니다. |
| IV | [Multi-tenancy·quota·isolation](docs/13-multitenancy-quotas-and-isolation.md) | tenant별 권한·공정성·blast radius 경계를 설계합니다. |
| IV | [Platform SLO·capacity·cost·support](docs/14-platform-slo-capacity-cost-and-support.md) | 여정별 신뢰성과 운영 책임을 수치와 절차로 관리합니다. |
| IV | [Upgrade·migration·deprecation](docs/15-upgrades-migrations-and-deprecation.md) | 플랫폼 변경을 호환성·wave·rollback 계약으로 전달합니다. |
| IV | [Supply chain과 platform security](docs/16-supply-chain-and-platform-security.md) | source에서 runtime까지 신뢰 근거와 guardrail을 제공합니다. |
| V | [Internal Developer Platform Capstone](docs/17-capstone.md) | 모든 경계를 하나의 self-service 플랫폼 설계로 통합합니다. |

## 실습 구조

핵심 실습은 cloud 계정이나 Kubernetes cluster가 없어도 수행할 수 있는 **계약 설계형 문제**입니다.

```text
exercises/NN-name/
├── README.md
├── contract.json
├── skeleton/submission.json
└── reference/submission.json
```

학습자는 `skeleton`을 `.workspace/`로 복사해 완성합니다.

```sh
mkdir -p .workspace
cp -R exercises/01-platform-product/skeleton .workspace/platform-product
python3 scripts/verify_submission.py \
  exercises/01-platform-product/contract.json \
  .workspace/platform-product/submission.json
```

`reference`는 한 가지 가능한 답입니다. 특정 문구를 외우는 것이 아니라 다음 계약을 만족하는지 비교합니다.

- 사용자가 누구이며 무엇을 요청하는가?
- 정본과 현재 상태는 어디에 있는가?
- 어떤 실패가 재시도 가능하고 어떤 실패가 사람의 결정을 요구하는가?
- 누가 변경하고 누가 승인하며 누가 복구하는가?
- 완료와 실패를 어떤 외부 근거로 판정하는가?

실제 Kubernetes, IaC, portal과 GitOps 도구를 실행하는 실습은 [`docs/90-optional-labs/00-index.md`](docs/90-optional-labs/00-index.md)에 분리했습니다. 도구 설치 여부는 핵심 과정의 완료 조건이 아닙니다.

## 준비와 검증

필수 실행 환경은 Python 3.10 이상과 POSIX 호환 셸입니다.

```sh
./prepare.sh
./verify.sh
```

`prepare.sh`는 시스템 package나 platform 도구를 설치하지 않습니다. 현재 source fingerprint와 Python 환경을 `.guide/platform-engineering/prepared.json`에 기록합니다.

`verify.sh`는 다음을 확인합니다.

1. 최종 파일 구조와 내부 Markdown 링크
2. JSON 예제와 실습 계약의 문법
3. 모든 reference 제출물이 계약을 통과하는지
4. 모든 skeleton이 같은 계약에 실제로 거부되는지
5. 셸 스크립트 문법과 실행 권한
6. 준비 이후 추적 대상 source가 바뀌지 않았는지

빠른 정적 검사는 다음과 같습니다.

```sh
make check
```

이 검증은 실제 cloud resource, Kubernetes admission, network isolation이나 deployment 성공을 증명하지 않습니다. 그런 주장은 선택 실습 또는 실제 플랫폼에서 별도 evidence를 남겨야 합니다.

## 과정 종료 기준

다음 질문에 근거를 제시할 수 있어야 합니다.

- 플랫폼이 해결하는 사용자 문제와 해결하지 않는 문제는 무엇입니까?
- self-service 요청의 정본 상태와 최종 완료 판정은 어디에 있습니까?
- IaC와 GitOps controller가 동시에 관리하는 자원이 없습니까?
- application team과 platform team이 각각 소유하는 실패는 무엇입니까?
- tenant 하나의 오류가 다른 tenant와 control plane에 미치는 범위는 어디까지입니까?
- 정책 예외와 긴급 변경은 누가, 언제까지, 어떤 audit 근거로 종료합니까?
- platform API, cluster, add-on과 template를 어떻게 upgrade하고 이전 버전을 폐기합니까?
- 개발자가 플랫폼을 사용한 뒤 실제로 더 빠르고 안전하게 결과를 전달했음을 어떻게 측정합니까?

이 질문에 답할 수 있으면 Kubernetes 명령을 아는 수준을 넘어, 실제 플랫폼 저장소와 운영 절차에 기여할 준비가 된 것입니다.
