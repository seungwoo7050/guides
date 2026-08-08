# Database Systems 학습 지도

이 가이드는 SQL 문장을 외우는 과정이 아니다. **논리적 데이터 계약이 어떤 물리 구조와 동시성·복구 계약을 거쳐 실행되는지**를 연결하는 과정이다. 간단한 CRUD 경험 이후부터 시작해, 애플리케이션의 스키마와 질의를 검토하는 경로와 작은 저장 엔진을 구현하는 경로를 함께 제공한다.

## 대상 독자

다음 중 하나에 해당하면 적합하다.

- 웹 애플리케이션에서 SQL과 migration을 사용해 봤지만 `NULL`, 격리 수준, 실행 계획과 인덱스를 체계적으로 설명하기 어렵다.
- B+ tree, buffer pool, MVCC, WAL을 따로 공부했지만 하나의 DBMS 요청 경로로 연결하지 못한다.
- ORM이 만든 SQL과 데이터베이스 내부 동작 사이의 경계를 이해하고 싶다.
- 데이터베이스 관련 장애를 “느리다”, “lock이 걸렸다” 수준이 아니라 증거와 불변식으로 분석하고 싶다.

## 선행지식

필수 선행지식은 다음 정도다.

- 테이블을 만들고 간단한 `SELECT`, `INSERT`, `UPDATE`, `DELETE`를 작성한 경험
- 기본 키와 외래 키가 무엇인지 아는 수준
- 터미널에서 명령을 실행하고 오류 출력을 읽는 능력
- 내부구조 연습을 진행한다면 Python 함수·클래스·리스트·딕셔너리의 기본 사용
- PostgreSQL 통합 연습을 위해 Docker를 실행할 수 있는 환경

이 저장소는 SQL 문법 입문과 애플리케이션 연결법을 다시 처음부터 가르치지 않는다. 그 범위는 [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app)이 소유한다.

## 이 가이드가 소유하는 범위

이 저장소의 주 소유 영역은 다음이다.

```text
관계 의미와 SQL의 실제 의미
함수 종속성·정규화·제약
페이지·레코드·B+ tree·buffer pool
transaction 이상 현상·lock·MVCC
WAL·checkpoint·crash recovery
join·sort·aggregation 실행
통계·비용 모델·EXPLAIN
schema·index·migration 튜닝 루프
```

다음은 의도적으로 다른 가이드에 남긴다.

- 애플리케이션에서 필요한 첫 SQL과 connection pool: [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app)
- JPA, `@Transactional`, Flyway 연결법: [`backend-spring-boot`](https://github.com/seungwoo7050/guides/tree/backend-spring-boot)
- 서비스별 데이터 소유권, Outbox, Saga, 재전달: [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services)
- PostgreSQL 호스트 운영, 백업 자동화, 모니터링 인프라: [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra)

주제가 겹치더라도 목적이 다르다. 예를 들어 이 가이드의 WAL은 DBMS의 복구 계약을 다루고, 분산 서비스 가이드의 Outbox는 서로 다른 서비스 사이의 전달 계약을 다룬다.

## 두 학습 경로

### 애플리케이션 데이터베이스 경로

다음 순서로 읽는다.

1. [`01/01 관계 모델`](01-relational-semantics-and-design/01-relational-model-and-algebra.md)
2. [`01/02 SQL 의미`](01-relational-semantics-and-design/02-sql-semantics-and-query-shape.md)
3. [`01/03 스키마·정규화·제약`](01-relational-semantics-and-design/03-er-normalization-and-constraints.md)
4. [`03/01 transaction·격리·lock`](03-transactions-and-recovery/01-transactions-isolation-and-locks.md)
5. [`04/02 통계·비용·EXPLAIN`](04-execution-and-optimization/02-statistics-cost-model-and-explain.md)
6. [`04/03 schema·index·migration loop`](04-execution-and-optimization/03-schema-index-and-tuning-loop.md)
7. [`05/01 애플리케이션 DB review`](05-capstones/01-application-database-review.md)

이 경로의 종료 능력은 다음이다.

> 업무 불변식을 스키마와 transaction 경계로 내리고, 대표 질의의 의미와 실행 계획을 설명하며, 측정 근거를 가진 인덱스·migration 변경을 제안하고 검증할 수 있다.

### DBMS 내부구조 경로

다음 순서로 읽는다.

1. [`01/01 관계 모델`](01-relational-semantics-and-design/01-relational-model-and-algebra.md)
2. [`02/01 페이지와 레코드`](02-storage-and-indexes/01-pages-records-and-files.md)
3. [`02/02 인덱스 구조`](02-storage-and-indexes/02-index-structures.md)
4. [`02/03 buffer pool`](02-storage-and-indexes/03-buffer-pool-and-replacement.md)
5. [`03/01 transaction·격리·lock`](03-transactions-and-recovery/01-transactions-isolation-and-locks.md)
6. [`03/02 MVCC·WAL·복구`](03-transactions-and-recovery/02-mvcc-wal-and-recovery.md)
7. [`04/01 질의 실행`](04-execution-and-optimization/01-query-execution-joins-and-sorting.md)
8. [`04/02 통계·비용·EXPLAIN`](04-execution-and-optimization/02-statistics-cost-model-and-explain.md)
9. [`05/02 미니 저장 엔진`](05-capstones/02-mini-storage-engine.md)

이 경로의 종료 능력은 다음이다.

> 논리 tuple이 페이지와 index entry로 저장되고, buffer pool·transaction·WAL·실행기를 거쳐 결과가 되는 과정을 작은 구현과 실패 조건으로 설명할 수 있다.

### 전체 경로

두 경로를 모두 수행하면 [`90 시스템 종합 검토`](90-system-review.md)로 끝낸다.

## 문서와 연습 대응표

| 구획 | 문서 | 연습 |
|---|---|---|
| 관계 의미 | 관계 모델·SQL 의미 | [`SQL 의미`](../exercises/01-relational-semantics-and-design/01-sql-semantics/README.md) |
| 스키마 설계 | ER·정규화·제약 | [`스키마와 제약`](../exercises/01-relational-semantics-and-design/02-schema-and-constraints/README.md) |
| 페이지 | 페이지·레코드 | [`Slotted page`](../exercises/02-storage-and-indexes/01-slotted-page/README.md) |
| 인덱스 | B+ tree·hash·BRIN | [`B+ tree`](../exercises/02-storage-and-indexes/02-bplus-tree/README.md) |
| 메모리 | Buffer pool·Clock | [`Buffer pool`](../exercises/02-storage-and-indexes/03-buffer-pool-clock/README.md) |
| 동시성 | 격리·lock | [`PostgreSQL isolation`](../exercises/03-transactions-and-recovery/01-postgres-isolation/README.md) |
| 복구 | MVCC·WAL | [`WAL recovery`](../exercises/03-transactions-and-recovery/02-wal-recovery/README.md) |
| 실행기 | Join·sort | [`Join algorithms`](../exercises/04-execution-and-optimization/01-join-algorithms/README.md) |
| 최적화 | EXPLAIN·index | [`Query plans`](../exercises/04-execution-and-optimization/02-query-plans-and-indexes/README.md) |
| 변경 | Migration·backfill | [`Safe migration`](../exercises/04-execution-and-optimization/03-safe-migration-and-backfill/README.md) |
| Capstone A | Application review | [`Ticketing DB`](../exercises/05-capstones/01-application-database-review/README.md) |
| Capstone B | Mini storage engine | [`Mini storage`](../exercises/05-capstones/02-mini-storage-engine/README.md) |

## 실행 계약

저장소 루트의 공개 명령은 다음 네 개다.

```bash
make prepare
make check
VERIFY_LOG=/tmp/database-systems-verify.log make verify
make clean
```

`prepare.sh`는 다음만 담당한다.

- Python과 Docker 환경을 확인한다.
- PostgreSQL 18.4 이미지를 immutable digest로 내려받고 image ID를 고정한다.
- source bytes·mode·symlink와 Git index가 바뀌지 않았음을 확인한다.
- namespaced JSON marker에 입력 fingerprint와 도구 판본을 기록한다.

`verify.sh`는 준비된 최종 저장소를 읽기 전용 검증 대상으로 취급한다.
로그 경로를 생략하면 `/tmp/guide-database-systems-verify-*.log`를 사용하고, `VERIFY_LOG`를 지정할 때는 저장소 밖 절대 경로만 허용한다.

- 구조와 Markdown 링크
- Python 예제
- reference가 통과하고 skeleton이 실패하는지
- 실제 PostgreSQL에서 SQL 의미·제약·동시성·실행 계획·migration
- 두 capstone
- 검증 전후 source와 Git index의 byte-for-byte 무변경
- 저장소 밖 절대 로그와 실행별 Docker label을 이용한 격리·정리

## 연습 사용법

`skeleton/`은 문제의 출발점이고 `reference/`는 검증된 비교 구현이다. 직접 수정할 작업 공간은 다음처럼 만든다.

```bash
./scripts/new-workspace.sh exercises/02-storage-and-indexes/01-slotted-page
```

권장 순서는 다음이다.

```text
문제 계약 읽기
→ 실패하는 테스트 확인
→ workspace 구현
→ 해당 exercise 테스트 통과
→ reference와 diff 비교
→ 설계 차이를 문장으로 기록
```

reference를 먼저 복사해 통과시키는 것은 학습 완료가 아니다. 테스트가 어떤 잘못된 상태를 막는지 설명할 수 있어야 한다.

## 버전 기준과 이식성

- Python 3.11 이상
- PostgreSQL 18.4 Alpine image(immutable digest)
- Docker daemon
- Bash 3.2 이상

내부구조 Python 구현은 DBMS의 전체 구현이 아니라 계약을 관찰하기 위한 축소 모델이다. PostgreSQL 실습은 실제 SQL 의미와 동시성·계획을 확인하지만, 특정 데이터 규모에서의 plan을 모든 환경에 일반화하지 않는다.
