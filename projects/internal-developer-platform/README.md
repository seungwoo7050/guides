# Internal Developer Platform Capstone

`Northstar`의 결제 서비스가 self-service 경로로 staging 환경을 요청하고, 검증된 artifact를 배포하며, 정책·관측·migration·retirement까지 운영하는 누적 종료 과제입니다. 개별 문서의 정답 문구보다 같은 식별자가 product 결정부터 실행 evidence까지 이어지는지가 중요합니다.

## 고정 시나리오

- [System brief](scenario/system-brief.md)
- [Canonical identifiers](scenario/identifiers.json)
- [자동 계약](contract.json)
- [사람 검토 루브릭](rubric.md)

모든 dossier는 다음 identity를 공유합니다.

```text
service_id   = svc-payments
resource_id  = env-payments-staging
operation_id = op-payments-staging-v3
tenant_id    = tenant-checkout
artifact_id  = sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
profile_id   = stateless-http/v3
```

## Workspace

tracked template를 직접 수정하지 않습니다.

```sh
mkdir -p .workspace
cp -R projects/internal-developer-platform/template \
  .workspace/internal-developer-platform
python3 scripts/verify_capstone.py .workspace/internal-developer-platform
```

template는 모든 필수 파일·heading을 보여 주지만 미완성 표시 때문에 처음에는 실패합니다. `reference/`는 한 가지 검토 가능한 해설이며 workspace로 복사하지 않습니다.

## 누적 결과물

| Dossier | 결합하는 계약 |
|---|---|
| `01-product.md` | 사용자·golden path·비범위 |
| `02-ownership.md` | single writer·failure owner·지원 |
| `03-api-status.md` | resource·operation·condition·evidence |
| `04-iac-runtime.md` | IaC state·drift·Kubernetes·tenant cleanup |
| `05-delivery.md` | artifact promotion·GitOps·partial effect |
| `06-security-catalog.md` | workload identity·secret·policy·catalog feedback |
| `07-slo-capacity.md` | journey SLO·fairness·capacity·cost·support |
| `08-migration-runbook.md` | wave·abort·runbook·retirement |
| `09-evidence.md` | 8개 failure scenario·model report·사람 한계 |
| `evidence-manifest.json` | `OWN-1..5`, `EXIT-1..3`, file/heading/JSON-pointer trace |

## 자동 검증

```sh
python3 scripts/verify_capstone.py \
  projects/internal-developer-platform/reference
```

검사기는 필수 dossier와 heading, 공통 ID, 8개 failure scenario, manifest 참조, model implementation/contract/report hash와 `PE-001..010` 통과를 확인합니다. 검증 과정에서 현재 model reference를 새 임시 report로 다시 실행해 제출 evidence와 비교합니다.

자동 통과는 실제 플랫폼의 production readiness를 의미하지 않습니다. 조직의 사용자 문제, 책임 경계, Kubernetes·IaC·identity enforcement, SLO 수치, 비용, rollback과 물리적 삭제의 타당성은 [루브릭](rubric.md)에 따라 사람이 판정합니다.
