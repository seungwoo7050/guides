package dev.guides.spring.kafkaavro;

import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.Acknowledgment;
import org.springframework.stereotype.Component;

@Component
public class EventConsumer {
  private final AvroEventCodec codec;
  private final EventProbe probe;

  public EventConsumer(AvroEventCodec codec, EventProbe probe) {
    this.codec = codec;
    this.probe = probe;
  }

  // [Implementation 5] decode와 처리 증거가 성공한 뒤에만 offset을 확정한다.
  @KafkaListener(topics = "${guide.kafka.consume-topic}", groupId = "${guide.kafka.group-id}")
  public void consume(ConsumerRecord<String, byte[]> record, Acknowledgment acknowledgment) {
    TaskSubmitted event = codec.decode(record.value());
    probe.record(record.key(), event);
    acknowledgment.acknowledge();
  }
}
