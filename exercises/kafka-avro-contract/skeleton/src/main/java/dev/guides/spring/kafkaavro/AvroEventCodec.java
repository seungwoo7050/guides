package dev.guides.spring.kafkaavro;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import org.apache.avro.Schema;
import org.apache.avro.generic.GenericData;
import org.apache.avro.generic.GenericDatumReader;
import org.apache.avro.generic.GenericDatumWriter;
import org.apache.avro.generic.GenericRecord;
import org.apache.avro.io.DecoderFactory;
import org.apache.avro.io.EncoderFactory;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

@Component
public class AvroEventCodec {
  private final Schema schema;

  public AvroEventCodec() {
    try (InputStream input = new ClassPathResource("avro/task-submitted.avsc").getInputStream()) {
      this.schema = new Schema.Parser().parse(input);
    } catch (IOException exception) {
      throw new IllegalStateException("Avro 스키마를 읽을 수 없습니다.", exception);
    }
  }

  public byte[] encode(TaskSubmitted event) {
    GenericRecord record = new GenericData.Record(schema);
    record.put("taskId", event.taskId());
    record.put("itemCount", event.itemCount());
    record.put("category", event.category());
    try (var output = new ByteArrayOutputStream()) {
      var encoder = EncoderFactory.get().binaryEncoder(output, null);
      new GenericDatumWriter<GenericRecord>(schema).write(record, encoder);
      encoder.flush();
      return output.toByteArray();
    } catch (IOException exception) {
      throw new IllegalStateException("이벤트를 Avro 형식으로 인코딩할 수 없습니다.", exception);
    }
  }

  public TaskSubmitted decode(byte[] payload) {
    try {
      var decoder = DecoderFactory.get().binaryDecoder(payload, null);
      GenericRecord record = new GenericDatumReader<GenericRecord>(schema).read(null, decoder);
      return new TaskSubmitted(
          record.get("taskId").toString(),
          (Long) record.get("itemCount"),
          record.get("category").toString());
    } catch (IOException exception) {
      throw new IllegalArgumentException("Avro 이벤트를 디코딩할 수 없습니다.", exception);
    }
  }
}
