
package dev.guides.spring.boundaries;

import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/requests")
public final class PreviewController {
  private final RequestPolicyProperties policy;

  public PreviewController(RequestPolicyProperties policy) {
    this.policy = policy;
  }

  @PostMapping("/preview")
  public PreviewResponse preview(@Valid @RequestBody PreviewRequest request) {
    if (!policy.category().equals(request.category())) {
      throw new PolicyViolationException("CATEGORY_NOT_SUPPORTED", "지원하지 않는 분류입니다.");
    }
    if (request.quantity() < policy.minQuantity()) {
      throw new PolicyViolationException("QUANTITY_OUT_OF_RANGE", "허용 범위를 벗어난 수량입니다.");
    }
    return new PreviewResponse(request.quantity(), request.category(), true);
  }
}
