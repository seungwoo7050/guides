# Spring Kafka와 Avro 어댑터

이 장은 Kafka 전달 보장 전체를 다시 설명하지 않는다. Spring Kafka에서 producer, listener container, serializer와 acknowledgement를 어떻게 연결하고 실제 broker로 검증하는지에 집중한다.

## 이벤트 계약의 소유 위치를 하나로 둔다

producer와 consumer가 이벤트 이름을 각자 문자열로 적지 않는다. event type, topic, key 규칙과 Avro schema의 정본을 하나로 정한다.

```text
topic: publication-events
event type: publication.created.v1
key: publicationId
schema: schemas/publication-created-v1.avsc
```

Spring 설정, 테스트 fixture와 release manifest가 같은 값을 사용하게 한다. application이 시작되었다는 사실만으로 listener가 올바른 topic에 연결되었다고 판단하지 않는다.

## serializer와 header를 명시한다

key와 value serializer를 producer·consumer 양쪽에서 고정한다. Avro logical type, namespace와 enum symbol의 호환성을 검사한다. 생성 class와 `GenericRecord` 중 어느 방식을 선택하든 schema 원본을 복제하지 않는다.

민감한 payload 전체를 오류 로그에 남기지 않는다. event ID, type, key, topic·partition·offset과 schema version을 진단 필드로 사용한다.

## 처리 뒤 acknowledgement한다

수동 acknowledgement를 사용한다면 application 상태 반영이 성공한 뒤 offset을 전진시킨다.

```text
record 수신
→ 역직렬화·계약 검사
→ 멱등 처리와 DB commit
→ acknowledgement
```

확인 전에 process가 종료되면 같은 record가 다시 전달될 수 있다. listener는 중복을 정상 입력으로 처리해야 한다. 먼저 acknowledgement하면 뒤의 실패에서 record를 잃는다.

ack mode와 transaction manager 조합은 test에서 실제로 확인한다. annotation 이름만 보고 전달 계약을 추정하지 않는다.

## 오류 종류를 분리한다

- 역직렬화·호환성 오류
- 일시적인 dependency 장애
- 재시도해도 바뀌지 않는 업무 거절
- 알려지지 않은 programming defect

모든 오류를 같은 retry와 DLT 정책으로 보내지 않는다. recoverer가 남기는 header와 원본 위치를 검사하고, 재처리 도구가 중복 효과를 만들지 않게 한다. 일반적인 retry·DLQ 설계는 `guide-distributed-services`에서 다룬다.

## listener lifecycle을 운영 신호에 연결한다

consumer assignment가 완료되었는지, shutdown 중 새 record를 받는지, 처리 중 작업을 얼마나 기다리는지 확인한다. lag와 DLT count를 application metric으로 노출하되 고유 event ID를 metric tag로 넣지 않는다.

## 실습

[Kafka·Avro 계약 실습](../../exercises/kafka-avro-contract/README.md)은 immutable digest로 고정한 공식 Kafka 4.3.1 컨테이너에 binary Avro event를 발행하고 listener가 같은 key와 field를 복원한 뒤 acknowledgement하는지 검사한다.
