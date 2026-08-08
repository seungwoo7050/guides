# 단일 서비스 통합 실습

## 목표

인증된 editor의 publication 생성 API에 Security, 외부 policy, PostgreSQL transaction, Outbox, Redis cache와 Micrometer 증거를 연결한다. 같은 actor와 멱등성 키의 완료 결과는 DB가 정본이다.

## 완료 기준

- 인증·역할·입력 오류는 각각 401·403·400이며 publication과 Outbox 상태를 바꾸지 않는다.
- 첫 생성은 201과 Location을 반환하고 publication·Outbox·양수 TTL cache·생성 metric을 함께 남긴다.
- cache를 비운 재요청과 동시 요청 8개 모두 기존 DB 결과로 수렴하며 외부 policy를 중복 호출하지 않는다.
- policy `409`는 업무 거절 metric과 409를, `500`은 Circuit Breaker 실패와 503을 만든다.

## 자기 설명

- policy 호출을 advisory lock보다 앞에 두거나 DB 완료 조회보다 앞에 두면 어떤 중복 부작용이 생기는가?
- transaction commit 뒤 cache 쓰기가 실패해도 publication 생성 자체를 실패로 바꾸지 않는 이유는 무엇인가?

## 검증

canonical skeleton에는 보안 경계, advisory lock, Outbox 저장과 commit 뒤 cache 갱신 결함이 있으며 고정 실패 fixture로 남는다. tracked skeleton은 수정하지 않고 학습자 workspace를 고치며 reference와 byte-identical 공개 test를 사용한다.

```sh
./scripts/new-workspace.sh single-service-capstone
#학습 구현: .workspace/single-service-capstone/src/main을 수정한다.
./scripts/check-workspace.sh single-service-capstone
./scripts/mvn-guide.sh -pl :single-service-capstone-reference -am test
```

PostgreSQL `18.4-alpine`, Redis `8.8.0-alpine`, WireMock 3.12.1을 사용하며 Kafka protocol은 `kafka-avro-contract` 실습이 담당한다.
