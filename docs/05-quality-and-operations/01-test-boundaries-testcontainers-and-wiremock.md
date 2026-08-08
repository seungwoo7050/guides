# 테스트 경계, Testcontainers와 WireMock

좋은 테스트는 모든 의존성을 실제로 실행하거나 모두 mock으로 바꾸는 것이 아니다. 확인하려는 계약에 맞는 가장 작은 실행 경계를 선택한다.

## 검증 질문과 테스트 종류를 맞춘다

| 질문 | 권장 경계 |
|---|---|
| 순수 계산·상태 전이가 맞는가 | JUnit 단위 테스트 |
| JSON binding·validation·ProblemDetail이 연결되는가 | MockMvc / `@WebMvcTest` |
| Security filter와 method authorization이 동작하는가 | MockMvc + `spring-security-test` |
| JPA query와 transaction이 PostgreSQL에서 맞는가 | 실제 PostgreSQL Testcontainer |
| migration이 빈 DB에서 적용되는가 | Spring Context + PostgreSQL Testcontainer |
| Redis serializer·TTL·장애 처리가 맞는가 | Redis Testcontainer |
| 외부 HTTP 오류를 올바르게 분류하는가 | WireMock |
| Kafka serializer·listener·ack가 맞는가 | embedded 또는 실제 test broker |
| 전체 Bean·설정·adapter 조립이 맞는가 | 제한된 `@SpringBootTest` |

모든 test를 `@SpringBootTest`로 만들지 않는다. 반대로 실제 기술 계약을 mock만으로 검증했다고 판단하지 않는다.

## Testcontainers를 성공 조건의 일부로 둔다

Docker를 사용할 수 없을 때 통합 테스트를 조용히 skip하면 `verify.sh` 성공의 의미가 달라진다. 이 저장소의 필수 integration test는 컨테이너를 시작하지 못하면 실패한다.

- test마다 독립적인 DB·key·topic namespace를 사용한다.
- container reuse에 의존하지 않는 최종 검사를 둔다.
- migration은 빈 DB에서 첫 version부터 적용한다.
- test가 만든 thread, executor와 client를 종료한다.
- 실패해도 container cleanup이 수행되게 한다.

## 동시성 테스트를 결정적으로 만든다

단순히 thread를 많이 만들고 `sleep`하는 방식은 경쟁 구간을 보장하지 않는다. barrier와 latch로 시작점을 맞추고 모든 `Future` 결과를 읽는다.

검사 대상은 HTTP status만이 아니다.

```text
성공 요청 수
최종 DB 상태
constraint 위반 수
Outbox 행 수
Redis key 수
외부 호출 횟수
```

## skeleton 실패도 검증 자산이다

각 skeleton은 알려진 결함 때문에 test가 실패해야 한다. 루트 `verify.sh`는 다음을 모두 확인한다.

1. reference 전체가 통과한다.
2. 각 skeleton test가 실제 test failure로 실패한다.
3. dependency resolution이나 compile error를 의도한 실패로 오인하지 않는다.

skeleton을 수정한 학습자는 해당 경로에서 test가 통과하는 것을 목표로 하지만, 저장소 정본에서는 실패 사례가 보존된다.

## 루트 검증 계약

```sh
./prepare.sh
./verify.sh
```

`prepare.sh`는 dependency와 Docker image를 준비하고 폐기 파일을 정리한다. `verify.sh`는 다음 순서로 검사한다.

```text
최종 트리와 문서 링크
→ POM·JSON·Java 정적 검사
→ reference compile
→ reference test와 integration test
→ skeleton의 의도한 실패
→ 검증 전후 최종 source tree 동일성
→ 새 Testcontainers 자원이 남지 않았는지 확인
```

필수 검사가 실행되지 못하면 전체 결과는 실패다. `SKIP`을 성공으로 바꾸지 않는다.
