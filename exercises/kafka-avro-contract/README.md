# Kafka·Avro 계약 실습

## 목표

Avro binary event를 immutable digest의 공식 Kafka 4.3.1 컨테이너에 발행하고, 소비자가 같은 topic·event name·key·schema로 복원한 뒤에만 offset을 수동 확정한다.

## 완료 기준

- 생산자와 소비자가 `TaskSubmitted.v1` 이름과 aggregate key를 그대로 공유한다.
- 소비 결과에서 식별자·제목·schema version이 발행 입력과 일치한다.
- listener는 decode와 처리 성공 뒤 acknowledgement하며 실패 경로에서는 성공 증거를 남기지 않는다.

## 자기 설명

- 생산자와 소비자의 event 이름 불일치가 애플리케이션 시작 실패로 드러나지 않는 이유는 무엇인가?
- aggregate ID를 Kafka key로 유지하면 partition ordering 판단이 어떻게 단순해지는가?

## 검증

canonical skeleton의 잘못된 소비자 event version은 고정 실패 fixture다. tracked skeleton은 수정하지 않고 학습자 workspace를 고쳐 제한 시간 안에 같은 계약을 소비하게 만든다.

저장소 루트에서 learner-owned workspace를 만들고 검사한다.

```sh
./scripts/new-workspace.sh kafka-avro-contract
./scripts/check-workspace.sh kafka-avro-contract  # 먼저 지정 실패를 확인한다.
# 학습 구현: .workspace/kafka-avro-contract/src/main을 수정한다.
./scripts/check-workspace.sh kafka-avro-contract  # 수정 뒤 PASS를 확인한다.
```

## 완료 뒤 reference walkthrough

workspace 검증이 성공한 뒤에만 `reference` source를 연다. `exercises/kafka-avro-contract/reference` 전체가 하나의 numbering scope이며, 다음 번호는 실제 과거 작성 순서가 아니라 완료 구현을 다시 만들 때의 권장 construction order다. 이 구현은 `GenericRecord`를 사용하므로 Avro code generation CLI는 없다.

<!-- implementation-order:start scope=exercises/kafka-avro-contract/reference semantics=recommended -->
| 번호 | 기준 파일·symbol | 먼저 고정하는 책임 |
|---:|---|---|
| 0 | [`pom.xml`](reference/pom.xml) | Spring Kafka와 Avro generic codec dependency를 고정한다. |
| [Implementation 1] | [`task-submitted.avsc`](reference/src/main/resources/avro/task-submitted.avsc) | 주석을 허용하지 않는 JSON schema가 event field와 namespace의 authoritative anchor다. |
| 2 | [`AvroEventCodec`](reference/src/main/java/dev/guides/spring/kafkaavro/AvroEventCodec.java) | 같은 schema로 encode·decode하고 malformed payload 실패를 분리한다. |
| 3 | [`application.yml`](reference/src/main/resources/application.yml) | serializer, producer idempotence, manual ack와 topic identity를 고정한다. |
| 4 | [`EventPublisher.publish`](reference/src/main/java/dev/guides/spring/kafkaavro/EventPublisher.java) | aggregate key를 보존하고 bounded send 완료를 기다린다. |
| 5 | [`EventConsumer.consume`](reference/src/main/java/dev/guides/spring/kafkaavro/EventConsumer.java) | decode와 처리 증거가 성공한 뒤에만 offset을 확정한다. |
<!-- implementation-order:end -->

다음 명령은 canonical comparator 자체의 test이며 learner workspace 검증을 대신하지 않는다.

```sh
./scripts/mvn-guide.sh -pl :kafka-avro-contract-reference -am test
```

비교를 마치면 [Outbox와 스케줄링](../../docs/04-distributed-adapters/02-outbox-and-scheduling.md)으로 진행한다.
