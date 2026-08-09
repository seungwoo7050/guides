# 공식 자료

최종 검토일: **2026-08-10**

이 가이드는 특정 제품을 필수 구현으로 고정하지 않는다. 아래 자료는 개념을 실제 플랫폼에 적용할 때 확인할 공식 출처다. API, 설정 이름과 기본값은 바뀔 수 있으므로 사용 시점에 다시 검증한다.

## 공통 처리 모델

### Apache Beam Programming Guide

- https://beam.apache.org/documentation/programming-guide/
- bounded/unbounded collection, event time, window, watermark, trigger와 stateful processing을 하나의 모델로 연결할 때 사용한다.
- 이 가이드의 축소 Python 모델은 Beam API를 재현하지 않는다.

## Schema와 record format

### Apache Avro 1.12.0 Specification

- https://avro.apache.org/docs/1.12.0/specification/
- writer/reader schema resolution, default와 type promotion을 실제 format 규칙으로 검토할 때 사용한다.

### Confluent Schema Registry 문서

- https://docs.confluent.io/platform/current/schema-registry/index.html
- compatibility mode, subject와 schema version 운영 사례를 확인할 때 사용한다.
- registry 제품의 compatibility 결과가 업무 의미 변화까지 판정하지는 않으므로 semantic review를 별도로 둔다.

### Apache Parquet 문서

- https://parquet.apache.org/docs/
- columnar format, encoding, metadata와 file layout을 확인할 때 사용한다.

## CDC

### Debezium Documentation

- https://debezium.io/documentation/reference/stable/
- source connector, snapshot mode, change event envelope, transaction metadata와 offset 저장을 실제 connector에 적용할 때 사용한다.
- source DB별 snapshot·schema·delete 보장이 다르므로 connector별 문서를 추가로 확인한다.

## Table format과 snapshot

### Apache Iceberg Documentation

- https://iceberg.apache.org/docs/latest/
- table snapshot, schema·partition evolution, maintenance와 catalog commit을 검토할 때 사용한다.

특정 프로젝트에서 Delta Lake나 Apache Hudi를 선택했다면 해당 프로젝트의 공식 transaction·concurrency·maintenance 문서로 같은 계약을 다시 검증한다.

## Orchestration

### Apache Airflow Documentation

- https://airflow.apache.org/docs/apache-airflow/stable/
- DAG, task, logical date/data interval, retry, catchup와 backfill을 실제 scheduler에 적용할 때 사용한다.
- orchestration metadata를 대량 데이터 전달 경로로 사용하지 않는다.

## Lineage

### OpenLineage Documentation

- https://openlineage.io/docs/
- run, job, input/output dataset과 facet 기반 lineage event를 실제 도구와 연결할 때 사용한다.

### OpenLineage specification repository

- https://github.com/OpenLineage/OpenLineage
- event schema와 client integration의 현재 상태를 확인할 때 사용한다.

## 검토 원칙

공식 문서를 읽을 때 다음 질문을 기록한다.

1. 이 기능이 보장하는 정확한 범위는 무엇인가?
2. source·partition·transaction·restart 경계에서 보장이 달라지는가?
3. 기본값과 retention 또는 timeout은 무엇인가?
4. version upgrade에서 state와 schema 호환성은 어떻게 처리하는가?
5. local filesystem 예제와 object storage·분산 runtime의 publish 원리가 같은가?
6. metric이 process 진행도인지 data correctness인지 구분되는가?
