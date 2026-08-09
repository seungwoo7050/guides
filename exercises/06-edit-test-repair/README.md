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

## 의도적 비범위

- 모델 품질 최적화
- multi-agent reviewer
- remote CI
