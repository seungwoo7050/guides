# Spring Security 요청 모델

Spring Security는 Controller 앞의 filter chain에서 요청을 해석하고 인증 정보를 `SecurityContext`에 둔다. 인증과 권한 판단이 어디서 수행되는지 모르면 permit rule 하나가 전체 API를 열거나, 이미 인증된 사용자를 다시 request body에서 신뢰하게 된다.

## 요청은 SecurityFilterChain을 먼저 통과한다

일반적인 흐름은 다음과 같다.

```text
HTTP request
→ SecurityFilterChain
→ credential 추출
→ AuthenticationManager / provider
→ SecurityContext 저장
→ request authorization
→ DispatcherServlet
→ method authorization
```

`requestMatchers`는 구체적인 공개 경로부터 선언한다. 마지막은 `anyRequest().authenticated()`처럼 닫힌 기본값으로 둔다.

```java
@Bean
SecurityFilterChain apiSecurity(HttpSecurity http) throws Exception {
  return http
      .authorizeHttpRequests(auth -> auth
          .requestMatchers("/actuator/health/**").permitAll()
          .requestMatchers(HttpMethod.GET, "/api/catalog/**").authenticated()
          .anyRequest().denyAll())
      .httpBasic(Customizer.withDefaults())
      .build();
}
```

개발 중 임시 `permitAll()`을 남기지 않는다. path pattern과 method 조합이 실제 endpoint를 모두 덮는지 security test로 고정한다.

## Authentication은 이미 검증된 주체다

Controller는 body나 `X-User-Id` header를 사용자 정본으로 신뢰하지 않는다. 인증 계층이 만든 `Authentication` 또는 principal에서 actor를 가져온다.

```java
@PostMapping("/projects")
ProjectResponse create(
    Authentication authentication,
    @Valid @RequestBody CreateProjectRequest request) {
  return service.create(authentication.getName(), request);
}
```

외부 gateway가 서명한 사용자 header를 전달하는 구조라면 애플리케이션이 gateway를 우회해 직접 노출되지 않는지, header를 누가 제거·생성하는지 인프라 계약까지 필요하다.

## 인증 방식은 세션 정책과 함께 고른다

- browser session: server가 session을 저장하고 cookie로 식별한다.
- HTTP Basic: 단순한 실습과 내부 도구에 적합하지만 매 요청 credential이 전송된다.
- bearer token: token 검증·만료·회전과 audience 계약이 필요하다.

방식을 섞기 전에 저장 위치, logout 의미, 만료와 폐기 경로를 정한다. 이 가이드는 Spring filter와 authorization 적용을 다루며 OAuth/OIDC protocol 전체는 별도 전문 영역이다.

## PasswordEncoder를 우회하지 않는다

비밀번호를 평문이나 단순 hash로 저장하지 않는다. `PasswordEncoder`를 사용하고 algorithm 변경을 고려해 `{id}encoded` 형식을 유지한다. 로그인 실패 이유로 사용자 존재 여부를 노출하지 않는다.

실습의 in-memory user는 filter·권한 경계를 작게 재현하기 위한 것이며 운영 사용자 저장 전략을 뜻하지 않는다.

## 401과 403을 구분한다

- 인증이 없거나 실패했다면 401이다.
- 인증은 성공했지만 권한이 부족하면 403이다.

두 응답은 HTML login page가 아니라 API의 `ProblemDetail` 계약을 반환하도록 entry point와 access denied handler를 구성할 수 있다. 자세한 내부 예외는 노출하지 않는다.

## method security는 두 번째 경계다

URL rule만으로 객체 단위 권한을 모두 표현하기 어렵다.

```java
@PreAuthorize("@projectAccess.canEdit(#projectId, authentication.name)")
public ProjectResponse rename(long projectId, String title) { ... }
```

`@EnableMethodSecurity`가 실제로 활성화되어야 하며, 같은 클래스 안의 자기 호출로 우회하지 않는지 확인한다. URL 권한과 method 권한은 서로 대체 관계가 아니다.

[Security 경계 실습](../../exercises/security-boundaries/README.md)에서 인증 없음, 역할 부족, 객체 소유권과 CSRF 실패를 실제 MockMvc 요청으로 구분한다.
