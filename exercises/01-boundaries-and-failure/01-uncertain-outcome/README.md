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

## 완료 기준

- 응답 유실 뒤에도 같은 `operationId` 조회가 `ACCEPTED`를 돌려줍니다.
- 같은 키의 재시도 뒤 업무 효과 수가 정확히 1입니다.
- 같은 키에 다른 입력을 보내면 상태 변경 없이 충돌로 거절됩니다.

## 자기 설명

- timeout을 곧바로 업무 실패로 확정하면 왜 중복 효과가 생길 수 있습니까?
- 재시도 키는 어떤 업무 입력까지 함께 식별해야 합니까?

## 검증

저장소 전체 검증은 reference가 통과하고 skeleton이 이 계약에서 실패하는지 확인합니다.

개별 reference를 실행하려면 루트의 준비를 마친 뒤 다음을 사용합니다.

```sh
./scripts/verify-java.sh \
  exercises/01-boundaries-and-failure/01-uncertain-outcome/reference
```
