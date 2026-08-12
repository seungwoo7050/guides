package dev.guides.spring.capstone;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.HandlerMethodValidationException;

// [Implementation 8-1] 입력·업무 거절·의존성 실패를 400·409·503 문제 계약으로 번역한다.
@RestControllerAdvice
public final class PublicationProblemAdvice {
  @ExceptionHandler(PolicyRejectedException.class)
  ProblemDetail rejected() {
    return problem(
        HttpStatus.CONFLICT,
        "POLICY_REJECTED",
        "외부 정책이 publication 생성을 허용하지 않았습니다.");
  }

  @ExceptionHandler(DependencyUnavailableException.class)
  ProblemDetail unavailable() {
    return problem(
        HttpStatus.SERVICE_UNAVAILABLE,
        "DEPENDENCY_UNAVAILABLE",
        "의존 서비스를 사용할 수 없습니다.");
  }

  @ExceptionHandler({
      MethodArgumentNotValidException.class,
      HandlerMethodValidationException.class
  })
  ProblemDetail invalid() {
    return problem(
        HttpStatus.BAD_REQUEST,
        "INVALID_REQUEST",
        "요청 형식이 올바르지 않습니다.");
  }

  private ProblemDetail problem(
      HttpStatus status,
      String errorCode,
      String detail) {
    ProblemDetail problem = ProblemDetail.forStatusAndDetail(status, detail);
    problem.setProperty("errorCode", errorCode);
    return problem;
  }
}
