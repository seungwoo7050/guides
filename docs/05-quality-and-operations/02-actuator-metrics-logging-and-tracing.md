# Actuator, metric, logging과 tracing

이 장은 metric 저장소나 dashboard 설치를 다루지 않는다. Spring 애플리케이션이 운영자가 판단할 수 있는 health, log, metric과 trace context를 올바르게 노출하는 방법에 집중한다.

## liveness와 readiness를 별도 group으로 노출한다

liveness는 process 재시작이 필요한 상태만 나타낸다. 일시적인 Kafka 지연, 외부 API 오류와 business backlog를 liveness에 넣어 restart loop를 만들지 않는다.

readiness는 새 요청 처리에 필수인 조건을 나타낸다. migration 실패, 필수 local resource 초기화 실패와 종료 중 상태를 반영한다. 느린 외부 호출을 health endpoint마다 동기 실행하지 않는다.

Actuator endpoint의 공개 범위를 제한한다. health의 필요한 detail만 공개하고 environment, configuration과 heap 정보는 인증 없이 노출하지 않는다.

## 구조화 로그에 판단 필드를 남긴다

```text
timestamp, level, service, traceId, spanId,
operation, actorId, aggregateId, errorCode, latencyMs
```

- 같은 오류의 stack trace를 여러 계층에서 반복 기록하지 않는다.
- password, token, 개인 key와 request body 전체를 기록하지 않는다.
- 금액과 시간에는 단위를 포함한다.
- actor·aggregate ID는 metric tag가 아니라 log·trace field로 둔다.
- idempotency key 원문은 민감도와 수명을 검토한 뒤 제한적으로 기록한다.

## application 판단에 필요한 metric을 만든다

기본 HTTP·JVM metric 외에 업무 처리 경계를 나타내는 낮은 cardinality metric을 추가한다.

- 요청 성공·거절·의존성 실패 수
- DB pool 사용·대기 수
- Redis cache hit·fallback·failure 수
- Outbox pending count와 oldest age
- Kafka processing·retry·DLT 수
- Circuit Breaker state와 short-circuit 수
- authorization denial 수

user ID, request ID와 entity ID를 tag로 넣지 않는다. 가능한 값이 무한히 늘어나는 label은 metric 시스템을 망가뜨린다.

## trace ID와 업무 식별자를 구분한다

trace ID는 하나의 관찰 흐름을 연결한다. idempotency key, event ID와 aggregate ID는 업무 계약이다. trace가 끊기거나 새로 시작되어도 중복 방지와 event 식별은 유지되어야 한다.

동기 HTTP에서 비동기 event로 trace context를 전달할 수 있지만, 신뢰하지 않는 외부 header를 그대로 내부 trace 정본으로 사용하지 않는다.

## metric 자체도 test한다

Micrometer test는 다음을 확인할 수 있다.

- 성공·실패 branch에서 기대한 counter가 증가한다.
- exception path에서도 timer가 종료된다.
- 민감하거나 high-cardinality tag가 추가되지 않는다.
- health contributor가 의도한 group에만 포함된다.

[단일 서비스 통합 과제 문서](../06-capstone.md)에서 생성 성공, 정책 거절과 Outbox 상태를 DB뿐 아니라 application metric으로도 확인할 최종 계약을 먼저 읽는다. 수집·alert·runbook은 `guide-web-infrastructure`에서 이어진다.
