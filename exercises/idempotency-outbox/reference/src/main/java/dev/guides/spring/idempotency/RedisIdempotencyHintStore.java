package dev.guides.spring.idempotency;

import java.time.Duration;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

@Component
public class RedisIdempotencyHintStore implements IdempotencyHintStore {
  private static final String PREFIX = "guide:idempotency:";
  private static final Duration TTL = Duration.ofMinutes(10);

  private final StringRedisTemplate redis;

  public RedisIdempotencyHintStore(StringRedisTemplate redis) {
    this.redis = redis;
  }

  @Override
  public Optional<OperationResult> get(String key) {
    String stored = redis.opsForValue().get(redisKey(key));
    if (stored == null) {
      return Optional.empty();
    }

    String[] fields = stored.split("\\|", 2);
    if (fields.length != 2) {
      throw new IllegalStateException("Redis에 저장된 멱등 처리 결과 형식이 올바르지 않습니다.");
    }
    return Optional.of(new OperationResult(UUID.fromString(fields[0]), Long.parseLong(fields[1])));
  }

  @Override
  public void put(String key, OperationResult result) {
    String value = result.operationId() + "|" + result.quantity();
    redis.opsForValue().set(redisKey(key), value, TTL);
  }

  private String redisKey(String key) {
    return PREFIX + key;
  }
}
