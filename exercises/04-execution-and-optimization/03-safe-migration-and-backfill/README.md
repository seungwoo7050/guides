# 안전한 migration과 backfill

데이터가 이미 존재하는 `orders`에 새 `status` 계약을 추가한다. 한 번에 `NOT NULL` 컬럼을 추가하는 대신 expand → backfill → validate → contract 순서를 사용한다.

## 완료 상태

- 기존 `legacy_state`는 호환 기간 동안 남아 있다.
- `status`는 모든 기존 행에서 채워져 있다.
- 허용 값은 `NEW`, `PAID`, `CANCELLED`뿐이다.
- `status`는 `NOT NULL`이다.
- 상태별 조회를 위한 인덱스가 있다.
- 잘못된 상태와 `NULL` insert는 데이터베이스가 거부한다.

문서: [`docs/04-execution-and-optimization/03-schema-index-and-tuning-loop.md`](../../../docs/04-execution-and-optimization/03-schema-index-and-tuning-loop.md)

## 검증 계약

reference의 migration은 중단 뒤 다시 적용해도 같은 최종 상태를 만들며, 루트 검증은 이를 두 번 실행해 확인한다.

## 목표

기존 write와 혼합 버전을 허용하면서 expand, backfill, validate, contract 단계를 재실행 가능한 SQL로 구성한다.

## 완료 기준

- 기존 모든 row의 `status`가 legacy 값에서 올바르게 채워지고 허용 집합 밖 값이 없다.
- migration을 연속 두 번 실행해도 schema와 data가 같은 최종 상태를 유지한다.
- contract 뒤 `NULL`과 잘못된 상태 insert가 거부되고 상태별 index가 catalog에 남는다.

## 자기 설명

1. 기본값 있는 `NOT NULL` column을 한 단계로 추가하지 않는 이유를 lock과 배포 호환성 관점에서 설명할 수 있는가?
2. `NOT VALID` 제약을 먼저 추가하고 나중에 validate하는 방식의 운영상 이점은 무엇인가?

## 검증

`./prepare.sh` 뒤 `make postgres-check`로 두 번 적용과 음성 insert를 실제 PostgreSQL에서 검사한다.
