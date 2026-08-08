# Capstone A: 애플리케이션 데이터베이스 검토

## 학습 목표

이 capstone은 개별 SQL 문장을 푸는 문제가 아니다. 하나의 업무 시스템에 대해 다음을 연결하는 것이 목표다.

- 업무 문장을 key·constraint·transaction으로 내리기
- SQL의 `NULL`, 중복, outer join과 ordering 의미 고정
- 동시 변경에서도 불변식 보존
- 대표 workload와 실행 계획 분석
- 측정 근거를 가진 index 설계
- 혼합 버전 배포를 고려한 migration과 backfill
- 변경 전후 correctness·성능·운영 비용 기록

## 시나리오

여러 조직이 사용하는 ticket 관리 시스템을 검토한다.

```text
조직
사용자와 조직 membership
프로젝트
프로젝트 ticket
ticket 담당자
상태와 우선순위
댓글 또는 활동 기록
```

핵심 요구 예시는 다음이다.

- project slug는 조직 안에서 유일하다.
- ticket 번호는 project 안에서 유일하다.
- 담당자는 해당 조직의 membership을 가져야 한다. 활성 상태 수명 주기를 추가한다면 그 경쟁은 별도 transaction 계약으로 검토한다.
- 닫힌 ticket을 일반 수정 경로로 다시 열 수 없다.
- 조직별 OPEN ticket 목록은 우선순위와 생성 시각, `id` 순으로 안정적으로 page된다.
- 담당자별 미완료 queue를 빠르게 조회한다.
- 새 column을 추가해 기존 ticket을 안전하게 backfill한다.

이 요구 중 일부는 단일 constraint로 표현할 수 있고, 일부는 transaction·trigger·application 경계를 함께 검토해야 한다. “DB가 모든 업무를 혼자 검사한다”와 “모든 검증을 application에 둔다” 사이에서 명시적인 책임을 정한다.

## 1단계: 용어와 row 단위를 고정한다

다음 표를 먼저 작성한다.

| 용어 | 식별자 | 수명 | 삭제 정책 | 소유 범위 |
|---|---|---|---|---|
| Organization |  |  |  |  |
| Membership |  |  |  |  |
| Project |  |  |  |  |
| Ticket |  |  |  |  |

같은 `user_id`라도 전역 사용자와 조직 membership은 다른 수명을 가진다. Ticket 담당자 권한이 전역 사용자 존재만으로 충분한지, 활성 membership이 필요한지 명확히 한다.

Query별 결과 row 단위도 적는다.

```text
조직별 OPEN ticket 목록 → ticket 한 개당 한 row
담당자 queue → 담당 ticket 한 개당 한 row
project 요약 → project 한 개당 한 row
```

Join 때문에 댓글 수만큼 ticket이 중복되면 계약 위반이다.

## 2단계: 업무 불변식을 schema로 내린다

최소한 다음을 검토한다.

- primary key
- tenant boundary를 포함한 candidate key
- foreign key
- `NOT NULL`
- `CHECK`
- composite `UNIQUE`
- 삭제와 참조 정책

Multi-tenant schema에서 전역 ID만 참조하면 다른 조직의 row를 잘못 연결할 수 있다. 가능한 경우 foreign key에 tenant key를 포함하거나, transaction에서 같은 조직임을 강제하고 테스트한다.

Constraint 이름은 오류 분류와 운영 진단에 사용할 수 있게 의미 있게 정한다.

## 3단계: Query 의미를 검증한다

다음 실패를 의도적으로 넣고 테스트한다.

- `NOT IN` subquery에 `NULL`
- LEFT JOIN 뒤 `WHERE`가 unmatched row를 제거
- 댓글 join으로 ticket 중복
- `ORDER BY updated_at` 동률에서 page 순서 불안정
- `count(column)`이 `NULL`을 제외
- 조직 filter 누락

Reference query는 결과만 맞으면 끝나지 않는다. 반환 column, 중복, 정렬과 tenant 범위를 문장으로 설명해야 한다.

## 4단계: Transaction 경계를 검토한다

예를 들어 담당자 변경은 다음을 함께 수행할 수 있다.

```text
활성 membership 확인
현재 ticket 상태 확인
assignee 변경
activity 기록
updated_at 갱신
```

동시에 membership이 비활성화되거나 ticket이 닫힐 수 있다. 단순히 transaction 안에서 두 번 `SELECT`하는 것만으로 충분한지 검토한다.

- 같은 row update에서 조건부 변경으로 모을 수 있는가
- lock ordering이 필요한가
- unique constraint가 경쟁을 해결하는가
- serializable retry가 필요한가
- 외부 알림은 transaction 밖에서 어떻게 전달하는가

자동 SQL fixture는 membership 존재와 tenant foreign key를 검사하지만, 축소 schema에는 membership 활성 상태나 activity table이 없다. 따라서 비활성화와 담당자 변경 경쟁을 자동 검증했다고 주장하지 않는다. Exercise의 `concurrency-review.md`에 두 session 순서, 허용·금지 결과, 일관된 lock 순서, bounded retry와 DB/application 책임 경계를 수동 근거로 남긴다.

## 5단계: 대표 workload와 index

최소 세 query를 기준선으로 삼는다.

```text
조직·상태별 ticket 목록 + 안정적 keyset pagination
담당자별 미완료 queue
project별 상태 집계
```

조직 목록의 canonical 순서는 `priority DESC, created_at DESC, id DESC`다. 다음 page는 마지막 row와 같은 tuple을 cursor로 삼아 `(priority, created_at, id) < (...)`를 적용한다. `id`까지 넣어 동률의 중복·누락을 막고, `ORDER BY`는 view 밖의 실제 호출 query에도 항상 명시한다. 담당자 queue는 `priority DESC, created_at, id`를 사용한다.

각 query에 대해 다음을 기록한다.

- 호출 빈도
- tenant 크기 분포
- 반환 row 수
- filter·join·ordering
- 현재 plan
- 실제 rows와 buffers
- 허용 latency

그 다음 composite, partial 또는 covering index를 제안한다. Index 하나가 여러 query를 완벽하게 해결할 것이라고 가정하지 않는다.

## 6단계: 안전한 migration

새 요구로 `tickets.severity` 같은 필수 column을 추가한다고 가정한다.

권장 흐름:

```text
nullable column 추가
→ 새 write path가 severity 기록
→ 기존 row batch backfill
→ 유효 값 constraint
→ NULL 0개 검증
→ NOT NULL
→ 이전 호환 경로 제거
```

Backfill은 다음 계약을 가진다.

- stable key 순서
- 작은 transaction batch
- 재실행 가능
- 중간 중단 뒤 재개 가능
- 신규 write와 충돌하지 않음
- 진행률과 오류 row 관찰 가능

Exercise는 작게 실행되지만, 설계 문서에는 실제 큰 table에서의 lock, WAL, replica와 disk 영향을 적는다.

## 7단계: 검증 근거

최종 제출은 코드만이 아니다.

```text
schema 불변식 표
query 결과 계약
동시성 위험과 해결 경계
index 전후 EXPLAIN 근거
migration 단계
실패·복구 경로
남은 비보장 범위
```

잘못된 상태 insert가 실제로 실패하고, skeleton의 불완전한 schema/query/migration이 검사를 통과하지 못해야 한다.

## 연결 연습

[`Application database review`](../../exercises/05-capstones/01-application-database-review/README.md)에서 ticketing schema를 완성한다.

- 조직 경계를 가진 key·foreign key·constraint
- 대표 조회 view/query
- 세 workload에 대응하는 정확한 composite·partial index와 실제 `EXPLAIN (ANALYZE)` 사용 근거
- 안전한 schema migration
- 잘못된 cross-tenant·중복 상태 거부
- 결과 정렬과 집계 검증
- 자동화 밖의 membership 경쟁을 위한 두-session 수동 검토 산출물

해당 연습은 reference 정답 하나를 외우기보다, 최소 계약을 자동 검사하는 형태다. 자신의 대안 schema가 같은 불변식과 query 계약을 만족하면 비교 가능한 설계가 될 수 있다.

## 완료 기준

다음 질문에 SQL, plan과 migration 단계로 답할 수 있어야 한다.

- 어떤 업무 규칙을 DB constraint가 직접 보장하는가?
- 어떤 규칙은 transaction 또는 application이 보장하며, 그 이유는 무엇인가?
- Query 하나가 반환하는 논리 row 단위는 무엇인가?
- Tenant 경계가 모든 key·query·index에 반영되었는가?
- 동시 update에서 깨질 수 있는 불변식과 conflict 지점은 무엇인가?
- 각 index가 어떤 predicate·ordering을 지원하고 어떤 쓰기 비용을 만드는가?
- Migration 중 이전·새 application이 동시에 실행되어도 안전한가?
- 실패 시 rollback, roll-forward 또는 restore 중 어떤 경로를 사용하는가?

애플리케이션 경로를 끝낸 뒤 내부구조 경로까지 수행했다면 [`시스템 종합 검토`](../90-system-review.md)로 이동한다.
