# 불확실한 응답

## 목표

서버가 상태를 저장한 직후 응답이 사라지는 상황에서 timeout을 업무 실패로 확정하지 않고 같은 `operation_id`로 결과를 확인합니다.

## 구현할 계약

- 같은 `operation_id`와 같은 입력은 이전 결과를 반환합니다.
- 같은 ID에 다른 입력이 오면 충돌로 거절합니다.
- 저장 뒤 응답을 잃어도 클라이언트는 조회로 `ACCEPTED`를 확인합니다.
- 재시도와 조회 뒤에도 업무 효과 횟수는 1입니다.

## 실패 조건

`skeleton`은 `ResponseLostException`을 받으면 결과를 조회하지 않고 `UNKNOWN`을 반환합니다. 서버의 상태는 이미 바뀌었으므로 이 응답만 보고 새 키로 다시 요청하면 중복 효과가 생길 수 있습니다.

## 작업

`Client.reserve`를 수정합니다. 예외를 숨기는 것이 아니라 동일한 연산 ID로 `Gateway.query`를 호출해 확정된 결과가 있는지 확인합니다. 조회에도 결과가 없을 때만 `UNKNOWN`을 반환합니다.

## 권장 구현 순서

범위는 이 실습의 `reference` 프로젝트 전체이며 아래 번호를 모든 구현 파일에서
공유합니다. 이 번호는 학습을 위한 권장 구성 순서이고 실제 Git 이력이나 과거 작성
순서를 뜻하지 않습니다.

| 순서 | 구현 위치 | 책임과 연결 |
| --- | --- | --- |
| Implementation 1 | `Status`, `Result` | 서버의 확정 결과와 클라이언트의 미확정 결과 어휘를 먼저 고정합니다. |
| Implementation 2 | `Gateway` | 연산별 입력·결과와 업무 효과의 소유 경계를 만듭니다. |
| Implementation 2-1 | `Gateway.reserve` | 입력 지문을 검사하고 신규 연산의 효과를 한 번만 기록합니다. |
| Implementation 2-2 | `Gateway.query` | 응답 유실 뒤 서버의 확정 결과를 다시 읽는 복구 경계를 엽니다. |
| Implementation 3 | `Client` | 전송 실패를 업무 실패로 단정하지 않고 같은 연산 ID로 조회합니다. |

## 완료 기준

- 응답 유실 뒤에도 같은 `operationId` 조회가 `ACCEPTED`를 돌려줍니다.
- 같은 키의 재시도 뒤 업무 효과 수가 정확히 1입니다.
- 같은 키에 다른 입력을 보내면 상태 변경 없이 충돌로 거절됩니다.

## 자기 설명

- timeout을 곧바로 업무 실패로 확정하면 왜 중복 효과가 생길 수 있습니까?
- 재시도 키는 어떤 업무 입력까지 함께 식별해야 합니까?

## 검증

처음 한 번 저장소 루트에서 추적된 skeleton을 안전한 workspace로 복사합니다. 기존
destination은 덮어쓰지 않습니다.

```sh
./scripts/new-workspace.sh uncertain-outcome
```

학습자 복사본은 다음 정본 명령으로 검사합니다.

```sh
./scripts/verify-java.sh .workspace/uncertain-outcome
```

저장소 전체 검증은 reference가 통과하고 skeleton이 이 계약에서 실패하는지 확인합니다.

학습자 workspace 검증을 통과하고 위 자기 설명에 답한 뒤에만 reference와 비교합니다.
개별 reference를 실행하려면 루트의 준비를 마친 뒤 다음을 사용합니다.

```sh
./scripts/verify-java.sh \
  exercises/01-boundaries-and-failure/01-uncertain-outcome/reference
```
