# 분산 서비스 설계와 복구 가이드

분산 서비스는 네트워크 호출이 많다는 이유만으로 어려운 것이 아닙니다. 호출 결과를 확정할 수 없는 순간, 같은 요청과 이벤트가 다시 도착하는 순간, 여러 서비스가 서로 다른 시점의 상태를 보는 순간에도 업무 결과가 올바르게 수렴해야 하기 때문에 어렵습니다.

이 가이드는 특정 프레임워크의 사용법보다 다음 능력을 목표로 합니다.

- 데이터와 변경 권한의 소유자를 정합니다.
- 성공·실패·알 수 없음(`UNKNOWN`)을 구분합니다.
- 중복 전달과 순서 역전을 정상 입력으로 처리합니다.
- Outbox, Saga와 재조정을 각 보장 범위에 맞게 사용합니다.
- 시간 예산, 재시도, Circuit Breaker, DLQ와 역압을 하나의 부하 계약으로 설계합니다.
- 릴리스 조합, 관측 정보, 장애 실험과 성능 주장을 재현 가능한 근거로 남깁니다.
- 여러 서비스가 얽힌 최종 과제에서 장애 전·중·복구 후의 업무 상태를 검증합니다.

공식 실습은 Java API/bytecode release 17, 실행 JDK 17~25, Maven Wrapper 3.3.4와 Maven 3.9.16을 사용합니다. 핵심 실습은 외부 브로커 없이 결정적으로 실행되며, Kafka 4.3.1 설정은 별도 실습으로 분리되어 있습니다.

## 선행 지식

다음 정도면 시작할 수 있습니다.

- Java의 클래스, 컬렉션, 예외와 기본 테스트 작성 경험
- Maven Wrapper를 사용해 Java 프로젝트를 빌드한 경험
- HTTP 요청·응답과 데이터베이스 트랜잭션의 기본 개념
- 메시지 브로커가 메시지를 저장하고 구독자에게 전달한다는 수준의 이해
- Git의 커밋, 태그와 작업 트리 개념

Spring Boot와 Kafka 운영 경험은 핵심 문서를 읽기 위한 필수 조건이 아닙니다. 다만 저장소 전체를 `make verify` 한 번으로 검증하려면 실행 중인 Docker Engine과 Docker Compose v2가 필요합니다.

## 시작

`distributed-services` 브랜치를 clone 또는 worktree로 받은 뒤 공개 명령 네 가지를 저장소 루트에서 사용합니다.

```sh
make prepare
make check
VERIFY_LOG=/tmp/guide-distributed-services-verify.log make verify
make clean
```

`make prepare`는 추적 소스를 변경하지 않고 저장소별 Maven 의존성 캐시와 Kafka 4.3.1 이미지를 준비합니다. Maven cache 준비용 임시 복사본에서는 학습자 `.workspace/`를 제외하지만, 이는 의존성 준비 입력을 curriculum으로 제한하기 위한 것이며 정식 source 보존 범위를 줄이지 않습니다. 모든 준비가 성공한 뒤에만 `.guide/distributed-services/prepared.json`에 입력 fingerprint와 이미지 identity를 기록하며, 필수 도구가 없으면 일부 검사를 묵시적으로 건너뛰지 않고 중단합니다.

`make verify`는 준비가 끝난 현재 working tree를 대상으로 다음을 한 번에 검사합니다.

- 문서 구조와 내부 링크
- 참조 구현의 컴파일과 계약 검사
- 학습자 skeleton이 의도한 결함 때문에 실패하는지
- Git 릴리스 명세 실습
- 장애 실험과 성능 판정
- 다중 서비스 capstone
- Kafka 실습의 정적 구성과 실제 broker·consumer group 동작

`make check`는 빠른 구조·교육 계약 검사를 실행하고 `make clean`은 명시된 생성물만 지우며 준비 cache와 학습자 `.workspace/`는 보존합니다. 검증 로그는 기본적으로 저장소 밖 `/tmp`에 남으며, `VERIFY_LOG=/absolute/outside/path.log make verify`로 경로를 지정할 수 있습니다. 상대 경로나 저장소 내부 로그 경로는 원본 불변 계약 때문에 거절됩니다.

## 읽는 순서

전체 지도와 선택 경로는 [학습 로드맵](docs/00-roadmap.md)에 있습니다.

별도 `examples/`는 없습니다. 각 개념은 바로 해당 실습의 결정적 실패 모델로
확인합니다. 다음 표의 순서대로 관련 문서를 읽고, 안전한 작업 공간을 만든 뒤
검사를 통과시키십시오. `reference` source는 workspace 검사가 통과하고 자기 설명을
작성한 뒤에만 비교합니다.

| 순서 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 뒤 비교·다음 |
|---:|---|---|---|---|---|---|
| 1 | [부분 실패와 확정할 수 없는 결과](docs/01-boundaries-and-failure/01-partial-failure-and-uncertain-outcomes.md) | — | [uncertain-outcome](exercises/01-boundaries-and-failure/01-uncertain-outcome/README.md) | `.workspace/uncertain-outcome` | `./scripts/verify-java.sh .workspace/uncertain-outcome` | `reference/` → 서비스 경계 |
| 2 | [서비스 경계와 데이터 소유권](docs/01-boundaries-and-failure/02-service-boundaries-and-data-ownership.md) | — | [service-boundary](exercises/01-boundaries-and-failure/02-service-boundary/README.md) | `.workspace/service-boundary` | `./scripts/verify-java.sh .workspace/service-boundary` | `reference/` → 요청 판정 |
| 3 | [동기·비동기 명령 계약](docs/01-boundaries-and-failure/03-synchronous-and-asynchronous-decisions.md) | — | [request-decision](exercises/01-boundaries-and-failure/03-request-decision/README.md) | `.workspace/request-decision` | `./scripts/verify-java.sh .workspace/request-decision` | `reference/` → 멱등성 |
| 4 | [멱등성과 단일 업무 효과](docs/02-delivery-and-consistency/01-idempotency-and-single-effects.md) | — | [duplicate-delivery](exercises/02-delivery-and-consistency/01-duplicate-delivery/README.md) | `.workspace/duplicate-delivery` | `./scripts/verify-java.sh .workspace/duplicate-delivery` | `reference/` → Outbox·Saga |
| 5 | [Outbox, Saga와 재조정](docs/02-delivery-and-consistency/02-outbox-saga-and-reconciliation.md) | — | [outbox-reconciliation](exercises/02-delivery-and-consistency/02-outbox-reconciliation/README.md) | `.workspace/outbox-reconciliation` | `./scripts/verify-java.sh .workspace/outbox-reconciliation` | `reference/` → 계약·순서 |
| 6 | [계약, 버전과 순서](docs/02-delivery-and-consistency/03-contracts-versioning-and-order.md) | — | [contracts-and-order](exercises/02-delivery-and-consistency/03-contracts-and-order/README.md) | `.workspace/contracts-and-order` | `./scripts/verify-java.sh .workspace/contracts-and-order` | `reference/` → 읽기 모델 |
| 7 | [읽기 모델, 지연 이벤트와 재구축](docs/02-delivery-and-consistency/04-read-models-and-late-events.md) | — | [read-model-rebuild](exercises/02-delivery-and-consistency/04-read-model-rebuild/README.md) | `.workspace/read-model-rebuild` | `./scripts/verify-java.sh .workspace/read-model-rebuild` | `reference/` → 재시도 예산 |
| 8 | [시간 예산, 재시도, Circuit Breaker와 DLQ](docs/03-resilience-and-load/01-timeouts-retries-circuit-breakers-and-dlq.md) | — | [retry-budget](exercises/03-resilience-and-load/01-retry-budget/README.md) | `.workspace/retry-budget` | `./scripts/verify-java.sh .workspace/retry-budget` | `reference/` → 역압 |
| 9 | [역압, Bulkhead와 Load Shedding](docs/03-resilience-and-load/02-backpressure-bulkheads-and-load-shedding.md) | — | [backpressure](exercises/03-resilience-and-load/02-backpressure/README.md) | `.workspace/backpressure` | `./scripts/verify-java.sh .workspace/backpressure` | `reference/` → 릴리스 명세 |
| 10 | [다중 저장소 릴리스 명세](docs/04-release-and-evidence/01-multi-repository-builds-and-release-manifests.md) | — | [release-manifest](exercises/04-release-and-evidence/01-release-manifest/README.md) | `.workspace/release-manifest/manifest_check.py` | `python3 exercises/04-release-and-evidence/01-release-manifest/tests/verify_manifest.py .workspace/release-manifest/manifest_check.py` | `reference/` → 관측성 |
| 11 | [분산 관측성](docs/04-release-and-evidence/02-distributed-observability.md) | — | [observability-correlation](exercises/04-release-and-evidence/02-observability-correlation/README.md) | `.workspace/observability-correlation` | `./scripts/verify-java.sh .workspace/observability-correlation` | `reference/` → 장애 근거 |
| 12 | [종단 간 장애 실험](docs/04-release-and-evidence/03-end-to-end-chaos-and-failure-evidence.md) | — | [chaos-evidence](exercises/04-release-and-evidence/03-chaos-evidence/README.md) | `.workspace/chaos-evidence` | `./scripts/verify-java.sh .workspace/chaos-evidence` | `reference/` → 성능 판정 |
| 13 | [성능 기준과 주장](docs/04-release-and-evidence/04-performance-gates-and-claims.md) | — | [performance-gate](exercises/04-release-and-evidence/04-performance-gate/README.md) | `.workspace/performance-gate` | `./scripts/verify-java.sh .workspace/performance-gate` | `reference/` → 통합 과제 |
| 14 | [통합 과제](docs/05-capstone.md) | — | [reservation-flow](exercises/05-capstone/reservation-flow/README.md) | `.workspace/reservation-flow` | `./scripts/verify-java.sh .workspace/reservation-flow` | `reference/` → 핵심 과정 완료 |
| 선택 | [단일 브로커 KRaft](docs/90-optional-labs/01-single-broker-kraft.md) | — | [broken/reference 구성 관찰](exercises/90-optional-labs/single-broker-kraft/README.md) | — | `./exercises/90-optional-labs/single-broker-kraft/verify.sh` | 관찰 근거 정리 → 과정 종료 |

## 실습 원칙

각 구현 실습에는 같은 계약을 공유하는 `skeleton`과 `reference`가 있습니다.

```text
문서에서 실패 모델을 이해합니다.
→ skeleton을 구현합니다.
→ 공개 검사를 실행합니다.
→ 실패 조건을 추가로 재현합니다.
→ reference와 결과·불변 조건을 비교합니다.
```

루트 `make verify`는 배포된 가이드 자체의 무결성을 검사하므로 원본 skeleton이 의도한 계약에서 실패해야 합니다. 학습할 때는 원본을 직접 고치지 않고 안전한 생성기로 `.workspace/` 아래에 작업합니다. 생성기는 알려진 실습만 허용하고 기존 destination이나 symlink를 덮어쓰지 않습니다. `.workspace/`는 Git과 exact curriculum tree 검사에서는 제외되지만 정식 검증의 외부 working-tree 복사와 source bytes·mode·symlink 불변성 검사에는 포함됩니다. 정식 검증이 실행하는 reference/skeleton 계약 검사는 계속 canonical tracked curriculum을 대상으로 합니다.

```sh
./scripts/new-workspace.sh uncertain-outcome

# checker는 workspace의 테스트 복사본이 아니라 추적된 정본 테스트를 사용합니다.
# 수정 전에는 실패하고, 계약을 구현한 뒤에는 통과해야 합니다.
./scripts/verify-java.sh .workspace/uncertain-outcome
```

작업 공간이 이미 있으면 생성기는 실패하며 기존 파일을 보존합니다. 구현이 정본 검사를
통과하고 위 실패 조건을 자신의 말로 설명한 뒤에만 해당 실습의 `reference/`를 읽습니다.
선택 KRaft 실습은 코드를 작성하는 단계가 아니라 두 canonical 구성을 실제 broker에서
비교하는 관찰형 예외이므로 별도 learner workspace가 없습니다.

reference의 소스 형태를 외우는 것이 목표가 아닙니다. 다음 네 가지가 검사로 증명되어야 합니다.

1. 중복되거나 늦은 입력에서도 업무 결과의 개수가 맞습니다.
2. 실패한 경로에서 바뀌면 안 되는 상태가 그대로입니다.
3. 복구 뒤 최종 상태가 정해진 값으로 수렴합니다.
4. 로그·지표·릴리스 정보만으로 어떤 실행이 어떤 결과를 만들었는지 추적할 수 있습니다.

## 범위

이 저장소가 소유하는 영역은 서비스 사이의 실패·전달·수렴 계약입니다.

다음 영역은 다른 가이드의 주 소유 범위입니다.

- Java 언어, JVM, Maven과 일반 동시성: [`java`](https://github.com/seungwoo7050/guides/tree/java)
- Spring MVC, JPA, Spring Kafka와 Resilience4j 적용법: [`backend-spring-boot`](https://github.com/seungwoo7050/guides/tree/backend-spring-boot)
- SQL 의미론, 격리 수준, MVCC와 WAL: [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems)
- 컨테이너, 호스트, DNS, TLS, 배포, 수집 시스템과 백업: [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra)

이 가이드는 필요한 접점만 설명하고 해당 영역 전체를 다시 가르치지 않습니다.
