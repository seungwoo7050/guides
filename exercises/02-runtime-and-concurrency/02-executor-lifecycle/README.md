# 실행기 수명 주기 실습

요청마다 스레드를 새로 만들거나 제한 없는 대기열을 사용하면 부하가 커질수록 자원 사용과 대기 시간이 통제되지 않습니다. 이 실습에서는 실행기의 용량과 종료를 공개 계약으로 만듭니다.

## 목표

작업자·대기열·대기 시간을 모두 제한하고 포화, 실패, timeout, 인터럽트와 종료를 호출자가 관찰할 수 있는 실행기 API로 만듭니다.

## 구현할 계약

- 작업자 수와 대기열 크기를 생성 시점에 고정합니다.
- 대기열이 가득 차면 `RejectedExecutionException`으로 거절합니다.
- 작업 예외는 `Future.get()`으로 관찰합니다.
- 제한 시간이 지난 작업은 인터럽트로 취소합니다.
- 정상 종료에서는 제출된 작업을 기다립니다.
- 제한 시간 안에 끝나지 않으면 남은 작업을 취소합니다.
- 종료 대기가 인터럽트되면 인터럽트 상태를 복원합니다.

```sh
./mvnw -f exercises/02-runtime-and-concurrency/02-executor-lifecycle/skeleton/pom.xml test
./mvnw -pl :executor-lifecycle-reference -am test
```

검사는 `CountDownLatch`로 작업 순서를 고정합니다. 컴퓨터가 느리거나 빠르다는 사실을 합격 조건으로 사용하지 않습니다. JFR 관찰은 루트 `./verify.sh`에도 포함됩니다.

## 완료 기준

- [ ] 작업자와 큐가 찬 상태에서 세 번째 제출이 `RejectedExecutionException`으로 즉시 실패합니다.
- [ ] 작업 예외는 Future에서 보존되고 timeout 작업은 인터럽트 취소되었다는 신호를 남깁니다.
- [ ] 정상·강제·인터럽트 종료 경로 모두 제한 시간 안에 끝나며 대기 작업 Future가 미완료로 남지 않습니다.

## 자기 설명

- 제한 없는 큐가 rejection을 없애는 대신 시스템 과부하를 숨기는 이유는 무엇인가요?
- timeout을 보고하는 것과 실제 작업을 `cancel(true)`로 중단하는 것은 어떻게 다른가요?

## 검증

```sh
./scripts/mvn-guide.sh -f exercises/02-runtime-and-concurrency/02-executor-lifecycle/skeleton/pom.xml test
./scripts/mvn-guide.sh -pl :executor-lifecycle-reference -am test
```
