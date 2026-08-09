# 실습 06: Edit-test-repair loop

## 목표

한 번의 patch 생성이 아니라 조사·편집·검사·실패 분류·재계획을 반복하는 coding loop를 설계합니다.

## fixture 요구사항

첫 번째 그럴듯한 patch가 실패하도록 과제를 설계합니다.

예:

```text
production code 한 곳을 수정하면 단위 test는 통과하지만
다른 call site의 type check가 실패합니다.
```

또는:

```text
issue가 원인을 잘못 설명하며 실제 문제는 test command의 cwd입니다.
```

## 설계할 책임

- `TaskSpec`
- evidence와 hypothesis
- plan step
- iteration state
- narrow/broad check 정책
- failure classifier
- repeated-failure detector
- stop·ask-user 조건
- final verification

## 필수 시나리오

### 정상

- 문제 재현
- 첫 hypothesis와 작은 patch
- 관련 test 통과
- 더 넓은 test에서 새 failure
- context refresh와 두 번째 patch
- 최종 verifier 통과

### 경계

- reproduction 불가
- 두 hypothesis가 같은 evidence를 설명
- test가 flaky
- user가 중간에 non-goal 추가
- diff가 예상 범위를 넘음

### 실패

- 같은 diagnostic 반복
- test 삭제로 green
- environment failure를 code patch로 우회
- budget 소진
- final test 뒤 workspace 변경

## 필수 산출물

```text
task-spec.md
evidence-log.md
hypothesis-table.md
plan-revisions.md
iteration-state.md
failure-taxonomy.md
stop-policy.md
final-verification.md
```

## 검증 계획

- scripted model이 첫 실패 뒤 동일 action을 반복하지 않습니다.
- failure category가 다음 허용 action을 바꿉니다.
- incorrect hypothesis는 investigation으로 되돌립니다.
- 최종 report가 실패한 시도와 미실행 gate를 숨기지 않습니다.
- 마지막 verifier revision과 final diff가 같습니다.

## 실행 파일과 판정

- 구현 경계: [starter `loop.py`](../10-capstone-local-coding-agent/starter/coding_agent/loop.py)
- 비교 구현: [reference `loop.py`](../10-capstone-local-coding-agent/reference/coding_agent/loop.py)
- 공개 판정: [`test_stage_06_loop.py`](../10-capstone-local-coding-agent/tests/test_stage_06_loop.py)

```sh
python3 exercises/10-capstone-local-coding-agent/tests/run.py --implementation reference --stage 06
python3 exercises/10-capstone-local-coding-agent/tests/run.py --implementation starter --stage 06 --expect-incomplete
python3 exercises/10-capstone-local-coding-agent/tests/run.py --implementation .workspace/local-coding-agent --stage 06
```

starter의 `NotImplementedError` 메시지에 있는 `stage-06`은 failure classification과 repeated-failure stop의 의도한 미완성 표식입니다. 대표 실패는 같은 revision·diagnostic에서 동일 action을 반복하거나 zero-test를 성공으로 분류하는 경우입니다. 단계 검사는 01부터 누적됩니다. 위 설계 산출물만으로는 완료가 아니며, 구현·canonical test 결과와 hypothesis→action→receipt→replan trace를 함께 제출합니다.

사람 검토 질문:

- failure category가 다음 허용 action과 context refresh를 실제로 바꾼 증거가 있습니까?
- stop·사용자 질문·재계획 중 하나를 선택한 근거와 실행하지 않은 최종 gate가 report에 남습니까?

## 의도적 비범위

- 모델 품질 최적화
- multi-agent reviewer
- remote CI
