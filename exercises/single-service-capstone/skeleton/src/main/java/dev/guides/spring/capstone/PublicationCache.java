package dev.guides.spring.capstone;

import tools.jackson.databind.json.JsonMapper;
import java.util.Optional;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

@Component
public class PublicationCache {
  public PublicationCache(
      StringRedisTemplate redis,
      JsonMapper mapper,
      PublicationMetrics metrics,
      PublicationCacheProperties properties) {}

  public Optional<PublicationResponse> find(
      String actorId,
      String idempotencyKey) {
    return Optional.empty();
  }

  public void put(
      String actorId,
      String idempotencyKey,
      PublicationResponse response) {}

  public static String key(String actorId, String idempotencyKey) {
    return "publication:result:v1:missing";
  }
}
