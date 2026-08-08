# Transaction, 격리와 lock

## 학습 목표

이 문서를 마치면 다음을 설명할 수 있어야 한다.

- transaction의 atomicity와 isolation이 서로 다른 실패를 다루는 이유
- read-modify-write가 transaction 안에서도 안전하지 않을 수 있는 이유
- lost update, non-repeatable read, phantom과 write skew의 차이
- row lock, predicate conflict와 guard row가 보호하는 범위
- deadlock이 발생하는 조건과 lock ordering으로 줄이는 방법
- serialization failure와 deadlock을 안전하게 retry하기 위한 경계

## 선행지식

스키마 제약과 대표 업무 불변식을 말할 수 있어야 한다. [`ER·정규화·제약`](../01-relational-semantics-and-design/03-er-normalization-and-constraints.md)을 권장한다.

## Transaction은 여러 명령을 하나의 상태 전이로 묶는다

transaction을 단순히 `BEGIN`과 `COMMIT` 사이의 코드로 보면 중요한 경계가 빠진다. 먼저 다음을 적는다.

```text
시작 상태에서 참인 불변식:
읽는 row와 predicate:
변경할 row:
성공 후 새 상태:
실패 시 남아야 할 상태:
동시에 실행되는 다른 transaction:
```

예를 들어 재고 10개에서 7개를 예약한다.

```text
불변식: available >= 0
전이: available := available - 7, 단 available >= 7일 때만
```

이 계약은 한 transaction의 rollback뿐 아니라 동시에 두 요청이 실행될 때도 보존되어야 한다.

## ACID를 실패 종류로 나눈다

### Atomicity

transaction의 변경이 모두 적용되거나 모두 취소된다. 여러 table 변경 중 일부만 남는 실패를 막는다.

### Consistency

DBMS가 모든 업무 규칙을 자동으로 아는 것은 아니다. schema constraint와 transaction 코드가 정의한 유효 상태에서 다른 유효 상태로 이동해야 한다.

### Isolation

동시 transaction의 중간 상태와 충돌이 최종 결과를 깨뜨리지 않게 한다. 어떤 현상을 막는지는 isolation level과 명령 형태에 따라 다르다.

### Durability

commit 성공을 반환한 결과가 crash 뒤에도 남는다. WAL과 복구가 이 계약을 구현한다.

“transaction을 썼으니 안전하다”는 말은 어느 속성이 어떤 명령으로 보장되는지 설명하지 못한다.

## Read-modify-write race

다음 코드는 한 transaction 안에 있어도 lost update를 만들 수 있다.

```text
A: SELECT available → 10
B: SELECT available → 10
A: UPDATE available = 3
B: UPDATE available = 3
A: COMMIT
B: COMMIT
```

두 요청이 각각 7개 예약에 성공했다고 생각하지만 최종 값은 3이다. 한 변경이 다른 변경을 덮었다.

안전한 형태는 판단과 변경을 한 SQL statement의 conflict 지점으로 모은다.

```sql
UPDATE inventory
SET available = available - :quantity
WHERE sku = :sku
  AND available >= :quantity
RETURNING available;
```

같은 row를 갱신하는 두 statement는 row lock에서 직렬화된다. 두 번째 statement는 첫 변경 뒤 조건을 다시 평가해 실패할 수 있다.

중요한 원칙:

> 애플리케이션 메모리에서 읽은 값을 다시 절대값으로 쓰기보다, DB가 현재 값을 기준으로 조건과 변경을 함께 수행하게 한다.

## 대표 이상 현상

### Dirty read

다른 transaction이 아직 commit하지 않은 값을 읽는다. rollback될 값을 업무 판단에 사용할 수 있다. PostgreSQL의 `READ COMMITTED`는 dirty read를 허용하지 않는다.

### Non-repeatable read

같은 row를 transaction 안에서 두 번 읽었는데 사이에 다른 committed update가 들어와 값이 달라진다.

### Phantom

같은 predicate query를 다시 실행했는데 다른 transaction의 insert·delete 때문에 row 집합이 달라진다.

### Lost update

둘이 같은 이전 값을 읽고 각각 새 값을 쓴 결과 한 변경이 사라진다. 단순한 isolation level 이름보다 update 문장 형태와 lock을 함께 봐야 한다.

### Write skew

각 transaction이 서로 다른 row를 수정하지만, 함께 보면 predicate 기반 불변식을 깨뜨린다.

```text
의사 A와 B가 모두 on_call=true
불변식: 최소 한 명은 on_call
A: B가 있으니 A를 off
B: A가 있으니 B를 off
결과: 0명
```

서로 다른 row를 update하므로 단순 row lock만으로 자동 충돌하지 않을 수 있다.

## Isolation level을 현상과 연결한다

DBMS마다 세부 구현과 허용 현상이 다르므로 이름만 암기하지 않는다. PostgreSQL 관점의 실용 모델은 다음과 같다.

### READ COMMITTED

각 statement가 시작할 때 새로운 snapshot을 본다. 같은 transaction의 두 select가 다른 committed 상태를 볼 수 있다. row update는 conflict 시 대기하고 최신 row에서 조건을 다시 평가할 수 있다.

### REPEATABLE READ

transaction snapshot을 유지한다. 반복 read가 안정적이지만 모든 predicate 불변식이 자동으로 보존되는 것은 아니다. PostgreSQL의 snapshot isolation 계열에서 write skew를 고려해야 한다.

### SERIALIZABLE

동시 실행 결과가 어떤 serial 순서와 동치가 되도록 conflict를 감지한다. 이를 위해 transaction 하나가 serialization failure로 abort될 수 있다. 성공률을 100% 보장하는 level이 아니라 **잘못된 성공 대신 명시적 실패를 허용하는 계약**이다.

## 명시적 lock

### `SELECT ... FOR UPDATE`

읽은 row를 이후 update할 의도가 있을 때 잠근다. 같은 row를 수정하거나 잠그려는 transaction과 충돌한다.

```sql
SELECT available
FROM inventory
WHERE sku = :sku
FOR UPDATE;
```

그러나 “조건을 만족하는 row가 하나도 없음” 자체를 보호하지 못할 수 있다. 새로운 row insert를 막아야 한다면 predicate lock, unique constraint, advisory lock 또는 guard row 같은 다른 conflict 지점이 필요하다.

### Guard row

여러 row에 걸친 불변식을 하나의 명시적 row lock으로 직렬화할 수 있다.

```sql
SELECT id FROM shift_guard WHERE id = 1 FOR UPDATE;
SELECT count(*) FROM doctors WHERE on_call;
```

같은 업무 불변식을 변경하는 모든 transaction이 동일한 guard를 잠가야 한다. 일부 경로가 빠지면 보호가 깨진다. guard는 간단하지만 hot spot이 될 수 있다.

### Advisory lock

DBMS row와 직접 연결되지 않은 업무 key를 잠글 수 있다. lock key mapping, session/transaction 수명, 누락 경로를 명확히 해야 한다. schema constraint를 대체하는 기본 수단은 아니다.

## Unique constraint를 경쟁 해결에 사용한다

다음 패턴은 race가 있다.

```text
SELECT 없음을 확인
→ INSERT
```

두 transaction이 동시에 없음을 보고 insert할 수 있다. unique constraint를 두고 insert 자체를 경쟁 지점으로 사용한다.

```sql
INSERT INTO users(email) VALUES (:email)
ON CONFLICT (...) DO ...;
```

또는 unique violation을 업무 충돌로 변환한다. DB constraint가 최종 승자를 정한다.

## Deadlock

다음 조건이 함께 있을 때 deadlock이 가능하다.

- 상호 배제되는 자원
- 자원을 가진 채 다른 자원을 기다림
- 선점할 수 없음
- 순환 대기

계좌 A→B와 B→A 이체가 서로 source row를 먼저 잠그면 순환할 수 있다.

해결 원칙:

```text
항상 더 작은 account_id부터 lock
```

모든 경로에서 같은 total order를 사용하면 순환을 줄인다. 그래도 다른 자원과 lock type 때문에 deadlock이 완전히 사라진다고 가정하지 않는다. DBMS는 cycle을 감지해 transaction 하나를 abort한다.

## Retry 경계

serialization failure와 deadlock victim은 전체 transaction을 처음부터 재시도해야 한다. statement 하나만 다시 실행하면 이전 read와 판단이 오래된 상태일 수 있다.

안전한 retry 조건:

- transaction block이 side effect 경계를 명확히 가진다.
- 외부 API 호출·email 발송을 transaction 중간에 직접 수행하지 않는다.
- retry 가능한 DB error를 분류한다.
- backoff와 최대 횟수를 둔다.
- 요청 전체에 deadline이 있다.
- idempotency 또는 unique key로 중복 효과를 막는다.

DB transaction 재시도와 분산 메시지 재전달은 관련 있지만 같은 문제가 아니다. 서비스 간 전달은 [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services)의 소유 영역이다.

## Long transaction의 비용

오래 열린 transaction은 다음을 만든다.

- lock 보유 시간 증가
- MVCC dead version 정리 지연
- 오래된 snapshot 유지
- replication lag와 WAL 보존 증가
- retry 비용 증가

사용자 입력을 기다리거나 큰 파일 처리를 transaction 안에서 수행하지 않는다. transaction은 업무 상태를 원자적으로 바꾸는 최소 구간이어야 한다.

## 검증은 동시에 실행해야 한다

동시성 코드를 순차 unit test로만 확인하면 race를 보지 못한다. 다음이 필요하다.

```text
session A와 B를 분리
두 read가 모두 끝난 시점 고정
동시에 write 진행
성공 수와 최종 상태 확인
반복 가능하게 barrier 또는 sleep 지점 고정
```

무작위 부하만 돌려 “한 번도 안 깨졌다”를 증거로 삼지 않는다. 먼저 결정적인 interleaving으로 실패를 재현한다.

## 연결 연습

- [`PostgreSQL isolation exercise`](../../exercises/03-transactions-and-recovery/01-postgres-isolation/README.md): 재고 lost update와 당직 write skew를 실제 session 두 개로 재현하고 수정한다.
- [`Transaction anomaly 예제`](../../examples/transaction_anomalies.py): read-modify-write가 한 변경을 잃는 최소 상태를 본다.
- 다음 문서인 [`MVCC·WAL·복구`](02-mvcc-wal-and-recovery.md)는 snapshot과 durability가 내부에서 구현되는 방식을 다룬다.

## 완료 기준

다음 질문에 답할 수 있어야 한다.

1. atomicity가 보장되어도 lost update가 가능한 이유는 무엇인가?
2. 조건부 atomic `UPDATE`가 read-modify-write보다 안전한 이유는 무엇인가?
3. write skew가 서로 다른 row update에서도 생기는 이유는 무엇인가?
4. row lock, guard row, unique constraint와 serializable 중 어떤 conflict를 만드는가?
5. deadlock retry가 전체 transaction 단위여야 하는 이유는 무엇인가?
6. 동시성 테스트가 실제로 두 session의 겹치는 실행을 보장하는가?
