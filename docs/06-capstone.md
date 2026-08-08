# 단일 서비스 통합 과제

개별 annotation을 아는 것과 하나의 서비스에서 경계를 올바른 순서로 조합하는 것은 다르다. 이 과제는 `publication` 생성 API를 통해 Spring Boot의 핵심 계약을 한 번에 검증한다.

## 문제

인증된 편집자가 publication 생성 요청을 보낸다. 이미 완료된 동일 요청이 없다면 외부 policy service에 허용 여부를 묻고, PostgreSQL transaction 안에 publication과 Outbox event를 함께 저장한다. commit이 끝난 뒤 Redis에 결과를 제한된 시간 동안 cache하고 application metric을 증가시킨다.

```text
HTTP Basic 인증·역할 검사
→ request validation
→ Redis 완료 결과 조회
→ PostgreSQL 완료 결과 조회
→ 새 요청일 때만 policy HTTP adapter
→ transactional writer
   ├─ advisory transaction lock
   ├─ publication
   └─ outbox event
→ commit
→ Redis result cache
→ response
```

Redis는 빠른 힌트이고 PostgreSQL은 완료 결과의 정본이다. Kafka 발행 adapter는 Outbox publisher 뒤에 연결할 수 있는 형태로 제공한다. Kafka protocol 자체의 검증은 기존 `kafka-avro-contract` 실습이 담당한다.

## 단계

### 1. 시작과 설정

- `@ConfigurationProperties`로 policy base URL·timeout, cache TTL과 Outbox 설정을 묶는다.
- HTTP·HTTPS가 아닌 URL, 비양수 timeout·TTL·poll interval은 Context 시작을 실패시킨다.
- `Clock`을 Bean으로 제공해 시간이 필요한 adapter에 명시적으로 전달한다.
- Flyway가 빈 PostgreSQL에 schema와 constraint를 생성한다.

### 2. HTTP와 Security

- 인증 없는 요청은 `401 AUTHENTICATION_REQUIRED`다.
- 인증됐지만 `EDITOR`가 아니면 `403 ACCESS_DENIED`다.
- actor ID는 request body가 아니라 `Authentication`에서 가져온다.
- body와 header validation은 모두 `400 INVALID_REQUEST`로 변환한다.
- application 오류는 내부 예외를 노출하지 않는 `ProblemDetail`로 반환한다.

이 capstone은 신뢰된 비브라우저 HTTP Basic client로 범위를 제한하고 stateless session과 비활성화된 CSRF를 사용한다. browser cookie/session API의 CSRF 계약은 `security-boundaries` 실습에서 별도로 검증한다.

### 3. 완료 결과를 먼저 찾는다

같은 `(actor, Idempotency-Key)`가 이미 처리되었다면 cache miss가 발생해도 외부 policy를 다시 호출하지 않는다.

```text
Redis hit → 기존 결과 반환
Redis miss + DB hit → cache 복원 후 기존 결과 반환
Redis miss + DB miss → 새 요청 처리
```

첫 요청 이후 policy 판단이 바뀌더라도 동일 요청은 첫 완료 결과를 반환해야 한다. test는 Redis를 비운 뒤 policy를 거절 상태로 바꾸고, 재요청이 policy를 호출하지 않는지 확인한다.

### 4. 외부 policy adapter

- `409`는 업무 거절로 변환하고 Circuit Breaker 실패에 포함하지 않는다.
- timeout, 연결 실패와 `5xx`는 `DependencyUnavailableException`으로 번역한다.
- dependency failure는 `503 DEPENDENCY_UNAVAILABLE`로 응답한다.
- policy 실패 시 데이터베이스에 아무 행도 생기지 않는다.
- actor는 인증 정보에서 가져온 값으로 전송한다.

### 5. transaction과 동시 멱등성

- `(actor_id, idempotency_key)` unique constraint를 최종 방어선으로 둔다.
- 동일 key에 대해 PostgreSQL transaction advisory lock을 얻은 뒤 다시 조회한다.
- publication과 Outbox 행은 같은 transaction에서 `saveAndFlush`로 확인한다.
- 동시에 들어온 여러 요청 중 하나만 `created=true`가 되고 행은 각각 하나만 남는다.
- 외부 HTTP 호출은 DB transaction과 lock을 잡기 전에 끝낸다.

### 6. cache와 Outbox

- cache는 writer transaction이 반환된 뒤에만 갱신한다.
- cache key는 actor와 idempotency key의 경계를 보존해 hash한다.
- cache entry에는 양수 TTL을 적용한다.
- Redis 실패가 중복 publication을 만들지 않는다.
- Outbox event ID, aggregate ID와 event type을 안정적으로 저장한다.
- Kafka record에는 event ID와 event type header를 추가한다.
- gateway 발행 성공과 `published_at` 기록을 별도 transaction으로 분리한다.

### 7. 관측성과 테스트

- 생성·중복·정책 거절·cache 실패 counter를 확인한다.
- 빈 PostgreSQL, Redis와 WireMock을 실제로 실행한다.
- HTTP status뿐 아니라 DB 행, Outbox, Redis TTL, 외부 호출 횟수와 Circuit Breaker metric을 검사한다.
- barrier로 동시 요청의 시작을 맞추고 모든 `Future` 결과를 읽는다.

## 완료 조건

[단일 서비스 통합 실습](../exercises/single-service-capstone/README.md)의 reference가 루트 `./verify.sh`에서 통과해야 한다. skeleton은 다음 결함 때문에 실패해야 한다.

- endpoint와 역할 경계가 열려 있다.
- 동일 key를 직렬화하는 advisory lock이 없다.
- transaction에서 Outbox 행을 저장하지 않는다.
- commit 뒤 Redis cache와 TTL을 갱신하지 않는다.

완료 뒤에는 개별 기능이 아니라 다음 질문에 답할 수 있어야 한다.

- 외부 호출은 왜 DB transaction 밖에 있는가?
- actor는 어느 경계에서 정본이 되는가?
- Redis가 비었거나 실패해도 첫 완료 결과를 어떻게 찾는가?
- 동시에 같은 key가 들어올 때 unique constraint 이전에 무엇이 직렬화하는가?
- Outbox 저장과 Kafka 발행은 왜 같은 순간에 완료되지 않는가?
- 어떤 실패가 409이고 어떤 실패가 503인가?
- 운영자가 처리 결과를 어떤 DB 상태와 metric으로 확인하는가?
