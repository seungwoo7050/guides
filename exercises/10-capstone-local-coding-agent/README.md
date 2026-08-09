# 실습 10: 로컬 코딩 에이전트 Capstone

## 목표

Codex나 Claude Code와 같은 도구의 핵심을 가진 로컬 coding-agent CLI를 설계합니다. 모델을 호출해 단일 답을 받는 프로그램이 아니라 저장소를 조사·편집·실행·검증하는 runtime이어야 합니다.

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
→ final verifier
→ diff·근거·잔여 위험 보고
```

## 필수 산출물

구현 여부와 관계없이 다음 산출물을 작성합니다.


`templates/`를 복사해 다음을 완성합니다.

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

## 최소 task 세트

1. 단일 module bug
2. 다중 file feature
3. 첫 patch가 실패하는 repair task
4. prompt injection이 있는 저장소
5. command timeout 또는 crash/resume

## 필수 하위 시스템

- CLI/session controller
- scripted + real model adapter
- repository snapshot/explorer
- context manager
- tool registry
- filesystem/search
- patch/diff engine
- bounded process runner
- Git/worktree adapter
- coding loop/failure classifier
- permission/approval/sandbox
- trace/checkpoint
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

### 안전

- repository prompt injection이 authority를 바꾸지 못합니다.
- path·network·secret·verifier 경계를 강제합니다.
- 사용자가 승인·cancel·revoke할 수 있습니다.

### 평가

- scripted adapter로 결정적 scenario를 통과합니다.
- real adapter로 최소 세 task를 실행합니다.
- external verifier가 hidden behavior와 policy를 판정합니다.
- 최종 report가 diff·command·test·assumption·risk를 포함합니다.

## 의도적 비범위

- remote push·merge
- production 배포
- multi-agent
- IDE extension
- cloud multi-tenant service
