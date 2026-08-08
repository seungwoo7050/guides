# Application database review capstone

멀티 조직 ticketing 서비스의 스키마, 업무 질의, 인덱스와 호환 migration을 하나의 검토 단위로 완성한다.

## 검토 대상

- 조직 경계를 넘는 참조를 데이터베이스가 거부하는가
- ticket 상태와 `closed_at` 조합이 일관적인가
- 조직별 open ticket page, 담당자 queue, 프로젝트 backlog의 행 단위가 명확한가
- keyset cursor까지 포함한 명시적 `ORDER BY`와 정확히 대응하는 composite partial index가 있는가
- `severity`에서 `priority`로 이동할 때 기존 데이터와 혼합 버전을 보존하는가
- 잘못된 상태를 테스트가 실제로 삽입해 보고 거부 여부를 확인하는가

## 파일

```text
schema.sql     최초 스키마와 제약
migration.sql  priority 확장·backfill·검증
queries.sql    검토 대상 view
indexes.sql    대표 workload 인덱스
concurrency-review.md  자동화 밖의 두 session 경쟁 검토
```

설계 지침: [`docs/05-capstones/01-application-database-review.md`](../../../docs/05-capstones/01-application-database-review.md)

## 검증 계약

reference의 migration은 중단 뒤 다시 적용해도 같은 최종 상태를 만들며, 루트 검증은 이를 두 번 실행해 확인한다. 세 workload는 다음 계약을 갖는다.

- 조직별 open ticket page: `priority DESC, created_at DESC, id DESC`와 동일 tuple keyset cursor
- 담당자별 미완료 queue: `priority DESC, created_at, id`의 완전한 tie-break
- 프로젝트별 backlog: 조직·프로젝트 단위 open count와 oldest timestamp

자동 fixture는 membership 존재와 ticket 상태·tenant 경계를 검사하지만, membership 비활성화와 assignee 변경의 실제 경쟁을 흉내 내지는 않는다. `workspace/concurrency-review.md`에 두 session 순서, 허용·금지 결과, lock 또는 retry 근거와 DB/application 책임 경계를 기록한다.

## 목표

멀티 조직 경계, ticket 상태, 업무 view, workload index와 호환 migration을 하나의 검토 가능한 데이터 계약으로 완성한다.

## 완료 기준

- 다른 조직의 project·assignee를 참조하는 ticket이 복합 외래 키에서 거부된다.
- 세 workload의 tenant filter·안정적 정렬·집계 결과가 seed의 기대 행과 정확히 일치한다.
- migration 재실행 뒤 priority가 보존되고 세 `EXPLAIN` 모두 exact partial index를 실제 사용하며 `Sort`가 없다.
- 두 session 동시성 산출물에 경쟁 순서, 허용·금지 결과, lock/retry 근거와 남은 비보장 범위가 적혀 있다.

## 자기 설명

1. `(priority, created_at, id)` cursor에서 마지막 `id`가 빠지면 같은 시각·우선순위 ticket에 어떤 중복이나 누락이 생기는가?
2. membership 비활성화와 assignee 변경이 경쟁할 때 어느 row를 어떤 순서로 잠그며, DB가 보장하지 않는 부분은 어디에 두는가?

## 검증

`make prepare` 뒤 workspace의 schema·query·index·migration을 같은 PostgreSQL fixture에서 검사한다.

```bash
./scripts/check-workspace.sh exercises/05-capstones/01-application-database-review
```

초기 skeleton은 `GUIDE_SEMANTIC:capstone-idempotent-migration`에서 실패하고, 세 workload와 조직 경계·migration 계약을 완성하면 같은 명령이 통과해야 한다.
