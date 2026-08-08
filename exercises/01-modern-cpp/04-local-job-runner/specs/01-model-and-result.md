# 단계 1: 값 모델과 Result 계약

`JobId`, `JobStatus`, `SubmitError`, `JobSnapshot`의 공개 형태는 앞선 실습과 문서에서 확정한 scaffold로 제공됩니다. 먼저 각 타입이 정수·boolean·내부 참조 대신 어떤 잘못된 상태를 막는지 설명합니다. 그다음 `Result<Value, Error>`의 잘못된 접근 거부와 `submit`의 입력 오류 분기를 완성합니다.

완료 조건은 다음과 같습니다.

- `JobId` 비교가 값 의미론을 따르고 정수와 암묵적으로 섞이지 않습니다.
- 성공 `Result`의 `error()`와 실패 `Result`의 `value()`는 `std::logic_error`로 거부됩니다.
- 빈 이름, 빈 callable, 종료된 runner, 가득 찬 queue가 서로 다른 오류입니다.
- caller는 성공 여부를 검사한 뒤 값 또는 오류 중 활성 상태에만 접근합니다.
