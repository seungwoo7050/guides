# Java와 Spring Boot 백엔드 개발 가이드

이 저장소는 Java·HTTP·SQL의 기초 이후에 Spring Boot의 프레임워크 경계를 구현과 검증으로 익히는 가이드다. Application Context, 설정, MVC, Spring Security, JPA·Flyway, Redis·Kafka 어댑터, Resilience4j, Testcontainers와 Actuator를 하나의 학습 경로로 연결한다.

일반적인 SQL·분산 시스템·운영 인프라 이론을 이 저장소에서 중복해 확장하지 않는다.

- 데이터베이스 의미론과 내부구조: `guide-database-systems`
- 멱등성·Outbox·재전달·retry의 일반 원리: `guide-distributed-services`
- host·DNS·TLS·배포·수집과 복구: `guide-web-infrastructure`

Spring 고유 구현 경계와 전체 읽기 순서는 [Spring Boot 백엔드 개발 로드맵](docs/00-roadmap.md)에서 시작한다.

## 적용과 전체 검증

준비와 검증은 일반 clone과 linked worktree에서 같은 계약으로 동작한다.

```sh
make prepare
make check
VERIFY_LOG="/tmp/backend-spring-boot-verify.log" make verify
make clean
```

- `make prepare`: source와 Git index를 바꾸지 않고 namespaced Maven cache, immutable 컨테이너 이미지와 fingerprint marker 준비
- `make check`: 문서·exact tree·validator mutant와 offline compile 빠른 검사
- `make verify`: 저장소 밖의 격리 사본에서 reference·workspace·통합 검사와 canonical skeleton 지정 실패 검증
- `make clean`: root와 canonical 실습의 지정 build 생성물만 제거하고 준비 cache와 `.workspace` 학습자 파일은 보존

네 명령은 저장소 루트에서 실행한다. `VERIFY_LOG`는 저장소 밖의 절대 경로여야 하며 `make prepare`는 반복 실행해도 source 상태를 바꾸지 않는다.

## 학습 경로

```text
Spring Core
→ MVC와 Security
→ JPA·Flyway·Redis
→ Kafka·Outbox·외부 HTTP client
→ Testcontainers·Actuator
→ 단일 서비스 통합 과제
```

핵심 문서:

- [로드맵과 범위](docs/00-roadmap.md)
- [Application Context와 Bean 수명](docs/01-spring-core/01-application-context-and-lifecycle.md)
- [Spring Security 요청 모델](docs/02-web-and-security/02-spring-security-request-model.md)
- [JPA 트랜잭션과 잠금](docs/03-persistence-and-cache/01-jpa-transactions-and-locking.md)
- [Spring Kafka와 Avro](docs/04-distributed-adapters/01-spring-kafka-and-avro.md)
- [테스트 경계](docs/05-quality-and-operations/01-test-boundaries-testcontainers-and-wiremock.md)
- [단일 서비스 통합 과제](docs/06-capstone.md)

## 실습

| 실습 | 확인하는 계약 |
|---|---|
| [application-boundaries](exercises/application-boundaries/README.md) | 설정 binding, MVC validation과 ProblemDetail |
| [security-boundaries](exercises/security-boundaries/README.md) | 401·403, 객체 소유권과 CSRF |
| [transaction-locking](exercises/transaction-locking/README.md) | PostgreSQL row lock과 최종 불변식 |
| [idempotency-outbox](exercises/idempotency-outbox/README.md) | DB 정본, Redis 힌트와 Outbox 복구 |
| [kafka-avro-contract](exercises/kafka-avro-contract/README.md) | Spring Kafka listener, Avro와 acknowledgement |
| [resilient-http-client](exercises/resilient-http-client/README.md) | 외부 응답 분류와 Circuit Breaker |
| [single-service-capstone](exercises/single-service-capstone/README.md) | Security·HTTP·PostgreSQL·Redis·Outbox·metric 통합 |

각 실습은 immutable canonical `skeleton`과 `reference`를 제공한다. `make verify`가 canonical skeleton의 의도한 실패를 고정하므로 tracked skeleton을 직접 수정하지 않는다. `./scripts/new-workspace.sh <실습>`으로 `.workspace/<실습>`을 만든 뒤 그 복사본만 수정하고 `./scripts/check-workspace.sh <실습>`으로 같은 공개 test를 통과시킨다. 루트 Maven reactor에는 검증 가능한 reference만 포함되며 `make clean`은 학습자 workspace를 지우지 않는다.

## 환경

기준 버전과 필요한 명령은 [버전과 개발 환경](docs/90-appendix/01-version-and-environment.md)에 정리되어 있다. 필수 통합 검사는 Docker를 사용할 수 없을 때 건너뛰지 않고 실패한다.
