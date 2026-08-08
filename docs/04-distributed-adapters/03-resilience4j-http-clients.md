# Resilience4j HTTP 클라이언트

Spring HTTP client와 Resilience4j annotation을 연결할 때 핵심은 모든 비정상 응답을 같은 실패로 기록하지 않는 것이다. 업무 거절, 잘못된 응답과 dependency 장애를 adapter에서 분류한다.

## client 설정을 타입으로 묶는다

base URL, connect timeout, read timeout과 connection limit를 `@ConfigurationProperties`로 묶고 시작 단계에서 검증한다. test에서는 WireMock 주소를 같은 property로 주입한다.

`RestClient`와 `WebClient` 중 애플리케이션 실행 모델에 맞는 하나를 선택한다. blocking MVC application에서 이유 없이 reactive client와 blocking 호출을 섞지 않는다.

## 외부 응답을 application 의미로 번역한다

```text
409 정책 거절         → PolicyRejectedException
429 제한              → 명시된 retry-after 정책
5xx·연결 실패·timeout → DependencyUnavailableException
잘못된 JSON           → DependencyContractException
```

Controller가 `RestClientException`이나 vendor DTO를 직접 알지 않게 한다. adapter가 외부 계약을 내부 결과로 변환한다.

## Circuit Breaker에 기록할 실패를 제한한다

정상적인 업무 거절까지 실패로 기록하면 dependency가 정상이어도 breaker가 열린다. `recordExceptions`와 `ignoreExceptions`를 실제 exception hierarchy에 맞춘다.

annotation도 proxy를 통해 적용된다. 같은 객체 내부 호출, 직접 생성한 client와 test mock은 실제 breaker 동작을 우회할 수 있다. integration test에서 연속 실패 뒤 open 상태와 빠른 거절을 확인한다.

## retry는 불확실한 결과를 만든다

쓰기 요청 timeout은 server가 처리하지 않았다는 뜻이 아니다. 자동 retry 전에 다음이 필요하다.

- server가 인식하는 안정적인 idempotency key
- 전체 요청 deadline 안의 제한된 횟수
- backoff와 jitter
- retry 가능한 오류의 좁은 분류
- 외부 호출 횟수를 확인하는 test

일반적인 retry budget, bulkhead와 load shedding은 `guide-distributed-services`에서 다룬다. Spring 장에서는 Resilience4j 설정과 client exception 분류를 검증한다.

## fallback은 정상 응답처럼 숨기지 않는다

fallback이 허용되는 기능과 허용되지 않는 기능을 업무 정책으로 구분한다. fallback 응답에는 degraded 상태를 표현하고 metric을 남긴다. 잘못된 허용 비용이 크다면 빠르게 503을 반환하는 편이 맞을 수 있다.

## WireMock으로 protocol 실패를 재현한다

최소 시나리오는 다음과 같다.

- 정상 응답
- 업무 `4xx`
- retry 가능한 `5xx`
- 지연과 timeout
- 연결 종료
- 잘못된 JSON
- breaker open 뒤 외부 호출 수

벽시계 시간만으로 성공 여부를 판단하지 않는다. 호출 횟수, exception type, breaker metric과 최종 HTTP 응답을 함께 검사한다.

[복원력 있는 HTTP 클라이언트 실습](../../exercises/resilient-http-client/README.md)은 `409`를 업무 결과로 유지하고 반복되는 server failure만 breaker에 기록하는지 확인한다.
