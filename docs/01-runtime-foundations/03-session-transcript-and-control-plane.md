# Session, transcript와 control plane

## 목표

대화형 CLI의 화면, 사용자와 모델의 transcript, 실제 작업 상태와 제어 명령을 분리합니다. 사용자가 에이전트를 중단·수정·재개할 수 있게 합니다.

## session의 정체성

한 session은 최소 다음 identity를 가집니다.

```text
session_id
repository_snapshot_id
workspace_id
task_id
principal_id
runtime_version
policy_profile
model_profile
created_at
```

같은 대화라도 repository snapshot이나 permission profile이 달라지면 실행 정체성이 달라집니다. `resume`은 단순히 마지막 메시지를 다시 읽는 기능이 아닙니다.

## transcript와 event log

### Transcript

사용자에게 보이는 의미 단위입니다.

- 사용자 요청과 추가 지시
- 모델의 설명·질문·요약
- tool call의 축약 표시
- 승인 요청과 사용자 응답
- 최종 결과

### Event log

runtime이 재개와 감사를 위해 사용하는 구조화된 기록입니다.

- model request·response identity
- validated action
- policy decision
- approval artifact
- tool start·result·receipt
- workspace digest
- state transition
- budget update
- cancel·pause·failure

Transcript를 수정해도 이미 수행한 effect history가 바뀌지 않습니다.

## control plane event

사용자 제어는 채팅 문장에 묻히지 않고 event로 처리합니다.

```text
UserMessageAdded
ApprovalGranted
ApprovalDenied
TaskAmended
PauseRequested
CancelRequested
ResumeRequested
BudgetExtended
PermissionChanged
```

예를 들어 “그 파일은 건드리지 마”라는 메시지는 다음을 만들 수 있습니다.

1. 새 user message
2. task constraint 변경 제안
3. 기존 plan·context·pending patch의 invalidation
4. permission grant 재계산
5. 다음 turn 시작

## interactive와 headless 실행

### Interactive

- 질문과 승인에 사용자가 즉시 답할 수 있습니다.
- tool output을 단계적으로 표시합니다.
- 사용자가 작업 중간에 범위를 바꿀 수 있습니다.
- foreground process와 terminal interaction이 필요할 수 있습니다.

### Headless

- 질문이 필요한 경우 정해진 정책으로 중단합니다.
- 승인은 사전 grant나 외부 approval service를 사용합니다.
- machine-readable event와 result가 필요합니다.
- deadline과 max turn을 반드시 둡니다.

같은 runtime을 사용하되 interface와 control policy를 분리합니다.

## session 상태 예시

```text
CREATED
→ SNAPSHOTTING
→ DISCOVERING
→ INVESTIGATING
→ PLANNING
→ WAITING_USER
→ EDITING
→ RUNNING_CHECKS
→ REPAIRING
→ FINAL_VERIFYING
→ SUCCEEDED
```

어느 active state에서도 다음으로 이동할 수 있습니다.

```text
PAUSING → PAUSED
CANCELLING → CANCELLED
POLICY_BLOCKED
BUDGET_EXHAUSTED
FAILED_ENVIRONMENT
FAILED_RUNTIME
```

UI의 spinner나 “thinking” 문구를 상태로 사용하지 않습니다.

## 사용자에게 보여 줄 근거

진행 화면은 chain-of-thought를 노출하는 것이 아니라 실행 근거를 보여 줍니다.

- 현재 phase
- 읽은 파일과 선택 이유
- 실행 중인 command와 cwd
- 변경 예정 파일과 diff
- test 결과와 실패 분류
- 남은 budget
- 승인 대기 항목
- 마지막 checkpoint

## 실패 조건

- 사용자의 cancel이 다음 model turn만 막고 이미 실행 중인 process는 남깁니다.
- session resume가 현재 Git 상태를 검사하지 않습니다.
- 사용자가 범위를 바꿔도 이전 patch와 context를 그대로 사용합니다.
- UI 출력 순서와 event log 순서가 달라 재현할 수 없습니다.
- headless mode가 질문에 임의로 답합니다.

## 완료 조건

- transcript 없이 event log만으로 실행 순서와 effect를 복원할 수 있습니다.
- event log 없이 transcript만으로는 effect를 재실행하지 않습니다.
- pause, cancel, task amendment와 permission change가 명시적 상태 전이를 만듭니다.
- interactive와 headless mode가 같은 runtime contract를 사용합니다.
