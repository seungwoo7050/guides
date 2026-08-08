# ER 모델, 정규화와 제약

## 학습 목표

이 문서를 마치면 다음을 할 수 있어야 한다.

- 업무 문장에서 entity, relationship, cardinality와 optionality를 추출한다.
- candidate key와 surrogate key의 역할을 구분한다.
- 함수 종속성으로 갱신 이상 현상을 설명한다.
- 1NF·2NF·3NF·BCNF를 암기 항목이 아니라 분해 판단에 사용한다.
- 애플리케이션 검증과 데이터베이스 제약의 책임을 구분한다.
- 비정규화를 선택할 때 동기화·검증·복구 계약을 함께 작성한다.

## 선행지식

[`SQL 의미와 질의 모양`](02-sql-semantics-and-query-shape.md)을 읽고, 기본 키와 외래 키의 문법을 알고 있어야 한다.

## 스키마는 column 목록이 아니라 업무 규칙의 실행 형태다

다음 요구사항을 보자.

```text
사용자는 여러 프로젝트에 참여할 수 있다.
프로젝트에는 여러 사용자가 참여할 수 있다.
참여자는 프로젝트마다 역할을 가진다.
작업 담당자는 해당 프로젝트의 참여자여야 한다.
완료된 작업에는 완료 시각이 반드시 있다.
```

이를 단순히 table 네 개로 옮기는 것만으로는 충분하지 않다. 각 문장을 key와 constraint로 내릴 수 있어야 한다.

```text
User
Project
Membership(project_id, user_id, role)
Task(project_id, assignee_id, status, completed_at)
```

`Membership`은 다대다 관계를 풀기 위한 중간 table이면서, 관계 자체의 `role`을 보관하는 entity다. `Task(project_id, assignee_id)`가 `Membership(project_id, user_id)`를 참조하면 “담당자는 같은 프로젝트의 참여자”라는 복합 업무 규칙을 DB가 검사할 수 있다.

## entity와 relationship 경계

entity를 찾을 때 “명사니까 table”이라는 규칙만 사용하면 table이 과도하게 늘어난다. 다음 질문을 사용한다.

- 독립적인 식별자가 필요한가?
- 다른 사실이 이 대상을 참조하는가?
- 자체 lifecycle과 상태 전이가 있는가?
- 연결 자체에 저장할 속성이 있는가?

주문과 상품의 연결에는 수량, 당시 가격, 할인처럼 관계 자체의 속성이 있다. 따라서 `OrderLine`이 필요하다.

```text
OrderLine(order_id, product_id, quantity, unit_price)
```

상품 ID를 쉼표로 연결한 문자열 하나에 저장하면 다음이 어려워진다.

- 상품 존재 여부를 외래 키로 검사
- 특정 상품을 포함한 주문 탐색
- 한 상품만 변경
- 수량과 당시 가격 저장
- concurrent update 충돌 범위 제한

## cardinality와 optionality

관계 수량 규칙은 외래 키 위치와 unique constraint를 정한다.

| 관계 | 대표 구현 |
|---|---|
| 1:1 | 한쪽 외래 키에 `UNIQUE` |
| 1:N | N 쪽에 외래 키 |
| N:M | 연결 table과 복합 key |
| optional | 외래 키의 `NULL` 허용 여부 |

“사용자는 기본 배송지 하나를 가진다”와 “배송지를 여러 개 저장하고 그중 하나를 기본으로 표시한다”는 다른 모델이다. 후자는 `Address` table과 사용자별 기본 주소 하나를 강제하는 별도 constraint 또는 transaction 계약이 필요하다.

cardinality가 애매하면 현재 화면이 아니라 변경 시나리오를 묻는다.

```text
한 사용자가 같은 프로젝트에 역할 두 개를 가질 수 있는가?
프로젝트 소유자는 변경되는가?
삭제된 사용자 기록을 주문에서 보존해야 하는가?
```

## candidate key와 surrogate key

candidate key는 업무 의미상 tuple을 유일하게 식별하는 최소 attribute 집합이다. surrogate key는 저장과 참조를 단순화하기 위해 만든 인공 식별자다.

예를 들어 사용자 table에 `id`가 있어도 email이 업무적으로 유일하다면 다음 두 규칙이 모두 필요할 수 있다.

```sql
id bigint PRIMARY KEY
CREATE UNIQUE INDEX ... ON users(lower(email))
```

surrogate key를 추가했다고 natural key의 업무 유일성이 사라지지 않는다. 이를 놓치면 같은 email을 가진 사용자 row가 여러 개 생기고 애플리케이션에서 임의 하나를 선택하게 된다.

반대로 변할 수 있는 값을 primary key로 사용하면 모든 참조에 변경이 전파된다. key 선택은 다음을 함께 본다.

- 안정성
- 크기와 index 비용
- 외부 노출 여부
- 생성 주체
- 유일성 범위

## 함수 종속성

`X → Y`는 같은 X 값을 가진 tuple이 항상 같은 Y 값을 가져야 한다는 뜻이다.

```text
user_id → email, grade
sku → product_name
(order_id, product_id) → quantity, unit_price
```

다음 table을 보자.

```text
OrderLine(order_id, product_id, product_name, quantity)
```

key가 `(order_id, product_id)`인데 `product_id → product_name`이면 상품명이 주문 line마다 반복된다. 다음 이상 현상이 생긴다.

- **수정 이상**: 상품명 변경 시 많은 row를 모두 바꿔야 한다.
- **삽입 이상**: 주문이 없으면 새 상품을 저장하기 어렵다.
- **삭제 이상**: 마지막 주문 line을 지우면 상품 정보도 사라진다.

함수 종속성을 문장으로 적으면 “중복이 많다”보다 정확하게 분해 이유를 설명할 수 있다.

## 정규형을 판단 도구로 사용한다

### 1NF

한 cell이 관계 안에서 더 쪼개야 할 반복 구조를 숨기지 않는지 본다. 문자열 목록이나 JSON이 항상 위반이라는 뜻은 아니다. 그 내부 요소를 독립적으로 참조·검색·제약해야 한다면 별도 relation이 필요하다는 뜻이다.

### 2NF

복합 candidate key의 일부에만 의존하는 non-key attribute가 있는지 본다.

```text
Enrollment(student_id, course_id, student_name, grade)
student_id → student_name
(student_id, course_id) → grade
```

`student_name`은 전체 key가 아니라 일부에 의존하므로 Student로 분리한다.

### 3NF

key가 아닌 attribute를 통해 다른 non-key attribute가 결정되는지 본다.

```text
Employee(employee_id, department_id, department_name)
department_id → department_name
```

부서명을 Department로 분리하지 않으면 같은 부서명이 반복된다.

### BCNF

모든 비자명한 함수 종속성의 determinant가 superkey인지 본다. 일부 복잡한 관계에서는 3NF가 dependency preservation을 위해 의도적으로 더 느슨할 수 있다. 중요한 것은 이름을 암기하는 것이 아니라 어떤 잘못된 갱신을 막기 위한 분해인지 설명하는 것이다.

## 데이터베이스 제약은 마지막 방어선이다

애플리케이션 검증은 사용자에게 빠르고 친절한 오류를 주는 데 필요하다. 그러나 DB 제약을 대신하지 못한다.

- 두 요청이 동시에 같은 email의 존재 여부를 검사할 수 있다.
- batch와 관리 SQL이 애플리케이션 경로를 우회할 수 있다.
- 서비스가 여러 언어와 버전으로 나뉠 수 있다.
- 검사와 insert 사이에 상태가 달라질 수 있다.

따라서 저장소에 남아서는 안 되는 상태는 가능한 한 제약으로 표현한다.

| 제약 | 보장하는 질문 |
|---|---|
| `PRIMARY KEY` | 이 row를 무엇으로 식별하는가 |
| `UNIQUE` | 어떤 업무 값이 중복되면 안 되는가 |
| `FOREIGN KEY` | 참조 대상이 존재하는가 |
| `NOT NULL` | 누락 상태를 허용하는가 |
| `CHECK` | 값 범위와 column 조합이 유효한가 |
| `EXCLUDE` | 시간 구간 등 겹침을 허용하는가 |

제약 위반을 정상적인 경쟁 결과로 사용할 수도 있다. “먼저 insert한 요청이 성공하고 다른 요청은 unique violation을 업무 충돌로 변환한다”는 방식은 check-then-insert race를 피한다.

## `NULL`의 업무 의미

`NULL`을 허용한다면 무엇을 뜻하는지 하나로 고정한다.

```text
아직 결정되지 않음
알 수 없음
이 row에는 적용되지 않음
외부 시스템에서 아직 오지 않음
```

서로 다른 의미를 한 column의 `NULL`에 모두 넣으면 질의와 제약이 모호해진다. 필요하면 상태 column이나 별도 relation으로 분리한다.

예를 들어 `completed_at IS NULL`이 “미완료”를 뜻한다면 status와 다음 일관성을 검사할 수 있다.

```sql
CHECK (
  (status = 'DONE' AND completed_at IS NOT NULL)
  OR
  (status <> 'DONE' AND completed_at IS NULL)
)
```

## 삭제 정책도 스키마 계약이다

외래 키의 `ON DELETE`는 편의 옵션이 아니다.

- `RESTRICT`: 참조가 남아 있으면 삭제를 거부한다.
- `CASCADE`: parent lifecycle에 child가 종속된다.
- `SET NULL`: 관계만 끊고 child는 보존한다.

감사 기록이나 결제 내역에 cascade를 사용하면 중요한 과거가 사라질 수 있다. 반대로 project에 완전히 종속된 임시 row를 restrict로 두면 정리 작업이 복잡해진다. 삭제 뒤 어떤 사실이 남아야 하는지 먼저 적는다.

## 비정규화는 측정 뒤에 선택한다

읽기 비용을 줄이기 위해 aggregate나 display 값을 중복 저장할 수 있다. 이때 다음 계약이 함께 있어야 한다.

```text
정본(source of truth):
파생 값 갱신 시점:
원자적으로 함께 갱신되는가:
불일치 탐지 질의:
재계산 방법:
허용 지연:
실패 시 읽기 정책:
```

이 기록 없이 column을 복사하면 빠른 읽기 대신 영구적인 불일치를 얻는다.

## 연결 연습

- [`스키마와 제약 exercise`](../../exercises/01-relational-semantics-and-design/02-schema-and-constraints/README.md): 프로젝트 참여자와 task 담당자의 복합 업무 규칙을 실제 constraint로 구현한다.
- [`Application database review`](../../exercises/05-capstones/01-application-database-review/README.md): 조직 경계, 상태·시간 조합, migration까지 포함한 스키마를 종합 검토한다.

## 완료 기준

다음 결과물을 만들 수 있어야 한다.

1. 도메인의 entity·relationship·cardinality를 글로 설명한다.
2. 각 table의 candidate key와 선택한 primary key를 구분한다.
3. 중요한 함수 종속성을 `X → Y`로 기록한다.
4. 허용해서는 안 되는 상태를 `UNIQUE`, `FOREIGN KEY`, `CHECK`, `NOT NULL`로 내린다.
5. 삭제 정책을 child lifecycle과 감사 요구사항으로 설명한다.
6. 비정규화 제안에 불일치 탐지와 재계산 절차를 포함한다.

다음 구획부터는 이 논리 계약이 page, index와 buffer pool로 내려가는 과정을 다룬다.
