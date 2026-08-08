# 인증, 객체 권한과 CSRF

역할 하나만 확인해도 되는 요청과 특정 자원의 소유권을 확인해야 하는 요청은 다르다. 또한 cookie 기반 인증에서는 사용자가 로그인되어 있다는 사실만으로 요청이 사용자의 의도에서 시작되었다고 볼 수 없다.

## URL 권한과 객체 권한을 분리한다

URL 규칙은 큰 경계를 닫는다.

```text
GET /api/projects/**   → 인증 사용자
POST /api/projects/**  → EDITOR 역할
/admin/**              → ADMIN 역할
```

그 뒤 service 또는 method security가 객체 관계를 확인한다.

```text
project.ownerId == authentication.name
organization membership가 ACTIVE
요청 역할이 해당 operation을 허용
```

요청 body의 `ownerId`와 인증 주체가 같다고 가정하지 않는다. actor는 인증 정보에서 받고, 대상 자원은 server가 조회한 뒤 관계를 판단한다.

자원 존재 여부를 숨겨야 하는 API에서는 권한 부족을 404로 바꿀 수 있다. 이 선택은 endpoint별로 일관되어야 하고 테스트에 고정한다.

## 권한 검사는 transaction과 함께 생각한다

권한을 조회한 뒤 상태를 변경하기 전에 관계가 바뀔 수 있다. 중요한 변경은 같은 transaction에서 권한에 필요한 상태와 대상 entity를 읽고 적용한다. 단순히 Controller에서 한 번 확인하고 service를 호출하는 구조는 경쟁 조건을 만들 수 있다.

Spring method security는 호출 허용 여부를 판단하지만 데이터베이스 동시성까지 해결하지 않는다. 필요한 경우 version, lock 또는 조건부 update를 함께 사용한다.

## cookie 인증에서는 CSRF를 유지한다

browser는 다른 origin의 페이지에서도 사용자의 cookie를 자동으로 보낼 수 있다. 따라서 session cookie로 인증하는 변경 요청은 CSRF token 또는 동등한 방어가 필요하다.

- 안전한 method인 GET·HEAD가 상태를 변경하지 않게 한다.
- cookie 기반 변경 요청은 CSRF token을 검사한다.
- SameSite는 보조 방어이며 모든 사용 사례를 대체하지 않는다.
- JSON API라는 이유만으로 CSRF를 자동으로 끄지 않는다.

HTTP Basic이나 bearer token을 browser 저장소에 두고 자동 첨부하는 구조도 위협 모델을 다시 검토해야 한다. `csrf().disable()`에는 왜 안전한지 설명할 수 있는 인증·client 전제가 있어야 한다.

## CORS는 인증이나 CSRF 대체물이 아니다

CORS는 browser가 다른 origin의 응답을 JavaScript에 노출할 수 있는지 정한다. server-to-server 요청, form submit과 credential 위조 전체를 막지 않는다.

허용 origin, method와 header를 명시하고 `*`와 credential 조합을 사용하지 않는다. preflight 성공이 실제 요청 권한을 의미하지 않는다.

## Security test는 실패 경계를 직접 요청한다

최소 검사는 다음을 포함한다.

- 인증 없는 요청은 401
- 인증됐지만 역할이 부족하면 403
- 다른 사용자의 자원을 변경하면 403 또는 계약된 404
- cookie/session 변경 요청에 CSRF token이 없으면 거부
- 올바른 사용자와 CSRF token은 성공
- body나 임의 header로 actor를 위조할 수 없음
- 로그아웃·만료 뒤 기존 session으로 접근할 수 없음
- 응답에 credential과 내부 예외가 없음

[Security 경계 실습](../../exercises/security-boundaries/README.md)은 위 조건 중 인증, 소유권과 CSRF를 하나의 작은 프로젝트로 검증한다.
