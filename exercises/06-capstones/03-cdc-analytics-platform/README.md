# CDC analytics platform capstone

consistent snapshot과 change log를 분석 table snapshot으로 전달하고 schema·delete·restart·backfill을 운영한다.

## 시나리오

주문·결제 운영 DB의 CDC를 canonical change record로 수집해 분석 table에 반영한다. 초기 snapshot과 log position, transaction metadata, tombstone, schema evolution, small-file compaction과 consumer snapshot promotion을 다룬다.

## 구현 선택

특정 framework는 강제하지 않는다. Python 표준 라이브러리의 축소 구현, 로컬 database·message broker, Spark/Beam/Flink, Airflow/Dagster, dbt, Debezium, Iceberg/Delta/Hudi 등 어떤 조합도 사용할 수 있다. 선택한 도구가 아래 계약을 실제로 증명해야 한다.

## 필수 산출물

- `skeleton/source-contract.md`
- `skeleton/snapshot-stream-protocol.md`
- `skeleton/cdc-envelope.md`
- `skeleton/table-layout.md`
- `skeleton/schema-change-plan.md`
- `skeleton/quality-reconciliation.md`
- `skeleton/security-retention.md`
- `skeleton/failure-matrix.md`
- `skeleton/incident-runbook.md`
- `skeleton/evidence.json`
- `skeleton/submission.json`

`skeleton/`은 작성 형식을 보여 주는 빈 작업 출발점이다. 완성된 reference 구현은 제공하지 않는다.

```bash
./scripts/new-workspace.sh exercises/06-capstones/03-cdc-analytics-platform
./scripts/check-workspace.sh exercises/06-capstones/03-cdc-analytics-platform
```

두 번째 명령은 각 Markdown template의 필수 section에 보이는 구체적 본문이 있는지, `submission.json`과 `evidence.json`의 run/input/code/output identity가 일치하는지, rubric의 모든 필수 시나리오가 각각 물리적으로 고유한 `evidence/` 파일을 가리키는지 검사한다. 학습자가 적은 `run_command`와 `verify_command`는 신뢰할 수 없는 임의 명령이므로 root checker가 실행하지 않는다.

## 완료 기준

- snapshot 시작·종료와 source log position 연결이 설명됨
- insert/update/delete와 transaction/source position이 보존됨
- schema compatibility와 incompatible change 절차가 있음
- raw immutable zone과 consumer table snapshot이 분리됨
- compaction이 logical content와 lineage를 바꾸지 않음
- restart, re-snapshot, backfill, rollback, source/sink 대사가 있음

## 검증 전략

최소한 다음 fixture 또는 실행 시나리오를 준비한다.

- `normal`: 고정 snapshot/position의 정상 projection과 publish
- `snapshot-log-gap-overlap`: snapshot과 log의 gap/overlap
- `snapshot-crash`: snapshot 중 connector crash
- `log-retention-risk`: source log retention 임박
- `sink-write-before-checkpoint-crash`: sink 성공 뒤 checkpoint 실패
- `missing-delete-event`: delete 누락
- `stale-replay`: 최신 row 뒤 stale replay
- `catalog-commit-failure`: catalog commit 전/후 실패
- `compaction-live-merge-conflict`: compaction과 live merge 충돌
- `retention-exceeded-outage`: outage가 retention 초과
- `schema-decoding-failure`: source schema change decode 실패
- `deletion-propagation`: old snapshot·aggregate까지 삭제 전파
- `conflicting-source-position`: 같은 position/key의 다른 payload
- `deletion-remnant-after-repair`: repair 뒤 삭제 대상 잔존
- `semantic-consumer-mismatch`: old consumer 의미 오해
- `reconciliation-mismatch`: source/current/aggregate/consumer 대사 불일치

root 검증은 빈 section, placeholder, scenario 누락·중복, 경로 탈출, identity 불일치와 비어 있는 evidence를 거부한다. 실제 pipeline의 정확성, evidence가 실제 실행에서 생성됐는지와 운영 가능성은 학습자가 선택한 runtime의 명령 실행 및 사람 검토로 확인해야 한다.

## 제출 전 질문

1. 입력과 출력의 정확한 version을 다시 찾을 수 있는가?
2. 같은 논리 범위를 재실행했을 때 무엇이 같아야 하는가?
3. consumer가 볼 수 있는 결과는 언제, 어떤 검사 뒤에 바뀌는가?
4. 잘못 publish한 결과를 이전 상태로 돌리는 절차가 있는가?
5. 결과가 맞다는 주장을 process 성공 외의 데이터 증거로 할 수 있는가?
