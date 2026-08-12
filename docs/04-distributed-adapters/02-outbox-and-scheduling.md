# Outbox와 Spring 스케줄링

Outbox가 필요한 이유와 중복 전달의 일반 원리는 `guide-distributed-services`가 소유한다. 이 장은 Spring transaction, repository, scheduler와 message gateway를 안전하게 연결하는 구현 경계를 다룬다.

## 업무 상태와 Outbox 행을 같은 transaction에 둔다

application service는 외부 broker를 transaction 안에서 호출하지 않는다.

```text
@Transactional writer
  → 업무 entity 저장
  → Outbox entity 저장
  → commit

별도 publisher
  → 보류 행 조회
  → message gateway 발행
  → 결과 기록
```

`@Transactional` method가 자기 호출로 우회되지 않는지 확인한다. DB commit 이후 cache 갱신과 publisher wake-up은 transaction 밖에서 수행한다.

## scheduler와 transaction 책임을 분리한다

`@Scheduled` method 하나가 긴 transaction을 열고 network I/O까지 수행하지 않게 한다.

```java
@Scheduled(fixedDelayString = "${outbox.poll-interval}")
void publishBatch() {
  for (UUID id : pendingFinder.nextBatch()) {
    publisher.publishOne(id);
  }
}
```

- finder는 제한된 batch와 안정적인 order를 반환한다.
- 여러 instance가 처리하면 `SKIP LOCKED`나 lease를 사용한다.
- gateway 발행과 완료 기록 사이의 process 종료를 허용한다.
- `publishOne`은 별도 Bean의 transaction 경계로 둔다.

중복 발행이 가능하므로 event ID를 안정적으로 유지한다. publisher가 재시도할 때 새 event ID를 만들지 않는다.

## 실패 상태를 저장한다

보류 행에는 최소한 다음 정보가 필요하다.

```text
attemptCount
nextAttemptAt
lastErrorCode
publishedAt
```

오류 원문과 credential을 저장하지 않는다. 최대 시도 횟수 뒤 격리 상태와 수동 재처리 절차를 정한다. 실패한 한 행이 전체 batch를 영구적으로 막지 않게 한다.

## 종료와 중복 실행을 검증한다

scheduler가 같은 instance에서 겹쳐 실행되지 않는지, 여러 instance가 같은 행을 동시에 처리하지 않는지 확인한다. shutdown 중 새 batch를 시작하지 않고 진행 중인 발행은 제한 시간 안에 끝낸다.

관찰할 application metric은 다음과 같다.

- 보류 행 수
- 가장 오래된 보류 행의 나이
- 발행 성공·실패 수
- 재시도·격리 수
- 한 batch 처리 시간

## 실습

[멱등성과 Outbox 실습](../../exercises/idempotency-outbox/README.md)은 Redis를 힌트로 제한하면서 첫 발행 실패를 저장하고 다음 실행에서 같은 행을 복구한다. Capstone의 통합 Outbox는 primary path의 나머지 문서를 마친 뒤 검증한다.
