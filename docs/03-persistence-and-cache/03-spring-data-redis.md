# Spring Data Redis 어댑터

Redis를 도입하기 전에 어떤 상태를 저장하고 장애 때 무엇을 허용할지 정한다. 이 장은 멱등성의 일반 이론이 아니라 Spring Data Redis의 연결, 직렬화와 transaction 이후 갱신 경계를 다룬다.

## Redis 역할을 이름으로 구분한다

- 조회 cache: 없어도 정본에서 복구 가능
- 계산 결과 memoization: 재계산 비용과 TTL을 관리
- rate limit·lease: 장애 시 fail-open 또는 fail-closed 정책 필요
- ephemeral coordination: 만료와 소유권 token 필요

한 `RedisTemplate<Object, Object>`로 모든 역할을 섞지 않는다. key prefix, value schema, TTL과 실패 정책을 adapter별로 고정한다.

## 직렬화 계약을 명시한다

Java 기본 직렬화를 사용하지 않는다. 문자열, 명시적인 JSON 또는 versioned binary schema를 선택한다.

```text
key: publication:result:v1:{sha256(actorId-length + actorId + idempotencyKey)}
value: {"id":"...","actorId":"...","title":"...","source":"..."}
ttl: 24h
```

시간, 금액과 enum의 표현을 명시한다. class package 이름이 바뀌어 기존 cache를 읽지 못하는 구조를 피한다. key 원문을 이어 붙이면 구분자 충돌과 민감 정보 노출이 생길 수 있으므로 길이 prefix 또는 hash로 안정적인 key material을 만든다. TTL은 설정으로 소유하고 test에서 양수인지 확인한다.

## 정본 transaction과 cache 쓰기를 분리한다

정확성은 데이터베이스 transaction과 constraint에서 만든다. cache는 commit 뒤에 갱신한다.

```text
DB transaction에서 상태 확정
→ commit 성공
→ Redis cache 갱신
```

transaction 안에서 cache를 먼저 변경하면 rollback된 결과가 cache에 남는다. `@TransactionalEventListener(phase = AFTER_COMMIT)` 또는 transaction을 수행하는 Bean 밖의 orchestration layer를 사용할 수 있다.

## 장애를 application 의미로 번역한다

조회 cache가 비었거나 실패하면 **외부 정책을 다시 호출하기 전에** DB 정본에서 이미 완료된 결과를 찾는다. 이미 처리된 멱등 요청이 cache miss 때문에 새로운 외부 판단을 받으면, 첫 성공 뒤 정책이 바뀌었을 때 동일 요청이 거절되는 모순이 생긴다.

```text
Redis 결과 조회
→ miss이면 DB 완료 결과 조회
→ 기존 결과가 있으면 cache 복원 후 반환
→ 둘 다 없을 때만 새 외부 정책과 쓰기 흐름 실행
```

반대로 강한 제한 상태를 Redis에만 두었다면 장애 시 요청을 허용할지 거부할지 업무 위험에 따라 정해야 한다.

Spring Data의 connection exception을 Controller까지 노출하지 않는다. adapter가 cache miss와 dependency failure를 구분하고, 허용된 fallback만 적용한다. 실패 수와 fallback 횟수를 metric에 남긴다.

## stampede와 TTL 집중을 관찰한다

많은 key가 동시에 만료되거나 service가 재시작되면 정본 저장소로 요청이 몰릴 수 있다.

- TTL에 제한된 jitter 적용
- key별 single-flight
- bounded warm-up
- DB pool과 cache fallback에 별도 limit

기법을 무조건 추가하기 전에 cache miss latency와 원본 부하를 측정한다.

## 다음 단계

[Spring Kafka와 Avro](../04-distributed-adapters/01-spring-kafka-and-avro.md)에서 비동기 전달 계약을 먼저 다룬다. Redis와 Outbox를 결합하는 멱등성 실습은 Kafka 실습과 Outbox 문서까지 마친 뒤 시작한다. 멱등성·재전달의 일반 원리는 `guide-distributed-services`가 소유한다.
