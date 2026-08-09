# isolated experiment

## Scope

필수 실험은 실제 cloud 계정 대신 repository의 결정적 local cloud model reference를 검증한다. 고정 계약은 `budget=0`, cloud credential은 `없음`, network 호출은 `없음`, 생성·변경 cloud resource는 `없음`이다. 실제 provider 실험은 별도 승인·budget·최소 권한·inventory·cleanup을 갖춘 선택 확장일 뿐 필수 경로가 아니다.

identity는 역할로 분리한다. human identity `human-reviewer`는 local 명령 실행과 content-free report 검토만 하고, workload identity `workload-document-processor`는 model 내부에서 tenant-scoped document/event effect만 수행한다. workload 역할은 human credential을 받지 않는다. 다만 둘은 별도 cloud/OS principal이 아니라 합성 모델의 논리적 identity이므로 OS-level separation을 입증하지 않는다.

현재 명령 계약은 `python3 scripts/verify_cloud_model.py --implementation exercises/07-local-cloud-model/reference/cloud_model.py --report <new-path>`다. `<new-path>`는 실행마다 존재하지 않는 임시 파일로 바꾼다. 다음은 repository root에서 실행한 정확한 형태다.

```sh
experiment_dir="$(mktemp -d)"
report_path="$experiment_dir/capstone-local-cloud-model.json"
test ! -e "$report_path"
python3 scripts/verify_cloud_model.py --implementation exercises/07-local-cloud-model/reference/cloud_model.py --report "$report_path"
python3 -m json.tool "$report_path"
```

검증기는 기존 report를 덮어쓰지 않으며 `report_path` 외 source, template, reference와 learner workspace를 수정하지 않는다.

## Stage 1 — IaaS

| inventory 대상 | before | command 직후 | cleanup 뒤 |
|---|---|---|---|
| cloud account·resource | 접근/생성 없음 | 변화 없음 | 변화 없음 |
| credential·secret | 주입 없음 | 변화 없음 | 변화 없음 |
| network connection | 필요 없음 | 사용 없음 | 사용 없음 |
| local experiment directory | 비어 있는 새 directory | JSON report 1개 | directory 제거 |
| tracked repository·learner workspace | 기존 상태 | 변화 없음 | 변화 없음 |

report의 `execution.external_resources_created=false`, `network_required=false`를 확인한다. CM-001은 두 stateful resource가 private임을 합성 inventory에서 관찰한다. 이는 VM, region·zone 또는 실제 private network를 만든 것이 아니며 zone 하나 손실, RPO 15분·RTO 60분 restore는 별도 isolated provider rehearsal이 필요하다.

cleanup은 report 내용을 검토하고 hash를 기록한 뒤 정확히 생성한 경로만 대상으로 한다.

```sh
rm "$report_path"
rmdir "$experiment_dir"
```

## Stage 2 — Managed platform

CM-002~CM-005에서 invalid tenant transition, owner update, foreign/missing read deny와 quota rejection의 원자적 공개 결과를 확인했다. 모든 check는 pass했고 failure path 뒤 state가 unchanged 또는 partial write 없음으로 보고됐다. 이는 application state contract evidence이며 managed runtime·database·queue의 SLA, control-plane failure, backup restore, retention과 service limit을 검증하지 않는다. 공급자와 가격은 선택되지 않아 모두 `unknown/unmeasured`다.

human reviewer는 report의 check ID, status와 content-free observed field만 읽는다. workload 역할은 reference model 내부 tenant-scoped operation을 실행하며 human reviewer의 filesystem/cloud 권한을 사용하는 별도 integration을 만들지 않는다.

## Stage 3 — FaaS

CM-006은 duplicate가 output·usage를 한 번만 만들고 distinct event는 다른 output을 만드는지, CM-007은 event ID가 tenant-scoped이며 payload conflict가 상태를 바꾸지 않는지 검증했다. CM-008은 attempts 2에서 dead letter 1개·usage 0인 bounded retry를, CM-009는 다른 tenant document event가 output·usage 없이 dead letter되는지를, CM-010은 bounded drain이 pending work를 숨기지 않는지를 관찰했다.

system brief 계산상 평균 동시성은 `2/s × 4s = 8`, 보수적 peak stress는 `50/s × 40s = 2,000`이다. peak에서 평균 8 MB object ingress는 400 MB/s이고 최대 100 MB stress는 5 GB/s다. invalid 1%, transient failure 2%와 한 tenant 30% workload는 설계·load-test input이다. 이 local 실행은 실제 concurrency, cold start, timeout, 400 MB/s·5 GB/s data path, provider retry나 tenant fairness를 부하 측정하지 않는다.

## Stage 4 — SaaS

CM-004·CM-009는 관찰한 read/event 경로의 cross-tenant deny를, CM-011은 deletion 뒤 active state 제거와 tombstone `DELETED`·aggregate usage 1 보존을, CM-012는 repeated deletion과 tenant ID reuse reject를, CM-013은 content-free·deep-copy·deterministic snapshot을 검증했다.

local model의 Starter active-document capacity `2`는 concurrency·state-transition 교육용 축소값이다. 실제 제품 entitlement인 Starter 100건/월·Pro 10,000건/월을 대신하지 않는다. tenant export 24시간, active deletion 7일, backup retention 고지와 membership/support/analytics 경계도 이 report가 검증하지 않으며 dossier와 실제 integration evidence가 필요하다.

## Evidence와 한계

| evidence | 관찰 결과 | 해석 |
|---|---|---|
| command/result | exit 0, `MODEL RESULT: PASS` | reference가 현재 공개 계약을 만족 |
| checks | 13 total, 13 passed, 0 failed, 0 errors | CM-001~CM-013 모두 실행됨 |
| implementation hash | `f1199b2e46d3f7a66f8b6af9ca8ed15f1dbba4cfa17d297c46803c0e4b45f22f` | 실행한 reference bytes 식별 |
| contract hash | `b328e8cd733654d53aa145d8ecd41484f4398e84f2355874f7bd9e15d58521ba` | 적용한 check contract 식별 |
| report SHA-256 | `95cc028d74360a274d6a63c2942182af1f69ff5d7a295cc0d1a24f0cb4fbe33e` | validator가 생성한 byte-identical `evidence/local-model-report.json` 비교 기준 |
| execution inventory | external resource false, network false, captured stdout/stderr 0 | cloud side effect가 없는 경로 |

before inventory와 after inventory는 위 표처럼 cloud resource·credential·network는 모두 없음이고 local report 1개만 생겼다가 exact-path cleanup 뒤 0개임을 확인한다. report 자체가 밝히듯 child process timeout은 5초지만 OS sandbox는 아니다. 합성 in-process 상태 모델은 실제 IAM·network·queue·billing·physical deletion, distributed transaction, process crash와 concurrent writer를 검증하지 않는다. report pass는 이 reference의 공개 행동만 증명하며 architecture 승인, provider 보장 또는 교육적 완료를 자동 판정하지 않는다.

## Open risks와 owner

| risk/condition | owner | due date | verification | rollback |
|---|---|---|---|---|
| OS-level human/workload identity separation 미검증 | security owner | 2026-09-22 | 선택 provider에서 distinct principals의 allow/deny audit | provider 실험을 중단하고 credential 없는 local-only 경로 유지 |
| 실제 provider IAM·network·queue·limit 미측정 | runtime owner | 2026-09-29 | 승인된 선택 experiment의 before/after inventory와 integration report | resource 생성 보류 또는 명시적 destroy 후 local evidence 유지 |
| RPO 15분·RTO 60분과 export/deletion 시간 미검증 | data owner | 2026-09-22 | isolated restore, export timestamp, 7일 subsystem inventory review | production tenant onboarding 보류 |
| local report 잔존 또는 기존 경로 overwrite 위험 | human reviewer | 2026-08-10 | create-only 명령 전 `test ! -e`, 종료 후 exact-path inventory 0 | report 생성을 중단하고 새 `mktemp -d`에서 재실행 |
