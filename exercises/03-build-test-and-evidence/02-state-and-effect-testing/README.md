# 상태와 효과 검증 실습

메서드가 값을 반환했다는 사실만으로 작업이 정확히 한 번 적용되었다고 말할 수 없습니다. 반복 요청에서 반환값, 내부 상태와 외부 효과의 횟수를 함께 확인합니다.

## 목표

같은 key의 반복 호출이 같은 완료 결과를 공유하고 상태 변경과 외부 효과를 한 번만 남긴다는 사실을 서로 독립된 관찰값으로 증명합니다.

## 권장 구현 순서

`reference/` 전체가 하나의 numbering scope입니다. 번호는 실제 과거 작성 순서가 아니라 state와 effect를 독립 evidence로 만들고 하나의 service 경계에서 조립하는 학습용 권장 구현 순서입니다. 제공된 Maven scaffold에는 Implementation 0을 부여하지 않습니다.

| 순서 | 구현 위치 | 책임 |
|---:|---|---|
| 1 | `OperationResult` | 반복 호출이 공유할 불변 completion evidence를 정의합니다. |
| 2 | `StateStore.append` | state change evidence의 소유자를 만듭니다. |
| 2-1 | `StateStore.changes`, `netChange` | 내부 collection을 노출하지 않고 독립 관찰값을 제공합니다. |
| 3 | `ExternalEffect.send` | 외부 effect evidence의 별도 소유자를 만듭니다. |
| 3-1 | `ExternalEffect.calls` | effect 호출을 방어적 snapshot으로 관찰합니다. |
| 4 | `IdempotentOperationService` constructor와 fields | 현재 상태, collaborator와 key별 결과 registry의 소유권을 고정합니다. |
| 5 | `IdempotentOperationService.apply` | effect 전에 기존 완료 결과를 찾고 같은 key가 한 transition을 공유하게 합니다. |
| 5-1 | `apply`의 mutation·effect·publication 블록 | 한 JVM에서 state, effect와 결과를 한 번만 남기는 순서를 고정합니다. |
| 5-2 | `currentValue` | mutation 권한을 노출하지 않고 현재 state evidence를 제공합니다. |

## 증명할 계약

- 같은 키의 반복 요청은 같은 작업 식별자를 반환합니다.
- 현재 값은 한 번만 변경됩니다.
- 상태 저장소에는 변경 기록 한 건만 추가됩니다.
- 외부 효과는 한 번만 발생합니다.
- 약한 테스트가 중복 효과를 놓치는 이유를 설명합니다.

```sh
./scripts/new-workspace.sh exercises/03-build-test-and-evidence/02-state-and-effect-testing
./scripts/check-workspace.sh exercises/03-build-test-and-evidence/02-state-and-effect-testing
```

이 실습은 분산 시스템의 전체 멱등성 설계를 가르치지 않습니다. 한 JVM 안에서 테스트가 반환값 외의 상태와 효과까지 관찰해야 한다는 Java 검증 원칙에 집중합니다.

## 완료 기준

- [ ] 스무 번의 같은 key 호출이 정확히 하나의 operation ID와 같은 현재 값을 반환합니다.
- [ ] 상태 저장소의 변경 건수·순변화와 외부 효과 호출 수가 각각 한 번임을 검사합니다.
- [ ] 약한 테스트는 defect를 놓치고 강한 테스트는 실제 skeleton 결함 때문에 실패함을 확인합니다.

## 자기 설명

- 모든 호출이 non-null을 반환했다는 사실만으로 중복 효과가 없다고 증명할 수 없는 이유는 무엇인가요?
- 같은 상태값을 반환하더라도 operation ID가 매번 달라지면 어떤 완료 결과 공유 계약이 깨지나요?

## 검증

```sh
./scripts/check-workspace.sh exercises/03-build-test-and-evidence/02-state-and-effect-testing
```

workspace가 통과하고 자기 설명을 마친 뒤에만 비교용 구현을 검증하고 `reference/` 소스를 읽습니다.

```sh
./scripts/mvn-guide.sh -pl :state-and-effect-testing-reference -am test
```
