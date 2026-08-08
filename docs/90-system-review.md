# Database Systems 종합 검토

## 학습 목표

이 문서는 새로운 기능을 추가하는 장이 아니다. 앞선 두 경로를 하나의 데이터베이스 요청과 장애 시나리오로 연결해 다음을 검증한다.

- 논리 데이터 계약과 물리 저장 계약을 분리하면서 연결한다.
- SQL 결과 의미와 실행 plan을 같은 설명 안에 둔다.
- schema constraint, transaction, lock, MVCC와 WAL의 책임 경계를 구분한다.
- index와 buffer pool이 읽기·쓰기·복구 비용에 미치는 영향을 추적한다.
- migration과 운영 장애에서 어떤 증거를 먼저 수집할지 정한다.
- 현재 가이드가 보장하지 않는 범위를 명시한다.

## 종합 질문: 요청 하나를 끝까지 추적한다

다음 API가 있다고 가정한다.

```text
POST /organizations/7/projects/3/tickets
```

입력:

```json
{
  "title": "checkout timeout",
  "assigneeId": 19,
  "priority": "HIGH"
}
```

데이터베이스 관점에서 다음 순서로 설명한다.

### 1. 논리 계약

- ticket의 식별자는 무엇인가?
- project 안에서 ticket 번호는 어떻게 유일한가?
- assignee가 조직의 활성 member라는 규칙은 어디서 보장하는가?
- `NULL`을 허용하는 column은 어떤 의미인가?
- 성공 후 새 상태와 실패 시 상태는 무엇인가?

### 2. SQL과 transaction

- 몇 개 statement가 필요한가?
- 하나의 조건부 statement로 줄일 수 있는 판단은 무엇인가?
- 동시에 membership이 비활성화되면 어떻게 되는가?
- unique conflict, serialization failure와 deadlock을 어떻게 분류하는가?
- retry해도 안전한 operation 경계는 어디인가?

### 3. 물리 저장

- insert되는 row와 index entry는 무엇인가?
- 어떤 heap page가 buffer pool에 들어오는가?
- page에 공간이 없으면 어떤 일이 생기는가?
- B+ tree leaf split이 발생할 수 있는 index는 무엇인가?
- tuple과 index entry의 RID 연결은 어떻게 유지되는가?

### 4. WAL과 commit

- 어떤 변경이 WAL에 기록되는가?
- dirty page를 쓰기 전에 무엇이 stable해야 하는가?
- commit 성공을 반환하기 전에 무엇이 flush되어야 하는가?
- data page flush 전 crash하면 어떤 record를 redo하는가?
- client가 commit 결과를 받지 못하면 application은 어떻게 결과를 확인하는가?

### 5. 조회와 실행 plan

다음 query를 생각한다.

```sql
SELECT id, title, priority, updated_at
FROM tickets
WHERE organization_id = 7
  AND project_id = 3
  AND status = 'OPEN'
ORDER BY priority DESC, updated_at DESC, id DESC
LIMIT 50;
```

- 정렬이 완전하고 안정적인가?
- composite index 후보와 partial index 후보는 무엇인가?
- tenant·project·status 분포가 추정에 어떤 영향을 주는가?
- index scan과 sequential scan 중 하나를 선택할 근거는 무엇인가?
- `EXPLAIN ANALYZE, BUFFERS`에서 어떤 node와 실제 row를 확인하는가?

### 6. Migration

`severity`를 필수 column으로 추가한다.

- expand 단계에서 이전 application이 계속 쓸 수 있는가?
- backfill cursor와 batch key는 무엇인가?
- 신규 write와 backfill이 같은 row를 다룰 때 우선순위는 무엇인가?
- constraint를 언제 validate하는가?
- contract 단계 전에 어떤 배포 상태를 확인하는가?
- 실패 시 rollback과 roll-forward 중 어느 경로를 택하는가?

## 장애 시나리오 검토

### 느린 조회

증상:

```text
특정 큰 조직의 OPEN ticket query p95가 급증했다.
```

수집 순서:

1. 실제 parameter와 결과 row 수
2. query ID와 호출 빈도
3. `EXPLAIN (ANALYZE, BUFFERS)`
4. 추정과 실제 row 차이
5. table/index 크기와 통계 시점
6. lock wait, temp spill와 concurrent workload
7. 최근 schema·data 분포 변경

처방을 먼저 정하지 않는다. Stale statistics, skew, missing index, deep offset, lock wait와 I/O saturation은 서로 다른 문제다.

### Deadlock

수집:

- involved transaction과 SQL
- 획득한 lock 순서
- 업무 key
- transaction 시작·종료 시각
- retry 여부

수정:

- 공통 lock ordering
- transaction 범위 축소
- 조건부 single statement
- 업무 key별 명시적 conflict 지점

모든 deadlock을 timeout 증가로 숨기지 않는다.

### Disk 사용량 급증

후보:

- 오래 열린 snapshot으로 vacuum 지연
- WAL 보존 증가
- index bloat
- 대량 backfill
- temp sort/hash spill
- backup 또는 replica lag

Table 크기 하나만 보지 않고 heap, index, WAL, temp와 보존 요구를 나눈다.

### Crash 뒤 startup 지연

확인:

- checkpoint 이후 WAL 범위
- redo 속도
- storage I/O
- recovery target
- replica와 backup 상태
- 반복 crash 여부

Recovery 중 강제 재시작은 진행을 되돌리거나 반복 작업을 늘릴 수 있다. 현재 단계와 증거를 확인한다.

## 계층별 불변식 표

| 계층 | 핵심 불변식 | 대표 실패 | 검증 |
|---|---|---|---|
| 관계·SQL | 결과 row 단위·중복·NULL·순서 | 누락·중복·불안정 page | 결과 fixture |
| Schema | key·참조·상태 범위 | orphan·중복 업무 key | invalid insert |
| Page | slot·free space·record 경계 | 손상·RID 불안정 | serialize round-trip |
| Index | 정렬·검색·RID 일치 | 누락·stale entry | full scan 비교 |
| Buffer | pin·dirty·frame mapping | pinned eviction·lost write | deterministic access |
| Transaction | 상태 전이 atomicity | lost update·write skew | concurrent clients |
| WAL | write-ahead·LSN 순서 | committed loss·dirty uncommitted | crash matrix |
| Executor | bag·NULL·operator 수명 | 잘못된 join multiplicity | 알고리즘 교차 비교 |
| Optimizer | 추정·비용의 근거 | bad join order·spill | estimate/actual diff |
| Migration | 혼합 버전 호환 | 장시간 lock·중간 상태 불일치 | 단계별 재실행 |

## 두 capstone의 차이

### Application database review

질문:

> 업무 계약을 DB schema·query·transaction·migration으로 어떻게 내릴 것인가?

주요 증거:

- SQL 결과
- constraint 실패
- 실제 PostgreSQL transaction
- EXPLAIN
- migration 단계

### Mini storage engine

질문:

> DBMS가 그 계약을 page·buffer·index·WAL로 어떻게 실행하고 복구하는가?

주요 증거:

- Python 불변식 test
- page serialization
- deterministic eviction
- WAL flush 순서
- crash recovery

한쪽만 수행해도 독립된 종료 능력이 있다. 두 경로를 모두 수행하면 ORM·SQL·실행 계획·storage 장애를 같은 시스템 모델로 연결할 수 있다.

## 보장하지 않는 범위

이 가이드 완료가 다음을 자동으로 의미하지 않는다.

- 특정 DBMS의 모든 lock mode와 내부 구현 숙련
- production backup·restore 운영 경험
- 대규모 cluster·replication 설계
- 분산 consistency와 saga 설계
- 모든 workload에 대한 성능 예측
- PostgreSQL source code 수준의 구현 이해

다음 단계는 목적에 따라 선택한다.

- 애플리케이션 통합: `guide-backend-spring-boot`
- 공개 DB 운영·backup·monitoring: `guide-web-infrastructure`
- 서비스별 데이터 소유권·Outbox·Saga: `guide-distributed-services`
- DBMS source·research paper: 별도 심화 과정

## 연결 연습

최종 검증은 두 capstone을 모두 실행한다.

- [`Application database review`](../exercises/05-capstones/01-application-database-review/README.md)
- [`Mini storage engine`](../exercises/05-capstones/02-mini-storage-engine/README.md)

그리고 저장소 루트에서 다음을 실행한다.

```bash
./prepare.sh
./verify.sh
```

`verify.sh`는 문서 링크, reference/skeleton 계약, Python 내부구조와 실제 PostgreSQL 통합 연습을 한 번에 검사한다.

## 완료 기준

다음 형식의 종합 설명을 작성할 수 있어야 한다.

```text
업무 불변식
→ schema와 query 결과 계약
→ transaction과 concurrency conflict
→ page·index·buffer 변화
→ WAL과 commit 경계
→ crash recovery
→ 조회 physical plan
→ 통계와 index 선택
→ migration과 운영 검증
```

설명에는 반드시 다음이 포함되어야 한다.

- 각 계층의 주 소유자
- 정상 상태뿐 아니라 실패 후 상태
- 자동 검증으로 증명한 범위
- 현재 모델이 보장하지 않는 범위
- 성능 주장에 사용한 환경과 workload

이 조건을 만족하면 데이터베이스를 단순한 저장 API가 아니라 **논리 의미, 동시성, 물리 저장과 복구가 결합된 상태 기계**로 다룰 준비가 된 것이다.
