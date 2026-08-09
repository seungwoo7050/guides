# Batch 데이터 제품 capstone

원천 snapshot에서 소비자용 일별 매출 데이터 제품을 재실행 가능하게 만들고 backfill·대사·publish 계약을 설계한다.

## 시나리오

운영 주문 원천과 환율 reference data를 사용해 `sales_date × currency` grain의 일별 순매출 데이터 제품을 만든다. 취소·환불 correction, 중복 event, source 재수집, 환율 revision과 부분 publish 실패를 정상 입력으로 다룬다.

## 구현 선택

특정 framework는 강제하지 않는다. Python 표준 라이브러리의 축소 구현, 로컬 database·message broker, Spark/Beam/Flink, Airflow/Dagster, dbt, Debezium, Iceberg/Delta/Hudi 등 어떤 조합도 사용할 수 있다. 선택한 도구가 아래 계약을 실제로 증명해야 한다.

## 필수 산출물

- `skeleton/data-contract.md`
- `skeleton/input-manifest.json`
- `skeleton/pipeline-design.md`
- `skeleton/failure-matrix.md`
- `skeleton/quality-plan.json`
- `skeleton/reconciliation.md`
- `skeleton/runbook.md`
- `skeleton/evidence.json`
- `skeleton/submission.json`

`skeleton/`은 작성 형식을 보여 주는 빈 작업 출발점이다. 완성된 reference 구현은 제공하지 않는다.

```bash
./scripts/new-workspace.sh exercises/06-capstones/01-batch-data-product
./scripts/check-workspace.sh exercises/06-capstones/01-batch-data-product
```

두 번째 명령은 각 Markdown template의 필수 section에 보이는 구체적 본문이 있는지, `submission.json`과 `evidence.json`의 run/input/code/output identity가 일치하는지, rubric의 모든 필수 시나리오가 각각 물리적으로 고유한 `evidence/` 파일을 가리키는지 검사한다. 학습자가 적은 `run_command`와 `verify_command`는 신뢰할 수 없는 임의 명령이므로 root checker가 실행하지 않는다.

## 완료 기준

- grain, stable key, event time, correction policy가 명시됨
- input snapshot과 transform/reference/schema version이 고정됨
- 동일 입력 replay가 같은 logical rows와 snapshot을 만듦
- staging, validation, publish pointer와 partial failure가 설명됨
- backfill canary, stop condition, resume, rollback이 있음
- count, key, aggregate reconciliation과 freshness/lineage가 있음

## 검증 전략

최소한 다음 fixture 또는 실행 시나리오를 준비한다.

- `normal`: 고정 manifest의 정상 실행과 publish
- `input-order-permutation`: file/row 순서 변경
- `duplicate-manifest-file`: manifest의 같은 file 중복
- `duplicate-payment-event`: 여러 file의 같은 payment event 중복
- `transform-crash`: transform 중간 종료와 재시작
- `quality-gate-failure`: staging 뒤 quality gate 실패
- `pre-publish-commit-failure`: metadata commit 직전 실패
- `post-publish-retry`: commit 뒤 응답 유실과 같은 run 재시도
- `concurrent-publish`: 같은 interval 동시 publish
- `missing-reference-snapshot`: 과거 reference snapshot 누락
- `late-refund-boundary`: correction window 안/밖 refund
- `partial-or-mutable-input`: partial file 또는 mutable object version
- `conflicting-payment-event`: 같은 ID의 다른 payload
- `backfill-live-contention`: backfill과 live capacity·freshness 충돌
- `semantic-canary-mismatch`: 같은 schema의 다른 metric 의미
- `reconciliation-mismatch`: source와 snapshot 대사 불일치

root 검증은 빈 section, placeholder, scenario 누락·중복, 경로 탈출, identity 불일치와 비어 있는 evidence를 거부한다. 실제 pipeline의 정확성, evidence가 실제 실행에서 생성됐는지와 운영 가능성은 학습자가 선택한 runtime의 명령 실행 및 사람 검토로 확인해야 한다.

## 제출 전 질문

1. 입력과 출력의 정확한 version을 다시 찾을 수 있는가?
2. 같은 논리 범위를 재실행했을 때 무엇이 같아야 하는가?
3. consumer가 볼 수 있는 결과는 언제, 어떤 검사 뒤에 바뀌는가?
4. 잘못 publish한 결과를 이전 상태로 돌리는 절차가 있는가?
5. 결과가 맞다는 주장을 process 성공 외의 데이터 증거로 할 수 있는가?
