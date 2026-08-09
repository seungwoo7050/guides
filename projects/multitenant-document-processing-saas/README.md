# 멀티테넌트 문서 처리 SaaS Capstone

## 목적과 완료 결과

하나의 B2B 문서 처리 workload를 `IaaS → managed platform → FaaS → SaaS`로 바꾸면서 책임·상태·실패·비용·tenant·exit 계약을 같은 dossier에 누적합니다. 완성 application code가 아니라, 구현 소유 브랜치에 넘길 수 있는 설계와 재현 가능한 증거가 결과물입니다.

완료하려면 다음을 함께 보여야 합니다.

- 동일 workload의 네 Stage에서 공급자·소비자 책임과 failure domain이 어떻게 이동하는지 설명합니다.
- event 중복·timeout·부분 성공, tenant 격리·quota·metering·export·deletion 불변식을 설계합니다.
- provider 가격을 만들지 않고 측정한 값, 계산한 bound와 아직 측정하지 않은 값을 구분합니다.
- budget `0`, cloud credential 없음, 외부 resource 없음인 필수 로컬 실험을 재현합니다.
- 자동 검사 결과와 사람의 release 판단을 구분하고 구현 owner에게 남은 일을 넘깁니다.

자세한 과정 설명은 [Capstone 단원](../../docs/15-capstone.md), 계약 추적은 [contract evidence map](../../reference/contract-evidence-map.md), 최종 판정은 [manual review guide](../../reference/manual-review-guide.md)를 함께 사용합니다.

## 고정 입력과 계산 기준

정본 입력은 [`inputs/system-brief.md`](inputs/system-brief.md)입니다.

| 항목 | 값 | dossier에서 사용하는 방식 |
|---|---:|---|
| 정상 upload rate | `2/s` | 평균 처리 시간이 4초이면 평균 in-flight 하한은 `2 × 4 = 8` |
| peak upload rate | `50/s` | p99 40초를 보수적으로 적용한 stress bound는 `50 × 40 = 2,000` concurrent |
| object 크기 | 평균 `8 MB`, 최대 `100 MB` | peak ingress는 평균 object 기준 `400 MB/s`; 전부 최대 크기인 stress bound는 `5 GB/s` |
| 처리 시간 | 평균 `4s`, p99 `40s` | queue age, timeout, concurrency와 downstream capacity의 입력 |
| 입력 실패 | invalid `1%`, transient `2%` | terminal reject와 retryable failure를 분리 |
| noisy tenant | 전체 workload의 `30%` | tenant별 concurrency·quota·cost attribution 경계 |
| recovery | RPO `15분`, RTO `60분` | backup 존재가 아니라 restore·rebuild 측정 목표 |
| monthly quota | starter `100`, pro `10,000` | active capacity와 구분한 commercial quota·usage 계약 |
| export | `24시간` 안에 준비 | throughput·queue·large tenant 성장 가정과 함께 검토 |
| active deletion | `7일` 안에 제거 | backup retention 고지와 분리해 subsystem별 상태를 추적 |

이 값으로 instance 수나 provider 비용을 확정하지 않습니다. 압축률, metadata overhead, 실제 p99 concurrency, 공급자 quota·SLA·price는 `unmeasured` 또는 `unknown`으로 남기고 측정 계획과 owner를 적습니다.

## Workspace

Capstone workspace는 tracked `template/`을 `.workspace/`로 복사하며 기존 workspace를 덮어쓰지 않습니다.

```sh
scripts/new_workspace.sh projects/multitenant-document-processing-saas
scripts/check_workspace.sh projects/multitenant-document-processing-saas
```

`contract.json`의 `workspace_source`는 `template`, validator는 `scripts/check_artifact.py`입니다. starter는 모든 dossier와 evidence JSON에 의도적인 미완성 표시가 있으므로 처음에는 실패해야 합니다. reference는 해설·비교용이며 workspace로 복사되지 않습니다.

## 필수 결과물

```text
01-responsibility-matrix.md
02-resource-and-state-inventory.md
03-identity-network-and-tenant-boundaries.md
04-failure-and-recovery-plan.md
05-event-and-idempotency-contract.md
06-cost-quota-and-metering.md
07-portability-exit-and-deletion.md
08-release-review.md
09-isolated-experiment.md
evidence-manifest.json
evidence/local-model-report.json
```

아홉 Markdown dossier는 모두 같은 네 Stage를 가집니다.

```text
Stage 1 — IaaS
Stage 2 — Managed platform
Stage 3 — FaaS
Stage 4 — SaaS
```

각 Stage를 독립 설계로 다시 쓰지 말고, 바로 이전 Stage에서 이동한 책임·새 limit·남은 실패·새 evidence를 갱신합니다. `evidence-manifest.json`은 네 Stage의 순서, `OWN-1..6`, `EXIT-1..4`, file+heading 근거, release condition과 구현 owner handoff를 연결합니다.

## 필수 로컬 실험

실제 cloud 계정은 필수가 아닙니다. 다음 reference command는 현재 공개 contract를 cloud credential·network·외부 resource 없이 실행하고, 기존 report를 덮어쓰지 않는 새 경로에 증거를 만듭니다.

```sh
report_dir="$(mktemp -d)"
python3 scripts/verify_cloud_model.py \
  --implementation exercises/07-local-cloud-model/reference/cloud_model.py \
  --report "$report_dir/local-model-report.json"
python3 -m json.tool "$report_dir/local-model-report.json"
```

학습자 구현을 완료했다면 `--implementation .workspace/07-local-cloud-model/cloud_model.py`로 같은 contract를 실행합니다. 생성된 report를 검토한 뒤 Capstone workspace의 placeholder를 명시적으로 교체하고, `09-isolated-experiment.md`에 command·human/workload identity·전후 inventory·관찰·cleanup·한계를 기록합니다.

reference report의 고정 근거는 다음과 같습니다.

```text
implementation_sha256 = f1199b2e46d3f7a66f8b6af9ca8ed15f1dbba4cfa17d297c46803c0e4b45f22f
contract_sha256       = b328e8cd733654d53aa145d8ecd41484f4398e84f2355874f7bd9e15d58521ba
report_sha256         = 95cc028d74360a274d6a63c2942182af1f69ff5d7a295cc0d1a24f0cb4fbe33e
checks                = CM-001..CM-013, 13/13 PASS
```

이 report는 실제 IAM·network·queue·billing·physical deletion, process crash, concurrent writer나 provider failure를 검증하지 않습니다.

## Stage 누적 순서

1. **IaaS**: VM pool·private database·object storage·worker·network·identity와 restore/rebuild 기준선을 만듭니다.
2. **Managed platform**: 공급자에게 이동한 task, 숨겨진 상태, maintenance·quota·restore·export 책임을 갱신합니다.
3. **FaaS**: worker를 event-driven function으로 바꾸고 duplicate·timeout·DLQ·concurrency·cost guard를 추가합니다.
4. **SaaS**: tenant·membership·plan·entitlement·monthly quota·usage·export·deletion을 customer lifecycle로 결합합니다.
5. **Release review**: `APPROVE`, `APPROVE_WITH_CONDITIONS`, `DEFER`, `REJECT` 중 하나를 고르고 condition마다 owner·due·verification·rollback을 적습니다.

## 실제 provider 선택 확장

provider profile은 선택 사항이며 필수 로컬 실험을 대체하지 않습니다. 실제 resource를 만들려면 먼저 별도 account/project, 최소 권한 human/workload identity, maximum budget, prefix·TTL, before inventory, 중단 조건, destroy 순서와 after inventory를 갖춰야 합니다. 이 저장소의 prepare·verify와 Capstone 기본 경로는 cloud resource를 만들거나 삭제하지 않습니다.

## 완료 판정

`scripts/check_workspace.sh` 통과는 필수 파일·heading·phrase·JSON key와 미완성 token이 없다는 자동 근거입니다. 다음은 사람이 확인합니다.

- 네 Stage의 책임·실패·비용 비교가 기술적으로 타당한가
- 계산의 입력·단위·bound와 `unmeasured`가 정직하게 구분되는가
- local report가 dossier의 주장과 실제로 연결되는가
- release condition이 owner·due·verification·rollback으로 닫힐 수 있는가
- `EXIT-1..4` 각각이 `충족`, `보완 필요`, `범위 밖` 중 무엇인지 근거로 설명되는가

자동 통과만으로 교육적 완료나 production readiness를 선언하지 않습니다.
