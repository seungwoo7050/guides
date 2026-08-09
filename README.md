# 클라우드 컴퓨팅과 서비스 모델 가이드

클라우드 컴퓨팅을 특정 공급자의 제품 목록이나 콘솔 사용법으로 배우지 않고, **누가 어떤 상태를 소유하며 어떤 책임이 공급자에게 이동하고 무엇이 소비자에게 남는지**를 기준으로 학습하는 가이드입니다.

```text
클라우드의 공통 특성과 책임 경계를 구분합니다.
→ IaaS의 compute·network·storage·identity 상태를 설계합니다.
→ PaaS와 관리형 서비스가 숨기는 운영과 남기는 책임을 확인합니다.
→ serverless/FaaS의 실행·이벤트·동시성·재시도 계약을 검증합니다.
→ SaaS의 tenant 격리·entitlement·metering·수명을 설계합니다.
→ 비용·가용성·보안·이식성·철수 계획을 함께 검토합니다.
```

이 브랜치의 목적은 AWS·Azure·Google Cloud의 모든 제품을 외우게 하는 것이 아닙니다. 개발자가 클라우드 기반 애플리케이션, SaaS, serverless, 관리형 데이터 서비스 또는 이후의 플랫폼 엔지니어링 프로젝트에 합류할 때 필요한 **서비스 선택 기준, 실패 모델, 검증 증거와 비용 경계**를 제공합니다.

처음에는 [`docs/00-roadmap.md`](docs/00-roadmap.md)를 읽으세요. 대상 독자, 선행 브랜치, 필수 문서 순서, 로컬 실습, 선택적인 실제 공급자 실험, Capstone과 완료 기준을 한곳에서 확인할 수 있습니다.

## 시작하기 전에

이 브랜치는 작은 공개 서비스를 배포·관찰·복구해 본 개발자를 위한 심화 과정입니다.

- 필수 기반: `web-infra`의 Linux 호스트, 컨테이너, DNS·TLS, 배포, 관측, 백업과 사고 대응
- 작업 기반: Git, 셸, Markdown·JSON, Python 표준 라이브러리를 실행할 수 있는 환경
- 문제별 보완:
  - 애플리케이션 기능과 인증은 `web-app`
  - 관계형 데이터와 트랜잭션은 `database-systems`
  - 중복·재시도·부분 실패는 `distributed-services`
  - 위협 모델·최소 권한·사고 대응의 일반 원리는 `cybersecurity`

`cloud-computing`은 위 내용을 반복하지 않습니다. 기존 시스템을 클라우드 서비스 모델로 옮겼을 때 **관리 경계, identity, failure domain, 과금 단위와 종료 절차가 어떻게 달라지는지**에 집중합니다.

## main 계약과 관계

이 가이드는 최신 `main`에서 `specialization`으로 정의됩니다. 관계 필드는 학습 순서를 강제하는 한 목록이 아니라 직접 필수, 권장 기반, 인접 협업과 일반적인 후속 경로를 구분합니다.

| 관계 | 브랜치 |
|---|---|
| `requires` | [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra) |
| `recommends` | [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems), [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity) |
| `connects` | [`platform-engineering`](https://github.com/seungwoo7050/guides/blob/887f4b8a679195c5b6c13457a91e0b0af357ccff/catalog/branches.json#L959), [`data-engineering`](https://github.com/seungwoo7050/guides/blob/887f4b8a679195c5b6c13457a91e0b0af357ccff/catalog/branches.json#L918), [`machine-learning`](https://github.com/seungwoo7050/guides/blob/887f4b8a679195c5b6c13457a91e0b0af357ccff/catalog/branches.json#L793), [`agentic-systems`](https://github.com/seungwoo7050/guides/blob/887f4b8a679195c5b6c13457a91e0b0af357ccff/catalog/branches.json#L835), [`distributed-systems`](https://github.com/seungwoo7050/guides/blob/887f4b8a679195c5b6c13457a91e0b0af357ccff/catalog/branches.json#L878) |
| `continues_to` | [`platform-engineering`](https://github.com/seungwoo7050/guides/blob/887f4b8a679195c5b6c13457a91e0b0af357ccff/catalog/branches.json#L959) |

`connects`와 `continues_to` 중 아직 원격 구현이 없는 항목은 `main` SHA `887f4b8`에서 승인된 목표 계약으로 연결합니다. 존재하지 않는 완료 브랜치처럼 설명하지 않습니다.

## 과정이 만드는 능력

과정을 마치면 다음 작업을 수행할 수 있어야 합니다.

- 마케팅 명칭이 아니라 on-demand self-service, resource pooling, elasticity, measured service와 책임 경계로 클라우드 서비스를 판별합니다.
- IaaS·PaaS·SaaS를 소비자가 제어하는 층과 공급자가 관리하는 층으로 구분합니다.
- FaaS를 NIST의 세 서비스 모델과 같은 축으로 오해하지 않고 serverless 실행·이벤트 처리 모델로 설명합니다.
- control plane과 data plane, 사람 identity와 workload identity, resource policy와 application authorization을 분리합니다.
- region·availability zone·fault domain의 차이를 설명하고 복제·복구·확장 주장의 실제 보장 범위를 검토합니다.
- VM·network·storage·load balancer·managed database·object storage의 상태 수명과 삭제 순서를 설계합니다.
- 관리형 서비스의 patching·backup·availability 책임이 어디까지 공급자에게 이동하고 무엇이 소비자에게 남는지 계약으로 작성합니다.
- event source, timeout, concurrency, retry, dead-letter와 idempotency를 연결해 FaaS의 중복·부분 성공을 처리합니다.
- SaaS의 tenant onboarding, data isolation, role, plan, entitlement, quota, usage, export와 deletion을 하나의 수명 주기로 설계합니다.
- request·duration·storage·I/O·egress·provisioned capacity 비용을 resource inventory와 workload 단위로 연결합니다.
- cloud architecture의 보안·관측·비용·복구·portability·exit 근거를 검토하고 잔여 위험을 기록합니다.
- 실제 공급자 계정 없이도 로컬 상태 모델과 문서 산출물로 핵심 계약을 재현하고, 실제 계정 실험은 명시적 예산·권한·정리 계약 아래 수행합니다.

## 이 브랜치가 소유하는 범위

`main` 카탈로그의 최종 설계에 맞춰 다음 범위를 소유합니다. 각 항목의 개념·실습·Capstone·판정 근거는 [`contract evidence map`](reference/contract-evidence-map.md)에서 추적할 수 있습니다.

- on-demand·resource pooling·elasticity·measured service와 공급자·소비자 공유 책임
- region·availability zone·failure domain과 compute·network·storage·identity의 관리 경계
- IaaS·PaaS·SaaS 서비스 모델과 VM·container·CaaS·serverless/FaaS 실행 모델의 구분
- FaaS event source·delivery·concurrency·cold start·timeout 제약에 기존 전달 계약을 적용하는 방법
- 고객 조직을 위한 SaaS tenant 수명·control/data plane·격리·metering·quota·export·deletion
- 예산·탄력성·가용성·portability·vendor lock-in의 근거 기반 비교

다음 영역은 다른 브랜치가 주로 소유합니다.

| 영역 | 주 소유 브랜치 | 이 브랜치에서 사용하는 방식 |
|---|---|---|
| 단일 호스트·Docker·DNS·TLS·배포·백업 | [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra) | 같은 서비스가 cloud resource로 이동할 때 책임과 실패가 어떻게 바뀌는지 비교합니다. |
| 웹 기능·세션·권한·API | [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app) | SaaS의 tenant context와 외부 서비스 계약의 입력으로 사용합니다. |
| 스키마·트랜잭션·DBMS 내부구조 | [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems) | managed database 선택과 tenant isolation의 데이터 계약에 적용합니다. |
| retry·멱등성·Outbox·부분 실패 | [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services) | FaaS event source와 cloud provisioning 작업에 적용합니다. |
| 일반 위협 모델·보안 검증·사고 대응 | [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity) | cloud identity, metadata, tenant isolation과 control plane 변경을 검토합니다. |
| 여러 팀의 Kubernetes·IaC module·golden path | [`platform-engineering` 목표 계약](https://github.com/seungwoo7050/guides/blob/887f4b8a679195c5b6c13457a91e0b0af357ccff/catalog/branches.json#L959) | 이 브랜치는 한 workload와 작은 SaaS의 cloud 책임을 다루고, 조직용 self-service 플랫폼은 후속 경로로 넘깁니다. |
| 합의·복제 상태 기계 | [`distributed-systems` 목표 계약](https://github.com/seungwoo7050/guides/blob/887f4b8a679195c5b6c13457a91e0b0af357ccff/catalog/branches.json#L878) | provider 서비스가 제공한다고 주장하는 일관성·가용성의 외부 계약만 사용합니다. |

## 학습 구조

### Part I. 클라우드 판단의 기반

1. [클라우드 상태, 책임과 증거](docs/01-cloud-state-responsibility-and-evidence.md)
2. [클라우드 특성, 서비스 모델과 배포 모델](docs/02-cloud-characteristics-service-and-deployment-models.md)
3. [Control plane, data plane과 identity](docs/03-control-plane-data-plane-and-identity.md)

### Part II. 인프라와 관리형 플랫폼

4. [IaaS compute, network와 storage](docs/04-iaas-compute-network-and-storage.md)
5. [Failure domain, elasticity와 recovery](docs/05-failure-domains-elasticity-and-recovery.md)
6. [PaaS와 managed service 계약](docs/06-paas-and-managed-service-contracts.md)

### Part III. Serverless와 FaaS

7. [Serverless와 FaaS runtime](docs/07-serverless-and-faas-runtime.md)
8. [Event delivery, concurrency와 idempotency](docs/08-event-delivery-concurrency-and-idempotency.md)

### Part IV. SaaS 제품 경계

9. [SaaS tenancy와 isolation](docs/09-saas-tenancy-and-isolation.md)
10. [Entitlement, metering와 billing](docs/10-saas-entitlements-metering-and-billing.md)

### Part V. 운영 판단과 종료

11. [Cloud security, observability와 incident](docs/11-cloud-security-observability-and-incidents.md)
12. [Cost, capacity, quota와 FinOps](docs/12-cost-capacity-quotas-and-finops.md)
13. [Portability, lock-in과 exit](docs/13-portability-lock-in-and-exit.md)
14. [서비스 선택과 architecture review](docs/14-service-selection-and-architecture-review.md)
15. [멀티테넌트 문서 처리 SaaS Capstone](docs/15-capstone.md)
16. [표준과 외부 자료 지도](docs/90-standards-map.md)

## 단계 실습

필수 실습은 실제 유료 클라우드 계정을 요구하지 않습니다. 문서 산출물과 Python 표준 라이브러리의 합성 상태 모델로 서비스 모델, 장애, 이벤트, 격리와 비용 계약을 검증합니다.

| 실습 | 결과물 |
|---|---|
| [01 서비스 분류](exercises/01-service-classification/README.md) | 사례별 IaaS·PaaS·SaaS·FaaS 분류와 책임 근거 |
| [02 IaaS failure domain](exercises/02-iaas-failure-domains/README.md) | resource inventory, failure map과 recovery evidence |
| [03 managed service 계약](exercises/03-managed-service-contract/README.md) | 공급자·소비자 책임, limit, backup과 exit 계약 |
| [04 FaaS event lifecycle](exercises/04-faas-event-lifecycle/README.md) | 중복·timeout·partial failure·DLQ 정책 |
| [05 SaaS tenant isolation](exercises/05-saas-tenant-isolation/README.md) | tenant context, data·cache·job·export 격리 검토 |
| [06 비용과 exit](exercises/06-cost-and-exit/README.md) | 비용 driver, budget, orphan resource와 철수 계획 |
| [07 로컬 cloud model](exercises/07-local-cloud-model/README.md) | 취약 skeleton의 cross-tenant·중복·quota·cleanup 실패를 수정하는 실행 실습 |

01~06은 정답 문구를 맞히는 문제가 아닙니다. 제공된 입력을 바탕으로 필수 산출물을 작성하고 reference와 **근거의 범위와 빠진 실패 조건**을 비교합니다. 07은 구현 형태가 아니라 tenant 거부, idempotent event, quota의 원자성, private state와 cleanup 불변식을 검사합니다.

## Capstone

[`projects/multitenant-document-processing-saas`](projects/multitenant-document-processing-saas/README.md)는 하나의 workload를 다음 네 단계로 재설계합니다.

```text
IaaS 배치
→ managed platform 전환
→ event-driven FaaS 처리
→ tenant·plan·quota·metering·export·deletion을 갖춘 SaaS
```

학습자는 각 단계에서 책임 matrix, resource inventory, identity와 network 경계, failure test, cost model, incident evidence와 exit plan을 갱신합니다. 선택적으로 실제 공급자 profile 하나를 적용할 수 있지만, 최종 판정은 공급자 이름이 아니라 증거와 불변식으로 수행합니다.

## 준비와 전체 검증

필수 환경은 Python 3.10 이상, POSIX shell과 `tar`입니다. 외부 Python package, Docker와 실제 cloud credential은 필요하지 않습니다.

```sh
./prepare.sh
./verify.sh
```

- `prepare.sh`는 source와 학습자 workspace를 바꾸지 않고 지원 환경과 source fingerprint를 기록합니다.
- `verify.sh`는 저장소 밖 임시 복사본에서 구조·링크·reference·template 음수 검사와 로컬 cloud model을 확인합니다.
- 모든 reference는 통과해야 하며, 미완성 template과 의도적으로 취약한 skeleton은 같은 검사에서 실패해야 합니다.
- 실제 cloud provider 접근은 검증 과정에 포함하지 않습니다.

문서 실습 workspace를 만듭니다.

```sh
scripts/new_workspace.sh exercises/01-service-classification
scripts/check_workspace.sh exercises/01-service-classification
```

Capstone workspace도 같은 방식으로 만듭니다.

```sh
scripts/new_workspace.sh projects/multitenant-document-processing-saas
scripts/check_workspace.sh projects/multitenant-document-processing-saas
```

07 코드 실습은 `template/` 대신 취약한 `skeleton/`에서 안전하게 시작하고 같은 공개 validator로 검사합니다.

```sh
scripts/new_workspace.sh exercises/07-local-cloud-model
scripts/check_workspace.sh exercises/07-local-cloud-model
```

wrapper는 기존 workspace·symlink·저장소 밖 경로를 거부하며 학습자 구현을 덮어쓰지 않습니다.

## 실제 공급자 실험

실제 AWS·Azure·Google Cloud 계정은 선택 사항입니다. 실행 전 반드시 [`cloud experiment safety`](reference/cloud-experiment-safety.md)를 읽고 다음을 갖춥니다.

```text
별도 학습 계정 또는 project/subscription
최소 권한 identity
고유 resource prefix
예산과 경보
종료 시각 또는 TTL tag
resource inventory
명시적인 destroy 절차
종료 후 잔존 자원 검사
```

`prepare.sh`와 `verify.sh`는 유료 자원을 만들거나 지우지 않습니다. 공급자 profile은 [`profiles/README.md`](profiles/README.md)의 계약에 따라 사람이 명시적으로 실행합니다.

## 종료점

이 브랜치를 마쳤다고 cloud architect나 SaaS 운영 전문가가 되는 것은 아닙니다. 종료점은 다음과 같습니다.

```text
처음 보는 cloud architecture를 책임·상태·실패·비용 단위로 복원합니다.
→ workload를 IaaS·managed platform·FaaS 중 어디에 둘지 근거로 선택합니다.
→ 작은 SaaS의 tenant isolation과 product lifecycle을 설계합니다.
→ 실패·비용·복구·exit 주장을 검증할 증거를 요구합니다.
→ 실제 프로젝트에서 공급자별 제품과 운영 경험을 추가할 수 있습니다.
```
