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

## 작업 공간

연습의 `skeleton/`을 직접 수정하지 않고 별도 작업 공간을 만들 수 있다.

```bash
./scripts/new-workspace.sh exercises/02-storage-and-indexes/01-slotted-page
```

생성된 `workspace/`는 Git에서 제외된다.

```bash
./scripts/check-workspace.sh exercises/02-storage-and-indexes/01-slotted-page
```

workspace 도구는 manifest에 등록된 exercise만 허용하고 경로 탈출, symlink와 필수 파일 누락을 거부한다.
새 workspace는 의도된 학습 계약에서 실패한다. 구현을 고친 뒤 같은 `check-workspace.sh` 명령이 공용 `tests/`를 통과해야 완료다.
