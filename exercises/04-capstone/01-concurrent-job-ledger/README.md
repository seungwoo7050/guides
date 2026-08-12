# 동시 작업 원장 capstone

이 실습은 Java 과정의 개별 주제를 하나의 작은 애플리케이션으로 결합합니다. 작업 원장은 크레딧과 차감 명령을 제한된 실행기에서 처리하고, 같은 작업이 다시 들어와도 성공한 효과가 한 번만 적용되게 합니다.

프레임워크, 데이터베이스와 네트워크는 사용하지 않습니다. 목표는 Java 언어·객체·시간·동시성·빌드·검증 계약을 한 JVM 안에서 스스로 완성하는 것입니다.

## 목표

값 객체, 주입된 시간, 원자적 잔액 변경, 작업별 결과 공유와 제한된 실행기 수명을 결합해 실패 뒤에도 설명 가능한 동시 작업 원장을 완성합니다.

## 권장 구현 순서

`reference/` 전체가 하나의 numbering scope입니다. 번호는 실제 과거 작성 순서가 아니라 여러 파일을 오가며 원장을 만드는 학습용 권장 구현 순서입니다. 제공된 Maven scaffold에는 Implementation 0을 부여하지 않습니다.

| 순서 | 구현 위치 | 책임 |
|---:|---|---|
| 1 | `JobId` | non-null·non-blank 작업 identity를 만듭니다. |
| 2 | `JobCommand` | 지원하는 command family를 sealed boundary로 닫습니다. |
| 2-1 | `CreditJob` | 양수 credit 불변식을 생성 시점에 고정합니다. |
| 2-2 | `DebitJob` | 양수 debit 불변식을 생성 시점에 고정합니다. |
| 3 | `JobKind` | 원장이 기록할 effect 종류를 닫힌 집합으로 고정합니다. |
| 3-1 | `JobReceipt` | effect 종류와 완료 시각을 불변 evidence로 표현합니다. |
| 4 | `ConcurrentJobLedger` fields와 constructor | balance, lock, clock, job registry, executor와 close state의 owner를 만듭니다. |
| 5 | `ConcurrentJobLedger.apply` | 다음 balance·count를 먼저 계산하고 두 state를 한 lock 안에서 commit합니다. |
| 5-1 | `currentBalance` | balance lock 아래에서 잔액을 관찰합니다. |
| 5-2 | `appliedJobCount` | 같은 lock 아래에서 짝을 이루는 적용 횟수를 관찰합니다. |
| 6 | `JobSlot` | command와 모든 중복 호출이 공유할 completion identity를 묶습니다. |
| 6-1 | `execute`, `JobTask` | executor의 성공·실패를 shared Future 완료로 번역합니다. |
| 7 | `submit` | ID별 dedup·conflict를 원자적으로 결정하고 rejection 때 admission을 rollback합니다. |
| 8 | `close(Duration)` | idempotent한 정상→강제 종료와 interruption restoration을 구현합니다. |
| 8-1 | `cancelQueued` | 승인됐지만 시작하지 못한 작업 Future를 취소합니다. |

## 공개 계약

`ConcurrentJobLedger`는 다음을 만족해야 합니다.

- 초기 잔액, 작업자 수와 대기열 용량은 생성 시점에 검증합니다.
- `CreditJob`과 `DebitJob`의 금액은 양수여야 합니다.
- 같은 `JobId`와 같은 명령을 반복 제출하면 같은 완료 결과를 공유합니다.
- 같은 `JobId`에 다른 명령을 제출하면 즉시 거절합니다.
- 성공한 작업은 잔액과 적용 횟수를 정확히 한 번만 바꿉니다.
- 잔액 부족과 정수 오버플로는 상태를 바꾸지 않고 실패합니다.
- 완료 시각은 주입된 `Clock`에서 얻습니다.
- 실행기의 작업자 수와 대기열은 제한되어야 하며 포화 상태를 호출자가 관찰할 수 있어야 합니다.
- 종료 뒤 새 작업은 거절합니다.
- 종료 대기가 인터럽트되면 인터럽트 상태를 보존합니다.

## 구현 순서

1. 정본 생성 명령으로 `.workspace/concurrent-job-ledger`를 만들고 `JobId`, `CreditJob`, `DebitJob`의 생성 불변식을 확인합니다.
2. 한 스레드에서 크레딧과 차감을 정확하게 적용합니다.
3. 잔액 변경 전체를 하나의 원자성 경계로 묶습니다.
4. 작업 ID별 완료 결과를 기억해 같은 명령의 중복 효과를 제거합니다.
5. 제한된 `ThreadPoolExecutor`와 명시적인 거절 정책을 사용합니다.
6. 실패한 작업이 중간 상태를 남기지 않는지 검사합니다.
7. 종료와 인터럽트 경로를 완성합니다.

처음에는 skeleton 테스트가 여러 계약에서 실패합니다.

```sh
./scripts/new-workspace.sh exercises/04-capstone/01-concurrent-job-ledger
./scripts/check-workspace.sh exercises/04-capstone/01-concurrent-job-ledger
```

구현이 reference와 같은 클래스 내부 구조를 가질 필요는 없습니다. 공개 계약, 실패 뒤 상태와 종료 수명을 더 명확하게 지키는 다른 설계도 유효합니다.

## 완료 기준

- [ ] 같은 ID·같은 명령은 하나의 Future와 효과를 공유하고 같은 ID·다른 명령은 즉시 거절됩니다.
- [ ] 동시 credit/debit, 잔액 부족과 오버플로 뒤에도 balance와 applied count 불변식이 유지됩니다.
- [ ] 포화·정상 종료·timeout·인터럽트 종료가 제한 시간 안에 끝나고 시작하지 못한 Future는 취소됩니다.

## 자기 설명

- 작업 ID를 결과 완료 뒤에만 기록하면 동시 중복 제출에서 어떤 race가 생기나요?
- `shutdownNow()`가 반환한 대기 작업의 Future를 취소하지 않으면 호출자는 어떤 무한 대기 상태를 보게 되나요?

## 검증

```sh
./scripts/check-workspace.sh exercises/04-capstone/01-concurrent-job-ledger
```

workspace가 통과하고 자기 설명을 마친 뒤에만 비교용 구현을 검증하고 `reference/` 소스를 읽습니다.

```sh
./scripts/mvn-guide.sh -pl :concurrent-job-ledger-reference -am test
```
