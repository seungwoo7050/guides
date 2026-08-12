
package dev.guides.spring.boundaries;

import java.net.URI;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

// [Implementation 4] 입력 오류와 업무 정책 위반을 서로 다른 ProblemDetail로 번역한다.
@RestControllerAdvice
public final class ProblemDetailsAdvice {
  @ExceptionHandler(PolicyViolationException.class)
  ProblemDetail handlePolicy(PolicyViolationException exception) {
    ProblemDetail detail = ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, exception.getMessage());
    detail.setType(URI.create("urn:guide:problem:policy-violation"));
    detail.setTitle("정책 위반");
    detail.setProperty("errorCode", exception.errorCode());
    return detail;
  }

  @ExceptionHandler(MethodArgumentNotValidException.class)
  ProblemDetail handleValidation(MethodArgumentNotValidException exception) {
    ProblemDetail detail = ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, "요청 값이 올바르지 않습니다.");
    detail.setType(URI.create("urn:guide:problem:invalid-request"));
    detail.setTitle("잘못된 요청");
    detail.setProperty("errorCode", "INVALID_REQUEST");
    Map<String, String> fields = new LinkedHashMap<>();
    exception.getBindingResult().getFieldErrors()
        .forEach(error -> fields.putIfAbsent(error.getField(), error.getDefaultMessage()));
    detail.setProperty("fields", fields);
    return detail;
  }
}
