# Spring Boot 백엔드 개발 로드맵

이 저장소는 Java와 웹의 기초를 다시 설명하는 입문서가 아니다. Java 애플리케이션을 작성하고 HTTP·SQL의 기본 계약을 이해하는 개발자가 Spring Boot의 **프레임워크 경계**를 실제 코드와 테스트로 익히기 위한 가이드다.

가이드를 마치면 다음을 독립적으로 수행할 수 있어야 한다.

- Application Context가 객체를 생성하고 연결하는 범위를 설명한다.
- 설정을 타입으로 묶고 잘못된 운영 설정을 시작 단계에서 거부한다.
- Spring MVC의 binding·validation·예외 변환 경계를 분리한다.
- Spring Security에서 인증, 권한, 객체 소유권과 CSRF를 구분한다.
- JPA 트랜잭션 프록시와 Flyway 마이그레이션을 실제 PostgreSQL에서 검증한다.
- Redis, Kafka, Outbox와 외부 HTTP 클라이언트를 Spring 어댑터로 연결한다.
- Testcontainers, WireMock, Actuator와 Micrometer로 실행 근거를 만든다.
- 위 요소를 하나의 서비스 안에서 조합하고 실패 뒤 상태를 검사한다.

## 선행 지식

다음 능력을 전제로 한다.

- Java 17 문법, record, collection, 예외와 JUnit
- Maven Wrapper로 프로젝트를 빌드하고 테스트하는 방법
- HTTP method, status, header, JSON과 cookie의 기본 의미
- 관계형 데이터베이스의 table, key, constraint와 transaction 기초
- Docker 컨테이너를 실행할 수 있는 개발 환경

부족한 영역은 각각 `guide-java`, `guide-web-applications`, `guide-database-systems`, `guide-web-infrastructure`에서 먼저 보완한다.

## 이 가이드가 소유하는 영역

이 저장소가 직접 가르치는 대상은 Spring 구현 계약이다.

- `ApplicationContext`, Bean 정의·수명·scope와 proxy
- `@ConfigurationProperties`, profile과 시작 단계 검증
- Spring MVC, Bean Validation과 `ProblemDetail`
- `SecurityFilterChain`, `SecurityContext`, method security와 security test
- Spring Data JPA, `@Transactional`, Flyway와 Spring Data Redis
- Spring Kafka, Spring scheduling, Resilience4j와 Spring HTTP client
- Spring test slice, Testcontainers, WireMock, Actuator와 Micrometer

다음 일반 이론은 다른 가이드가 주 소유자다.

- SQL 의미론, isolation, MVCC와 index 내부구조: `guide-database-systems`
- 멱등성, 재전달, Outbox, Saga, retry budget과 DLQ의 일반 원리: `guide-distributed-services`
- 호스트 구축, DNS·TLS, 이미지 배포, 수집 시스템과 운영 복구: `guide-web-infrastructure`

본문은 Spring 코드를 적용하는 데 필요한 최소 모델을 요약하지만, 위 전문 영역 전체를 다시 설명하지 않는다.

## 읽는 순서

| 단계 | 문서 | 종료 능력 | 실습 시작 |
|---:|---|---|---|
| 0 | 이 문서 | 범위와 선행 관계를 결정한다. | - |
| 1 | [Application Context와 Bean 수명](01-spring-core/01-application-context-and-lifecycle.md) | 객체 그래프와 proxy 경계를 추적한다. | 3 뒤 시작 |
| 2 | [설정·프로필·준비 상태](01-spring-core/02-configuration-profiles-and-readiness.md) | 잘못된 설정을 시작 단계에서 거부한다. | 3 뒤 시작 |
| 3 | [MVC 검증과 ProblemDetail](02-web-and-security/01-mvc-validation-and-problem-detail.md) | HTTP·업무·인프라 오류를 구분한다. | [application-boundaries](../exercises/application-boundaries/README.md) |
| 4 | [Spring Security 요청 모델](02-web-and-security/02-spring-security-request-model.md) | 인증과 권한 판단 위치를 설명한다. | 5 뒤 시작 |
| 5 | [권한·소유권·CSRF](02-web-and-security/03-authentication-authorization-and-csrf.md) | 객체 권한과 브라우저 요청 위조를 검사한다. | [security-boundaries](../exercises/security-boundaries/README.md) |
| 6 | [JPA 트랜잭션과 잠금](03-persistence-and-cache/01-jpa-transactions-and-locking.md) | 실제 proxy 호출과 잠금 경계를 검증한다. | 7 뒤 시작 |
| 7 | [Flyway와 스키마 연결](03-persistence-and-cache/02-flyway-and-schema-integration.md) | 빈 DB에서 스키마를 재현한다. | [transaction-locking](../exercises/transaction-locking/README.md) |
| 8 | [Spring Data Redis](03-persistence-and-cache/03-spring-data-redis.md) | 캐시 장애를 정확성 경계 밖에 둔다. | 10 뒤 시작 |
| 9 | [Spring Kafka와 Avro](04-distributed-adapters/01-spring-kafka-and-avro.md) | listener·serializer·ack를 연결한다. | [kafka-avro-contract](../exercises/kafka-avro-contract/README.md) |
| 10 | [Outbox와 스케줄링](04-distributed-adapters/02-outbox-and-scheduling.md) | Spring transaction과 발행 작업을 분리한다. | [idempotency-outbox](../exercises/idempotency-outbox/README.md) |
| 11 | [Resilience4j HTTP 클라이언트](04-distributed-adapters/03-resilience4j-http-clients.md) | 업무 거절과 의존성 장애를 다르게 기록한다. | [resilient-http-client](../exercises/resilient-http-client/README.md) |
| 12 | [테스트 경계](05-quality-and-operations/01-test-boundaries-testcontainers-and-wiremock.md) | 단위·slice·통합 검사를 배치한다. | 앞선 실습의 검증을 재해석하고 이후 capstone에 적용 |
| 13 | [Actuator와 애플리케이션 관측성](05-quality-and-operations/02-actuator-metrics-logging-and-tracing.md) | 운영 판단에 필요한 신호를 노출한다. | 14 뒤 시작 |
| 14 | [단일 서비스 통합 과제](06-capstone.md) | 한 서비스 안의 경계를 통합 검증한다. | [single-service-capstone](../exercises/single-service-capstone/README.md) |

Primary capstone 경로는 1~13을 순서대로 마친 뒤 14를 수행한다. HTTP와 PostgreSQL까지만 필요한 독자는 1~7에서 일단 종료할 수 있고, capstone을 수행하지 않는 독자만 8~11의 어댑터 장을 실제 사용 범위에 맞게 선택해 읽을 수 있다.

## 실습 방식

각 실습은 같은 공개 test 계약을 공유하는 canonical 시작점과 완료 구현, 그리고 학습자 소유 작업 공간으로 구성된다.

```text
skeleton  → tracked designated-failure baseline이며 직접 수정하지 않는다.
workspace → new-workspace로 만든 복사본에서 지정 실패를 관찰하고 src/main만 수정·검증한다.
reference → workspace가 PASS한 뒤 설계 선택과 권장 구현 순서를 비교한다.
```

reference를 먼저 열거나 복사하지 않는다. 실습 README의 실패 조건을 workspace에서 재현하고, 테스트가 어떤 외부 효과와 최종 상태를 검사하는지 확인한 뒤 구현한다.

저장소를 clone하거나 linked worktree로 연 직후에는 루트에서 다음 두 명령을 실행한다.

```sh
./prepare.sh
./verify.sh
```

`prepare.sh`는 source를 변경하지 않고 도구 확인과 namespaced 의존성·immutable image 준비만 담당한다. `verify.sh`는 외부 임시 사본에서 문서·구조·reference·skeleton 실패 조건과 통합 테스트를 한 번에 검사한다.

## 버전과 환경

재현 기준과 필요한 도구는 [버전과 개발 환경](90-appendix/01-version-and-environment.md)에 고정한다. 버전을 올릴 때는 POM만 수정하지 말고 모든 reference와 skeleton, Docker 이미지, 마이그레이션과 폐기 예정 API를 함께 검증한다.
