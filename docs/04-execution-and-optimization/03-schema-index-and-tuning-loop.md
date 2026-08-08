# Schema, index와 안전한 tuning loop

## 학습 목표

이 문서를 마치면 다음을 설명할 수 있어야 한다.

- 성능 변경 전에 업무 불변식과 대표 workload를 먼저 고정하는 이유
- schema constraint, query rewrite, index, denormalization의 선택 순서
- composite index column 순서를 equality·range·ordering과 연결하는 방법
- partial·covering·expression index의 적용 조건과 숨은 비용
- expand/backfill/validate/contract migration이 혼합 버전 배포를 안전하게 하는 방식
- 큰 table의 backfill과 index build가 lock·WAL·replica에 미치는 영향
- rollback과 roll-forward를 구분하는 이유
- tuning 결과를 correctness·latency·write cost·운영 복구로 검증하는 방법

## 선행지식

[`스키마·정규화·제약`](../01-relational-semantics-and-design/03-er-normalization-and-constraints.md), [`통계·비용 모델과 EXPLAIN`](02-statistics-cost-model-and-explain.md)을 먼저 읽는다. transaction과 lock 영향은 [`Transaction, 격리와 lock`](../03-transactions-and-recovery/01-transactions-isolation-and-locks.md)을 참고한다.

## Tuning은 느린 SQL 한 줄을 고치는 일이 아니다

변경의 출발점은 다음 네 계약이다.

```text
업무 불변식
대표 workload
성공 지표
허용 가능한 쓰기·운영 비용
```

예:

```text
불변식: 같은 조직 안에서 project slug는 유일함
workload: 조직별 OPEN ticket를 최근 갱신순으로 50개 조회
성공: p95 < 50ms, 결과 순서 안정
비용 한도: ticket insert p95 증가 < 5ms, index < 2GB
```

이 계약 없이 “인덱스를 추가한다”부터 시작하면 조회 하나는 빨라져도 write, vacuum, migration과 장애 복구가 악화될 수 있다.

## 먼저 의미 오류를 제거한다

성능보다 다음을 먼저 확인한다.

- query가 올바른 row 단위를 반환하는가
- `NULL`, outer join과 중복 의미가 맞는가
- 정렬이 완전하고 안정적인가
- schema가 잘못된 상태를 거부하는가
- transaction이 동시 실행에서도 불변식을 보존하는가

틀린 query를 빠르게 만드는 것은 개선이 아니다. 애플리케이션에서 중복 제거하거나 누락을 보정하는 코드가 있으면 DB 계약이 불명확한 신호일 수 있다.

## 대표 workload를 기록한다

한 table에 대한 “CRUD”만 적지 않는다.

```text
query ID
호출 빈도
parameter 분포
반환 row 수
허용 latency
transaction 범위
동시에 실행되는 write
정렬·pagination 계약
```

평균값 하나보다 분포를 기록한다.

- 작은 tenant와 큰 tenant
- 최근 날짜와 오래된 날짜
- 흔한 status와 드문 status
- cold cache와 warm cache
- 평시와 batch 동시 실행

## Schema부터 검토한다

### 타입과 domain

값 범위와 연산에 맞는 타입을 사용한다. 숫자를 text로 저장하면 ordering, validation과 index 비용이 달라진다. timestamp의 timezone 의미, monetary decimal의 scale, identifier의 비교 규칙을 명확히 한다.

### Key와 constraint

Unique·foreign key·check는 정확성뿐 아니라 옵티마이저 정보다. 그러나 constraint 추가는 기존 데이터 검증과 lock을 요구할 수 있다.

### Row 폭과 hot update

자주 읽고 갱신하는 row에 큰 payload를 함께 두면 page density와 cache 효율이 낮아질 수 있다. 서로 다른 수명과 접근 패턴을 가진 data를 분리할 수 있다.

반대로 무조건 table을 잘게 나누면 join과 transaction 복잡도가 증가한다. 대표 workload로 판단한다.

## Query rewrite

Index 전에 query shape를 정리할 수 있다.

- 필요한 column만 반환한다.
- N+1 query를 명시적 join 또는 batch로 바꾼다.
- 동일한 correlated subquery를 반복하지 않는다.
- `OFFSET`이 깊어지는 pagination을 keyset pagination으로 바꾼다.
- index column에 불필요한 함수를 적용하지 않는다.
- predicate가 논리적으로 같은지 검증한 뒤 sargable 형태로 바꾼다.

Keyset pagination 예:

```sql
WHERE (updated_at, id) < (:last_updated_at, :last_id)
ORDER BY updated_at DESC, id DESC
LIMIT 50;
```

정렬 key는 동률을 깨는 unique column까지 포함해야 page 사이 중복·누락을 줄일 수 있다.

## Composite index 순서

일반적인 사고 순서는 다음이다.

```text
항상 equality로 고정되는 prefix
→ 선택적인 range
→ 요구 ordering
→ 반환에 필요한 include column
```

예:

```sql
WHERE tenant_id = $1
  AND status = 'OPEN'
  AND updated_at < $2
ORDER BY updated_at DESC, id DESC
LIMIT 50;
```

후보:

```sql
CREATE INDEX ...
ON tickets (tenant_id, status, updated_at DESC, id DESC);
```

하지만 `status='OPEN'`이 대부분 row라면 column 순서와 partial index를 다시 검토해야 한다. 공식처럼 적용하지 말고 실제 분포와 plan을 본다.

## Partial index

조건을 만족하는 row만 index에 넣는다.

```sql
CREATE INDEX ... ON jobs (scheduled_at, id)
WHERE completed_at IS NULL;
```

장점:

- 크기 감소
- hot subset 조회 개선
- write 부담 감소 가능

제약:

- query predicate가 partial 조건을 논리적으로 증명해야 한다.
- parameterized predicate와 표현 차이 때문에 사용되지 않을 수 있다.
- 상태 변화 시 index entry insert/delete가 발생한다.

## Covering index와 `INCLUDE`

검색·정렬 key가 아닌 반환 column을 leaf에 포함해 index-only scan 가능성을 높일 수 있다.

```sql
CREATE INDEX ... ON events (tenant_id, created_at DESC, id DESC)
INCLUDE (event_type, actor_id);
```

포함 column도 공간과 write 비용을 만든다. 자주 바뀌거나 큰 column을 무분별하게 포함하지 않는다. Visibility map 상태와 heap fetch도 함께 측정한다.

## Expression index

Query가 동일한 표현을 사용할 때 유용하다.

```sql
CREATE UNIQUE INDEX users_email_lower_uq
ON users (lower(email));
```

다음 계약을 함께 고정한다.

- 대소문자 정규화 정책
- locale/collation
- application validation과 DB constraint 일치
- query가 같은 표현을 사용하는지

표현 index는 원본 column 의미의 모호함을 해결하지 않는다. 가능하면 domain 정책을 schema에 명확히 둔다.

## 인덱스의 쓰기 비용

각 insert, delete와 key column update는 index도 바꾼다.

- WAL 증가
- page split
- cache pressure
- vacuum 비용
- backup·restore 크기
- migration 시간
- replica lag

사용되지 않는 index도 비용을 낸다. 사용 횟수만으로 즉시 삭제하지 말고, constraint 지원·장애 대응·월간 batch 같은 드문 workload를 확인한다.

## Denormalization

측정된 병목과 재생성 계약이 있을 때만 선택한다.

예:

```text
project.open_ticket_count를 별도 저장
```

필수 질문:

- 같은 transaction에서 갱신되는가
- event로 비동기 갱신되는가
- 누락·중복을 어떻게 탐지하는가
- source of truth는 무엇인가
- 전체 재계산 방법은 무엇인가
- 불일치 허용 시간은 얼마인가

이 질문에 답하지 못하면 읽기 비용을 데이터 불일치 위험으로 바꾼 것이다.

## Migration은 혼합 버전 시스템 변경이다

운영 배포에서는 이전 application과 새 application이 잠시 함께 실행될 수 있다. migration은 단일 SQL 파일이 아니라 compatibility 단계다.

### Expand

새 schema를 기존 코드와 호환되게 추가한다.

- nullable column 추가
- 새 table 추가
- 새 index 준비
- 이전·새 column 동시 지원

### Backfill

기존 row를 작은 batch로 채운다.

- stable key 순서
- batch 크기
- transaction 수명
- pause/resume cursor
- retry idempotence
- write 경쟁과 replica lag

### Validate

새 불변식이 모든 row에서 참인지 확인한다.

- `CHECK ... NOT VALID` 후 별도 validate 같은 전략
- null·중복·orphan row 확인
- application dual-write 또는 read path 검증

### Contract

모든 실행 중인 application이 새 schema만 사용한다고 확인한 뒤 이전 column·table·호환 코드를 제거한다.

```text
expand와 contract를 같은 배포에 묶지 않는다.
```

## `NOT NULL` 추가 예시

큰 table에 값이 없는 새 column을 즉시 `NOT NULL`로 추가하면 기존 row 때문에 실패하거나 긴 검증이 필요할 수 있다.

안전한 흐름:

```text
1. nullable column 추가
2. 새 write가 값을 채우게 배포
3. 기존 row batch backfill
4. NULL 0개 검증
5. constraint validate
6. NOT NULL 고정
7. 임시 호환 코드 제거
```

각 단계는 다시 실행해도 안전해야 하고, 중간 상태에서 이전 application이 계속 작동해야 한다.

## Index build와 lock

운영 DB에서 일반 `CREATE INDEX`는 write를 오래 막을 수 있다. PostgreSQL의 concurrent build 같은 기능은 blocking을 줄이지만 더 오래 걸리고, 실패 시 invalid index 정리가 필요할 수 있다.

계획에 다음을 포함한다.

- 예상 table/index 크기
- 필요한 disk 여유
- WAL과 replica 영향
- statement/lock timeout
- 실패 시 invalid object 확인
- 중복 실행 방지
- 완료 뒤 통계 갱신과 plan 확인

구체 문법과 제약은 사용하는 DBMS 버전의 문서를 확인해야 한다.

## Rollback과 roll-forward

Schema 변경은 항상 단순 rollback이 가능하지 않다.

- column drop 뒤 데이터를 즉시 되살릴 수 없음
- backfill이 외부 효과와 연결됨
- 새 application이 새 형식으로 쓰기 시작함
- index build는 재시도하는 편이 안전함

각 단계에 다음 중 하나를 지정한다.

```text
되돌릴 수 있음
앞으로 수정해야 함
복원에서만 되돌릴 수 있음
```

Migration 전 backup이 있다는 사실만으로 즉시 rollback 가능한 것은 아니다. restore 시간과 데이터 손실 범위를 알아야 한다.

## Tuning loop

전체 절차를 고정한다.

```text
1. 업무 불변식과 query 의미 고정
2. workload와 parameter 분포 수집
3. EXPLAIN ANALYZE·BUFFERS로 기준선 기록
4. 가장 큰 비용 또는 추정 오차 가설 작성
5. 변경 하나 적용
6. correctness와 concurrency 재검증
7. latency·I/O·memory·write 비용 비교
8. migration·rollback·관측 계획 작성
9. production 제한 배포
10. 결과 기록과 불필요 변경 제거
```

여러 index와 query rewrite를 한 번에 적용하면 어떤 변경이 효과를 냈는지 알기 어렵다. 실험 단위를 작게 유지한다.

## 연결 연습

두 연습을 수행한다.

1. [`Query plans and indexes`](../../exercises/04-execution-and-optimization/02-query-plans-and-indexes/README.md)
   - 대표 query와 ordering 계약
   - composite·partial·covering index
   - 실제 plan 비교

2. [`Safe migration and backfill`](../../exercises/04-execution-and-optimization/03-safe-migration-and-backfill/README.md)
   - expand
   - idempotent batch backfill
   - constraint validation
   - contract 전 안전 상태
   - 잘못된 즉시 `NOT NULL` 변경이 실패하는지

## 완료 기준

다음 산출물을 하나의 변경 제안서로 작성할 수 있어야 한다.

- 정확한 업무 불변식과 query 결과 계약
- 대표 parameter 분포와 기준 plan
- 선택한 schema/query/index 변경의 가설
- 읽기 성능뿐 아니라 쓰기·공간 비용
- 혼합 버전에서도 안전한 migration 단계
- retry·재개 가능한 backfill
- 실패 시 rollback 또는 roll-forward 경로
- 변경 전후 correctness·concurrency·성능 증거

이제 애플리케이션 경로는 [`Application database review`](../05-capstones/01-application-database-review.md)에서 전체 계약을 통합한다. 내부구조 경로는 [`Mini storage engine`](../05-capstones/02-mini-storage-engine.md)으로 이어진다.
