package dev.guides.spring.kafkaavro;

import java.util.concurrent.TimeUnit;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

@Component
public class EventPublisher {
  private final KafkaTemplate<String, byte[]> kafka;
  private final AvroEventCodec codec;
  private final String topic;

  public EventPublisher(
      KafkaTemplate<String, byte[]> kafka,
      AvroEventCodec codec,
      @Value("${guide.kafka.publish-topic}") String topic) {
    this.kafka = kafka;
    this.codec = codec;
    this.topic = topic;
  }

  public void publish(String key, TaskSubmitted event) {
    try {
      kafka.send(topic, key, codec.encode(event)).get(10, TimeUnit.SECONDS);
    } catch (Exception exception) {
      throw new IllegalStateException("Kafka 이벤트 발행에 실패했습니다.", exception);
    }
  }
}
