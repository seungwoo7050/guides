# Database Systems Guide

관계형 데이터베이스를 **정확한 스키마와 질의**, **저장 엔진 내부구조**, **동시성·복구**, **실행 계획과 튜닝**의 한 흐름으로 학습하는 가이드다.

이 저장소는 SQL 문법 입문서가 아니다. 간단한 테이블 생성과 `SELECT`·`INSERT`·`UPDATE`·`DELETE`를 작성해 본 독자를 대상으로 한다. 웹 애플리케이션에서 필요한 최소 SQL 이후, 데이터베이스 자체를 설계·관찰·구현하는 단계부터 시작한다.

## 시작

```bash
make prepare
make check
VERIFY_LOG=/tmp/database-systems-verify.log make verify
make clean
```

- `make prepare`는 source와 Git index를 바꾸지 않고 Python·Docker를 확인하고 digest로 고정한 PostgreSQL 18.4 이미지를 준비한다.
- `make check`는 네트워크나 PostgreSQL container 없이 문서·Python·validator 계약을 빠르게 검사한다.
- `make verify`는 저장소 밖 임시 복사본과 외부 절대 로그에서 문서, Python, skeleton/reference, PostgreSQL 통합 실습과 capstone을 검사한다.
- `make clean`은 명시된 생성물만 지우며 준비 cache와 learner workspace는 보존한다.
- `VERIFY_LOG`를 생략하면 `/tmp/guide-database-systems-verify-*.log`를 사용하며, 직접 지정할 때도 저장소 밖 절대 경로만 허용한다.
- 준비 상태는 `.guide/database-systems/prepared.json`에 guide ID, source/index fingerprint와 이미지 ID로 기록된다.

학습 순서와 두 개의 권장 경로는 [`docs/00-roadmap.md`](docs/00-roadmap.md)에 있다.

## 두 학습 경로

- **애플리케이션 데이터베이스 경로**: 관계 의미 → 제약 → 트랜잭션 → 실행 계획 → 안전한 마이그레이션 → 운영 질의 검토
- **DBMS 내부구조 경로**: 페이지 → 인덱스 → 버퍼 풀 → MVCC·WAL → 조인 실행기 → 미니 저장 엔진

두 경로는 같은 데이터베이스 계약을 서로 다른 높이에서 본다. 한쪽만 완료할 수 있으며, 전체 과정을 완료하면 애플리케이션의 질의와 DBMS 내부 동작을 연결해 설명할 수 있다.

## 학습 순서

먼저 학습 지도를 읽고 한 경로를 고른다. 각 행에서는 문서를 읽은 뒤 관찰 예제를 실행하고, `skeleton/`에서 만든 `workspace/`만 수정한다. 처음 실패를 확인하고 구현·검증을 마친 다음에만 `reference/`와 비교한다. 예제는 정답이 아니라 한 가지 현상을 고립해 보는 작은 실험이며, 예제가 없는 단계는 바로 exercise로 진행한다. 각 예제의 권장 construction order는 [`examples/README.md`](examples/README.md)에 있다.

| 순서 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 뒤 비교·다음 |
|---:|---|---|---|---|---|---|
| 0 | [학습 지도](docs/00-roadmap.md) | — | 애플리케이션 DB 또는 DBMS 내부구조 경로 선택 | — | `make check` | 아래 경로의 1단계 |

### 애플리케이션 데이터베이스 경로

| 순서 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 뒤 비교·다음 |
|---:|---|---|---|---|---|---|
| A1 | [관계 모델](docs/01-relational-semantics-and-design/01-relational-model-and-algebra.md) → [SQL 의미](docs/01-relational-semantics-and-design/02-sql-semantics-and-query-shape.md) | [`relational_algebra.py`](examples/relational_algebra.py) | [SQL 의미](exercises/01-relational-semantics-and-design/01-sql-semantics/README.md) | `exercises/01-relational-semantics-and-design/01-sql-semantics/workspace/answers.sql` | `./scripts/check-workspace.sh exercises/01-relational-semantics-and-design/01-sql-semantics` | `exercises/01-relational-semantics-and-design/01-sql-semantics/reference/answers.sql` → A2 |
| A2 | [ER·정규화·제약](docs/01-relational-semantics-and-design/03-er-normalization-and-constraints.md) | — | [스키마와 제약](exercises/01-relational-semantics-and-design/02-schema-and-constraints/README.md) | `exercises/01-relational-semantics-and-design/02-schema-and-constraints/workspace/schema.sql` | `./scripts/check-workspace.sh exercises/01-relational-semantics-and-design/02-schema-and-constraints` | `exercises/01-relational-semantics-and-design/02-schema-and-constraints/reference/schema.sql` → A3 |
| A3 | [Transaction·격리·lock](docs/03-transactions-and-recovery/01-transactions-isolation-and-locks.md) | [`transaction_anomalies.py`](examples/transaction_anomalies.py) | [PostgreSQL isolation](exercises/03-transactions-and-recovery/01-postgres-isolation/README.md) | `exercises/03-transactions-and-recovery/01-postgres-isolation/workspace/functions.sql` | `./scripts/check-workspace.sh exercises/03-transactions-and-recovery/01-postgres-isolation` | `exercises/03-transactions-and-recovery/01-postgres-isolation/reference/functions.sql` → A4 |
| A4 | [통계·비용·EXPLAIN](docs/04-execution-and-optimization/02-statistics-cost-model-and-explain.md) | [`index_cost_simulator.py`](examples/index_cost_simulator.py) | [실행 계획과 인덱스](exercises/04-execution-and-optimization/02-query-plans-and-indexes/README.md) | `exercises/04-execution-and-optimization/02-query-plans-and-indexes/workspace/indexes.sql` | `./scripts/check-workspace.sh exercises/04-execution-and-optimization/02-query-plans-and-indexes` | `exercises/04-execution-and-optimization/02-query-plans-and-indexes/reference/indexes.sql` → A5 |
| A5 | [Schema·index·migration loop](docs/04-execution-and-optimization/03-schema-index-and-tuning-loop.md) | — | [안전한 migration](exercises/04-execution-and-optimization/03-safe-migration-and-backfill/README.md) | `exercises/04-execution-and-optimization/03-safe-migration-and-backfill/workspace/migration.sql` | `./scripts/check-workspace.sh exercises/04-execution-and-optimization/03-safe-migration-and-backfill` | `exercises/04-execution-and-optimization/03-safe-migration-and-backfill/reference/migration.sql` → A6 |
| A6 | [Application DB review](docs/05-capstones/01-application-database-review.md) | — | [Ticketing DB capstone](exercises/05-capstones/01-application-database-review/README.md) | `exercises/05-capstones/01-application-database-review/workspace/`의 SQL 4개와 검토 문서 | `./scripts/check-workspace.sh exercises/05-capstones/01-application-database-review` | `exercises/05-capstones/01-application-database-review/reference/` → 애플리케이션 경로 종료 |

### DBMS 내부구조 경로

| 순서 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 뒤 비교·다음 |
|---:|---|---|---|---|---|---|
| B1 | [관계 모델](docs/01-relational-semantics-and-design/01-relational-model-and-algebra.md) | [`relational_algebra.py`](examples/relational_algebra.py) | 예제의 선택·사영·조인 결과 관찰 | — | `python3 examples/relational_algebra.py` | — → B2 |
| B2 | [페이지와 레코드](docs/02-storage-and-indexes/01-pages-records-and-files.md) | [`slotted_page.py`](examples/slotted_page.py) | [Slotted page](exercises/02-storage-and-indexes/01-slotted-page/README.md) | `exercises/02-storage-and-indexes/01-slotted-page/workspace/slotted_page.py` | `./scripts/check-workspace.sh exercises/02-storage-and-indexes/01-slotted-page` | `exercises/02-storage-and-indexes/01-slotted-page/reference/slotted_page.py` → B3 |
| B3 | [인덱스 구조](docs/02-storage-and-indexes/02-index-structures.md) | [`index_cost_simulator.py`](examples/index_cost_simulator.py) | [B+ tree](exercises/02-storage-and-indexes/02-bplus-tree/README.md) | `exercises/02-storage-and-indexes/02-bplus-tree/workspace/bplus_tree.py` | `./scripts/check-workspace.sh exercises/02-storage-and-indexes/02-bplus-tree` | `exercises/02-storage-and-indexes/02-bplus-tree/reference/bplus_tree.py` → B4 |
| B4 | [Buffer pool](docs/02-storage-and-indexes/03-buffer-pool-and-replacement.md) | [`buffer_pool.py`](examples/buffer_pool.py) | [Clock buffer pool](exercises/02-storage-and-indexes/03-buffer-pool-clock/README.md) | `exercises/02-storage-and-indexes/03-buffer-pool-clock/workspace/buffer_pool.py` | `./scripts/check-workspace.sh exercises/02-storage-and-indexes/03-buffer-pool-clock` | `exercises/02-storage-and-indexes/03-buffer-pool-clock/reference/buffer_pool.py` → B5 |
| B5 | [Transaction·격리·lock](docs/03-transactions-and-recovery/01-transactions-isolation-and-locks.md) | [`transaction_anomalies.py`](examples/transaction_anomalies.py) | [PostgreSQL isolation](exercises/03-transactions-and-recovery/01-postgres-isolation/README.md) | `exercises/03-transactions-and-recovery/01-postgres-isolation/workspace/functions.sql` | `./scripts/check-workspace.sh exercises/03-transactions-and-recovery/01-postgres-isolation` | `exercises/03-transactions-and-recovery/01-postgres-isolation/reference/functions.sql` → B6 |
| B6 | [MVCC·WAL·복구](docs/03-transactions-and-recovery/02-mvcc-wal-and-recovery.md) | [`wal_recovery.py`](examples/wal_recovery.py) | [WAL recovery](exercises/03-transactions-and-recovery/02-wal-recovery/README.md) | `exercises/03-transactions-and-recovery/02-wal-recovery/workspace/recovery.py` | `./scripts/check-workspace.sh exercises/03-transactions-and-recovery/02-wal-recovery` | `exercises/03-transactions-and-recovery/02-wal-recovery/reference/recovery.py` → B7 |
| B7 | [질의 실행](docs/04-execution-and-optimization/01-query-execution-joins-and-sorting.md) | [`join_algorithms.py`](examples/join_algorithms.py) | [Join algorithms](exercises/04-execution-and-optimization/01-join-algorithms/README.md) | `exercises/04-execution-and-optimization/01-join-algorithms/workspace/joins.py` | `./scripts/check-workspace.sh exercises/04-execution-and-optimization/01-join-algorithms` | `exercises/04-execution-and-optimization/01-join-algorithms/reference/joins.py` → B8 |
| B8 | [통계·비용·EXPLAIN](docs/04-execution-and-optimization/02-statistics-cost-model-and-explain.md) | [`index_cost_simulator.py`](examples/index_cost_simulator.py) | [실행 계획과 인덱스](exercises/04-execution-and-optimization/02-query-plans-and-indexes/README.md) | `exercises/04-execution-and-optimization/02-query-plans-and-indexes/workspace/indexes.sql` | `./scripts/check-workspace.sh exercises/04-execution-and-optimization/02-query-plans-and-indexes` | `exercises/04-execution-and-optimization/02-query-plans-and-indexes/reference/indexes.sql` → B9 |
| B9 | [Mini storage engine](docs/05-capstones/02-mini-storage-engine.md) | — | [Mini storage capstone](exercises/05-capstones/02-mini-storage-engine/README.md) | `exercises/05-capstones/02-mini-storage-engine/workspace/mini_storage.py` | `./scripts/check-workspace.sh exercises/05-capstones/02-mini-storage-engine` | `exercises/05-capstones/02-mini-storage-engine/reference/mini_storage.py` → DBMS 경로 종료 |

### 두 경로를 모두 마친 뒤

| 순서 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 뒤 비교·다음 |
|---:|---|---|---|---|---|---|
| C1 | [시스템 종합 검토](docs/90-system-review.md) | — | 두 capstone의 논리·물리·동시성·복구 계약을 함께 설명 | 완료한 두 `workspace/` | `VERIFY_LOG=/tmp/database-systems-verify.log make verify` | 두 capstone `reference/` 재검토 → 가이드 종료 또는 연결 가이드 |

## 작업 공간

연습의 `skeleton/`은 canonical start와 지정 실패를 보존하는 자료이므로 직접 수정하지 않는다. 다음 명령으로 learner-owned `workspace/`를 만들어 그 안만 수정한다.

```bash
./scripts/new-workspace.sh exercises/02-storage-and-indexes/01-slotted-page
```

생성된 `workspace/`는 Git에서 제외된다.

```bash
./scripts/check-workspace.sh exercises/02-storage-and-indexes/01-slotted-page
```

workspace 도구는 manifest에 등록된 exercise만 허용하고 경로 탈출, symlink와 필수 파일 누락을 거부한다.
새 workspace는 의도된 학습 계약에서 실패한다. 구현을 고친 뒤 같은 `check-workspace.sh` 명령이 공용 `tests/`를 통과해야 완료다.
