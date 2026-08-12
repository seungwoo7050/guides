# 복원력 있는 HTTP 클라이언트 실습

## 목표

업무 거절과 의존성 장애를 분리하고, `Duration` 기반 connect/read timeout과 두 번의 고정 retry budget을 적용한다. 재시도에서도 같은 요청 식별자를 보존한다.

## 완료 기준

- `409` 업무 거절은 Circuit Breaker 실패에 포함되지 않고 반복해도 circuit이 닫혀 있다.
- `500`, 연결 reset, read timeout과 잘못된 JSON은 `DependencyUnavailableException`으로 번역된다.
- 한 호출은 최대 두 번이며 두 요청 본문에 같은 request ID가 기록된다.

## 자기 설명

- 쓰기 요청 timeout이 서버의 미처리를 뜻하지 않는 이유와 멱등성 키의 관계는 무엇인가?
- 업무 거절을 Circuit Breaker 실패로 기록하면 정상 트래픽에서 어떤 잘못된 상태 전이가 생기는가?

## 검증

canonical skeleton은 bounded retry loop가 없고 Circuit Breaker가 기록할 예외 범위도 너무 넓은 고정 실패 fixture다. tracked skeleton은 수정하지 않고 학습자 workspace를 고치며, 동일한 공개 test suite가 오류 분류, timeout과 호출 횟수를 검사한다.

저장소 루트에서 learner-owned workspace를 만들고 검사한다.

```sh
./scripts/new-workspace.sh resilient-http-client
./scripts/check-workspace.sh resilient-http-client  # 먼저 지정 실패를 확인한다.
# 학습 구현: .workspace/resilient-http-client/src/main을 수정한다.
./scripts/check-workspace.sh resilient-http-client  # 수정 뒤 PASS를 확인한다.
```

## 완료 뒤 reference walkthrough

workspace 검증이 성공한 뒤에만 `reference` source를 연다. `exercises/resilient-http-client/reference` 전체가 하나의 numbering scope이며, 다음 번호는 실제 과거 작성 순서가 아니라 완료 구현을 다시 만들 때의 권장 construction order다.

<!-- implementation-order:start scope=exercises/resilient-http-client/reference semantics=recommended -->
| 번호 | 기준 파일·symbol | 먼저 고정하는 책임 |
|---:|---|---|
| 0 | [`pom.xml`](reference/pom.xml) | RestClient·validation·Resilience4j·Actuator dependency를 고정한다. |
| 1 | [`DecisionClientProperties`](reference/src/main/java/dev/guides/spring/failclosed/DecisionClientProperties.java) | base URL, 양수 timeout과 bounded retry budget을 시작 단계에서 검증한다. |
| 2 | [`DecisionClientConfiguration.decisionRestClient`](reference/src/main/java/dev/guides/spring/failclosed/DecisionClientConfiguration.java) | connect/read timeout을 실제 transport resource에 적용한다. |
| 3 | [`DecisionClient.check`](reference/src/main/java/dev/guides/spring/failclosed/DecisionClient.java) | 같은 request ID로 bounded retry하고 업무 거절과 의존성 장애를 분리한다. |
| 4 | [`application.yml`](reference/src/main/resources/application.yml) | dependency failure만 Circuit Breaker에 기록하고 business decline은 제외한다. |
<!-- implementation-order:end -->

다음 명령은 canonical comparator 자체의 test이며 learner workspace 검증을 대신하지 않는다.

```sh
./scripts/mvn-guide.sh -pl :resilient-http-client-reference -am test
```

비교를 마치면 [테스트 경계](../../docs/05-quality-and-operations/01-test-boundaries-testcontainers-and-wiremock.md)로 진행한다.
