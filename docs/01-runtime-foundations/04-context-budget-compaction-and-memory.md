# Context budget, compaction과 memory

## 목표

저장소 전체를 한 번에 모델에 넣지 않고 현재 과제에 필요한 근거를 선택·요약·갱신합니다. 오래된 context가 실제 workspace와 달라지는 문제를 다룹니다.

## context의 종류

```text
Authority context    system·user·repository instruction과 permission
Task context         목표·acceptance·비범위·사용자 결정
Repository evidence  파일 excerpt·symbol·history·manifest·test
Execution evidence   command·test·diagnostic·diff·receipt
Working state        가설·계획·열린 질문·다음 행동
Memory               여러 turn이나 session에 유지할 요약·결정
```

모든 항목은 같은 신뢰 수준이 아닙니다. repository file과 terminal output은 사실 근거가 될 수 있지만 사용자 권한을 부여하지 않습니다.

## ContextManifest

모델에 보낸 context를 manifest로 남깁니다.

```text
item_id
kind
origin
canonical_location
revision_or_digest
line_range_or_symbol
retrieved_at
trust_label
scope
freshness_state
content_length
summary_parent?
```

모델 응답이 어떤 file revision을 바탕으로 만들어졌는지 추적할 수 있어야 합니다.

## 선택 순서

처음부터 vector retrieval에 의존하지 않습니다.

1. task의 명시적 path·symbol·error를 추출합니다.
2. repository instruction과 manifest를 읽습니다.
3. filename·text search로 후보를 좁힙니다.
4. symbol definition·reference와 import/dependency를 추적합니다.
5. 관련 test·build config·history를 읽습니다.
6. 현재 가설에 필요한 최소 excerpt를 선택합니다.
7. tool result와 변경 뒤 affected context를 갱신합니다.

embedding이나 semantic search는 후보 생성에 사용할 수 있지만 canonical source와 digest를 잃지 않습니다.

## budget 배분

하나의 context window를 다음처럼 구분할 수 있습니다.

```text
고정 reserve      system·tool schema·안전 경계
과제 reserve      task·acceptance·사용자 결정
근거 budget       코드·test·manifest·output
작업 상태 budget  plan·open questions·recent receipts
출력 reserve      다음 action과 설명
```

대용량 test output이나 minified file이 전체 budget을 소모하지 않도록 tool에서 먼저 상한과 요약을 적용합니다.

## compaction

compaction은 대화문을 짧게 만드는 일이 아니라 **향후 행동에 필요한 상태를 손실 없이 재표현하는 작업**입니다.

보존해야 할 것:

- task와 변경된 constraint
- 현재 Git·workspace identity
- 확정된 사실과 source reference
- 아직 검증되지 않은 가설
- 적용한 patch와 receipt
- 실행한 check와 결과
- pending approval·question
- 남은 budget과 다음 행동

버려도 되는 것:

- 이미 source로 대체 가능한 장황한 설명
- 중복 tool output
- 폐기된 가설의 세부 reasoning
- 완료된 read-only action의 원문 전체

## memory 계층

### Turn memory

현재 model call을 위한 context입니다.

### Session memory

현재 task 동안 유지하는 결정·가설·receipt입니다.

### Repository memory

프로젝트의 build 명령, architecture, style처럼 여러 session에서 재사용할 수 있지만 repository revision과 scope를 가져야 합니다.

### User preference

개인 선호와 조직 정책을 분리합니다. 사용자 선호가 repository rule이나 보안 policy를 덮어쓰지 못합니다.

## staleness와 invalidation

다음 사건은 context를 stale로 만듭니다.

- file edit 또는 formatter 실행
- branch·commit 변경
- dependency install이나 code generation
- user가 task 범위를 변경
- test가 예상과 다른 실행 경로를 드러냄
- 다른 process가 workspace를 변경

stale item을 삭제할지, 다시 읽을지, “변경 전 근거”로 보존할지 구분합니다.

## 실패 조건

- file content를 digest 없이 session memory에 저장합니다.
- patch 뒤 같은 file의 이전 excerpt를 계속 사용합니다.
- test output 요약이 실패한 test 이름과 exit status를 잃습니다.
- repository memory가 branch·revision과 무관하게 재사용됩니다.
- compaction이 pending approval과 적용한 effect를 누락합니다.
- 모델이 “기억한다”는 문장을 실제 session state로 간주합니다.

## 완료 조건

- 모든 repository evidence가 canonical source와 revision을 가집니다.
- context item이 stale이 되는 사건과 갱신 정책을 정의합니다.
- compaction 전후에 next action, pending effect와 verifier state가 보존됩니다.
- 작은 저장소와 큰 저장소에서 서로 다른 context budget 전략을 제시할 수 있습니다.
