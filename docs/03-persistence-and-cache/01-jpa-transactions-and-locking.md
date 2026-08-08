# JPA 트랜잭션과 잠금

`@Transactional`은 데이터베이스 transaction을 여는 Spring 경계다. annotation이 있다는 사실만으로 업무 불변식, proxy 호출과 동시성 전략이 올바르다고 보장되지는 않는다.

## 함께 성공하거나 실패할 상태부터 정한다

transaction 범위는 repository 호출 수가 아니라 업무 불변식으로 결정한다.

```text
재고 수량 감소
+ 작업 기록 저장
+ Outbox 행 저장
```

위 상태가 하나의 결정이라면 같은 transaction에 둔다. 외부 HTTP와 Kafka 응답을 기다리는 동안 connection과 row lock을 잡지 않는다.

## 실제 proxy 호출을 확인한다

다음 코드는 `reserve()`의 transaction이 적용되지 않을 수 있다.

```java
@Service
class ReservationService {
  void handle() {
    reserve(); // 자기 호출
  }

  @Transactional
  void reserve() { ... }
}
```

transaction 경계를 별도 Bean의 public method로 분리하고, Spring Context를 사용하는 integration test에서 실제 commit·rollback을 확인한다. 순수 객체 단위 테스트는 proxy 효과를 검증하지 않는다.

## entity 수명과 HTTP 수명을 섞지 않는다

Open Session in View에 기대어 response serialization 중 lazy query가 실행되지 않게 한다. service transaction 안에서 필요한 projection이나 DTO를 만들고 Controller에는 영속 entity를 넘기지 않는다.

cascade와 orphan removal은 편의 기능이 아니라 aggregate 저장 계약이다. 관계 양쪽을 무조건 cascade하면 예상하지 않은 delete와 대량 write가 발생할 수 있다.

## 비관적 잠금

같은 행을 읽어 조건을 확인한 뒤 변경하고 즉시 직렬화해야 한다면 비관적 잠금을 사용할 수 있다.

```java
@Lock(LockModeType.PESSIMISTIC_WRITE)
@Query("select item from InventoryItem item where item.id = :id")
Optional<InventoryItem> findByIdForUpdate(UUID id);
```

- 실제 경쟁 단위만 잠근다.
- 여러 자원을 잠글 때 순서를 고정한다.
- lock timeout과 deadlock exception을 application error로 번역한다.
- 재시도한다면 외부 효과가 반복되지 않는 범위만 다시 실행한다.

## 낙관적 잠금과 조건부 SQL

충돌이 드물고 작업을 안전하게 다시 시도할 수 있다면 `@Version`이 적합할 수 있다. 단순 수량 차감은 조건부 update와 affected row count가 더 명확할 수도 있다.

```sql
update inventory
set available = available - :amount
where id = :id and available >= :amount;
```

같은 entity 행이 아직 존재하지 않는 생성 요청은 row lock만으로 직렬화할 수 없다. PostgreSQL에 종속된 실습에서는 `(actor, idempotencyKey)`에서 안정적인 값을 만들고 transaction-scoped advisory lock을 얻은 뒤 조회·생성을 수행할 수 있다. 최종 방어선으로 unique constraint도 유지한다.

```text
transaction 시작
→ advisory lock
→ 동일 key 조회
→ 없으면 entity와 Outbox 저장
→ commit에서 lock 자동 해제
```

advisory lock은 편의적인 application protocol이므로 key 생성 규칙과 범위를 test에 고정한다. DBMS 독립성이 필요하다면 별도 idempotency row, 조건부 insert 또는 다른 직렬화 전략을 선택한다.

어떤 전략을 선택하든 최종 데이터베이스 상태와 성공 요청 수를 동시에 검사한다. isolation·MVCC의 일반 이론은 `guide-database-systems`에서 다룬다.

## 실습

[트랜잭션 잠금 실습](../../exercises/transaction-locking/README.md)은 PostgreSQL에서 동시에 20개 요청을 실행하고 정확히 허용 가능한 요청만 성공하는지 검증한다.
