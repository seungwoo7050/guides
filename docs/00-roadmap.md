# 학습 로드맵

## 목표

이 저장소는 “서비스를 여러 개로 나누는 방법”보다 **서비스가 나뉜 뒤 실패를 어떻게 표현하고, 상태를 어떻게 수렴시키며, 그 결과를 어떻게 증명할 것인가**를 다룹니다.

가이드를 마치면 다음 질문에 구현과 검사로 답할 수 있어야 합니다.

- 이 데이터의 정본과 유일한 변경 주체는 어디입니까?
- 응답이 사라졌을 때 처리가 실패한 것인지, 성공했는지, 알 수 없는지 어떻게 구분합니까?
- 같은 요청과 이벤트가 여러 번 들어와도 결과가 하나만 남는 이유는 무엇입니까?
- 일부 서비스만 성공했을 때 어떤 상태를 남기고 누가 다시 처리합니까?
- 이벤트가 늦거나 순서가 바뀌었을 때 어떤 기준으로 적용·보류·거절합니까?
- 시간 제한과 재시도가 전체 요청 기한과 부하 한도 안에 있습니까?
- 시스템이 회복됐다는 사실을 프로세스 상태가 아니라 업무 상태로 어떻게 증명합니까?

## 대상 독자

다음 중 하나에 해당하면 적합합니다.

- 하나의 백엔드 애플리케이션을 구현해 본 뒤 서비스를 나누려는 개발자
- 메시지 브로커를 사용했지만 중복·순서·재처리 계약을 명확히 설명하기 어려운 개발자
- Outbox, Saga, Circuit Breaker 같은 패턴을 이름이 아니라 실패 조건과 검증으로 배우려는 개발자
- 여러 저장소와 서비스가 함께 배포되는 시스템의 릴리스·장애 근거를 정리하려는 개발자

Java 문법과 Maven이 처음이라면 `guide-java`의 언어, 빌드와 테스트 부분을 먼저 보는 편이 좋습니다. 트랜잭션 격리와 WAL 자체를 깊게 배우려면 `guide-database-systems`가 선행 또는 병행 과정입니다.

## 범위와 소유권

이 가이드가 주로 소유하는 개념은 다음과 같습니다.

```text
부분 실패와 불확실한 결과
서비스 경계와 데이터 소유권
동기·비동기 명령 계약
멱등성, 중복 전달과 단일 효과
Outbox, Saga와 재조정
이벤트 계약, 순서와 읽기 모델
시간 예산, 재시도, Circuit Breaker와 DLQ
역압, Bulkhead와 Load Shedding
다중 저장소 릴리스 명세
분산 관측성
장애 실험과 성능 판정 근거
```

다음은 필요한 접점만 설명합니다.

- Java 객체 모델, 동시성, Maven: `guide-java`
- SQL, 격리 수준, MVCC, WAL: `guide-database-systems`
- Spring Boot와 Spring Kafka 구현: `guide-backend-spring-boot`
- Docker, 호스트, 배포, 로그·지표 수집기: `guide-web-infrastructure`

## 읽기 경로

### 최소 설계 경로

처음 서비스 경계를 정하거나 동기·비동기 방식을 선택할 때 읽습니다.

1. [부분 실패와 확정할 수 없는 결과](01-boundaries-and-failure/01-partial-failure-and-uncertain-outcomes.md)
2. [서비스 경계와 데이터 소유권](01-boundaries-and-failure/02-service-boundaries-and-data-ownership.md)
3. [동기·비동기 명령 계약](01-boundaries-and-failure/03-synchronous-and-asynchronous-decisions.md)
4. [멱등성과 단일 업무 효과](02-delivery-and-consistency/01-idempotency-and-single-effects.md)

이 경로를 마치면 요청의 결과 상태, 변경 주체와 재시도 키를 설계할 수 있습니다.

### 전달과 수렴 경로

이벤트, Outbox 또는 읽기 모델을 구현할 때 읽습니다.

1. 최소 설계 경로
2. [Outbox, Saga와 재조정](02-delivery-and-consistency/02-outbox-saga-and-reconciliation.md)
3. [계약, 버전과 순서](02-delivery-and-consistency/03-contracts-versioning-and-order.md)
4. [읽기 모델, 지연 이벤트와 재구축](02-delivery-and-consistency/04-read-models-and-late-events.md)

이 경로를 마치면 중복·순서 역전·부분 성공을 복구 가능한 상태로 다룰 수 있습니다.

### 운영 신뢰성 경로

장애 대응, 부하 제어와 릴리스 검증을 맡을 때 읽습니다.

1. 전달과 수렴 경로
2. [시간 예산, 재시도, Circuit Breaker와 DLQ](03-resilience-and-load/01-timeouts-retries-circuit-breakers-and-dlq.md)
3. [역압, Bulkhead와 Load Shedding](03-resilience-and-load/02-backpressure-bulkheads-and-load-shedding.md)
4. [다중 저장소 릴리스 명세](04-release-and-evidence/01-multi-repository-builds-and-release-manifests.md)
5. [분산 관측성](04-release-and-evidence/02-distributed-observability.md)
6. [종단 간 장애 실험](04-release-and-evidence/03-end-to-end-chaos-and-failure-evidence.md)
7. [성능 기준과 주장](04-release-and-evidence/04-performance-gates-and-claims.md)

마지막에는 [통합 과제](05-capstone.md)를 수행합니다.

## 문서와 실습 대응

| 문서 | 실습 |
|---|---|
| 부분 실패와 확정할 수 없는 결과 | [uncertain-outcome](../exercises/01-boundaries-and-failure/01-uncertain-outcome/README.md) |
| 서비스 경계와 데이터 소유권 | [service-boundary](../exercises/01-boundaries-and-failure/02-service-boundary/README.md) |
| 동기·비동기 명령 계약 | [request-decision](../exercises/01-boundaries-and-failure/03-request-decision/README.md) |
| 멱등성과 단일 업무 효과 | [duplicate-delivery](../exercises/02-delivery-and-consistency/01-duplicate-delivery/README.md) |
| Outbox, Saga와 재조정 | [outbox-reconciliation](../exercises/02-delivery-and-consistency/02-outbox-reconciliation/README.md) |
| 계약, 버전과 순서 | [contracts-and-order](../exercises/02-delivery-and-consistency/03-contracts-and-order/README.md) |
| 읽기 모델과 재구축 | [read-model-rebuild](../exercises/02-delivery-and-consistency/04-read-model-rebuild/README.md) |
| 시간 예산과 재시도 | [retry-budget](../exercises/03-resilience-and-load/01-retry-budget/README.md) |
| 역압과 부하 제한 | [backpressure](../exercises/03-resilience-and-load/02-backpressure/README.md) |
| 릴리스 명세 | [release-manifest](../exercises/04-release-and-evidence/01-release-manifest/README.md) |
| 분산 관측성 | [observability-correlation](../exercises/04-release-and-evidence/02-observability-correlation/README.md) |
| 장애 실험 | [chaos-evidence](../exercises/04-release-and-evidence/03-chaos-evidence/README.md) |
| 성능 판정 | [performance-gate](../exercises/04-release-and-evidence/04-performance-gate/README.md) |
| 전체 과정 | [reservation-flow](../exercises/05-capstone/reservation-flow/README.md) |
| 선택 Kafka 환경 | [single-broker-kraft](../exercises/90-optional-labs/single-broker-kraft/README.md) |

## 실습 방법

각 Java 실습에는 동일한 검사와 공개 API를 가진 두 구현이 있습니다.

- `skeleton`: 컴파일되지만 핵심 계약을 위반합니다.
- `reference`: 같은 검사에서 계약을 만족합니다.

권장 순서는 다음과 같습니다.

1. README의 실패 조건을 먼저 적습니다.
2. skeleton 검사를 실행해 어떤 상태가 잘못 남는지 확인합니다.
3. 구현을 수정합니다.
4. 정상 결과뿐 아니라 바뀌면 안 되는 상태도 검사합니다.
5. reference와 소스 모양이 아니라 관찰 가능한 계약을 비교합니다.

저장소 전체 검증은 reference가 통과하는 것뿐 아니라 원본 skeleton이 **의도한 이유로 실패하는지**까지 확인합니다. 따라서 학습 구현은 원본 skeleton을 덮어쓰지 않고 `.workspace/`에 복사해 진행합니다.

```sh
mkdir -p .workspace
cp -R exercises/03-resilience-and-load/02-backpressure/skeleton \
  .workspace/backpressure

# 배포된 skeleton의 기준 실패만 확인합니다.
./scripts/verify-skeletons.sh \
  exercises/03-resilience-and-load/02-backpressure/skeleton

# .workspace 구현은 처음에는 실패하고, 계약을 완성한 뒤 통과해야 합니다.
./scripts/verify-java.sh .workspace/backpressure

# 필요할 때만 reference의 관찰 결과를 확인합니다.
./scripts/verify-java.sh \
  exercises/03-resilience-and-load/02-backpressure/reference
```

루트 `./verify.sh`는 학습자 구현의 채점 명령이 아니라 **가이드 배포본 전체의 무결성 검사**입니다.

## 완료 기준

다음 산출물을 스스로 작성할 수 있으면 가이드의 목표를 달성한 것입니다.

- 서비스별 데이터 소유권 표
- 명령별 동기·비동기 결정 기록
- 성공·거절·대기·알 수 없음 상태와 전이
- 멱등성 키의 범위와 충돌 규칙
- 이벤트 계약, 파티션 키, 순서와 호환성 정책
- Outbox·재조정·DLQ의 담당자와 종료 조건
- 전체 시간 예산과 유입량 제한
- 요청·명령·이벤트를 잇는 관측 식별자
- 장애 전·중·복구 후의 실패 행렬
- 릴리스 명세와 성능 판정 근거
