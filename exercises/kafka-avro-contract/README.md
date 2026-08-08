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

```sh
./scripts/new-workspace.sh kafka-avro-contract
#학습 구현: .workspace/kafka-avro-contract/src/main을 수정한다.
./scripts/check-workspace.sh kafka-avro-contract
./scripts/mvn-guide.sh -pl :kafka-avro-contract-reference -am test
```
