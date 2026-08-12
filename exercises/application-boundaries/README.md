# 애플리케이션 경계 실습

## 목표

설정 binding, HTTP 입력 검증과 업무 정책을 서로 다른 경계에 배치한다. 범위를 벗어난 요청은 RFC 9457 `ProblemDetail`로 번역하고, 서로 모순되는 설정은 첫 요청 전 Context 시작 단계에서 거부한다.

## 완료 기준

- 최소값보다 작은 요청과 최대값보다 큰 요청이 모두 `POLICY_VIOLATION`으로 거부된다.
- 비어 있거나 형식이 잘못된 본문은 controller 업무 코드에 도달하기 전에 400이 된다.
- `minimum > maximum` 설정으로 Context를 시작하면 원인을 포함한 검증 오류로 실패한다.

## 자기 설명

- Bean Validation과 업무 범위 검사를 같은 annotation 하나로 합치면 어떤 변경에 취약한가?
- 잘못된 설정을 첫 요청이 아니라 시작 단계에서 거부해야 하는 운영상 이유는 무엇인가?

## 검증

canonical skeleton의 `PreviewController`는 최대 경계를 빠뜨린 고정 실패 fixture다. tracked skeleton은 수정하지 않고 학습자 workspace에 누락된 최대 경계를 추가해 최소·최대 경계를 함께 보존한다.

저장소 루트에서 learner-owned workspace를 만들고 검사한다.

```sh
./scripts/new-workspace.sh application-boundaries
./scripts/check-workspace.sh application-boundaries  # 먼저 지정 실패를 확인한다.
# 학습 구현: .workspace/application-boundaries/src/main을 수정한다.
./scripts/check-workspace.sh application-boundaries  # 수정 뒤 PASS를 확인한다.
```

## 완료 뒤 reference walkthrough

workspace 검증이 성공한 뒤에만 `reference` source를 연다. `exercises/application-boundaries/reference` 전체가 하나의 numbering scope이며, 다음 번호는 실제 과거 작성 순서가 아니라 완료 구현을 다시 만들 때의 권장 construction order다.

<!-- implementation-order:start scope=exercises/application-boundaries/reference semantics=recommended -->
| 번호 | 기준 파일·symbol | 먼저 고정하는 책임 |
|---:|---|---|
| 0 | [`pom.xml`](reference/pom.xml) | Spring MVC·validation·Actuator dependency 경계를 고정한다. |
| 1 | [`RequestPolicyProperties`](reference/src/main/java/dev/guides/spring/boundaries/RequestPolicyProperties.java) | 설정 binding과 최소·최대 교차 불변식을 Context 시작 과정에서 검증한다. |
| 2 | [`PreviewRequest`](reference/src/main/java/dev/guides/spring/boundaries/PreviewRequest.java) | transport 입력의 형식 경계를 업무 정책과 분리한다. |
| 3 | [`PreviewController.preview`](reference/src/main/java/dev/guides/spring/boundaries/PreviewController.java) | 검증된 입력에 category와 quantity 업무 정책을 적용한다. |
| 4 | [`ProblemDetailsAdvice`](reference/src/main/java/dev/guides/spring/boundaries/ProblemDetailsAdvice.java) | validation과 policy 실패를 서로 다른 HTTP 문제 계약으로 번역한다. |
<!-- implementation-order:end -->

다음 명령은 canonical comparator 자체의 test이며 learner workspace 검증을 대신하지 않는다.

```sh
./scripts/mvn-guide.sh -pl :application-boundaries-reference -am test
```

비교를 마치면 [Spring Security 요청 모델](../../docs/02-web-and-security/02-spring-security-request-model.md)로 진행한다.
