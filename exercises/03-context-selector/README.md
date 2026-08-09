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

## 의도적 비범위

- embedding model 선택
- 대규모 vector database
- 장기 사용자 personalization
