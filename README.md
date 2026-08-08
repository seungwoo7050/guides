# Database Systems Guide

관계형 데이터베이스를 **정확한 스키마와 질의**, **저장 엔진 내부구조**, **동시성·복구**, **실행 계획과 튜닝**의 한 흐름으로 학습하는 가이드다.

이 저장소는 SQL 문법 입문서가 아니다. 간단한 테이블 생성과 `SELECT`·`INSERT`·`UPDATE`·`DELETE`를 작성해 본 독자를 대상으로 한다. 웹 애플리케이션에서 필요한 최소 SQL 이후, 데이터베이스 자체를 설계·관찰·구현하는 단계부터 시작한다.

## 시작

```bash
./prepare.sh
./verify.sh
```

- `prepare.sh`는 기존 평면 구조를 최종 구조로 정리하고, 검증에 필요한 도구와 PostgreSQL 이미지를 준비한다.
- `verify.sh`는 문서 링크, Python 예제·연습, skeleton/reference 계약, PostgreSQL 통합 실습과 capstone을 저장소 루트에서 한 번에 검사한다.

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
