
package dev.guides.spring.failclosed;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.NotBlank;
import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

// [Implementation 1] URL·양수 timeout·bounded attempt를 시작 단계에서 검증한다.
@ConfigurationProperties("clients.decision")
@Validated
public record DecisionClientProperties(
    @NotBlank String baseUrl,
    @NotNull Duration connectTimeout,
    @NotNull Duration readTimeout,
    @Min(1) @Max(3) int maxAttempts) {
  public DecisionClientProperties {
    requirePositive(connectTimeout, "connect-timeout");
    requirePositive(readTimeout, "read-timeout");
  }

  private static void requirePositive(Duration value, String name) {
    if (value != null && (value.isZero() || value.isNegative())) {
      throw new IllegalArgumentException(name + "은 양수여야 합니다.");
    }
  }
}
