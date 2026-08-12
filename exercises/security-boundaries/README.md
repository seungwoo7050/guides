# Spring Security 경계 실습

## 목표

인증, 역할, 객체 소유권과 CSRF를 서로 다른 보안 경계로 다룬다. 모든 실패는 내부 예외를 노출하지 않고 `application/problem+json` 계약으로 반환한다.

## 완료 기준

- 인증 없는 조회는 `401 AUTHENTICATION_REQUIRED`, 다른 사용자의 변경은 `403 ACCESS_DENIED`다.
- 소유자라도 CSRF token이 없는 변경은 거부되고, 소유자와 token이 함께 있을 때만 성공한다.
- 빈 제목은 MVC validation에서 400으로 거부되며 저장 상태는 바뀌지 않는다.

## 자기 설명

- 401과 403을 같은 응답으로 합치면 client와 운영자가 잃는 증거는 무엇인가?
- URL 접근 규칙만으로 객체 소유권을 판정할 수 없는 이유는 무엇인가?

## 검증

canonical skeleton은 모든 요청을 허용하고 CSRF와 method security를 끈 고정 실패 fixture다. tracked skeleton은 수정하지 않고 학습자 workspace를 닫힌 기본값으로 고쳐 동일한 공개 test suite를 통과시킨다.

저장소 루트에서 learner-owned workspace를 만들고 검사한다.

```sh
./scripts/new-workspace.sh security-boundaries
./scripts/check-workspace.sh security-boundaries  # 먼저 지정 실패를 확인한다.
# 학습 구현: .workspace/security-boundaries/src/main을 수정한다.
./scripts/check-workspace.sh security-boundaries  # 수정 뒤 PASS를 확인한다.
```

## 완료 뒤 reference walkthrough

workspace 검증이 성공한 뒤에만 `reference` source를 연다. `exercises/security-boundaries/reference` 전체가 하나의 numbering scope이며, 다음 번호는 실제 과거 작성 순서가 아니라 완료 구현을 다시 만들 때의 권장 construction order다.

<!-- implementation-order:start scope=exercises/security-boundaries/reference semantics=recommended -->
| 번호 | 기준 파일·symbol | 먼저 고정하는 책임 |
|---:|---|---|
| 0 | [`pom.xml`](reference/pom.xml) | Spring MVC·validation·Security dependency 경계를 고정한다. |
| 1 | [`ProjectStore`](reference/src/main/java/dev/guides/spring/security/ProjectStore.java) | project state와 owner의 정본을 한 component가 소유한다. |
| 2 | [`ProjectAccess.canEdit`](reference/src/main/java/dev/guides/spring/security/ProjectAccess.java) | 인증 이름과 object owner를 비교하는 권한 결정을 분리한다. |
| 3 | [`ProjectController.rename`](reference/src/main/java/dev/guides/spring/security/ProjectController.java) | request validation과 method authorization을 mutation 앞에 둔다. |
| 4 | [`SecurityConfiguration`](reference/src/main/java/dev/guides/spring/security/SecurityConfiguration.java) | 사용자·password encoder와 method security baseline을 구성한다. |
| 4-1 | [`SecurityConfiguration.securityFilterChain`](reference/src/main/java/dev/guides/spring/security/SecurityConfiguration.java) | health 예외 외에는 인증을 요구하고 기본 CSRF 보호와 401·403 응답을 유지한다. |
<!-- implementation-order:end -->

다음 명령은 canonical comparator 자체의 test이며 learner workspace 검증을 대신하지 않는다.

```sh
./scripts/mvn-guide.sh -pl :security-boundaries-reference -am test
```

비교를 마치면 [JPA 트랜잭션과 잠금](../../docs/03-persistence-and-cache/01-jpa-transactions-and-locking.md)으로 진행한다.
