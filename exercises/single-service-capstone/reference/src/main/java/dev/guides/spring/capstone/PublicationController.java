package dev.guides.spring.capstone;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.net.URI;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/publications")
public final class PublicationController {
  private final PublicationService service;

  public PublicationController(PublicationService service) {
    this.service = service;
  }

  @PostMapping
  public ResponseEntity<PublicationResponse> create(
      Authentication authentication,
      @RequestHeader("Idempotency-Key")
          @NotBlank @Size(max = 120) String idempotencyKey,
      @Valid @RequestBody CreatePublicationRequest request) {
    PublicationResult result = service.create(
        authentication.getName(),
        idempotencyKey,
        request);
    if (result.created()) {
      return ResponseEntity
          .created(URI.create("/api/publications/" + result.response().id()))
          .body(result.response());
    }
    return ResponseEntity.ok(result.response());
  }
}
