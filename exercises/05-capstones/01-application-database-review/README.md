# Application database review capstone

멀티 조직 ticketing 서비스의 스키마, 업무 질의, 인덱스와 호환 migration을 하나의 검토 단위로 완성한다.

## 검토 대상

- 조직 경계를 넘는 참조를 데이터베이스가 거부하는가
- ticket 상태와 `closed_at` 조합이 일관적인가
- 프로젝트 backlog와 담당자 queue 질의의 행 단위가 명확한가
- 대표 질의의 필터·정렬에 맞는 인덱스가 있는가
- `severity`에서 `priority`로 이동할 때 기존 데이터와 혼합 버전을 보존하는가
- 잘못된 상태를 테스트가 실제로 삽입해 보고 거부 여부를 확인하는가

## 파일

```text
schema.sql     최초 스키마와 제약
migration.sql  priority 확장·backfill·검증
queries.sql    검토 대상 view
indexes.sql    대표 workload 인덱스
```

설계 지침: [`docs/05-capstones/01-application-database-review.md`](../../../docs/05-capstones/01-application-database-review.md)

## 검증 계약

reference의 migration은 중단 뒤 다시 적용해도 같은 최종 상태를 만들며, 루트 검증은 이를 두 번 실행해 확인한다.
