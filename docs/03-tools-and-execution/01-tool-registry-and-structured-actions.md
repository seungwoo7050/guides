# Tool registry와 구조화된 action

## 목표

모델이 자유 문자열로 권한을 행사하지 못하게 하고, 코딩 작업에 필요한 모든 행동을 versioned tool contract로 표현합니다.

## tool을 등록하는 이유

다음 구현은 단순하지만 경계를 잃습니다.

```text
model: "grep ... && sed ... && pytest ..."
runtime: shell=True로 실행
```

하나의 문자열 안에 검색, 파일 읽기, process 실행, network, redirection과 여러 외부 효과가 섞입니다. policy가 무엇을 승인했는지 설명하기 어렵고 output도 구조화되지 않습니다.

대신 tool registry가 다음을 소유합니다.

```text
name와 version
input schema
output schema
effect class
resource scope
permission requirement
timeout·output profile
idempotency contract
implementation adapter
redaction policy
```

## coding-agent 기본 tool 집합

### Read-only

```text
repository_status
list_files
read_file
search_text
find_symbol
find_references
read_git_history
show_diff
```

### Workspace write

```text
create_patch
apply_patch
write_file
create_file
delete_file
format_paths
restore_change_set
```

### Compute/process

```text
run_command
run_check
start_process
poll_process
send_input
terminate_process
```

### Git effect

```text
create_worktree
stage_paths
create_commit
switch_branch
```

기본 Capstone에서는 remote push·PR·merge를 제외합니다.

## effect class

```text
PURE_READ             상태를 바꾸지 않는 읽기
LOCAL_CACHE           source 밖 cache만 바꿈
REVERSIBLE_WORKSPACE  change set으로 복구 가능한 작업 공간 변경
PROCESS_EFFECT        child process·service 실행
DEPENDENCY_EFFECT     package install·code generation
VCS_EFFECT            index·branch·commit 변경
REMOTE_EFFECT         push·issue·PR·API 쓰기
IRREVERSIBLE_EFFECT   배포·삭제·결제 등 되돌리기 어려운 효과
```

같은 `run_command`라도 command profile에 따라 effect가 다릅니다. `pytest`와 `npm install`을 같은 권한으로 취급하지 않습니다.

## validation pipeline

```text
raw model output
→ protocol parse
→ action schema validation
→ phase validation
→ tool lookup/version check
→ argument canonicalization
→ policy decision
→ approval decision
→ execution
→ output validation
→ receipt
```

canonicalization 전에 path나 command permission을 비교하면 우회가 생길 수 있습니다.

## tool result

모델에게 stdout 문자열만 반환하지 않습니다.

```text
tool_call_id
operation_id
tool_name·version
status
started_at·ended_at
normalized_result
raw_artifact_refs
resource_receipts
workspace_before·after
effect_summary
truncation·redaction
policy_decision_id
```

읽기 tool도 content digest와 repository snapshot identity를 포함합니다.

## tool error 분류

```text
INVALID_ARGUMENT
POLICY_DENIED
APPROVAL_REQUIRED
RESOURCE_NOT_FOUND
STALE_PRECONDITION
TIMEOUT
OUTPUT_LIMIT
CANCELLED
PROCESS_FAILED
ENVIRONMENT_FAILURE
TOOL_INTERNAL_ERROR
RESULT_SCHEMA_ERROR
```

모델이 재시도해도 되는 오류와 사용자 또는 runtime 수정이 필요한 오류를 구분합니다.

## tool versioning

checkpoint와 trace에는 tool version을 남깁니다. version 변경으로 다음이 달라질 수 있습니다.

- argument 의미
- output schema
- path canonicalization
- default timeout
- permission classification
- patch semantics

resume 시 compatible version인지 확인하고 아니면 migration 또는 manual review로 이동합니다.

## 실패 조건

- 모든 command를 범용 shell tool 하나로 노출합니다.
- tool description만 있고 runtime schema validation이 없습니다.
- tool output parser 실패를 command 실패로 보고합니다.
- effect class가 tool name에만 고정돼 arguments를 반영하지 않습니다.
- model이 tool result의 exit code나 digest를 임의로 만들 수 있습니다.

## 완료 조건

- 기본 coding-agent 행동이 tool catalog로 완전히 표현됩니다.
- read, edit, process, Git, remote effect가 다른 정책을 가집니다.
- invalid action이 구현 adapter 호출 전에 거절됩니다.
- tool receipt만으로 실행한 행동과 실제 변경을 추적할 수 있습니다.
