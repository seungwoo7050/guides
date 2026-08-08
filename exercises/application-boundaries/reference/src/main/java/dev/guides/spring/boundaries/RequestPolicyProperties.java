
package dev.guides.spring.boundaries;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

@ConfigurationProperties("request.policy")
@Validated
public record RequestPolicyProperties(
    @Min(1) long minQuantity,
    @Min(1) long maxQuantity,
    @NotNull String category) {

  public RequestPolicyProperties {
    if (maxQuantity < minQuantity) {
      throw new IllegalArgumentException("최대 수량은 최소 수량보다 작을 수 없습니다.");
    }
  }
}
