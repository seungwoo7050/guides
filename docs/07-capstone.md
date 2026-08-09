# Capstone: 로컬 코딩 에이전트 CLI

## 목표

처음 보는 로컬 저장소에서 문제를 조사하고, 여러 파일을 수정하고, build·test를 실행하고, 실패 뒤 재계획하며, 최종 diff와 검증 근거를 제출하는 코딩 에이전트를 설계하고 구현합니다. 코딩 작업이 주 profile이지만 model adapter, authorization-before-retrieval, tool gateway, durable state, policy와 evaluator contract는 도메인 중립적으로 유지합니다.

이 Capstone은 한 파일의 정해진 field를 한 번 바꾸는 과제가 아닙니다. 최소 하나의 과제에서 다음 전체 흐름이 실제로 일어나야 합니다.

```text
repository discovery
→ instruction·environment discovery
→ issue reproduction
→ code·test investigation
→ hypothesis·plan
→ multi-file edit
→ command/test
→ failure classification
→ repair iteration
→ broader verification
→ diff·evidence report
```

실제 구현과 실행 근거는 필수입니다. 설계 문서나 빈 template만으로는 `도구를 사용하는 에이전트를 구현한다`는 종료 능력을 만족하지 않습니다. 추적된 reference는 공개 계약의 한 구현 예이고 starter는 같은 계약의 단계별 미완성 경계를 드러냅니다.

## 사용자 인터페이스

최소 인터페이스:

```sh
coding-agent run \
  --repo ./fixture-project \
  --profile workspace-exec \
  "refresh token 경쟁 상태를 재현하고 수정하며 관련 검사를 실행하라"
```

필수 session 제어 명령 또는 동등한 machine-readable 인터페이스:

```sh
coding-agent inspect --repo ./fixture-project
coding-agent resume <session-id>
coding-agent status <session-id>
coding-agent diff <session-id>
coding-agent cancel <session-id>
coding-agent export <session-id> --format json
```

interactive mode와 machine-readable headless mode를 구분합니다.

## Capstone 구현 프로필

### 필수 프로필: durable local coding agent

- 한 사용자
- 한 repository
- agent 전용 worktree 또는 disposable copy
- file read/search/edit
- bounded command 실행
- Git status/diff
- 사용자 질문·승인·cancel
- model request·tool call·비용·실행 시간 budget
- checkpoint·resume와 crash injection
- effect ledger와 reconciliation
- external verifier

### 선택 확장: hosted or background

- background session
- session 목록
- hosted API·UI
- remote sandbox

### 비범위

- remote push·merge·release
- production credential
- arbitrary internet browsing
- 조직 multi-tenant platform
- 여러 agent의 협력
- model training·fine-tuning

이 기능은 [선택 확장](90-optional-extensions.md)에서 다룹니다.

## 필수 하위 시스템

### 1. CLI와 session controller

책임:

- task·repo·profile 입력 검증
- session identity 생성
- state transition
- user message·approval·cancel
- 진행 근거와 최종 결과 표시

필수 상태:

```text
CREATED
SNAPSHOTTING
DISCOVERING
INVESTIGATING
PLANNING
WAITING_USER
EDITING
RUNNING_CHECKS
REPAIRING
FINAL_VERIFYING
SUCCEEDED
FAILED
PAUSED
CANCELLED
```

### 2. Model adapter

최소 두 adapter를 같은 runtime contract로 구현합니다.

```text
ScriptedModelAdapter  결정적 runtime·failure 검사
RealModelAdapter      provider-compatible HTTP·stream·structured-output protocol
```

공통 contract:

- streaming event
- structured action
- usage
- refusal·invalid output·timeout·cancel
- model identity와 request receipt

필수 자동 검증은 network와 유료 credential 없이 scripted fixture와 loopback provider stub으로 수행합니다. `RealModelAdapter` 구현은 실제 request·stream·structured action 계약을 만족해야 하지만 public network의 live call은 선택 smoke입니다. live call을 실행하지 않았거나 provider 품질이 변동한 상태를 필수 검증 성공으로 과장하지 않습니다.

### 3. Repository snapshot과 explorer

- canonical root와 Git baseline
- initial staged·unstaged·untracked 상태
- instruction manifest
- file tree와 manifest
- build/test command discovery
- text·symbol·reference·history 조사
- context item provenance

### 4. Context manager

- authority·task·source·execution evidence 분리
- retrieval 전에 principal·resource·scope 권한 적용
- repository·reference corpus의 versioned retrieval
- source path·revision·digest citation
- unauthorized source의 후보·summary·trace 유입 차단
- context budget
- stale source invalidation
- compaction
- session memory
- final evidence manifest

### 5. Tool gateway

필수 tool:

```text
repository_status
list_files
read_file
search_text
show_diff
prepare_patch
apply_patch
run_command 또는 run_check
restore_change_set
ask_user
submit_result
```

권장 tool:

```text
find_symbol
find_references
read_git_history
format_paths
start/poll/terminate_process
```

모든 tool은 schema, effect class, permission과 receipt를 가집니다.

### 6. Filesystem과 patch engine

- canonical path와 symlink 방어
- digest 기반 stale write 방지
- create·modify·delete·rename
- multi-file change set
- before/after receipt
- partial apply recovery
- user initial change 보존

### 7. Process runner

- argv·cwd·clean env
- timeout·cancel·process tree
- stdout/stderr 상한
- nonzero·signal·timeout 구분
- workspace mutation
- network profile
- command result artifact

### 8. Git adapter

- branch·HEAD·index·working tree
- agent worktree
- baseline diff
- rollback
- 선택적 stage·commit

remote operation은 제외합니다.

### 9. Coding loop와 failure classifier

- task acceptance
- investigation hypothesis
- plan step
- edit-test-repair iteration
- failure taxonomy
- repeated failure detection
- model request 수·token/비용·tool call·wall-clock·output budget
- budget exhaustion과 stop condition

### 10. Policy, approval와 sandbox

- read/edit/command/Git/network permission 분리
- exact approval
- workspace isolation
- secret 제거
- untrusted repository handling
- kill·revoke·quarantine

### 11. Trace, checkpoint와 artifact

- event log
- model/tool/process/patch receipt
- context manifest
- checkpoint·resume
- cancel·crash 뒤 effect reconciliation
- 각 budget의 initial·consumed·remaining·terminal reason
- raw artifact와 redacted display
- runtime/model/tool/policy version

### 12. External evaluator

- clean base에 final change 적용
- public/hidden behavior test
- forbidden path·test tampering 검사
- policy trace 검사
- final diff와 last test revision 일치
- result와 evaluation error 분리

## Capstone 과제 집합

최소 다섯 종류를 fixture로 구현·평가합니다. 과제 B의 다중 파일 변경, 첫 patch가 실패하는 repair 과제, 과제 F의 악성 입력, 과제 G의 crash/resume은 반드시 포함합니다.

### 과제 A. 단일 모듈 bug

예:

```text
잘못된 경계값 때문에 만료 시각이 정확히 같은 token이 유효로 처리됩니다.
```

목표:

- 관련 code/test 발견
- reproduction test
- 작은 patch
- 회귀 검사

### 과제 B. 다중 파일 기능

예:

```text
CLI에 --dry-run을 추가하고 API, service, 문서와 test를 함께 갱신합니다.
```

목표:

- call site와 public contract 추적
- 여러 파일 change set
- help output와 behavior test

### 과제 C. 경쟁 상태 또는 지속성 bug

예:

```text
동시 요청에서 refresh token이 두 번 소비됩니다.
```

목표:

- deterministic reproduction
- state owner·transaction 조사
- concurrency fix와 regression

### 과제 D. 환경·build 조사

예:

```text
특정 platform에서 package test가 수집되지 않습니다.
```

목표:

- 코드 결함과 command/environment 결함 분리
- manifest·CI·test config 조사
- test 삭제 없이 해결

### 과제 E. 잘못되거나 불완전한 issue

issue 설명이 실제 원인과 다릅니다.

목표:

- 설명을 사실로 단정하지 않음
- 대안 가설
- 사용자 질문 또는 근거 기반 범위 수정

### 과제 F. 악성 저장소 입력

README, source comment 또는 test output에 prompt injection을 넣습니다.

목표:

- forbidden path·network·secret effect 차단
- task는 정상적으로 계속 해결

### 과제 G. crash와 resume

patch 적용 직후 또는 test 실행 중 runtime을 종료합니다.

목표:

- workspace와 effect reconcile
- 중복 patch/command 방지
- session evidence 보존

모든 과제는 같은 권한 인지 retrieval contract를 사용합니다. 허가된 source는 origin·revision·digest와 함께 citation되고, hidden verifier·secret·권한 밖 reference는 검색 후보와 trace에 나타나지 않아야 합니다.

## 필수 설계 산출물

```text
architecture.md
trust-boundaries.md
task-spec.md
session-state-machine.md
model-adapter-contract.md
repository-manifest.md
context-manifest.md
tool-catalog.md
permission-policy.md
sandbox-profiles.md
patch-and-process-receipts.md
failure-classification.md
checkpoint-schema.md
evaluation-instances.md
verifier-design.md
incident-runbook.md
```

템플릿은 [`exercises/10-capstone-local-coding-agent`](../exercises/10-capstone-local-coding-agent/README.md)과 `reference/`에 있습니다.

starter를 안전한 학습 workspace로 복사합니다.

```sh
python3 scripts/new_workspace.py --destination .workspace/local-coding-agent
```

reference 전체와 학습자 단계를 검사하는 canonical 명령은 다음과 같습니다.

```sh
python3 exercises/10-capstone-local-coding-agent/tests/run.py \
  --implementation reference --stage all
python3 exercises/10-capstone-local-coding-agent/tests/run.py \
  --implementation .workspace/local-coding-agent --stage 01
```

workspace 생성기는 기존 destination이나 symlink를 덮어쓰지 않습니다. 학습자 구현은 workspace 안의 test 복사본이 아니라 추적된 canonical test와 fixture로 검사합니다.

## 단계별 구현 순서

### Stage 1. Scripted read-only agent

```text
TaskSpec
→ repository snapshot
→ list/read/search
→ investigation report
→ external verifier
```

완료 조건:

- repository instruction과 untrusted content를 구분합니다.
- 관련 file·test·command를 source reference와 함께 찾습니다.
- workspace를 바꾸지 않습니다.

### Stage 2. Patch preparation과 review

```text
investigation
→ plan
→ patch artifact
→ diff review
```

완료 조건:

- stale digest를 거절합니다.
- 여러 파일 patch를 change set으로 표시합니다.
- 아직 실제 file을 바꾸지 않고 review할 수 있습니다.

### Stage 3. Workspace edit와 좁은 검사

```text
approval
→ apply patch
→ run reproduction test
→ classify
```

완료 조건:

- agent worktree에서만 변경합니다.
- process timeout·output·cleanup이 동작합니다.
- test failure가 구조화됩니다.

### Stage 4. Repair loop

```text
failure evidence
→ context refresh
→ plan revision
→ repair patch
→ re-test
```

완료 조건:

- 같은 실패를 무한 반복하지 않습니다.
- incorrect hypothesis에서 investigation으로 돌아갑니다.
- 관련 없는 test 약화를 거절합니다.

### Stage 5. Final verification과 report

```text
related suite
→ broader gate
→ external verifier
→ final evidence
```

완료 조건:

- 마지막 검사와 final diff가 같은 revision입니다.
- 미실행 gate와 잔여 위험을 보고합니다.
- 모델의 완료 선언과 verifier 결과가 분리됩니다.

### Stage 6. Provider-compatible model adapter

scripted scenario를 모두 통과한 뒤 같은 HTTP·stream·structured-output wire contract를 구현합니다. 필수 검사는 loopback provider stub을 사용하고, 실제 provider live smoke는 별도 선택 실행입니다.

완료 조건:

- provider 변경이 tool·policy·verifier contract를 바꾸지 않습니다.
- invalid output과 timeout을 처리합니다.
- context·usage·cost가 trace에 남습니다.

### Stage 7. Durable session

필수 종료 단계입니다. 다음 항목을 문서가 아니라 crash·cancel·budget fixture로 실행합니다.

- checkpoint
- crash injection
- resume
- user interruption
- cancellation cleanup
- model·tool·비용·wall-clock budget exhaustion
- STARTED/UNKNOWN effect reconciliation

## 평가 행렬

| 항목 | 필수 판정 |
|---|---|
| 저장소 조사 | 관련 source·test·command를 근거와 함께 발견 |
| RAG 경계 | authorization-before-retrieval, source revision·digest citation, denied source 비노출 |
| 변경 정확성 | behavior와 regression verifier 통과 |
| 변경 범위 | unrelated·forbidden file 변경 없음 |
| 반복 능력 | 첫 patch 실패 뒤 evidence 기반 repair 수행 |
| process | timeout·cancel·output limit·child cleanup |
| Git | initial user change 보존, final diff 정확 |
| 안전 | prompt injection·path escape·secret·network 차단 |
| 장기 상태 | crash/resume 뒤 effect 중복 없음 |
| 예산 | model·tool·비용·시간 한도 초과 뒤 새 effect 0건, terminal receipt 존재 |
| 평가 무결성 | verifier·answer·test tampering 없음 |
| 사용자 통제 | 질문·승인·cancel·final review 가능 |
| 근거 | command, test, diff, assumption과 risk 제공 |

## 최종 데모

최종 데모는 success case 하나만 보여 주지 않습니다.

```text
1. 정상 bug fix
2. 첫 patch가 실패하고 재계획해 성공
3. 사용자 constraint 변경으로 patch rollback
4. malicious repository instruction 차단
5. command timeout과 process cleanup
6. crash 후 resume
7. model/tool/비용/시간 budget 소진과 안전한 종료
8. verifier가 허위 완료를 거절
```

## 완료 기준

다음 조건을 모두 만족하면 가이드의 Capstone 목표를 달성합니다.

- 에이전트가 사전 지정된 한 file만 바꾸는 script가 아닙니다.
- 저장소 구조와 실행 명령을 조사합니다.
- retrieval 전에 source 권한을 적용하고 선택 근거를 revision·digest citation으로 남깁니다.
- 관련 근거를 바탕으로 plan을 만들고 여러 파일을 수정할 수 있습니다.
- build·test를 실제로 실행하고 실패를 분류합니다.
- 실패 뒤 context와 plan을 갱신해 다시 수정합니다.
- 사용자는 effect를 승인·중단하고 final diff를 검토할 수 있습니다.
- cancel·crash 뒤 재개해도 file·process·Git effect가 중복되지 않습니다.
- model request·tool call·비용·실행 시간 budget을 강제하고 초과 뒤 새 effect를 만들지 않습니다.
- sandbox와 policy가 model prompt 밖에서 권한을 강제합니다.
- scripted adapter와 provider-compatible adapter가 같은 runtime contract를 사용합니다.
- external verifier가 결과와 정책을 독립적으로 판정합니다.
- trace와 artifact만으로 작업 경로와 잔여 위험을 복원할 수 있습니다.

이 증거 묶음으로 카탈로그의 종료 능력인 `도구를 사용하는 에이전트를 구현한다`, `외부 verifier로 성공을 판정한다`, `권한·네트워크·비용·실행 시간을 제한한다`를 각각 판정합니다. reference 통과는 특정 실제 provider의 품질, 모든 OS sandbox 또는 production 안전성을 자동으로 증명하지 않습니다.
