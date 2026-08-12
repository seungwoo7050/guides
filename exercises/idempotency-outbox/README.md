# 멱등성과 Outbox 실습

## 목표

PostgreSQL 완료 결과를 정본으로, Redis를 복구 가능한 힌트로 사용한다. 같은 멱등성 키의 동시 요청을 직렬화하고 업무 행과 Outbox 행을 같은 transaction에 기록한다.

## 완료 기준

- Redis가 정상일 때 commit된 결과가 양수 TTL의 cache로 저장되고 재요청에 재사용된다.
- Redis 접근이 실패해도 동시 요청 20개의 operation ID가 하나이며 업무 행과 Outbox 행이 각각 하나다.
- 첫 발행 실패는 시도 횟수·오류·다음 시각을 남기고 다음 poll에서 같은 Outbox 행을 성공 처리한다.

## 자기 설명

- Redis lock이나 cache hit를 정확성의 정본으로 삼으면 어떤 장애에서 중복이 생기는가?
- Outbox 발행 실패를 transaction 전체 rollback으로 처리하지 않는 이유는 무엇인가?

## 검증

canonical skeleton에는 advisory transaction lock, Redis hint adapter와 scheduler 활성화가 빠져 있으며 고정 실패 fixture로 남는다. Outbox 행 저장은 시작 코드에 이미 제공되므로 이를 새로 발명하지 않고 lock·cache·발행 수명 경계를 완성한다. tracked skeleton은 수정하지 않고 학습자 workspace를 고치며, workspace와 reference는 같은 공개 test 파일을 사용한다.

저장소 루트에서 learner-owned workspace를 만들고 검사한다.

```sh
./scripts/new-workspace.sh idempotency-outbox
./scripts/check-workspace.sh idempotency-outbox  # 먼저 지정 실패를 확인한다.
# 학습 구현: .workspace/idempotency-outbox/src/main을 수정한다.
./scripts/check-workspace.sh idempotency-outbox  # 수정 뒤 PASS를 확인한다.
```

## 완료 뒤 reference walkthrough

workspace 검증이 성공한 뒤에만 `reference` source를 연다. `exercises/idempotency-outbox/reference` 전체가 하나의 numbering scope이며, 다음 번호는 실제 과거 작성 순서가 아니라 완료 구현을 다시 만들 때의 권장 construction order다. Flyway migration은 애플리케이션 시작 수명에 속하며 별도 중간 CLI는 없다.

<!-- implementation-order:start scope=exercises/idempotency-outbox/reference semantics=recommended -->
| 번호 | 기준 파일·symbol | 먼저 고정하는 책임 |
|---:|---|---|
| 0 | [`pom.xml`](reference/pom.xml) | JPA·Redis·Flyway·PostgreSQL dependency 경계를 고정한다. |
| [Implementation 1] | [`V1__create_operation_and_outbox.sql`](reference/src/main/resources/db/migration/V1__create_operation_and_outbox.sql) | checksum이 고정된 기존 migration을 바꾸지 않고 operation unique key와 Outbox retry state·due index를 따른다. |
| 2 | [`OperationRecord`](reference/src/main/java/dev/guides/spring/idempotency/OperationRecord.java) | PostgreSQL 완료 결과를 정본으로 표현한다. |
| 2-1 | [`OutboxEvent`](reference/src/main/java/dev/guides/spring/idempotency/OutboxEvent.java) | pending·published·retry lifecycle을 하나의 entity가 소유한다. |
| 3 | [`RedisIdempotencyHintStore`](reference/src/main/java/dev/guides/spring/idempotency/RedisIdempotencyHintStore.java) | Redis를 양수 TTL의 복구 가능한 조회 힌트로 제한한다. |
| 4 | [`OperationService.apply`](reference/src/main/java/dev/guides/spring/idempotency/OperationService.java) | hint miss 뒤 advisory lock·DB 재조회·operation과 Outbox 저장을 묶는다. |
| 4-1 | [`OperationService.cacheAfterCommit`](reference/src/main/java/dev/guides/spring/idempotency/OperationService.java) | commit 뒤 cache를 채우고 cache 실패가 DB 결과를 뒤집지 않게 한다. |
| 5 | [`OutboxPublisher.publishDueEvents`](reference/src/main/java/dev/guides/spring/idempotency/OutboxPublisher.java) | due batch를 발행하고 성공·실패 state를 같은 transaction에 남긴다. |
| 5-1 | [`OutboxScheduler`](reference/src/main/java/dev/guides/spring/idempotency/OutboxScheduler.java), [`IdempotencyApplication`](reference/src/main/java/dev/guides/spring/idempotency/IdempotencyApplication.java), [`application.yml`](reference/src/main/resources/application.yml) | `@EnableScheduling`이 polling을 활성화하고 initial·poll delay 설정을 publisher 호출 수명에 연결한다. |
<!-- implementation-order:end -->

다음 명령은 canonical comparator 자체의 test이며 learner workspace 검증을 대신하지 않는다.

```sh
./scripts/mvn-guide.sh -pl :idempotency-outbox-reference -am test
```

PostgreSQL `18.4-alpine`과 Redis `8.8.0-alpine`의 immutable image를 사용한다.

비교를 마치면 [Resilience4j HTTP 클라이언트](../../docs/04-distributed-adapters/03-resilience4j-http-clients.md)로 진행한다.
