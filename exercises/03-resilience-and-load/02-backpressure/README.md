# 역압, Bulkhead와 Load Shedding

## 목표

유입량이 처리량보다 클 때 요청을 무한히 쌓지 않고, 각 의존성의 동시 실행과 대기열을 분리해 한 장애가 다른 흐름까지 막지 않게 합니다.

## 문제 계약

`AdmissionSystem`은 의존성별로 다음 값을 가집니다.

- 동시에 실행할 수 있는 작업 수
- 대기할 수 있는 작업 수
- 현재 실행 중인 작업과 대기 작업
- 거절된 요청 수

`submit(lane, requestId)`는 `STARTED`, `QUEUED`, `REJECTED` 중 하나를 반환합니다. 대기열이 가득 찼다면 즉시 거절해야 하며, 거절한 요청을 나중에 몰래 실행해서는 안 됩니다. 한 lane이 가득 차도 다른 lane의 용량은 영향을 받지 않아야 합니다.

## 실패 조건

skeleton은 모든 의존성이 하나의 공용 대기열을 공유하고, 대기열 상한도 적용하지 않습니다. 느린 알림 흐름을 가득 채우면 재고 확인 요청까지 밀리고, 메모리 사용량도 유입량에 따라 계속 늘어납니다.

## 권장 구현 순서

아래 번호는 실제 과거 작성 순서가 아니라, 이 reference 전체를 이해하기 위한 권장 학습용 구성 순서입니다.

| 번호 | 구현 대상 | 책임과 연결 |
|---|---|---|
| Implementation 1 | `Admission` | 즉시 실행, 제한된 대기, 명시적 거절 결과를 고정합니다. |
| Implementation 2 | `Lane` | 의존성별 실행·대기·완료 상태와 포화 근거를 소유합니다. |
| Implementation 2-1 | `Lane.submit` | 중복·만료를 먼저 판정하고 용량 안에서만 요청을 받습니다. |
| Implementation 2-2 | `Lane.completeOne` | 완료된 슬롯 하나에 대기 작업 하나만 승격합니다. |
| Implementation 2-3 | `Lane.expire` | deadline과 최대 queue age가 지난 작업을 실행 전에 제거합니다. |
| Implementation 2-4 | `Lane.oldestAge` | 가장 오래 기다린 항목의 나이로 포화 지속 시간을 드러냅니다. |
| Implementation 3 | `AdmissionSystem` | 이름별 lane을 격리하고 제어·관찰 API를 제공합니다. |

## 완료 기준

- lane별 실행·대기 수가 각각 설정 상한을 넘지 않습니다.
- 포화된 lane의 요청은 즉시 거절되고 다른 lane의 첫 요청은 시작됩니다.
- deadline이나 최대 queue age가 지난 항목은 실행되지 않고 만료 근거가 남습니다.

## 자기 설명

- 의존성별 bulkhead가 공용 queue보다 장애 격리를 잘하는 이유는 무엇입니까?
- queue 길이뿐 아니라 가장 오래 기다린 시간도 관찰해야 하는 이유는 무엇입니까?

## 검증

처음 한 번 안전한 학습자 workspace를 만듭니다. 이미 같은 경로가 있으면 덮어쓰지 않고 실패합니다.

```sh
./scripts/new-workspace.sh backpressure
```

학습자 복사본은 다음 정본 명령으로 검사합니다.

```sh
./scripts/verify-java.sh .workspace/backpressure
```

workspace 검증을 통과하고 위 자기 설명에 답한 뒤에만 reference와 비교합니다.

```sh
./scripts/verify-java.sh \
  exercises/03-resilience-and-load/02-backpressure/reference
```

저장소 루트에서 `./verify.sh`를 실행하면 reference가 다음을 만족하는지 검사합니다.

- 대기열이 가득 찬 뒤의 요청은 `REJECTED`입니다.
- 한 lane의 포화가 다른 lane의 첫 요청을 막지 않습니다.
- 완료 뒤에는 대기 중인 작업 하나만 실행 상태로 이동합니다.
- 거절된 요청은 완료 목록에 나타나지 않습니다.

같은 검사에서 skeleton은 실패해야 합니다.
