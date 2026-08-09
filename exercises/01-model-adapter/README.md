# 실습 01: Model adapter 계약

## 목표

서로 다른 model provider 또는 scripted model을 같은 coding-agent runtime에 연결할 내부 protocol을 설계합니다.

## 초기 상태

다음 세 구현을 연결해야 한다고 가정합니다.

```text
Provider A: streaming text와 tool call delta
Provider B: 완성된 JSON action만 반환
Scripted: fixture 조건에 따라 action 또는 오류 반환
```

provider SDK type을 runtime에 직접 노출하면 안 됩니다.

## 설계할 책임

- `ModelRequest`
- streaming `ModelEvent`
- `ActionCandidate`
- usage·latency receipt
- cancellation
- provider error taxonomy
- schema repair policy
- model profile와 version identity

## 필수 시나리오

### 정상

- text explanation 뒤 `search_text` action
- 여러 argument delta가 합쳐져 valid action 완성
- usage와 completion reason 기록

### 경계

- 빈 text와 valid action
- action 없이 사용자 질문
- context budget 직전 요청
- provider가 server-side state ID 반환

### 실패

- 잘린 JSON
- unknown tool
- 추가 field
- rate limit
- stream 중 network 중단
- cancel과 response completion 경쟁
- 같은 request ID의 중복 event

## 필수 산출물

```text
model-adapter-contract.md
model-request.schema
model-event.schema
action-candidate.schema
error-taxonomy.md
scripted-scenarios.md
adapter-state-machine.md
```

실제 JSON Schema 사용은 선택이지만 field와 invariant는 정확히 기록합니다.

## 검증 계획

- scripted adapter가 모든 event 순서를 결정적으로 생성합니다.
- partial action은 실행기로 전달되지 않습니다.
- invalid action은 tool registry 이전에 거절됩니다.
- cancel 뒤 late event가 session을 다시 활성화하지 않습니다.
- provider를 바꿔도 runtime event와 verifier가 바뀌지 않습니다.

## 실행 파일과 판정

- 구현 경계: [starter `model.py`](../10-capstone-local-coding-agent/starter/coding_agent/model.py), [starter `contracts.py`](../10-capstone-local-coding-agent/starter/coding_agent/contracts.py)
- 비교 구현: [reference `model.py`](../10-capstone-local-coding-agent/reference/coding_agent/model.py), [reference `contracts.py`](../10-capstone-local-coding-agent/reference/coding_agent/contracts.py)
- 공개 판정: [`test_stage_01_model.py`](../10-capstone-local-coding-agent/tests/test_stage_01_model.py)

```sh
python3 exercises/10-capstone-local-coding-agent/tests/run.py --implementation reference --stage 01
python3 exercises/10-capstone-local-coding-agent/tests/run.py --implementation starter --stage 01 --expect-incomplete
python3 exercises/10-capstone-local-coding-agent/tests/run.py --implementation .workspace/local-coding-agent --stage 01
```

starter의 `NotImplementedError` 메시지에 있는 `stage-01`은 의도한 미완성 표식입니다. 대표 실패는 partial·unknown action이나 terminal 뒤 late event가 실행 가능한 action으로 통과하는 경우입니다. 위 설계 산출물만으로는 완료가 아니며, 같은 불변식을 구현한 learner module, canonical test 결과, 정상·대표 실패 trace를 함께 제출합니다.

사람 검토 질문:

- provider SDK type이나 server-side state가 runtime의 정본 계약으로 새어 나오지 않는다는 증거는 무엇입니까?
- cancel과 terminal event가 경쟁할 때 단 하나의 종료 상태만 남는 이유를 trace로 설명할 수 있습니까?

## 의도적 비범위

- model 품질 비교
- fine-tuning
- prompt 최적화
- provider authentication UI
