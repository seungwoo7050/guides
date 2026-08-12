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

## 시작

```bash
./scripts/new-workspace.sh exercises/04-execution-and-optimization/03-safe-migration-and-backfill
```

직접 수정할 파일은 `workspace/migration.sql`이다. 최초 실패와 두 번 적용 결과를 같은 workspace 검증으로 확인한다.

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

## 권장 구현 순서

아래 번호는 `reference/migration.sql` 전체의 권장 construction order다. 과거 이력이 아니며, workspace를 두 번 적용해 통과한 뒤 reference의 단계 주석과 비교한다.

| 순서 | 파일·단계 | 책임 |
|---:|---|---|
| 1 | expand | nullable column을 재실행 가능하게 추가 |
| 2 | backfill | legacy state를 새 값으로 정규화 |
| 3 | constraint creation | NOT VALID write boundary |
| 4 | validate·contract | 기존 row 검증 뒤 NOT NULL 전환 |
| 5 | access path | 최종 상태 조회 index |

## 검증

`make prepare` 뒤 workspace migration의 두 번 적용과 음성 insert를 실제 PostgreSQL에서 검사한다.

```bash
./scripts/check-workspace.sh exercises/04-execution-and-optimization/03-safe-migration-and-backfill
```

초기 skeleton은 `GUIDE_SEMANTIC:migration-backfill-order`에서 실패하고, expand·backfill·validate·contract 순서를 완성하면 같은 명령이 통과해야 한다.
