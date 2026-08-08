package dev.guides.spring.capstone;

import java.time.Clock;
import java.util.Optional;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class PublicationWriter {
  private final PublicationRepository publications;
  private final Clock clock;

  public PublicationWriter(
      PublicationRepository publications,
      Clock clock) {
    this.publications = publications;
    this.clock = clock;
  }

  @Transactional(readOnly = true)
  public Optional<PublicationResponse> findExisting(
      String actorId,
      String idempotencyKey) {
    return publications.findByActorIdAndIdempotencyKey(actorId, idempotencyKey)
        .map(PublicationEntity::toResponse);
  }

  @Transactional
  public PublicationResult createOrFind(
      String actorId,
      String idempotencyKey,
      CreatePublicationRequest request) {
    var existing = publications.findByActorIdAndIdempotencyKey(
        actorId,
        idempotencyKey);
    if (existing.isPresent()) {
      return new PublicationResult(existing.orElseThrow().toResponse(), false);
    }

    PublicationEntity publication = publications.saveAndFlush(
        PublicationEntity.create(
            actorId,
            idempotencyKey,
            request,
            clock.instant()));
    return new PublicationResult(publication.toResponse(), true);
  }
}
