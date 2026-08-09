# Capstone A: 재실행 가능한 batch 데이터 제품

## 목적

운영 시스템의 주문·결제 export를 입력으로 받아 일별 매출 데이터 제품을 만든다. 구현 기술보다 **계약, 재실행, publish와 품질 근거**를 완성하는 것이 목적이다.

## 문제 배경

매일 다음 file이 도착한다.

```text
orders/YYYY-MM-DD/orders-*.jsonl
payments/YYYY-MM-DD/payments-*.jsonl
accounts/snapshot-<id>.jsonl
```

현실적인 조건:

- file은 여러 번 전달될 수 있다.
- 같은 event가 다른 file에 중복될 수 있다.
- 결제는 주문보다 늦게 도착할 수 있다.
- 내부 test 계정을 제외해야 한다.
- 환불은 원 결제 날짜의 매출을 correction한다.
- account classification snapshot은 run마다 달라질 수 있다.
- output write 중 failure가 발생할 수 있다.

## 목표 output

`currency`, `sales_date` grain의 일별 fact를 publish한다.

필수 column 예:

```text
sales_date
currency
gross_amount
refund_amount
net_amount
paid_order_count
source_order_count
source_payment_count
input_manifest_id
transform_version
published_at
quality_status
```

정확한 schema는 학습자가 정의하되 grain과 correction 의미를 문서화한다.

## 필수 artifact

1. `data-contract.md`
2. `input-manifest.json`
3. `pipeline-design.md`
4. `failure-matrix.md`
5. `quality-plan.json`
6. `reconciliation.md`
7. `runbook.md`
8. `evidence.json` — run/input/code/output identity와 capstone별 필수 시나리오의 관측 파일
9. `submission.json` — 구현 profile, 실행·검증 명령과 알려진 한계

템플릿은 [`exercises/06-capstones/01-batch-data-product`](../../exercises/06-capstones/01-batch-data-product/README.md)에 있다.

## 누적 evidence 연결

기존 artifact 안에서 다음 여덟 높이를 서로 같은 grain·key·time·version 용어로 연결한다.

| 높이 | artifact에 남길 evidence |
|---|---|
| contract와 ownership | `data-contract.md`: source·producer·operator·consumer owner, structural/semantic schema, correction·SLO·classification·retention |
| ingestion과 raw | `input-manifest.json`: immutable object version/checksum/complete marker, delivery duplicate와 partial/mutable file 판정 |
| processing state | `pipeline-design.md`: deterministic transform, job/run/attempt/output identity, input·code·config·reference version |
| storage와 publish | `pipeline-design.md`: partition/file target, staging, validation gate, atomic metadata pointer와 previous snapshot |
| orchestration과 backfill | `runbook.md`: run state, 90일 dry-run, live quota, pause/resume/abort/rollback |
| quality와 reconciliation | `quality-plan.json`·`reconciliation.md`: hard/statistical rule, sticky quarantine, count·amount·key/detail diff |
| lineage·freshness·cost·access | `evidence.json`·`submission.json`·`runbook.md`: input/output/code/schema/quality lineage, source/pipeline delay, unit cost, 최소 권한 |
| evolution과 consumer cutover | `data-contract.md`·`runbook.md`: old/new matrix, shadow result, canary consumer, migration, deprecation와 rollback/roll-forward |

Artifact가 존재하는 것만으로 evidence가 되지는 않는다. `evidence.json`의 각 시나리오는 고유한 `evidence/` 파일과 run/input/code/output identity를 가리키며, 각 결정은 fixture, 실행 결과, manifest/snapshot ID, diff 또는 사람 sign-off로 뒷받침한다. Root checker는 이 연결과 본문 충실도를 정적으로 검사하지만 학습자가 적은 임의 명령은 실행하지 않는다.

## 상태와 경계

```text
DISCOVERED
→ INPUT_PINNED
→ TRANSFORMING
→ STAGED
→ VALIDATED
→ PUBLISHED

실패:
FAILED_TRANSFORM
FAILED_QUALITY
FAILED_COMMIT
SUPERSEDED
```

consumer는 `PUBLISHED` snapshot만 읽어야 한다.

## 필수 설계 결정

### input snapshot

- object key만으로 충분한가?
- version/checksum을 어떻게 고정하는가?
- late file은 기존 manifest를 수정하는가, 새 correction run을 만드는가?

### identity

- order, payment, refund의 stable key는 무엇인가?
- file 중복과 event 중복을 어떻게 구분하는가?

### time

- 매출 일자는 order, payment, refund 중 어느 event time인가?
- timezone과 calendar boundary는 무엇인가?

### reference data

- account snapshot ID를 어떻게 고정하는가?
- 과거 run의 classification을 재현할 수 있는가?

### publish

- partition replace, versioned snapshot, merge 중 무엇인가?
- validation 실패 때 이전 정상 snapshot은 어떻게 유지되는가?

### correction

- late payment/refund가 과거 partition을 어떻게 바꾸는가?
- correction window와 마감 이후 정책은 무엇인가?

## 필수 실패 시나리오

- `normal`: 고정 manifest와 version의 정상 실행·검증·publish
- `input-order-permutation`: 같은 입력 집합의 file/row 순서를 바꾼 재실행
- `duplicate-manifest-file`: 같은 file이 input manifest에 두 번 등록됨
- `duplicate-payment-event`: 같은 payment event가 다른 file에 중복됨
- `transform-crash`: transform 중간에 process 종료
- `quality-gate-failure`: staging은 완료됐지만 quality가 실패
- `pre-publish-commit-failure`: quality 통과 뒤 metadata commit 직전 failure
- `post-publish-retry`: metadata commit 뒤 응답 유실로 같은 run을 재시도
- `concurrent-publish`: 같은 interval의 두 run이 동시에 publish 시도
- `missing-reference-snapshot`: 과거 account snapshot이 누락됨
- `late-refund-boundary`: late refund가 correction window 안/밖에 도착
- `partial-or-mutable-input`: complete marker 전 partial file 또는 같은 object key의 mutable version을 발견
- `conflicting-payment-event`: 같은 payment event ID에 서로 다른 payload가 도착
- `backfill-live-contention`: backfill이 live source·warehouse capacity를 압박해 freshness SLO를 위협
- `semantic-canary-mismatch`: old/new metric은 schema가 같지만 의미가 달라 canary consumer 결과가 어긋남
- `reconciliation-mismatch`: source와 published snapshot의 key·count·amount가 어긋남

각 시나리오에서 다음을 기록한다.

- consumer-visible state
- retry 가능 여부
- cleanup 대상
- alert와 owner
- reconciliation 결과

## 품질과 reconciliation

최소 검사:

- input manifest checksum
- payment/refund event ID uniqueness
- order-payment join multiplicity
- allowed currency/domain
- `net = gross - refund`
- source별 count와 amount
- internal account 제외 수
- output key uniqueness
- expected partition coverage
- previous snapshot 대비 변화 설명
- conflicting ID가 이후 duplicate로 재승인되지 않는 sticky quarantine
- old/new output의 key·aggregate·sample diff와 consumer sign-off

## 사람·runtime 검토 evidence

Root validator는 필수 section의 보이는 본문, submission/evidence identity, rubric의 모든 필수 시나리오와 고유한 `evidence/` 파일의 정적 연결을 검사한다. 명령 실행 결과의 진실성과 다음 의미 판단은 선택 runtime과 사람이 별도로 확인한다.

- 동일 manifest·version의 두 실행이 만든 canonical row digest와 snapshot ID
- transform/publish 지점의 failure injection 뒤 consumer-visible pointer와 cleanup 결과
- conflicting duplicate, partial/mutable file, late refund와 missing reference fixture의 판정
- canary backfill의 source load·live freshness·stop condition과 resume 결과
- old/new output reconciliation, consumer cutover 승인과 rollback rehearsal
- 실제 접근·retention·quarantine 정책을 사용하지 않았다면 그 비보장 범위

## 완료 판정

다음 조건을 모두 만족한다.

- 같은 input manifest와 transform version을 두 번 실행해 같은 논리 결과를 만든다.
- partial failure에서 이전 published snapshot을 보존한다.
- duplicate file/event를 추가해도 net 결과가 변하지 않는다.
- late correction이 정한 정책대로 새 version을 만든다.
- manifest와 lineage만으로 input, code와 output snapshot을 추적할 수 있다.
- runbook만 보고 다른 개발자가 canary, publish, rollback과 대사를 수행할 수 있다.
- runtime 결과와 사람 검토를 구분하고 자동 구조 검사만으로 교육적 완성을 주장하지 않는다.

## 범위 밖

- 대규모 cluster tuning
- BI dashboard 디자인
- source DB의 업무 transaction 구현
- 실제 개인정보 사용
- 모든 table format/engine 비교

## 후속 확장

- 실제 columnar format과 table snapshot 사용
- incremental batch와 merge
- consumer contract test
- data quality history dashboard
- OpenLineage event 전송
