# isolated experiment

## Scope

필수 경로는 실제 cloud가 아니라 결정적 local cloud model 실험이다. 예산은 `0`, credential은 `없음`, network 호출은 `없음`, 생성 cloud resource는 `없음`으로 고정한다. 실제 provider 실험은 선택 사항이며 이 필수 evidence를 대체하지 않는다.

| identity | 역할 | 허용 행동 | 금지 행동 |
|---|---|---|---|
| `human-reviewer` | 명령 실행·report 검토 | local source 읽기, 새 report path 생성 | cloud login, model state mutation |
| `workload-document-processor` | model 내부 document 처리 주체 | tenant-scoped read/write/event | human 권한·credential 사용 |

TODO: 두 identity가 evidence와 권한 표에서 구분되는 이유와, 로컬 validator가 OS-level identity separation을 제공하지 않는 한계를 적는다.

실행할 현재 명령 형식은 `python3 scripts/verify_cloud_model.py --implementation exercises/07-local-cloud-model/reference/cloud_model.py --report <new-path>`다. `<new-path>`는 존재하지 않는 새 파일이어야 하며 tracked source나 learner workspace를 가리키면 안 된다.

## Stage 1 — IaaS

실험 전 inventory를 작성한다.

| 대상 | before | expected after | cleanup |
|---|---|---|---|
| cloud account/resource | 없음 | 없음 | 불필요 |
| credential/environment secret | 없음 | 없음 | 불필요 |
| network connection | 없음 | 없음 | 불필요 |
| local report | 없음 | 새 JSON 1개 | TODO: 정확한 파일만 삭제 |

TODO: local model의 private resource inventory와 zone/failure-domain 주장 중 무엇을 관찰할지 적는다.

## Stage 2 — Managed platform

TODO: local model report에서 공개 state transition, quota, isolation 결과를 읽고 managed queue/database/runtime의 실제 SLA·backup·limit을 검증한 것으로 오해하지 않게 관찰표를 작성한다. 공급자 선택과 credential은 필요하지 않다.

## Stage 3 — FaaS

TODO: duplicate, payload conflict, bounded retry, dead letter, tenant-scoped event ID와 usage-once check ID를 report에서 연결한다. 평균 동시성 8과 보수적 peak 2,000, 400 MB/s·5 GB/s ingress 계산은 설계 input이며 이 로컬 실행의 load measurement가 아님을 표시한다.

## Stage 4 — SaaS

TODO: Starter 100건/월·Pro 10,000건/월 product quota와 local model의 축소된 active-document quota를 구분한다. cross-tenant read, deletion, tombstone, aggregate usage와 content-free evidence 관찰을 기록한다.

## Evidence와 한계

| evidence | expected observation | 결과 | limitation |
|---|---|---|---|
| command exit | success | TODO | reference implementation에 한정 |
| JSON hash/check IDs | deterministic·all pass | TODO | 실제 concurrency 없음 |
| before/after inventory | report 외 변화 없음 | TODO | OS sandbox 아님 |
| credential/network/cloud resource | 모두 없음 | TODO | provider IAM/SLA 미검증 |

TODO: 새 report path, SHA-256, check 수, cleanup 뒤 inventory를 기록한다. 자동 결과가 architecture 승인이나 실제 cloud 보장을 뜻하지 않는다고 적는다.

## Open risks와 owner

| risk/condition | owner | due date | verification | rollback |
|---|---|---|---|---|
| TODO: OS-level human/workload 분리 미검증 | TODO | TODO: YYYY-MM-DD | TODO | local-only 유지 |
| TODO: 실제 provider IAM/network/limit 미측정 | TODO | TODO: YYYY-MM-DD | TODO | provider 실험 보류 |
| TODO: report path 잔존 | TODO | TODO: YYYY-MM-DD | after inventory 후 해당 파일만 삭제 | TODO |
