# 정본 계약 Evidence Map

이 문서는 최신 `main`의 `platform-engineering` 객체를 학습 파일과 종료 증거에 연결합니다. 식별자는 이 브랜치 안에서만 사용하는 안정적인 축약입니다. 자동 검사는 파일·공개 행동·불변식의 연결을 확인하지만, 조직에 맞는 설계 판단은 [사람 검토 가이드](manual-review-guide.md)가 판정합니다.

## 읽는 법

각 행은 다음 사슬을 끊김 없이 보여야 합니다.

```text
owns → 개념의 상태·책임·실패 → 단계 실습과 known-bad → 결정적 모델 → Capstone → exit capability
```

- `reference/submission.json`은 계약을 만족하는 한 가지 해설입니다.
- `skeleton/submission.json`은 공개 shape를 보여 주지만 필수 판단이 비어 있어 exit `1`이어야 합니다.
- `known_bad/submission.json`은 shape는 완성됐지만 표에 적은 핵심 불변식 하나를 어겨 exit `1`이어야 합니다.
- `PE-*`는 [결정적 control-plane 공개 검사](../exercises/13-platform-control-plane/README.md#정상경계대표-실패)입니다.
- `FS-*`는 [Capstone의 누적 실패 evidence](../projects/internal-developer-platform/reference/09-evidence.md#실패-시나리오)입니다.

## OWN-1 — 플랫폼 사용자와 golden path

정본 문구: **플랫폼 사용자와 golden path**

| 연결 단계 | 구현 근거 |
|---|---|
| 개념 | [사용자·journey·outcome](../docs/01-platform-as-product.md), [요청·상태·결과·운영·수명 계약](../docs/02-platform-contracts-and-ownership.md), [self-service API](../docs/07-self-service-platform-apis-and-catalogs.md), [golden path lifecycle](../docs/08-golden-paths-and-service-lifecycle.md) |
| 단계 실습 | [`01-platform-product`](../exercises/01-platform-product/)의 platform operator 관점 누락, [`02-platform-contract`](../exercises/02-platform-contract/)의 `Ready`에 잘못 지정한 failure owner, [`06-self-service`](../exercises/06-self-service/)의 dependency timeout retry 분류 오류 |
| 결정적 행동 | `PE-001` 요청→외부 evidence→Ready, `PE-002` idempotent retry와 payload conflict, `PE-003` partial effect 공개 |
| Capstone | [Product와 Golden path](../projects/internal-developer-platform/reference/01-product.md#golden-path), [Operation과 Evidence](../projects/internal-developer-platform/reference/03-api-status.md#operation과-evidence), `FS-01`, `FS-02` |
| 종료 연결 | `EXIT-1`의 self-service 서비스 경로 설계, `EXIT-2`의 사용자에게 보이는 정책·배포 결과 |

## OWN-2 — Infrastructure as Code와 drift

정본 문구: **Infrastructure as Code와 drift**

| 연결 단계 | 구현 근거 |
|---|---|
| 개념 | [reconciliation과 partial effect](../docs/03-control-planes-and-reconciliation.md), [state·locking·drift·destroy](../docs/04-infrastructure-as-code-state-and-drift.md), [migration wave와 rollback](../docs/15-upgrades-migrations-and-deprecation.md) |
| 단계 실습 | [`03-reconciliation`](../exercises/03-reconciliation/)의 transient dependency retry 차단, [`04-iac-state`](../exercises/04-iac-state/)의 source 변경 뒤 stale plan 허용, [`11-migration`](../exercises/11-migration/)의 source와 target이 같은 no-op migration |
| 결정적 행동 | `PE-003` visible partial effect, `PE-005` GitOps drift 수렴, `PE-008` wave abort, `PE-009` retirement cleanup |
| Capstone | [IaC State와 Drift](../projects/internal-developer-platform/reference/04-iac-runtime.md#iac-state와-drift), [Migration Waves](../projects/internal-developer-platform/reference/08-migration-runbook.md#migration-waves), `FS-04`, `FS-06`, `FS-07`, `FS-08` |
| 종료 연결 | `EXIT-1`의 provisioning 경로와 `EXIT-3`의 upgrade·retirement 운영 |

## OWN-3 — 컨테이너 오케스트레이션

정본 문구: **컨테이너 오케스트레이션**

| 연결 단계 | 구현 근거 |
|---|---|
| 개념 | [Kubernetes API·controller·workload](../docs/05-kubernetes-api-workloads-and-controllers.md), [network·storage·scheduling](../docs/06-kubernetes-network-storage-and-scheduling.md), [tenant isolation](../docs/13-multitenancy-quotas-and-isolation.md) |
| 단계 실습 | [`05-workload-contract`](../exercises/05-workload-contract/)의 “process 실행=Ready” 오판, [`09-multitenancy`](../exercises/09-multitenancy/)의 per-tenant queue를 global queue로 바꾼 격리 위반 |
| 결정적 행동 | `PE-004` tenant quota와 queue 격리, `PE-007` static credential fallback 거부, `PE-009` resource·credential cleanup |
| Capstone | [Kubernetes Runtime](../projects/internal-developer-platform/reference/04-iac-runtime.md#kubernetes-runtime), [Tenant Isolation과 Cleanup](../projects/internal-developer-platform/reference/04-iac-runtime.md#tenant-isolation과-cleanup), `FS-03`, `FS-05`, `FS-08` |
| 종료 연결 | `EXIT-1`의 runtime profile 설계와 `EXIT-3`의 capacity·isolation 운영 |

이 가이드는 Kubernetes substrate를 플랫폼 고유 계약에 적용하는 부분만 소유합니다. cluster bootstrap, CNI·CSI 내부 구현과 단일 workload 운영 기초는 비소유 범위입니다.

## OWN-4 — 재사용 가능한 CI/CD·GitOps

정본 문구: **재사용 가능한 CI/CD·GitOps**

| 연결 단계 | 구현 근거 |
|---|---|
| 개념 | [immutable artifact promotion](../docs/09-delivery-platform-and-artifact-promotion.md), [GitOps desired state·prune·break-glass](../docs/10-gitops-reconciliation-and-emergency-changes.md), [supply-chain evidence](../docs/16-supply-chain-and-platform-security.md) |
| 단계 실습 | [`07-delivery-gitops`](../exercises/07-delivery-gitops/)의 builder credential과 environment workload identity 혼합, [`08-identity-policy`](../exercises/08-identity-policy/)의 장기 shared automation token |
| 결정적 행동 | `PE-005` desired artifact로 수렴, `PE-006` owner·reason·expiry·evidence가 있는 bounded exception |
| Capstone | [Build Once와 Promotion](../projects/internal-developer-platform/reference/05-delivery.md#build-once와-promotion), [GitOps Reconciliation](../projects/internal-developer-platform/reference/05-delivery.md#gitops-reconciliation), `FS-04` |
| 종료 연결 | `EXIT-2`의 배포·정책·관측 자동화 |

## OWN-5 — identity·secret·관측·catalog·multi-tenancy

정본 문구: **identity·secret·관측·catalog·multi-tenancy**

| 연결 단계 | 구현 근거 |
|---|---|
| 개념 | [catalog와 status API](../docs/07-self-service-platform-apis-and-catalogs.md), [identity·secret·policy](../docs/11-identity-secrets-and-policy.md), [journey telemetry와 audit](../docs/12-observability-audit-and-developer-feedback.md), [tenant 격리](../docs/13-multitenancy-quotas-and-isolation.md), [SLO·capacity·support](../docs/14-platform-slo-capacity-cost-and-support.md) |
| 단계 실습 | [`06-self-service`](../exercises/06-self-service/)의 timeout retry 차단, [`08-identity-policy`](../exercises/08-identity-policy/)의 장기 token, [`09-multitenancy`](../exercises/09-multitenancy/)의 global queue, [`10-platform-slo`](../exercises/10-platform-slo/)의 platform defect SLO 제외 |
| 결정적 행동 | `PE-004` fairness, `PE-006` bounded break-glass, `PE-007` workload identity, `PE-010` secret-free deterministic snapshot |
| Capstone | [Identity와 Secret](../projects/internal-developer-platform/reference/06-security-catalog.md#identity와-secret), [Catalog와 Developer Feedback](../projects/internal-developer-platform/reference/06-security-catalog.md#catalog와-developer-feedback), [Journey SLO](../projects/internal-developer-platform/reference/07-slo-capacity.md#journey-slo), `FS-03`, `FS-05` |
| 종료 연결 | `EXIT-1`, `EXIT-2`, `EXIT-3` 모두의 공통 운영·evidence 경계 |

## EXIT-1 — Self-service 서비스 경로 설계

정본 능력: **self-service 서비스 경로를 설계한다.**

필수 근거는 `OWN-1`, `OWN-2`, `OWN-3`, `OWN-5`를 결합합니다. 학습자는 `01`, `02`, `03`, `04`, `05`, `06`, `09`, `12` 단계 실습을 통과해야 합니다. 특히 `12`의 known-bad처럼 중복-timeout 시나리오를 정상 생성의 반복으로 바꾸면 안 됩니다. Control-plane의 `PE-001..004`, `PE-009` 행동과 Capstone의 product, ownership, API/status, IaC/runtime dossier, `FS-01..03`, `FS-07..08`이 종료 산출물입니다. 최종 판단 질문은 [EXIT-1 사람 검토](manual-review-guide.md#exit-1--self-service-서비스-경로)에서 확인합니다.

## EXIT-2 — 정책·배포·관측 자동화

정본 능력: **정책·배포·관측을 플랫폼 계약으로 자동화한다.**

필수 근거는 `OWN-2`, `OWN-4`, `OWN-5`를 결합합니다. 학습자는 `07`, `08`, `10`, `12` 단계 실습과 `PE-003`, `PE-005..007`, `PE-010`을 통해 immutable artifact, reconciliation, exception, identity와 공개 evidence를 증명합니다. 종료 산출물은 delivery, security/catalog, SLO dossier와 `FS-02`, `FS-04`, `FS-05`, `FS-07`입니다. 최종 판단 질문은 [EXIT-2 사람 검토](manual-review-guide.md#exit-2--정책배포관측-자동화)에서 확인합니다.

## EXIT-3 — SLO·용량·업그레이드 운영

정본 능력: **플랫폼 SLO·용량·업그레이드를 운영한다.**

필수 근거는 `OWN-2`, `OWN-3`, `OWN-5`를 결합합니다. 학습자는 `09`, `10`, `11`, `12` 단계 실습과 `PE-004`, `PE-008`, `PE-009`을 통해 fairness, capacity admission, wave abort와 retirement를 증명합니다. 종료 산출물은 SLO/capacity, migration/runbook dossier와 `FS-03`, `FS-06`, `FS-08`입니다. 최종 판단 질문은 [EXIT-3 사람 검토](manual-review-guide.md#exit-3--slo용량업그레이드-운영)에서 확인합니다.

## 검증 명령과 증명 한계

```sh
python3 scripts/verify_submission.py \
  exercises/06-self-service/contract.json \
  exercises/06-self-service/reference/submission.json

python3 scripts/verify_platform_model.py \
  --implementation exercises/13-platform-control-plane/reference/platform_model.py

python3 scripts/verify_capstone.py \
  projects/internal-developer-platform/reference
```

첫 검사는 단계 설계 shape와 교차 불변식, 두 번째는 결정적 공개 행동, 세 번째는 dossier·heading·JSON pointer·hash 연결을 확인합니다. 어느 검사도 실제 조직의 제품 적합성, cloud/IAM/Kubernetes enforcement, 동시성, 비용, 장애 복구 또는 production readiness를 자동 판정하지 않습니다.
