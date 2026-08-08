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
