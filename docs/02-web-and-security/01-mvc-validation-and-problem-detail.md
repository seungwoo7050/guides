# Spring MVC 검증과 ProblemDetail

HTTP 입력, 업무 규칙과 인프라 실패는 서로 다른 경계에서 발생한다. 모든 오류를 Controller의 `try-catch` 하나로 처리하면 클라이언트 계약과 내부 복구 정책이 섞인다.

## 전송 모델과 저장 모델을 분리한다

요청 본문을 JPA entity로 직접 받지 않는다.

```java
public record CreateProjectRequest(
    @NotBlank @Size(max = 120) String title,
    @NotNull URI source) {}

public record ProjectResponse(UUID id, String title, URI source) {}
```

요청 DTO는 JSON과 HTTP 입력 계약을 표현한다. entity는 저장 구조와 영속 수명을 표현한다. application command가 따로 필요하다면 Controller에서 명시적으로 변환한다.

## 세 종류의 검증을 구분한다

### Binding과 형식 검증

잘못된 JSON, 지원하지 않는 media type, path variable 변환 실패는 MVC 경계에서 발생한다. 이 단계에서는 업무 service가 호출되지 않아야 한다.

### Bean Validation

길이, 빈 값, 숫자 범위처럼 단일 요청에서 판단할 수 있는 조건을 DTO와 method parameter에 둔다. validation message를 외부 error code로 그대로 사용하지 말고 안정적인 필드 오류 형식으로 변환한다.

`@Valid @RequestBody`의 객체 검증은 주로 `MethodArgumentNotValidException`으로 나타난다. `@RequestHeader @NotBlank`처럼 Controller method parameter에 constraint를 직접 선언하면 Spring MVC method validation이 동작하고 `HandlerMethodValidationException`이 발생할 수 있다. API advice는 두 경로를 같은 외부 계약으로 번역해야 한다.

```java
@ExceptionHandler({
    MethodArgumentNotValidException.class,
    HandlerMethodValidationException.class
})
ProblemDetail invalidRequest() { ... }
```

Spring MVC의 내장 method validation을 사용할 때 Controller class에 `@Validated`를 붙여 AOP 검증과 중복시키지 않는다. 어떤 예외가 발생하는지는 method signature에 따라 달라지므로 body와 header 실패를 각각 MockMvc로 확인한다.

### 업무 규칙

현재 저장 상태, 사용자 권한과 다른 aggregate가 필요한 규칙은 application service가 판단한다. 이미 존재하는 자원, 허용되지 않은 상태 전이와 외부 정책 거절을 이름 있는 예외 또는 결과 타입으로 표현한다.

## 상태 코드와 error code를 안정화한다

출발점은 다음과 같다.

| 원인 | HTTP 상태 | 예시 error code |
|---|---:|---|
| JSON·필드 형식 오류 | 400 | `INVALID_REQUEST` |
| 인증 정보 없음·실패 | 401 | `AUTHENTICATION_REQUIRED` |
| 권한 부족 | 403 | `ACCESS_DENIED` |
| 자원 없음 | 404 | `PROJECT_NOT_FOUND` |
| 현재 상태와 충돌 | 409 | `PROJECT_CONFLICT` |
| 의존 시스템 장애 | 503 | `DEPENDENCY_UNAVAILABLE` |

상태 코드만으로 세부 원인을 분기하게 하지 않는다. `ProblemDetail`에 프로그램이 안정적으로 판단할 `errorCode`, 필요하다면 field errors와 correlation ID를 추가한다.

```java
ProblemDetail problem = ProblemDetail.forStatusAndDetail(
    HttpStatus.CONFLICT,
    "현재 상태에서는 요청을 완료할 수 없습니다."
);
problem.setProperty("errorCode", "PROJECT_CONFLICT");
```

예외 클래스 이름, SQL, 내부 host, stack trace와 credential은 응답에 포함하지 않는다.

## 예외 번역 책임을 한곳에 둔다

`@RestControllerAdvice`는 기술 예외를 무차별적으로 숨기는 장소가 아니다. 공개하기로 한 application exception을 HTTP 계약으로 번역한다. 예상하지 못한 예외는 500으로 처리하되 상세 정보는 서버 로그에 한 번만 남긴다.

repository·HTTP client의 기술 예외는 adapter 경계에서 의미 있는 application exception으로 번역한다. Controller가 `DataAccessException`, `RestClientException`을 직접 알지 않게 한다.

## MockMvc가 실제 연결을 확인한다

순수 service test만으로는 JSON converter, validation과 exception handler 연결을 알 수 없다. MockMvc test는 다음을 검사한다.

- 실제 content type과 JSON field
- 잘못된 JSON에서 service 미호출
- field error의 안정적인 구조
- 업무 예외의 상태와 `errorCode`
- 응답에 내부 정보가 없는지

[애플리케이션 경계 실습](../../exercises/application-boundaries/README.md)에서 설정, validation과 `ProblemDetail` 변환을 같은 Context에서 확인한다.
