
package dev.guides.spring.boundaries;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;

// [Implementation 2] transport 형식 검증을 controller의 업무 정책과 분리한다.
public record PreviewRequest(
    @Min(1) long quantity,
    @NotBlank String category) {}
