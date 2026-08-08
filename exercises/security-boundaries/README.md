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

```sh
./scripts/new-workspace.sh security-boundaries
#학습 구현: .workspace/security-boundaries/src/main을 수정한다.
./scripts/check-workspace.sh security-boundaries
./scripts/mvn-guide.sh -pl :security-boundaries-reference -am test
```
