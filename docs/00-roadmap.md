# 클라우드 컴퓨팅 학습 경로

## 이 과정의 위치

`cloud-computing`은 작은 공개 서비스를 직접 운영해 본 개발자가 **클라우드 서비스가 어떤 책임을 숨기고 어떤 책임을 남기는지**, 그리고 그 선택이 failure domain·identity·비용·tenant·exit에 어떤 영향을 주는지 학습하는 심화 브랜치입니다.

```text
web-infra
단일 Linux 호스트와 공개 서비스 운영 기준선
        │
        ▼
cloud-computing
IaaS·managed platform·FaaS·SaaS의 책임과 상태 전이
        │
        ├── 실제 SaaS·serverless·cloud application 프로젝트
        └── platform-engineering 등 조직 단위 후속 심화
```

클라우드는 “서버가 인터넷 어딘가에 있다”는 뜻만으로 성립하지 않습니다. 독자는 자원 생성·확장·삭제가 API로 자동화되고, 공유 자원이 풀에서 할당되며, 사용량이 측정되고, 공급자와 소비자의 관리 경계가 달라지는 환경을 다룹니다.

## 대상 독자

다음 조건을 만족하는 개발자를 대상으로 합니다.

- 작은 웹 또는 API 서비스를 실행해 본 경험이 있습니다.
- process, port, DNS, TLS, container, database, log와 backup의 역할을 구분할 수 있습니다.
- 장애가 발생했을 때 마지막 성공 지점과 첫 실패 지점을 찾는 기본 절차를 알고 있습니다.
- Git, Markdown, JSON과 Python 표준 라이브러리를 사용할 수 있습니다.
- 공급자 제품명을 외우는 대신 책임과 증거를 기준으로 architecture를 비교하려 합니다.

클라우드 계정, 신용카드, Kubernetes 경험은 필수 조건이 아닙니다.

## 선행 브랜치

### 필수: `web-infra`

다음 능력을 전제로 합니다.

- Linux 호스트와 프로세스의 실행 경계를 설명합니다.
- image, container, network, volume과 상태 수명을 구분합니다.
- DNS·TLS·gateway·application·database 실패를 분리합니다.
- release, rollback, secret, observability, backup과 incident response의 기준선을 이해합니다.

이 내용이 부족하면 먼저 `web-infra`를 완료하거나 필요한 절과 종료 실습을 확인합니다. 이 브랜치는 그 내용을 cloud resource로 옮겼을 때의 차이만 다룹니다.

### 권장

- `web-app`: SaaS의 사용자·조직·권한·API를 이해할 때 필요합니다.
- `database-systems`: managed database와 tenant data isolation의 실제 보장 범위를 판단할 때 필요합니다.
- `distributed-services`: event retry, duplicate delivery, idempotency와 provisioning partial failure를 다룰 때 필요합니다.
- `cybersecurity`: workload identity, metadata, resource policy, tenant isolation과 cloud incident를 검토할 때 필요합니다.

권장 브랜치를 모두 완료해야 시작할 수 있다는 뜻은 아닙니다. 관련 문서에서 해당 지식을 필요로 할 때 소유 브랜치로 이동합니다.

## 브랜치 계약과 트랙을 구분하기

이 브랜치는 최신 `main` SHA `887f4b8`에서 `specialization`으로 정의됩니다. 관계 필드는 다음처럼 서로 다른 의미를 가집니다.

| 관계 | 브랜치 |
|---|---|
| 직접 필수 `requires` | [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra) |
| 문제별 권장 `recommends` | [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems), [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity) |
| 인접 협업 `connects` | [`platform-engineering`](https://github.com/seungwoo7050/guides/blob/887f4b8a679195c5b6c13457a91e0b0af357ccff/catalog/branches.json#L959), [`data-engineering`](https://github.com/seungwoo7050/guides/blob/887f4b8a679195c5b6c13457a91e0b0af357ccff/catalog/branches.json#L918), [`machine-learning`](https://github.com/seungwoo7050/guides/blob/887f4b8a679195c5b6c13457a91e0b0af357ccff/catalog/branches.json#L793), [`agentic-systems`](https://github.com/seungwoo7050/guides/blob/887f4b8a679195c5b6c13457a91e0b0af357ccff/catalog/branches.json#L835), [`distributed-systems`](https://github.com/seungwoo7050/guides/blob/887f4b8a679195c5b6c13457a91e0b0af357ccff/catalog/branches.json#L878) |
| 일반적인 후속 `continues_to` | [`platform-engineering`](https://github.com/seungwoo7050/guides/blob/887f4b8a679195c5b6c13457a91e0b0af357ccff/catalog/branches.json#L959) |

카탈로그에만 있고 아직 원격 구현이 없는 연결 항목은 완료 브랜치가 아니라 위 고정 SHA의 목표 계약으로 표시합니다. 이 브랜치의 완료는 다음 상태·근거를 하나의 흐름으로 연결했다는 뜻입니다.

- cloud service의 책임 경계
- IaaS resource와 failure domain
- managed service 계약
- FaaS event lifecycle
- SaaS tenant와 commercial state
- 비용·관측·복구·exit evidence

### `main`에 등재된 다섯 트랙의 위치

| 트랙 | 위치 | 대상이 포함된 `linear_paths` |
|---|---|---|
| `web-backend` | `advanced` | 없음. 백엔드 학습 뒤 선택하는 심화 브랜치입니다. |
| `full-stack-web` | `advanced` | 없음. 풀스택 학습 뒤 선택하는 심화 브랜치입니다. |
| `saas-product-engineering` | `required` | `small-product`, `spring-product` |
| `cloud-engineering` | `required` | `default` |
| `infrastructure-platform` | `recommended` | `cloud-platform` |

대상이 포함된 선형 경로는 다음 네 개이며, 순서는 카탈로그와 같습니다.

```text
saas-product-engineering / small-product
git → web-app → database-systems → web-infra → cloud-computing

saas-product-engineering / spring-product
git → web-app → java → backend-spring-boot → database-systems → web-infra → cloud-computing

cloud-engineering / default
git → unix-systems → computer-networks → web-infra → cloud-computing

infrastructure-platform / cloud-platform
git → unix-systems → computer-networks → web-infra → cloud-computing → cybersecurity → platform-engineering
```

트랙은 브랜치를 어느 맥락에서 선택할지 보여 주지만, 브랜치 계약을 늘리거나 줄이지 않습니다. 브랜치나 트랙 완료는 실제 고객 데이터, 청구, 대규모 장애와 공급자 지원을 다룬 경험을 대신하지 않습니다.

## 품질 프로필

이 브랜치는 다음 품질 프로필을 사용합니다.

### 설계·운영 판단 프로필

핵심 결과는 코드 양이 아니라 책임 matrix, resource inventory, failure map, tenant contract, cost model과 exit plan입니다. 자동 검사는 산출물의 존재와 미완성 여부만 확인하고, 설계 판단은 rubric과 사람 검토로 평가합니다.

### 결정적 상태 모델 프로필

실제 cloud provider는 비용, 계정, 지역, quota와 현재 서비스 상태에 따라 결과가 달라질 수 있습니다. 필수 실행 실습은 Python 표준 라이브러리로 tenant isolation, event duplicate, quota와 cleanup을 결정적으로 재현합니다.

### 선택적 외부 환경 프로필

실제 공급자 실험은 선택 사항입니다. 필수 과정의 완료를 위해 요구하지 않으며, 실행할 때는 별도 account/project, 최소 권한, budget, TTL, inventory와 destroy evidence가 필요합니다.

## 전체 읽기 순서

### Part I. 클라우드 판단의 기반

| 순서 | 문서 | 종료 능력 | 연결 실습 |
|---:|---|---|---|
| 1 | [클라우드 상태, 책임과 증거](01-cloud-state-responsibility-and-evidence.md) | cloud claim을 상태·owner·evidence로 바꿉니다. | 01 |
| 2 | [클라우드 특성, 서비스·배포 모델](02-cloud-characteristics-service-and-deployment-models.md) | IaaS·PaaS·SaaS와 FaaS의 분류 축을 구분합니다. | 01 |
| 3 | [Control plane, data plane과 identity](03-control-plane-data-plane-and-identity.md) | resource 변경 권한과 workload data access를 분리합니다. | 01·03 |

### Part II. 인프라와 관리형 플랫폼

| 순서 | 문서 | 종료 능력 | 연결 실습 |
|---:|---|---|---|
| 4 | [IaaS compute, network와 storage](04-iaas-compute-network-and-storage.md) | resource 수명과 연결을 inventory로 표현합니다. | 02 |
| 5 | [Failure domain, elasticity와 recovery](05-failure-domains-elasticity-and-recovery.md) | zone·region·scaling·recovery 주장의 실제 범위를 검토합니다. | 02 |
| 6 | [PaaS와 managed service 계약](06-paas-and-managed-service-contracts.md) | 공급자에게 이동한 운영과 남은 소비자 책임을 기록합니다. | 03 |

### Part III. Serverless와 FaaS

| 순서 | 문서 | 종료 능력 | 연결 실습 |
|---:|---|---|---|
| 7 | [Serverless와 FaaS runtime](07-serverless-and-faas-runtime.md) | invocation·ephemeral runtime·cold start·limit을 설명합니다. | 04 |
| 8 | [Event delivery, concurrency와 idempotency](08-event-delivery-concurrency-and-idempotency.md) | duplicate·timeout·batch failure·DLQ 뒤 상태를 수렴시킵니다. | 04·07 |

### Part IV. SaaS 제품 경계

| 순서 | 문서 | 종료 능력 | 연결 실습 |
|---:|---|---|---|
| 9 | [SaaS tenancy와 isolation](09-saas-tenancy-and-isolation.md) | tenant context와 data·cache·job·export 경계를 설계합니다. | 05·07 |
| 10 | [Entitlement, metering와 billing](10-saas-entitlements-metering-and-billing.md) | plan·feature·quota·usage·invoice 상태를 분리합니다. | 05·06 |

### Part V. 운영 판단과 종료

| 순서 | 문서 | 종료 능력 | 연결 실습 |
|---:|---|---|---|
| 11 | [Cloud security, observability와 incident](11-cloud-security-observability-and-incidents.md) | control plane·data plane evidence와 containment를 연결합니다. | 02·05·07 |
| 12 | [Cost, capacity, quota와 FinOps](12-cost-capacity-quotas-and-finops.md) | 비용 driver와 resource owner를 연결하고 낭비를 검출합니다. | 06 |
| 13 | [Portability, lock-in과 exit](13-portability-lock-in-and-exit.md) | export·restore·replacement·deletion을 실제 절차로 만듭니다. | 03·06 |
| 14 | [서비스 선택과 architecture review](14-service-selection-and-architecture-review.md) | workload에 맞는 서비스 모델과 잔여 위험을 결정합니다. | 01~06 |
| 15 | [Capstone](15-capstone.md) | IaaS→managed→FaaS→SaaS 변화의 책임·실패·비용을 누적 검토합니다. | 프로젝트 |
| 16 | [표준과 외부 자료 지도](90-standards-map.md) | 원리와 시간에 따라 변하는 공급자 동작을 구분합니다. | 전체 |

## 실습 순서

```text
01 서비스 분류
→ 02 IaaS failure domain
→ 03 managed service 계약
→ 04 FaaS event lifecycle
→ 05 SaaS tenant isolation
→ 06 비용과 exit
→ 07 로컬 cloud model
→ Capstone
```

01~06은 `template/`에서 시작합니다. 원본 template을 직접 수정하지 않고 `.workspace/`로 복사합니다.

```sh
scripts/new_workspace.sh exercises/02-iaas-failure-domains
scripts/check_workspace.sh exercises/02-iaas-failure-domains
```

복사 직후 검사는 `TODO`와 미완성 분량 때문에 실패합니다. 요구된 근거를 채운 뒤 검사에 통과하고, 그 다음 `reference/`와 비교합니다. reference는 유일한 정답이 아니라 빠진 책임과 실패를 발견하기 위한 검토 예시입니다.

07은 코드 실습입니다. 먼저 tests를 읽고 `skeleton/cloud_model.py`를 수정하는 별도 workspace를 만들거나 복사본에서 작업합니다. 원본 skeleton은 루트 검증이 의도한 실패를 확인하므로 변경하지 않습니다.

## 실제 공급자 실험을 선택할 때

실제 계정을 쓰기 전에 다음을 문서로 확정합니다.

1. 실험 목적과 성공 조건
2. 사용할 account·subscription·project
3. 사람과 workload identity
4. 허용 region과 resource 종류
5. 최대 예산과 경보
6. 고유 prefix와 tag
7. 종료 시간과 destroy 순서
8. 삭제 뒤 inventory·청구·로그 확인
9. 실험 중단 조건

공급자 profile은 서비스 이름을 외우는 과정이 아니라 generic contract를 실제 자원에 매핑하는 과정입니다. provider UI나 CLI의 현재 동작은 반드시 공식 문서에서 다시 확인합니다.

## Capstone 종료 근거

Capstone은 완성된 제품 코드를 필수로 요구하지 않습니다. 다음 근거를 함께 제시해야 합니다.

- workload와 사용자·tenant 정의
- 네 단계의 responsibility matrix
- resource inventory와 owner
- identity와 network boundary
- state lifetime과 backup·restore
- failure injection과 expected evidence
- event retry·idempotency·DLQ 계약
- tenant isolation과 commercial state
- cost driver·budget·quota
- provider-specific dependency와 exit plan
- release decision, residual risk와 후속 프로젝트

사람 리뷰어는 다음 질문으로 판정합니다.

- 관리형 서비스로 옮기면서 사라진 책임과 남은 책임이 구체적입니까?
- “multi-AZ”, “serverless”, “managed”, “secure” 같은 표현이 검증 가능한 상태로 바뀌었습니까?
- 중복·부분 성공·quota 초과·tenant context 누락 뒤에도 불변식이 유지됩니까?
- 비용과 cleanup의 owner가 있습니까?
- 서비스 종료나 공급자 변경 시 데이터·identity·configuration을 회수할 수 있습니까?

## 완료 뒤 다음 단계

브랜치 완료 뒤 다음 중 하나의 실제 프로젝트로 이동합니다.

- 작은 서비스를 IaaS와 managed runtime에 각각 배치하고 운영 비용을 비교합니다.
- event-driven worker를 FaaS로 구현하고 duplicate·timeout·DLQ를 주입합니다.
- 기존 웹 애플리케이션에 organization·plan·quota·usage·export를 추가합니다.
- IaC 없이 수동으로 만든 cloud resource를 inventory와 declarative configuration으로 옮깁니다.
- 실제 provider 한 곳의 architecture review 또는 cost optimization issue에 기여합니다.
- 이후 `platform-engineering`에서 여러 팀이 사용하는 self-service·policy·orchestration 문제로 확장합니다.

실제 프로젝트에서는 공급자 장애, quota, 지원 종료, billing, 고객 데이터와 조직 정책을 겪으며 이 가이드의 빈 부분을 추가해야 합니다.
