# 전체 시간 예산과 재시도

## 목표

업무 거절과 일시 실패를 구분하고, 같은 operation ID와 전체 deadline 안에서만 재시도합니다.

## 구현할 계약

- 재시도는 같은 operation ID를 사용합니다.
- backoff는 양수이며 하나의 전체 deadline 안에서만 적용됩니다.
- `BusinessRejection`은 재시도하거나 breaker 실패로 기록하지 않고, half-open probe에서는 응답 성공으로 회로를 닫습니다.
- 다음 backoff가 전체 deadline을 넘으면 새 시도를 시작하지 않습니다.
- 연속 transient failure가 임계값에 도달하면 breaker가 열립니다.
- 열린 breaker는 의존성을 호출하지 않고 빠르게 거절합니다.

## 실패 조건

`skeleton`은 시도마다 새 ID를 만들고 모든 예외를 재시도하며 deadline을 무시합니다. 이는 중복 효과와 retry amplification을 만들 수 있습니다.

## 작업

`Executor.execute`에서 실패 분류, deadline 검사와 키 보존을 구현합니다. 실제 sleep 대신 `VirtualClock`을 사용합니다.

## 권장 구현 순서

아래 번호는 실제 과거 작성 순서가 아니라, 이 reference 전체를 이해하기 위한 권장 학습용 구성 순서입니다.

| 번호 | 구현 대상 | 책임과 연결 |
|---|---|---|
| Implementation 1 | 실패 유형 | 업무 거절, transient failure, deadline, open circuit를 분리합니다. |
| Implementation 2 | `VirtualClock` | deadline과 backoff의 결정적인 시간 소유자를 둡니다. |
| Implementation 3 | `Dependency` 경계 | operation ID 보존과 호출 결과를 관찰할 수 있게 합니다. |
| Implementation 4 | `CircuitBreaker` | 연속 transient failure와 probe lifecycle을 소유합니다. |
| Implementation 4-1 | `CircuitBreaker.beforeCall` | OPEN 대기 시간과 HALF_OPEN 전이를 호출 전에 판정합니다. |
| Implementation 4-2 | `CircuitBreaker.recordSuccess` | 의존성 응답 뒤 실패 표본을 지우고 회로를 닫습니다. |
| Implementation 4-3 | `CircuitBreaker.recordTransientFailure` | transient failure만 집계하고 실패한 probe의 새 open window를 시작합니다. |
| Implementation 5 | `DeadLetter` | 재생에 필요한 event ID, operation ID, payload를 묶습니다. |
| Implementation 5-1 | `DeadLetterQueue` | 재생 대기 메시지와 제거 lifecycle을 소유합니다. |
| Implementation 5-2 | `DeadLetterQueue.replayNext` | handler 성공 뒤에만 원본을 제거합니다. |
| Implementation 6 | `Executor` | 하나의 deadline 안에서 retry, backoff, breaker를 조정합니다. |
| Implementation 6-1 | `Executor.execute` | 같은 operation ID를 유지하고 분류된 실패에만 재시도합니다. |

## 완료 기준

- 모든 재시도가 같은 operation ID와 하나의 전체 deadline을 사용합니다.
- 0 이하 backoff를 거절하고, 다음 backoff가 deadline을 넘으면 새 시도를 시작하지 않습니다.
- 업무 거절은 재시도·breaker 실패 횟수에서 제외되고 transient 실패만 집계되며, half-open 업무 응답 뒤에는 회로가 닫힙니다.
- open 뒤 반개방 probe가 성공하면 닫히며, 실패 메시지는 같은 event ID·operation ID·payload로 DLQ에서 재생됩니다.

## 자기 설명

- 시도별 timeout 합계와 업무 전체 deadline은 어떻게 다릅니까?
- backoff와 breaker가 있어도 업무 거절을 재시도해서는 안 되는 이유는 무엇입니까?

## 검증

처음 한 번 안전한 학습자 workspace를 만듭니다. 이미 같은 경로가 있으면 덮어쓰지 않고 실패합니다.

```sh
./scripts/new-workspace.sh retry-budget
```

학습자 복사본은 다음 정본 명령으로 검사합니다.

```sh
./scripts/verify-java.sh .workspace/retry-budget
```

workspace 검증을 통과하고 위 자기 설명에 답한 뒤에만 reference와 비교합니다.

```sh
./scripts/verify-java.sh \
  exercises/03-resilience-and-load/01-retry-budget/reference
```
