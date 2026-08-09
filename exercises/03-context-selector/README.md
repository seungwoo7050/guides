# 실습 03: Context selector

## 목표

repository explorer가 찾은 많은 evidence에서 현재 가설과 action에 필요한 context packet을 선택하고, edit와 test 결과 뒤 stale item을 갱신합니다.

## 초기 상태

다음 evidence를 가진 fixture를 만듭니다.

- 같은 이름의 symbol 세 개
- production code와 관련 test
- 관련 없는 대형 log
- 오래된 history
- nested instruction
- patch 전·후 두 revision의 file
- prompt injection 문장이 있는 comment

## 설계할 책임

- `ContextItem`
- `ContextManifest`
- budget allocator
- ranking evidence
- summary와 source mapping
- staleness·invalidation
- compaction

## 필수 시나리오

### 정상

- task identifier에서 definition·reference·test를 선택
- action에 필요한 최소 excerpt 생성
- source path·line·digest 보존

### 경계

- context window가 매우 작음
- 동일 관련성 후보가 많음
- search index가 한 revision 늦음
- summary가 여러 source를 결합

### 실패

- patch 뒤 이전 excerpt 사용
- log가 budget 대부분 소비
- untrusted instruction이 authority block에 들어감
- summary가 실패 test 이름을 잃음
- hidden answer가 context 후보가 됨

## 필수 산출물

```text
context-item.schema
context-packet.md
ranking-policy.md
budget-policy.md
invalidation-table.md
compaction-contract.md
```

## 검증 계획

- 같은 task와 snapshot에서 deterministic selection mode를 제공합니다.
- edit 뒤 affected context가 stale이 됩니다.
- summary에서 원 source로 돌아갈 수 있습니다.
- authority, fact, hypothesis와 tool output이 다른 type으로 전달됩니다.
- context overflow가 임의 truncation이 아니라 명시적 failure 또는 compaction을 만듭니다.

## 실행 파일과 판정

- 구현 경계: [starter `context.py`](../10-capstone-local-coding-agent/starter/coding_agent/context.py)
- 비교 구현: [reference `context.py`](../10-capstone-local-coding-agent/reference/coding_agent/context.py)
- 공개 판정: [`test_stage_03_context.py`](../10-capstone-local-coding-agent/tests/test_stage_03_context.py)

```sh
python3 exercises/10-capstone-local-coding-agent/tests/run.py --implementation reference --stage 03
python3 exercises/10-capstone-local-coding-agent/tests/run.py --implementation starter --stage 03 --expect-incomplete
python3 exercises/10-capstone-local-coding-agent/tests/run.py --implementation .workspace/local-coding-agent --stage 03
```

starter의 `NotImplementedError` 메시지에 있는 `stage-03`은 의도한 미완성 표식입니다. 대표 실패는 authorization 전에 source를 읽거나 stale·conflicting evidence를 `READY`로 조용히 승격하는 경우입니다. 단계 검사는 01부터 누적됩니다. 위 설계 산출물만으로는 완료가 아니며, 구현과 canonical test 결과뿐 아니라 선택·제외 이유와 citation identity가 보이는 trace를 함께 제출합니다.

사람 검토 질문:

- 거절된 scope의 내용이 후보·context·citation·trace 어디에도 나타나지 않았음을 어떻게 입증합니까?
- summary의 각 주장에서 원 source revision과 digest로 돌아갈 수 있습니까?

## 의도적 비범위

- embedding model 선택
- 대규모 vector database
- 장기 사용자 personalization
