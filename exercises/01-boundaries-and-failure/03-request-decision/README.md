# 동기·비동기 요청 판정

## 목표

즉시 판정이 필요한 요청과 나중에 처리할 수 있는 요청의 계약을 구분하고, 정책 판정이 실패한 경로에서 상태가 바뀌지 않는지 확인합니다.

## 구현할 계약

- 동기 요청은 정책 결과를 받은 뒤에만 수량을 변경합니다.
- 정책이 거절되거나 응답하지 않으면 `REJECTED`이며 수량 변화는 0입니다.
- 비동기 수락은 `PENDING`과 작업 소유권만 약속합니다.
- 비동기 요청은 실제 처리 단계에서 정책을 확인한 뒤 결과를 확정합니다.
- 같은 operation ID는 이전 결과를 반환합니다.

## 실패 조건

`skeleton`은 정책 서비스를 호출하기 전에 수량을 먼저 예약합니다. 응답이 거절 또는 장애여도 부정 불변 조건이 깨집니다.

## 작업

`Coordinator.decideNow`에서 상태 변경의 순서를 고칩니다. 원격 정책 결과가 `ALLOW`일 때만 `CapacityLedger.reserve`를 호출합니다.

## 권장 구현 순서

범위는 이 실습의 `reference` 프로젝트 전체이며 아래 번호를 모든 구현 파일에서
공유합니다. 이 번호는 학습을 위한 권장 구성 순서이고 실제 Git 이력이나 과거 작성
순서를 뜻하지 않습니다.

| 순서 | 구현 위치 | 책임과 연결 |
| --- | --- | --- |
| Implementation 1 | `Mode`, `PolicyResult`, `Status`, 요청·결과 값 | 동기 확정과 비동기 접수가 공유할 계약 어휘를 정의합니다. |
| Implementation 2 | `CapacityLedger` | 예약 수량의 유일한 로컬 변경 경계를 만듭니다. |
| Implementation 3 | `Coordinator` | 연산별 입력·결과와 비동기 대기열의 lifecycle을 소유합니다. |
| Implementation 3-1 | `Coordinator.submit` | 입력 지문으로 중복을 막고 비동기 요청에는 `PENDING`만 약속합니다. |
| Implementation 3-2 | `Coordinator.processNext` | 대기 요청을 꺼내 정책 판정과 최종 결과 기록을 끝냅니다. |
| Implementation 3-3 | `Coordinator.decideNow` | 정책 허용 뒤에만 예약 상태를 변경합니다. |

## 완료 기준

- 정책 거절과 장애에서는 예약 수량이 0으로 유지됩니다.
- 비동기 수락은 확정 성공이 아닌 `PENDING`과 처리 소유권만 반환합니다.
- 같은 operation ID 재요청은 정책이나 상태 효과를 중복 실행하지 않습니다.

## 자기 설명

- 원격 판정보다 로컬 상태를 먼저 바꾸면 어떤 부정 불변식이 깨집니까?
- `PENDING` 응답은 호출자에게 무엇을 약속하고 무엇은 약속하지 않습니까?

## 검증

처음 한 번 저장소 루트에서 추적된 skeleton을 안전한 workspace로 복사합니다. 기존
destination은 덮어쓰지 않습니다.

```sh
./scripts/new-workspace.sh request-decision
```

학습자 복사본은 다음 정본 명령으로 검사합니다.

```sh
./scripts/verify-java.sh .workspace/request-decision
```

학습자 workspace 검증을 통과하고 위 자기 설명에 답한 뒤에만 reference와 비교합니다.

```sh
./scripts/verify-java.sh \
  exercises/01-boundaries-and-failure/03-request-decision/reference
```

정상 응답만 보지 말고 `REJECTED`와 `UNAVAILABLE`에서 `reserved == 0`인지 확인합니다.
