
package dev.guides.spring.boundaries;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;

public record PreviewRequest(
    @Min(1) long quantity,
    @NotBlank String category) {}
