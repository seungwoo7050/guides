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
if [ -e .workspace/internal-developer-platform ]; then
  printf '%s\n' 'ERROR: existing Capstone workspace를 보존했습니다.' >&2
  exit 2
fi
cp -R projects/internal-developer-platform/template \
  .workspace/internal-developer-platform
```

template는 모든 필수 파일·heading을 보여 주지만 미완성 표시 때문에 처음에는 실패합니다. `reference/`는 한 가지 검토 가능한 해설이며 workspace로 복사하지 않습니다.

먼저 [`13-platform-control-plane`](../../exercises/13-platform-control-plane/)의 learner 구현을 완성해 통과시킵니다. 아래 첫 복사는 learner 파일이 아직 없을 때만 수행하므로 기존 작업을 덮어쓰지 않습니다. report writer도 source나 기존 파일을 덮어쓰지 않으므로 저장소 밖 새 임시 파일에 evidence를 만든 뒤, workspace의 명시적 placeholder를 보존 이름으로 옮기고 새 report를 복사합니다.

```sh
(
set -eu
mkdir -p .workspace/13-platform-control-plane
if [ ! -f .workspace/13-platform-control-plane/platform_model.py ]; then
  cp exercises/13-platform-control-plane/skeleton/platform_model.py \
    .workspace/13-platform-control-plane/platform_model.py
fi

# platform_model.py를 완성한 뒤 실행합니다.
repository_root="$(pwd -P)"
report_dir="$(TMPDIR=/tmp mktemp -d)"
report_root="$(cd "$report_dir" && pwd -P)"
case "$report_root" in
  "$repository_root"|"$repository_root"/*)
    printf '%s\n' 'ERROR: report directory must remain outside the repository.' >&2
    exit 2
    ;;
esac
python3 scripts/verify_platform_model.py \
  --implementation .workspace/13-platform-control-plane/platform_model.py \
  --report "$report_dir/platform-model-report.json"

if [ -e .workspace/internal-developer-platform/evidence/platform-model-report.placeholder.json ]; then
  printf '%s\n' 'ERROR: existing placeholder backup을 보존했습니다.' >&2
  exit 2
fi
mv .workspace/internal-developer-platform/evidence/platform-model-report.json \
  .workspace/internal-developer-platform/evidence/platform-model-report.placeholder.json
cp "$report_dir/platform-model-report.json" \
  .workspace/internal-developer-platform/evidence/platform-model-report.json
python3 -c 'import hashlib, pathlib, sys; [print(hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest(), p) for p in sys.argv[1:]]' \
  .workspace/internal-developer-platform/evidence/platform-model-report.json \
  .workspace/13-platform-control-plane/platform_model.py
rm "$report_dir/platform-model-report.json"
rmdir "$report_dir"
)
```

`evidence-manifest.json`의 `model_report.sha256`에는 첫 hash를 기록하고, `implementation`, `contract`, `contract_code`, `identifiers`, `check_ids`는 생성된 report의 같은 객체를 그대로 선언합니다. `implementation.path`는 위 learner 파일을 가리켜야 합니다. `OWN-*`·`EXIT-*`에는 [reference manifest](reference/evidence-manifest.json)의 field 구조를 참고하되 자신의 dossier heading과 필요한 `PE-*` pointer를 연결합니다. 이후 실행합니다.

```sh
python3 scripts/verify_capstone.py \
  .workspace/internal-developer-platform
```

Capstone validator는 선언한 learner implementation hash를 확인하고 같은 공개 계약으로 새 report를 저장소 밖에서 다시 생성해 제출 report와 비교합니다. canonical `reference/` 자체만 내장 reference 구현·report를 사용할 수 있습니다. 그 밖의 dossier는 내장 reference 경로 또는 그 파일과 같은 hash를 선언하면 거부되며, learner 경로의 구현과 그 구현에서 새로 생성한 report를 제출해야 합니다. 이 출처 검사는 학습자의 독창성이나 production 적합성을 자동 증명하지 않습니다.

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

검사기는 필수 dossier와 fence 밖 heading, 공통 ID, 8개 failure scenario, 의미별 `PE-*` coverage, model implementation·공개 계약·실행 계약·report hash와 `PE-001..010` 통과를 확인합니다. 검증 과정에서 manifest가 선언한 learner implementation을 새 임시 report로 다시 실행해 제출 evidence와 비교합니다.

자동 통과는 실제 플랫폼의 production readiness를 의미하지 않습니다. 조직의 사용자 문제, 책임 경계, Kubernetes·IaC·identity enforcement, SLO 수치, 비용, rollback과 물리적 삭제의 타당성은 [루브릭](rubric.md)에 따라 사람이 판정합니다.
