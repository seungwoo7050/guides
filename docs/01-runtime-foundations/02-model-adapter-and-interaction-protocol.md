# Model adapter와 상호작용 프로토콜

## 목표

모델 공급자의 API, streaming event와 tool-call 형식을 코딩 에이전트 내부의 안정적인 protocol로 변환합니다. 특정 SDK 객체가 runtime 전체로 퍼지지 않게 합니다.

## adapter의 책임

Model adapter는 다음을 수행합니다.

- 내부 `ModelRequest`를 공급자 요청으로 변환합니다.
- streaming delta를 순서 있는 내부 event로 변환합니다.
- text, structured action, usage, refusal와 종료 이유를 구분합니다.
- rate limit, timeout, network, authentication과 provider error를 분류합니다.
- request identity, model identity와 usage receipt를 보존합니다.
- 취소 요청을 공급자 호출에 전달하고 종료 상태를 확정합니다.

다음은 adapter의 책임이 아닙니다.

- 파일 경로 허용 여부 판정
- command 실행
- tool 결과 진위 판정
- session 완료 판정
- 사용자 승인

## 내부 요청 계약

예시 필드:

```text
request_id
session_id
turn_id
model_profile
instruction_blocks[]
context_items[]
tool_definitions[]
response_contract
deadline
max_output_budget
previous_provider_state? 
```

`instruction_blocks`와 `context_items`를 하나의 문자열로 합쳐 출처를 잃지 않습니다. 각 항목은 origin, scope, trust, digest와 freshness를 유지합니다.

## 내부 event 계약

streaming UI와 durable state가 같은 provider-specific chunk를 직접 처리하지 않게 다음 event를 정의할 수 있습니다.

```text
ResponseStarted
TextDelta
ReasoningSummaryDelta
ActionStarted
ActionArgumentsDelta
ActionCompleted
UsageUpdated
ResponseCompleted
ResponseFailed
ResponseCancelled
```

`ActionCompleted` 전에 JSON 일부를 실행하지 않습니다. streaming 중 잘린 tool arguments를 완전한 action으로 취급하지 않습니다.

## action protocol

모델이 선택할 수 있는 action은 tool catalog에 등록된 이름과 schema로 제한합니다.

```json
{
  "action_id": "a-104",
  "tool": "search_text",
  "arguments": {
    "query": "refresh_token",
    "paths": ["src", "tests"]
  },
  "purpose": "token 사용 경로와 검사를 찾습니다."
}
```

`purpose`는 사용자 설명과 trace에 유용하지만 권한 근거가 아닙니다. 실제 허용은 principal, tool, arguments, resource grant와 policy로 판정합니다.

## schema 실패와 repair

구조화 출력 실패를 자동으로 무한 재시도하지 않습니다.

분류:

- JSON syntax 실패
- unknown tool
- 필수 field 누락
- 추가 field 금지 위반
- type·range·enum 위반
- 현재 phase에서 허용되지 않는 action
- tool catalog version 불일치

repair 요청에는 원문 전체 대신 오류 위치, 예상 schema와 허용된 action을 제공합니다. 동일 오류가 반복되면 model profile 변경, 사용자 개입 또는 session 실패로 이동합니다.

## provider state와 독립성

일부 API는 server-side conversation state나 response ID를 제공합니다. 편리하지만 내부 session의 유일한 정본으로 사용하지 않습니다.

- provider state가 만료돼도 session을 복원할 수 있어야 합니다.
- model provider를 바꿀 때 필요한 context를 재구성할 수 있어야 합니다.
- provider가 저장한 원문과 로컬 privacy policy가 충돌하지 않아야 합니다.
- adapter version과 request serialization version을 trace에 남깁니다.

## scripted adapter

실제 모델보다 먼저 scripted adapter를 설계합니다.

```text
입력 context와 tool result의 조건
→ 미리 정의한 action 또는 오류 event
```

이를 통해 다음을 결정적으로 검사합니다.

- invalid action 거절
- tool result 뒤 다음 action
- test 실패 뒤 재계획
- budget 소진
- 사용자 질문
- cancellation
- crash와 resume

실제 모델 평가는 runtime contract를 통과한 뒤 추가합니다.

## 실패 조건

- SDK response 객체를 session state에 그대로 직렬화합니다.
- text와 action을 구분하지 않고 shell parser로 해석합니다.
- tool schema를 prompt에만 쓰고 runtime validation을 하지 않습니다.
- provider retry가 같은 tool effect를 다시 실행하게 만듭니다.
- streaming partial JSON을 실행합니다.
- model의 `finish_reason`을 작업 성공으로 해석합니다.

## 완료 조건

- provider 두 개 또는 scripted/real adapter가 같은 내부 contract를 만족합니다.
- model 호출 실패와 tool 실행 실패가 서로 다른 상태로 기록됩니다.
- action schema 오류가 tool gateway에 도달하기 전에 거절됩니다.
- request·response·usage·model version을 재현 가능한 receipt로 남깁니다.
