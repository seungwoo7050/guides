# PostgreSQL 트랜잭션 잠금 실습

## 목표

같은 재고 행에 대한 20개 동시 차감 요청을 PostgreSQL 비관적 잠금으로 직렬화한다. 테스트는 모든 worker가 준비된 뒤 함께 시작하며 각 대기와 결과 회수에 상한을 둔다.

## 완료 기준

- 1,000에서 100씩 차감하는 20개 요청 중 정확히 10개만 성공한다.
- 모든 Future를 제한 시간 안에 회수하고 최종 수량이 정확히 0임을 확인한다.
- executor는 성공·실패와 관계없이 종료되고 검증 뒤 PostgreSQL container가 남지 않는다.

## 자기 설명

- Java의 시작 latch만으로 데이터베이스 lost update를 막을 수 없는 이유는 무엇인가?
- 낙관적 잠금 대신 비관적 잠금을 선택했을 때 처리량과 실패 형태는 어떻게 달라지는가?

## 검증

canonical skeleton의 일반 조회는 고정 실패 fixture다. tracked skeleton은 수정하지 않고 학습자 workspace에서 잠금 조회로 바꾸고 transaction 범위를 유지한다.

저장소 루트에서 learner-owned workspace를 만들고 검사한다.

```sh
./scripts/new-workspace.sh transaction-locking
./scripts/check-workspace.sh transaction-locking  # 먼저 지정 실패를 확인한다.
# 학습 구현: .workspace/transaction-locking/src/main을 수정한다.
./scripts/check-workspace.sh transaction-locking  # 수정 뒤 PASS를 확인한다.
```

## 완료 뒤 reference walkthrough

workspace 검증이 성공한 뒤에만 `reference` source를 연다. `exercises/transaction-locking/reference` 전체가 하나의 numbering scope이며, 다음 번호는 실제 과거 작성 순서가 아니라 완료 구현을 다시 만들 때의 권장 construction order다. Flyway migration은 애플리케이션 시작 수명에 속하며 별도 중간 CLI는 없다.

<!-- implementation-order:start scope=exercises/transaction-locking/reference semantics=recommended -->
| 번호 | 기준 파일·symbol | 먼저 고정하는 책임 |
|---:|---|---|
| 0 | [`pom.xml`](reference/pom.xml) | JPA·Flyway·PostgreSQL runtime dependency를 고정한다. |
| 1 | [`application.yml`](reference/src/main/resources/application.yml) | datasource, pool, schema validation과 Flyway 수명을 연결한다. |
| [Implementation 2] | [`V1__create_inventory_item.sql`](reference/src/main/resources/db/migration/V1__create_inventory_item.sql) | checksum이 고정된 기존 migration을 바꾸지 않고 schema owner와 nonnegative DB constraint를 따른다. |
| 3 | [`InventoryItem`](reference/src/main/java/dev/guides/spring/locking/InventoryItem.java) | 재고 state와 차감 불변식을 aggregate 안에 둔다. |
| 4 | [`InventoryRepository.findByIdForUpdate`](reference/src/main/java/dev/guides/spring/locking/InventoryRepository.java) | 같은 DB row를 pessimistic write lock으로 직렬화한다. |
| 5 | [`InventoryService.reserve`](reference/src/main/java/dev/guides/spring/locking/InventoryService.java) | lock 조회부터 state mutation·commit까지 transaction이 소유한다. |
<!-- implementation-order:end -->

다음 명령은 canonical comparator 자체의 test이며 learner workspace 검증을 대신하지 않는다.

```sh
./scripts/mvn-guide.sh -pl :transaction-locking-reference -am test
```

PostgreSQL `18.4-alpine`의 immutable image를 사용하므로 Docker daemon이 필수다.

비교를 마치면 [Spring Data Redis](../../docs/03-persistence-and-cache/03-spring-data-redis.md)로 진행한다.
