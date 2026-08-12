# 단일 서비스 통합 실습

## 목표

인증된 editor의 publication 생성 API에 Security, 외부 policy, PostgreSQL transaction, Outbox, Redis cache와 Micrometer 증거를 연결한다. 같은 actor와 멱등성 키의 완료 결과는 DB가 정본이다.

## 완료 기준

- 인증·역할·입력 오류는 각각 401·403·400이며 publication과 Outbox 상태를 바꾸지 않는다.
- 첫 생성은 201과 Location을 반환하고 publication·Outbox·양수 TTL cache·생성 metric을 함께 남긴다.
- cache를 비운 재요청과 동시 요청 8개 모두 기존 DB 결과로 수렴하며 외부 policy를 중복 호출하지 않는다.
- policy `409`는 업무 거절 metric과 409를, `500`은 Circuit Breaker 실패와 503을 만든다.

## 자기 설명

- policy 호출을 advisory lock보다 앞에 두거나 DB 완료 조회보다 앞에 두면 어떤 중복 부작용이 생기는가?
- transaction commit 뒤 cache 쓰기가 실패해도 publication 생성 자체를 실패로 바꾸지 않는 이유는 무엇인가?

## 검증

canonical skeleton에는 보안 경계, advisory lock, Outbox 저장과 commit 뒤 cache 갱신 결함이 있으며 고정 실패 fixture로 남는다. tracked skeleton은 수정하지 않고 학습자 workspace를 고치며 reference와 byte-identical 공개 test를 사용한다.

저장소 루트에서 learner-owned workspace를 만들고 검사한다.

```sh
./scripts/new-workspace.sh single-service-capstone
./scripts/check-workspace.sh single-service-capstone  # 먼저 지정 실패를 확인한다.
# 학습 구현: .workspace/single-service-capstone/src/main을 수정한다.
./scripts/check-workspace.sh single-service-capstone  # 수정 뒤 PASS를 확인한다.
```

## 완료 뒤 reference walkthrough

workspace 검증이 성공한 뒤에만 `reference` source를 연다. `exercises/single-service-capstone/reference` 전체가 하나의 numbering scope이며, 다음 번호는 실제 과거 작성 순서가 아니라 완료 구현을 다시 만들 때의 권장 construction order다. Flyway migration은 애플리케이션 시작 수명에 속하며 별도 중간 CLI는 없다.

<!-- implementation-order:start scope=exercises/single-service-capstone/reference semantics=recommended -->
| 번호 | 기준 파일·symbol | 먼저 고정하는 책임 |
|---:|---|---|
| 0 | [`pom.xml`](reference/pom.xml) | Web·Security·JPA·Redis·Kafka·Resilience·Flyway·Actuator dependency를 고정한다. |
| 1 | [`application.yml`](reference/src/main/resources/application.yml) | typed properties와 DB·Redis·Kafka·policy·Outbox·metric 설정을 연결한다. |
| [Implementation 2] | [`V1__create_publication_and_outbox.sql`](reference/src/main/resources/db/migration/V1__create_publication_and_outbox.sql) | checksum이 고정된 기존 migration을 바꾸지 않고 actor/key uniqueness, publication·Outbox FK와 pending index를 따른다. |
| 3 | [`PublicationEntity`](reference/src/main/java/dev/guides/spring/capstone/PublicationEntity.java) | publication state와 응답 변환을 DB 정본에 둔다. |
| 3-1 | [`OutboxEventEntity`](reference/src/main/java/dev/guides/spring/capstone/OutboxEventEntity.java) | publication-created event의 pending·published lifecycle을 소유한다. |
| 4 | [`PolicyClient.ensureAllowed`](reference/src/main/java/dev/guides/spring/capstone/PolicyClient.java) | 업무 거절과 transport·dependency 실패를 분류한다. |
| 5 | [`PublicationWriter.createOrFind`](reference/src/main/java/dev/guides/spring/capstone/PublicationWriter.java) | advisory lock 뒤 DB를 재조회하고 publication·Outbox를 한 transaction에 저장한다. |
| 6 | [`PublicationCache`](reference/src/main/java/dev/guides/spring/capstone/PublicationCache.java) | actor/key 경계를 보존한 digest와 TTL cache를 best effort로 관리한다. |
| 7 | [`PublicationService.create`](reference/src/main/java/dev/guides/spring/capstone/PublicationService.java) | cache → DB → policy → writer 순서와 outcome metric을 조립한다. |
| 8 | [`PublicationController.create`](reference/src/main/java/dev/guides/spring/capstone/PublicationController.java) | principal·idempotency header·body validation과 201·200 응답을 연결한다. |
| 8-1 | [`PublicationProblemAdvice`](reference/src/main/java/dev/guides/spring/capstone/PublicationProblemAdvice.java) | 입력·업무 거절·의존성 실패를 400·409·503으로 번역한다. |
| 9 | [`SecurityConfiguration.securityFilterChain`](reference/src/main/java/dev/guides/spring/capstone/SecurityConfiguration.java) | stateless API의 editor-only POST와 deny-all·401·403 경계를 고정한다. |
| 10 | [`OutboxPublisher.publishPending`](reference/src/main/java/dev/guides/spring/capstone/OutboxPublisher.java) | gateway 발행 성공 뒤 별도 transaction으로 published state를 기록한다. |
<!-- implementation-order:end -->

다음 명령은 canonical comparator 자체의 test이며 learner workspace 검증을 대신하지 않는다.

```sh
./scripts/mvn-guide.sh -pl :single-service-capstone-reference -am test
```

PostgreSQL `18.4-alpine`, Redis `8.8.0-alpine`, WireMock 3.12.1을 사용하며 Kafka protocol은 `kafka-avro-contract` 실습이 담당한다.

비교를 마친 뒤 [capstone 완료 질문](../../docs/06-capstone.md#완료-조건)에 답하면 이 학습 경로가 끝난다.
