# Data Engineering 학습 지도

이 가이드는 데이터를 한 번 옮겨 보는 과정이 아니다. **원천의 사실을 소비자가 반복해서 신뢰할 수 있는 상태로 전달하는 계약**을 학습한다.

데이터 파이프라인의 핵심 질문은 다음과 같다.

```text
무엇을 한 record로 보는가?
그 record를 다시 식별할 수 있는가?
어느 시간이 업무 사실이고 어느 시간이 처리 상태인가?
입력 범위와 실행 버전을 재현할 수 있는가?
중복·순서 역전·late event·delete·correction을 어떻게 반영하는가?
부분 실패 뒤 다시 실행해도 같은 논리 결과가 되는가?
소비자가 결과의 freshness·completeness·lineage를 판단할 수 있는가?
```

## 대상 독자

다음 중 하나에 해당하면 적합하다.

- SQL과 Python으로 파일이나 테이블을 변환해 봤지만 재실행·backfill·late data를 체계적으로 설계하기 어렵다.
- Kafka, Spark, Airflow, dbt, Debezium, Iceberg 같은 도구를 사용했지만 각 도구가 어떤 데이터 계약을 책임지는지 설명하기 어렵다.
- 운영 DB의 데이터를 분석·모델 학습·검색·리포팅 시스템에 안전하게 전달하고 싶다.
- batch와 stream을 별개 제품처럼 배웠지만 동일한 identity·time·state·publish 문제로 연결하고 싶다.
- pipeline 성공 표시와 데이터가 실제로 맞다는 사실을 구분하고 싶다.

## 선행지식

필수 기반:

- [`python`](https://github.com/seungwoo7050/guides/tree/python): 함수·class·파일·JSON·CLI·테스트·예외 처리
- [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems): table·key·constraint·transaction·migration의 기본 의미

권장 기반:

- [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services): 중복 전달, 순서 역전, retry, Outbox와 재조정
- [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks): timeout·연결·partition·flow control을 분리하는 능력
- [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra): immutable artifact, secret, 관측, backup과 incident response

선행 브랜치를 모두 완주할 필요는 없다. 아래 진단 질문에 답하지 못할 때 해당 문서로 이동한다.

- transaction commit과 파일 write 완료가 왜 같은 보장이 아닌가?
- 중복 요청을 식별하려면 어떤 안정적인 key가 필요한가?
- timeout이 실패를 뜻하지 않고 결과 미확정을 뜻할 수 있는 이유는 무엇인가?
- migration 중 이전 reader와 새 writer가 공존할 때 무엇을 보존해야 하는가?

## 이 가이드가 소유하는 범위

```text
data product와 producer/consumer 계약
grain·identity·event time·correction
schema evolution과 호환성
bounded batch와 input snapshot
partition·shuffle·join·aggregation
columnar file과 table layout
unbounded stream과 source offset
window·watermark·trigger·late data
keyed state·dedup·checkpoint·sink commit
CDC snapshot·log position·delete·transaction
warehouse·lake·table format·snapshot
orchestration·data interval·retry·backfill
replay·reconciliation·quality·lineage·freshness
분류·접근·보존·삭제 같은 데이터 운영 경계
```

다음은 다른 브랜치가 소유한다.

- 관계 모델, index, MVCC, WAL, query plan: [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems)
- Outbox, Saga, 서비스 명령의 결과 수렴: [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services)
- consensus, replicated log, quorum, sharding: `distributed-systems`
- 모델 학습, 평가와 fine-tuning: `machine-learning`
- workload cluster, multi-tenancy와 self-service platform: `platform-engineering`
- 인증·권한·위협 모델·사고 대응의 일반 원리: `cybersecurity`

주제가 겹쳐도 질문이 다르다. 예를 들어 이 가이드의 CDC는 **분석 소비자가 source transaction과 delete를 어떤 record로 관찰하는가**를 다룬다. `database-systems`의 WAL은 DBMS가 crash 뒤 내부 상태를 어떻게 복구하는가를 다룬다.

## 공통 기반: 계약과 record

모든 경로가 먼저 읽는다.

1. [`01/01 데이터 제품과 소유권`](01-contracts-and-records/01-data-products-and-ownership.md)
2. [`01/02 schema evolution과 호환성`](01-contracts-and-records/02-schema-evolution-and-compatibility.md)
3. [`01/03 identity·시간·correction`](01-contracts-and-records/03-identity-time-and-corrections.md)
4. [`01/04 분석 모델과 역사 보존`](01-contracts-and-records/04-analytical-modeling-and-history.md)

공통 기반의 종료 능력:

> 한 데이터셋의 grain, stable key, event time, source position, correction 방식, schema 호환성, fact/dimension 역사, measure 집계 규칙, freshness와 품질 책임을 producer와 consumer 관점에서 문서화할 수 있다.

## 경로 A: 분석 데이터 제품

다음 순서로 읽는다.

1. 공통 기반 4개 문서
2. [`02/01 bounded data와 replay-safe batch`](02-batch-processing/01-bounded-data-and-replay-safe-batch.md)
3. [`02/02 partition·shuffle·join·aggregation`](02-batch-processing/02-partition-shuffle-join-and-aggregation.md)
4. [`02/03 columnar file과 table layout`](02-batch-processing/03-columnar-files-and-table-layout.md)
5. [`05/01 orchestration과 data interval`](05-orchestration-and-operations/01-orchestration-data-intervals-and-idempotency.md)
6. [`05/02 backfill·replay·reconciliation`](05-orchestration-and-operations/02-backfill-replay-and-reconciliation.md)
7. [`05/03 품질·lineage·freshness`](05-orchestration-and-operations/03-quality-lineage-freshness-and-observability.md)
8. [`06/01 batch 데이터 제품 capstone`](06-capstones/01-batch-data-product.md)

종료 능력:

> source snapshot과 data interval, transform version, output partition과 publish 경계를 고정하고, 동일 입력의 재실행·부분 실패·backfill에서도 같은 논리 결과를 만들며 품질과 lineage로 결과를 증명할 수 있다.

## 경로 B: 스트림 처리

다음 순서로 읽는다.

1. 공통 기반 4개 문서
2. [`03/01 unbounded data와 event time`](03-stream-processing/01-unbounded-data-and-event-time.md)
3. [`03/02 window·watermark·trigger`](03-stream-processing/02-windows-watermarks-and-triggers.md)
4. [`03/03 state·dedup·delivery`](03-stream-processing/03-state-deduplication-and-delivery.md)
5. [`05/02 backfill·replay·reconciliation`](05-orchestration-and-operations/02-backfill-replay-and-reconciliation.md)
6. [`05/03 품질·lineage·freshness`](05-orchestration-and-operations/03-quality-lineage-freshness-and-observability.md)
7. [`06/02 event-time pipeline capstone`](06-capstones/02-event-time-pipeline.md)

종료 능력:

> out-of-order, duplicate, late event, restart와 sink 재시도를 정상 입력으로 다루고, watermark와 trigger가 만드는 잠정 결과·수정 결과·최종성의 범위를 소비자에게 명시할 수 있다.

## 경로 C: CDC와 데이터 플랫폼

다음 순서로 읽는다.

1. 공통 기반 4개 문서
2. [`04/01 CDC snapshot과 log position`](04-ingestion-and-storage/01-cdc-snapshots-and-log-position.md)
3. [`04/02 warehouse·lake·table format`](04-ingestion-and-storage/02-warehouse-lake-and-table-formats.md)
4. [`04/03 evolution·compaction·maintenance`](04-ingestion-and-storage/03-evolution-compaction-and-maintenance.md)
5. [`05/01 orchestration과 data interval`](05-orchestration-and-operations/01-orchestration-data-intervals-and-idempotency.md)
6. [`05/02 backfill·replay·reconciliation`](05-orchestration-and-operations/02-backfill-replay-and-reconciliation.md)
7. [`05/03 품질·lineage·freshness`](05-orchestration-and-operations/03-quality-lineage-freshness-and-observability.md)
8. [`05/04 보안·governance·retention`](05-orchestration-and-operations/04-security-governance-and-retention.md)
9. [`06/03 CDC analytics platform capstone`](06-capstones/03-cdc-to-analytics-platform.md)

종료 능력:

> consistent snapshot과 변경 로그를 하나의 source position으로 연결하고, insert·update·delete·schema change·restart를 보존하며 table snapshot과 reconciliation으로 sink 상태를 증명할 수 있다.

## 전체 경로

세 경로를 모두 완료하면 [`90 시스템 종합 검토`](90-system-review.md)를 수행한다.

전체 경로는 도구를 많이 설치하는 것이 목적이 아니다. 하나의 변경이 다음 높이를 통과하는 과정을 설명하고 검증한다.

```text
업무 사건
→ source transaction 또는 file
→ ingestion position
→ canonical record
→ transform state
→ physical files/table snapshot
→ consumer-visible dataset
→ quality·freshness·lineage evidence
→ correction·replay·retention
```

## 문서와 연습 대응표

| 구획 | 핵심 문서 | 구현·설계 연습 |
|---|---|---|
| 계약 | data product·schema·identity·분석 역사 | [`schema evolution`](../exercises/01-contracts-and-records/01-schema-evolution/README.md), [`batch capstone`](../exercises/06-capstones/01-batch-data-product/README.md) |
| Batch | snapshot·replay·publish | [`replay-safe batch`](../exercises/02-batch-processing/01-replay-safe-batch/README.md) |
| Stream | event time·watermark | [`event-time windows`](../exercises/03-stream-processing/01-event-time-windows/README.md) |
| CDC | snapshot·position·merge | [`CDC snapshot merge`](../exercises/04-ingestion-and-storage/01-cdc-snapshot-merge/README.md) |
| 운영 | interval·backfill·reconcile | [`backfill plan`](../exercises/05-orchestration-and-operations/01-backfill-plan/README.md) |
| 품질 | checks·freshness·lineage | [`quality and lineage`](../exercises/05-orchestration-and-operations/02-quality-and-lineage/README.md) |
| Capstone A | batch 데이터 제품 | [`batch capstone`](../exercises/06-capstones/01-batch-data-product/README.md) |
| Capstone B | event-time pipeline | [`stream capstone`](../exercises/06-capstones/02-event-time-pipeline/README.md) |
| Capstone C | CDC analytics platform | [`CDC capstone`](../exercises/06-capstones/03-cdc-analytics-platform/README.md) |

## 실행 계약

저장소 루트의 공개 명령은 다음 네 개다.

```bash
make prepare
make check
VERIFY_LOG=/tmp/data-engineering-verify.log make verify
make clean
```

`prepare.sh`는 다음만 담당한다.

- Python 3.11 이상을 확인한다.
- source bytes·mode와 symlink fingerprint를 계산한다.
- `.guide/data-engineering/prepared.json`에 guide ID와 fingerprint를 기록한다.
- source, exercise skeleton과 Git index를 수정하지 않는다.

`make check`는 빠른 정적 검사를 수행한다.

- 필수 파일과 문서 section
- Markdown 내부 링크
- Python syntax와 unit test
- manifest·workspace 경로 계약

`make verify`는 외부 임시 복사본에서 다음을 검사한다.

- 모든 example의 결정적 결과
- 각 reference가 통과하고 skeleton이 지정된 semantic code로 실패하는지
- capstone artifact validator가 유효 fixture를 수용하고 누락 fixture를 거부하는지
- source와 실행 권한이 검증 전후 바뀌지 않는지
- 로그가 저장소 밖에 남고 임시 디렉터리가 정리되는지

## 버전 기준과 이식성

- 필수 실행 환경: Python 3.11 이상, POSIX shell
- 기본 example과 exercise: Python 표준 라이브러리만 사용
- 외부 도구: 개념을 실제 플랫폼에 적용하는 선택 profile이며 root 검증의 필수 조건이 아니다.

공식 프로젝트의 API와 버전은 변할 수 있다. 이 가이드의 정본은 특정 제품 함수가 아니라 identity, time, state, publish, replay와 evidence 계약이다. 최신 구현 자료는 [`reference/official-sources.md`](../reference/official-sources.md)에서 확인한다.
