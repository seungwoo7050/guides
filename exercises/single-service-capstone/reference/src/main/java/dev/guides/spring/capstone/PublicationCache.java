package dev.guides.spring.capstone;

import tools.jackson.databind.json.JsonMapper;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Optional;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

// [Implementation 6] cache가 actor/key digest와 TTL을 소유하되 DB 정확성을 뒤집지 않는다.
@Component
public class PublicationCache {
  private final StringRedisTemplate redis;
  private final JsonMapper mapper;
  private final PublicationMetrics metrics;
  private final PublicationCacheProperties properties;

  public PublicationCache(
      StringRedisTemplate redis,
      JsonMapper mapper,
      PublicationMetrics metrics,
      PublicationCacheProperties properties) {
    this.redis = redis;
    this.mapper = mapper;
    this.metrics = metrics;
    this.properties = properties;
  }

  public Optional<PublicationResponse> find(
      String actorId,
      String idempotencyKey) {
    try {
      String value = redis.opsForValue().get(key(actorId, idempotencyKey));
      if (value == null) {
        return Optional.empty();
      }
      return Optional.of(mapper.readValue(value, PublicationResponse.class));
    } catch (RuntimeException exception) {
      metrics.cacheFailure();
      return Optional.empty();
    }
  }

  public void put(
      String actorId,
      String idempotencyKey,
      PublicationResponse response) {
    try {
      redis.opsForValue().set(
          key(actorId, idempotencyKey),
          mapper.writeValueAsString(response),
          properties.ttl());
    } catch (RuntimeException exception) {
      metrics.cacheFailure();
    }
  }

  public static String key(String actorId, String idempotencyKey) {
    String material = actorId.length() + ":" + actorId + idempotencyKey;
    try {
      byte[] digest = MessageDigest.getInstance("SHA-256")
          .digest(material.getBytes(StandardCharsets.UTF_8));
      return "publication:result:v1:" + HexFormat.of().formatHex(digest);
    } catch (NoSuchAlgorithmException exception) {
      throw new IllegalStateException("SHA-256을 사용할 수 없습니다.", exception);
    }
  }
}
