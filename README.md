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
- `make verify`: 저장소 밖의 격리 사본에서 reference·통합 검사, workspace 생성·검증 메커니즘과 canonical skeleton 지정 실패 검증
- `make clean`: root와 canonical 실습의 지정 build 생성물만 제거하고 준비 cache와 `.workspace` 학습자 파일은 보존

네 명령은 저장소 루트에서 실행한다. `VERIFY_LOG`는 저장소 밖의 절대 경로여야 하며 `make prepare`는 반복 실행해도 source 상태를 바꾸지 않는다.

## 학습 순서

첫 문서는 [로드맵과 범위](docs/00-roadmap.md)다. 모든 명령은 저장소 루트에서 실행하며, 여러 문서가 하나의 실습에 연결되면 표에 적힌 마지막 문서까지 읽은 뒤 실습을 시작한다. 학습자는 workspace 검증이 성공하기 전에는 `reference` source를 열거나 복사하지 않는다.

별도 `examples/`는 없다. 문서의 짧은 코드와 상태 모델을 읽은 뒤 canonical `skeleton`에서 만든 workspace로 직접 구현한다. 루트 `make verify`는 repository가 제공하는 reference와 workspace 메커니즘을 검사할 뿐 현재 학습자 workspace의 완료를 판정하지 않는다.

<!-- learning-map:start -->
| 순서 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 뒤 비교·다음 |
|---:|---|---|---|---|---|---|
| 시작 | [로드맵과 범위](docs/00-roadmap.md), [버전과 환경](docs/90-appendix/01-version-and-environment.md) | — | 저장소 baseline 확인 | — | `make prepare`, `make check`, 외부 절대 `VERIFY_LOG`를 지정한 `make verify` | 1~3으로 진행하고 [명령과 장애 진단](docs/90-appendix/02-command-and-troubleshooting.md)은 필요할 때 확인한다. |
| 1~3 | [Application Context와 Bean 수명](docs/01-spring-core/01-application-context-and-lifecycle.md) → [설정·프로필·준비 상태](docs/01-spring-core/02-configuration-profiles-and-readiness.md) → [MVC 검증과 ProblemDetail](docs/02-web-and-security/01-mvc-validation-and-problem-detail.md) | — | [application-boundaries](exercises/application-boundaries/README.md) | `.workspace/application-boundaries/src/main` | `./scripts/check-workspace.sh application-boundaries` | 성공 뒤 [reference](exercises/application-boundaries/reference/) 비교 → 4~5 |
| 4~5 | [Spring Security 요청 모델](docs/02-web-and-security/02-spring-security-request-model.md) → [권한·소유권·CSRF](docs/02-web-and-security/03-authentication-authorization-and-csrf.md) | — | [security-boundaries](exercises/security-boundaries/README.md) | `.workspace/security-boundaries/src/main` | `./scripts/check-workspace.sh security-boundaries` | 성공 뒤 [reference](exercises/security-boundaries/reference/) 비교 → 6~7 |
| 6~7 | [JPA 트랜잭션과 잠금](docs/03-persistence-and-cache/01-jpa-transactions-and-locking.md) → [Flyway와 스키마 연결](docs/03-persistence-and-cache/02-flyway-and-schema-integration.md) | — | [transaction-locking](exercises/transaction-locking/README.md) | `.workspace/transaction-locking/src/main` | `./scripts/check-workspace.sh transaction-locking` | 성공 뒤 [reference](exercises/transaction-locking/reference/) 비교 → 8 |
| 8 | [Spring Data Redis](docs/03-persistence-and-cache/03-spring-data-redis.md) | — | 10에서 Outbox와 함께 수행 | — | — | `reference`를 보지 않고 9로 진행한다. |
| 9 | [Spring Kafka와 Avro](docs/04-distributed-adapters/01-spring-kafka-and-avro.md) | — | [kafka-avro-contract](exercises/kafka-avro-contract/README.md) | `.workspace/kafka-avro-contract/src/main` | `./scripts/check-workspace.sh kafka-avro-contract` | 성공 뒤 [reference](exercises/kafka-avro-contract/reference/) 비교 → 10 |
| 10 | [Outbox와 스케줄링](docs/04-distributed-adapters/02-outbox-and-scheduling.md), 8의 Redis 개념 | — | [idempotency-outbox](exercises/idempotency-outbox/README.md) | `.workspace/idempotency-outbox/src/main` | `./scripts/check-workspace.sh idempotency-outbox` | 성공 뒤 [reference](exercises/idempotency-outbox/reference/) 비교 → 11 |
| 11 | [Resilience4j HTTP 클라이언트](docs/04-distributed-adapters/03-resilience4j-http-clients.md) | — | [resilient-http-client](exercises/resilient-http-client/README.md) | `.workspace/resilient-http-client/src/main` | `./scripts/check-workspace.sh resilient-http-client` | 성공 뒤 [reference](exercises/resilient-http-client/reference/) 비교 → 12 |
| 12 | [테스트 경계](docs/05-quality-and-operations/01-test-boundaries-testcontainers-and-wiremock.md) | — | 앞선 실습의 공개 test를 경계별로 분류하고 DB·Redis·Kafka·HTTP 최종 상태가 왜 완료 증거인지 설명 | 저장소 밖 개인 학습 기록 | 각 workspace의 PASS 결과와 test assertion을 근거로 설명을 검토한다. | 설명한 test boundary와 상태 증거를 13~14에 적용한다. |
| 13~14 | [Actuator와 애플리케이션 관측성](docs/05-quality-and-operations/02-actuator-metrics-logging-and-tracing.md) → [단일 서비스 통합 과제](docs/06-capstone.md) | — | [single-service-capstone](exercises/single-service-capstone/README.md) | `.workspace/single-service-capstone/src/main` | `./scripts/check-workspace.sh single-service-capstone` | 성공 뒤 [reference](exercises/single-service-capstone/reference/) 비교와 자기 설명을 마치고 종료한다. |
<!-- learning-map:end -->

## 실습 구조

각 실습은 immutable canonical `skeleton`과 완료 뒤 비교할 `reference`를 제공한다. `make verify`가 canonical skeleton의 의도한 실패를 고정하므로 tracked skeleton을 직접 수정하지 않는다. `./scripts/new-workspace.sh <실습>`으로 `.workspace/<실습>`을 만든 뒤 먼저 `./scripts/check-workspace.sh <실습>`의 지정 실패를 관찰한다. 그 복사본의 `src/main`만 수정하고 같은 명령이 PASS할 때까지 반복한 뒤에만 reference walkthrough로 이동한다. 루트 Maven reactor에는 repository 검증용 reference만 포함되며 `make clean`은 학습자 workspace를 지우지 않는다.

각 reference의 `[Implementation 0]`은 과거에 Spring Initializr나 별도 generator를 실행했다는 주장이 아니다. 이미 존재하는 Maven project를 다시 구성할 때 application logic보다 먼저 고정할 권장 dependency baseline을 뜻한다.

## 환경

기준 버전과 필요한 명령은 [버전과 개발 환경](docs/90-appendix/01-version-and-environment.md)에 정리되어 있다. 필수 통합 검사는 Docker를 사용할 수 없을 때 건너뛰지 않고 실패한다.
