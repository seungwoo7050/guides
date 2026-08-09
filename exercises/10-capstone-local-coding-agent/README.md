# 실습 10: 로컬 코딩 에이전트 Capstone

## 목표

Codex나 Claude Code와 같은 도구의 핵심을 가진 durable local coding-agent CLI를 구현합니다. 모델을 호출해 단일 답을 받는 프로그램이 아니라 저장소를 조사·편집·실행·검증하고 cancel·crash·budget 소진 뒤 상태를 수렴시키는 runtime이어야 합니다. 코딩 과제가 주 profile이지만 내부 model·retrieval·tool·state·policy·evaluator contract는 다른 agent 도메인에서도 재사용할 수 있게 분리합니다.

상세 요구는 [`docs/07-capstone.md`](../../docs/07-capstone.md)에 있습니다.

## 필수 사용자 흐름

```text
coding-agent run --repo <path> "<task>"
→ repository와 instruction 조사
→ 문제 재현
→ 관련 code·test·command 탐색
→ plan 표시
→ edit 승인
→ 여러 file 변경
→ test/build 실행
→ 첫 실패 해석
→ context·plan 갱신
→ repair
→ checkpoint·crash/resume 또는 cancel
→ final verifier
→ diff·근거·잔여 위험 보고
```

## 필수 산출물

`templates/`를 복사해 다음 설계 산출물을 완성하고, 같은 계약의 실행 가능한 runtime·fixture·trace를 함께 제출합니다.

```text
architecture.md
state-machine.md
tool-catalog.md
permission-policy.md
task-fixtures.md
evaluation-report.md
```

추가로 다음 contract를 reference template에서 연결합니다.

- model adapter
- repository manifest
- context manifest
- command result
- patch receipt
- session checkpoint
- threat model

빈 template나 설계만 제출하는 프로필은 완료로 인정하지 않습니다.

## 시작과 단계 검사

저장소 루트에서 starter를 비파괴적으로 복사합니다.

```sh
python3 scripts/new_workspace.py --destination .workspace/local-coding-agent
```

reference 전체 계약과 학습자 1단계 계약은 각각 다음처럼 검사합니다.

```sh
python3 exercises/10-capstone-local-coding-agent/tests/run.py \
  --implementation reference --stage all
python3 exercises/10-capstone-local-coding-agent/tests/run.py \
  --implementation .workspace/local-coding-agent --stage 01
```

기존 destination이나 symlink는 덮어쓰지 않습니다. 학습자 workspace의 test 복사본이 아니라 추적된 canonical test와 fixture가 구현을 검사합니다.

## 최소 task 세트

1. 단일 module bug
2. 다중 file feature
3. 첫 patch가 실패하는 repair task
4. prompt injection이 있는 저장소
5. command timeout과 crash/resume

다중 파일 변경, 첫 patch 실패 뒤 repair, malicious input, crash/resume은 필수입니다. 각 task의 retrieval 결과는 principal의 source 권한을 먼저 적용하고 origin·revision·digest citation을 남겨야 합니다.

## 필수 하위 시스템

- CLI/session controller
- scripted + provider-compatible model adapter
- repository snapshot/explorer
- authorization-aware RAG/context manager
- tool registry
- filesystem/search
- patch/diff engine
- bounded process runner
- Git/worktree adapter
- coding loop/failure classifier
- permission/approval/sandbox
- trace/checkpoint/resume/cancel/budget ledger
- external evaluator

## 검증 계획

다음 항목을 scripted scenario, fixture repository와 external verifier로 판정합니다.


### 기능

- target file을 미리 고정하지 않고 관련 code를 찾습니다.
- 여러 파일을 하나의 change set으로 수정합니다.
- 실제 command와 test를 실행합니다.
- 실패 뒤 같은 action을 반복하지 않고 재계획합니다.

### 상태

- Git baseline과 initial user change를 보존합니다.
- context와 patch의 source revision을 추적합니다.
- crash/resume 뒤 effect가 중복되지 않습니다.
- cancel 뒤 descendant process·pending action·credential을 정리합니다.
- model request·tool call·비용·실행 시간 budget 초과 뒤 새 effect를 만들지 않습니다.

### Retrieval

- 권한을 retrieval 전에 적용합니다.
- 허가된 source의 origin·revision·digest를 context와 최종 citation에 유지합니다.
- secret·hidden verifier·권한 밖 reference가 후보, summary와 trace에 노출되지 않습니다.
- stale index나 source 변경은 명시적 refresh 또는 failure를 만듭니다.

### 안전

- repository prompt injection이 authority를 바꾸지 못합니다.
- path·network·secret·verifier 경계를 강제합니다.
- 사용자가 승인·cancel·revoke할 수 있습니다.

### 평가

- scripted adapter로 결정적 scenario를 통과합니다.
- provider-compatible adapter를 loopback fixture에서 request·stream·structured action까지 검사합니다.
- external verifier가 hidden behavior와 policy를 판정합니다.
- 최종 report가 diff·command·test·assumption·risk를 포함합니다.

필수 검증에는 public network, API key나 유료 model 호출이 필요하지 않습니다. 실제 provider live smoke는 선택이며, 미실행·rate limit·provider 품질 변동을 필수 runtime의 성공 근거로 사용하지 않습니다.

## 의도적 비범위

- remote push·merge
- production 배포
- multi-agent
- IDE extension
- cloud multi-tenant service

## 완료 근거

- `도구를 사용하는 에이전트를 구현한다`: discovery, authorized retrieval, structured tool call, 다중 파일 edit, command, repair와 resume trace
- `외부 verifier로 성공을 판정한다`: agent 환경 밖에서 behavior·regression·policy를 판정하고 known-bad를 거부한 결과
- `권한·네트워크·비용·실행 시간을 제한한다`: task identity·grant, network deny, cancel cleanup과 model/tool/cost/time budget receipt

reference 통과는 실제 provider의 품질, 모든 운영체제의 kernel sandbox 또는 production 환경의 안전성을 자동으로 증명하지 않습니다. 이 한계와 미실행 선택 검사를 evaluation report에 남깁니다.
