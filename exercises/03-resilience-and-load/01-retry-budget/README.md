# 전체 시간 예산과 재시도

## 목표

업무 거절과 일시 실패를 구분하고, 같은 operation ID와 전체 deadline 안에서만 재시도합니다.

## 구현할 계약

- 재시도는 같은 operation ID를 사용합니다.
- `BusinessRejection`은 재시도하거나 breaker 실패로 기록하지 않습니다.
- 다음 backoff가 전체 deadline을 넘으면 새 시도를 시작하지 않습니다.
- 연속 transient failure가 임계값에 도달하면 breaker가 열립니다.
- 열린 breaker는 의존성을 호출하지 않고 빠르게 거절합니다.

## 실패 조건

`skeleton`은 시도마다 새 ID를 만들고 모든 예외를 재시도하며 deadline을 무시합니다. 이는 중복 효과와 retry amplification을 만들 수 있습니다.

## 작업

`Executor.execute`에서 실패 분류, deadline 검사와 키 보존을 구현합니다. 실제 sleep 대신 `VirtualClock`을 사용합니다.

## 검증

```sh
./scripts/verify-java.sh \
  exercises/03-resilience-and-load/01-retry-budget/reference
```
