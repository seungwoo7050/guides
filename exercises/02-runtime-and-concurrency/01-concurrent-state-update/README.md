# 동시 상태 갱신 실습

초기 값이 100인 카운터에서 두 스레드가 각각 80을 차감합니다. 두 스레드가 같은 값을 읽고 판단한 뒤 쓰면 각 작업은 성공했다고 기록하면서 전체 결과는 계약을 위반할 수 있습니다.

`RacyCounter`는 배리어로 동일한 교차 실행을 반복해서 만듭니다. `LockedCounter`는 읽기·판단·쓰기를 하나의 원자성 경계에 둡니다.

## 목표

공유 상태의 읽기·판단·쓰기가 분리될 때 깨지는 보존 법칙을 결정적으로 재현하고, 잠금 범위를 계약 전체로 확장해 복구합니다.

## 권장 구현 순서

`reference/` 전체가 하나의 numbering scope입니다. 번호는 실제 과거 작성 순서가 아니라 경쟁을 먼저 재현한 뒤 같은 불변식을 잠금으로 보호하는 학습용 권장 구현 순서입니다. 제공된 Maven scaffold에는 Implementation 0을 부여하지 않습니다.

| 순서 | 구현 위치 | 책임 |
|---:|---|---|
| 1 | `RacyCounter.trySubtract` | 의도적으로 분리된 읽기·판단·쓰기가 만드는 손실 갱신을 드러냅니다. |
| 1-1 | `RacyCounter.await` | 우연한 sleep 대신 barrier가 같은 interleaving을 소유합니다. |
| 2 | `DeterministicRaceDemo.main` | bounded wait, Future 실패 전달, 보존 법칙 evidence와 executor 정리를 조립합니다. |
| 3 | `LockedCounter.trySubtract` | 읽기·판단·쓰기를 하나의 lock ownership 경계로 묶습니다. |
| 3-1 | `LockedCounter.value` | 관찰도 같은 state ownership 경계를 사용합니다. |

## 확인할 계약

- `sleep`이 아니라 latch와 barrier로 경쟁을 재현합니다.
- 작업 스레드의 예외를 `Future.get()`으로 호출자에게 전달합니다.
- 최종 값만 아니라 성공 횟수와 승인된 변경량의 합을 함께 확인합니다.
- 잠금은 읽기·판단·쓰기 전체를 보호합니다.

```sh
./scripts/new-workspace.sh exercises/02-runtime-and-concurrency/01-concurrent-state-update
./scripts/check-workspace.sh exercises/02-runtime-and-concurrency/01-concurrent-state-update
```

## 완료 기준

- [ ] 배리어로 두 작업이 같은 초기 값을 읽는 교차 실행을 만들고 보존 법칙 위반을 관찰합니다.
- [ ] `LockedCounter`에서는 두 차감 중 하나만 승인되고 `accepted + value == initial`이 유지됩니다.
- [ ] 모든 Future·barrier·executor 대기에 제한 시간이 있으며 종료 후 작업 스레드가 남지 않습니다.

## 자기 설명

- `value` 필드를 `volatile`로 바꾸는 것만으로 읽기·판단·쓰기 계약이 원자적이 되지 않는 이유는 무엇인가요?
- 최종 값만 검사하지 않고 승인 금액의 합을 함께 검사해야 어떤 손실 갱신을 발견할 수 있나요?

## 검증

```sh
./scripts/check-workspace.sh exercises/02-runtime-and-concurrency/01-concurrent-state-update
```

workspace가 통과하면 자신의 결정적 재현 프로그램에서 보존 법칙 evidence를 확인합니다.

```sh
./scripts/mvn-guide.sh -f .workspace/concurrent-state-update/pom.xml package
java -cp .workspace/concurrent-state-update/target/classes \
  dev.guides.java.concurrentstate.DeterministicRaceDemo
```

자기 설명을 마친 뒤에만 비교용 구현을 확인합니다.

```sh
./scripts/mvn-guide.sh -pl :concurrent-state-update-reference -am test
```
