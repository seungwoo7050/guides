# Edit-test-repair loop

## 목표

코딩 에이전트의 핵심인 `조사 → 작은 변경 → 좁은 검사 → 실패 해석 → 재수정 → 넓은 검증` 루프를 상태와 evidence로 구현합니다.

## 기본 loop

```text
INVESTIGATE
→ PLAN
→ PREPARE_EDIT
→ APPLY_EDIT
→ RUN_NARROW_CHECK
→ CLASSIFY_RESULT
   ├── PASS → EXPAND_VERIFICATION
   ├── EXPECTED_FAILURE_CHANGED → REPAIR
   ├── HYPOTHESIS_REFUTED → REINVESTIGATE
   ├── ENVIRONMENT_FAILURE → RECOVER_ENVIRONMENT
   └── POLICY/BUDGET → WAIT_OR_STOP
→ FINAL_VERIFY
→ REPORT
```

단순히 `while tests fail: ask model again`으로 구현하지 않습니다.

## change unit

한 iteration은 검증 가능한 가설 하나를 다룹니다.

- 한 invariant
- 한 failure path
- 한 API contract
- 한 migration 단계

여러 독립 리팩터링을 동시에 하면 어떤 변경이 결과를 만들었는지 알기 어렵습니다.

## 좁은 검사와 넓은 검사

### 좁은 검사

- reproduction test
- 특정 test case
- 한 package compile
- 대상 file type-check

빠른 causal feedback을 줍니다.

### 넓은 검사

- 관련 module suite
- repository lint/type check
- 전체 suite
- integration/e2e
- release-specific gate

회귀와 integration을 확인합니다.

에이전트는 좁은 검사 통과를 최종 성공으로 과장하지 않습니다.

## iteration state

```text
iteration_id
starting_change_set
active_hypothesis
selected_evidence
patch_artifact
applied_receipt
checks[]
classification
new_evidence
plan_revision
budget_delta
```

이 기록이 있어야 실패한 시도와 최종 patch의 관계를 분석할 수 있습니다.

## test 추가

bug fix에서는 가능한 경우 수정 전에 실패하는 reproduction test를 만듭니다.

주의:

- task 요구를 test에 그대로 하드코딩해 production code와 무관하게 통과시키지 않습니다.
- hidden implementation detail 대신 public behavior와 invariant를 검사합니다.
- flaky timing 문제에는 barrier·fake clock·deterministic scheduler를 우선합니다.
- 기존 test가 잘못됐다면 근거와 함께 수정합니다.

## repair 전략

실패할 때 동일 patch를 조금씩 바꾸는 것만이 답이 아닙니다.

```text
syntax/type correction
local logic correction
missing call-site update
wrong abstraction boundary
incorrect hypothesis
incomplete test setup
environment repair
rollback and alternate design
ask user
```

repair action은 실패 분류에 따라 제한합니다.

## 반복 정지 조건

- 같은 diagnostic fingerprint 반복 횟수
- 새 evidence 없이 같은 file 반복 수정
- step·token·time·command budget
- diff 크기 증가율
- plan 범위 밖 file 확장
- test flakiness
- 사용자 결정 필요

한도 초과 시 현재 상태와 필요한 결정을 보고하고 멈춥니다.

## 최종 verification

최종 단계에서 다음을 고정합니다.

1. current Git diff와 changed paths
2. reproduction test 통과
3. 관련 regression test 통과
4. repository-required gate 실행 여부
5. formatter·generated artifact 확인
6. secret·forbidden path·unexpected network 확인
7. verifier 판정
8. 미실행 검사와 잔여 위험

## 실패 조건

- test failure마다 전체 context 없이 “고쳐 줘”를 다시 호출합니다.
- 한 iteration에서 unrelated file을 광범위하게 바꿉니다.
- test를 삭제하거나 assertion을 약화해 green을 만듭니다.
- 동일 실패를 무제한 반복합니다.
- 최종 diff가 마지막 검사 뒤 추가로 바뀌었습니다.
- 관련 test만 통과하고 repository-required gate를 숨깁니다.

## 완료 조건

- 각 iteration이 hypothesis, patch, check와 classification을 가집니다.
- 실패 분류가 다음 action 종류를 실제로 제한합니다.
- 재현 test에서 넓은 회귀 검사로 확장하는 정책이 있습니다.
- 반복 한도와 사용자 개입 조건이 명시됩니다.
