# Event-time stream capstone

out-of-order·duplicate·late event·restart를 처리하는 실시간 집계와 correction 계약을 설계한다.

## 시나리오

매장 결제 event를 5분 fixed window로 집계한다. partition별 지연, duplicate delivery, 1시간 이내 late correction, watermark 이후 도착한 매우 늦은 event와 sink retry를 처리한다.

## 구현 선택

특정 framework는 강제하지 않는다. Python 표준 라이브러리의 축소 구현, 로컬 database·message broker, Spark/Beam/Flink, Airflow/Dagster, dbt, Debezium, Iceberg/Delta/Hudi 등 어떤 조합도 사용할 수 있다. 선택한 도구가 아래 계약을 실제로 증명해야 한다.

## 필수 산출물

- `skeleton/event-contract.md`
- `skeleton/window-policy.md`
- `skeleton/state-and-checkpoint.md`
- `skeleton/sink-contract.md`
- `skeleton/quality-and-lateness.md`
- `skeleton/failure-matrix.md`
- `skeleton/reconciliation.md`
- `skeleton/runbook.md`
- `skeleton/submission.json`

`skeleton/`은 작성 형식을 보여 주는 빈 작업 출발점이다. 완성된 reference 구현은 제공하지 않는다.

```bash
./scripts/new-workspace.sh exercises/06-capstones/02-event-time-pipeline
./scripts/check-workspace.sh exercises/06-capstones/02-event-time-pipeline
```

두 번째 명령은 필수 artifact와 JSON 구조만 검사한다. 실제 pipeline의 정확성은 `workspace/submission.json`의 `verify_command`와 별도 failure fixture로 증명한다.

## 완료 기준

- event time, ingestion time, processing time이 분리됨
- window, watermark, trigger, allowed lateness 계약이 명시됨
- dedup key·state TTL·checkpoint·restart 경계가 있음
- sink result key와 correction/version 또는 upsert 계약이 있음
- backpressure·idle partition·poison event 실패가 포함됨
- batch replay와 stream 결과를 대사하는 방법이 있음

## 검증 전략

최소한 다음 fixture 또는 실행 시나리오를 준비한다.

- 정상 입력
- duplicate와 입력 순서 변경
- 필수 필드 또는 schema 오류
- 중간 단계 종료와 재시작
- 같은 interval 또는 offset replay
- correction/delete/late data 중 해당 경로의 핵심 사건
- publish 직전과 직후 실패
- source와 sink reconciliation 불일치

root 검증은 산출물 template과 rubric의 구조만 확인한다. 실제 pipeline의 정확성과 운영 가능성은 학습자가 선택한 runtime에서 별도 검사해야 한다.

## 제출 전 질문

1. 입력과 출력의 정확한 version을 다시 찾을 수 있는가?
2. 같은 논리 범위를 재실행했을 때 무엇이 같아야 하는가?
3. consumer가 볼 수 있는 결과는 언제, 어떤 검사 뒤에 바뀌는가?
4. 잘못 publish한 결과를 이전 상태로 돌리는 절차가 있는가?
5. 결과가 맞다는 주장을 process 성공 외의 데이터 증거로 할 수 있는가?
