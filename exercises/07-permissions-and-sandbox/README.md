# 실습 07: Permission과 sandbox

## 목표

코딩 에이전트의 read·edit·command·network·Git 권한을 task-scoped grant와 실행 sandbox로 강제합니다.

## fixture 요구사항

- 정상 source와 test
- `.env` 또는 fake credential
- workspace 밖 target을 가리키는 symlink
- prompt injection README
- home file을 읽으려는 test script
- external domain 연결을 시도하는 command
- hidden verifier path

## 설계할 책임

- principal model
- resource grant
- permission rule
- approval artifact
- sandbox profile
- credential broker 경계
- deny/revoke
- policy decision log

## 필수 시나리오

### 정상

- source read
- exact patch 승인
- registered test command 실행
- final verifier 접근 없이 결과 제출

### 경계

- nested path rule
- approval expiry
- same command, different args
- dependency install permission
- loopback service

### 실패

- path traversal·symlink escape
- secret read
- network exfiltration
- verifier 접근
- permission file 수정
- broad Bash grant 우회
- revoke 뒤 pending action 실행

## 필수 산출물

```text
principals.md
resource-grant.schema
permission-matrix.md
approval-artifact.schema
sandbox-profiles.md
threat-model.md
policy-decision.schema
incident-cases.md
```

## 검증 계획

- 모델이 공격 지시를 따르더라도 forbidden effect가 발생하지 않습니다.
- deny가 allow보다 우선합니다.
- approval arguments가 달라지면 거절됩니다.
- sandbox 밖 host credential과 verifier가 보이지 않습니다.
- revoke 뒤 tool gateway와 credential broker 모두 차단합니다.

## 실행 파일과 판정

- 구현 경계: [starter `policy.py`](../10-capstone-local-coding-agent/starter/coding_agent/policy.py), [starter `tools.py`](../10-capstone-local-coding-agent/starter/coding_agent/tools.py)
- 비교 구현: [reference `policy.py`](../10-capstone-local-coding-agent/reference/coding_agent/policy.py), [reference `tools.py`](../10-capstone-local-coding-agent/reference/coding_agent/tools.py)
- 공개 판정: [`test_stage_07_policy.py`](../10-capstone-local-coding-agent/tests/test_stage_07_policy.py)

```sh
python3 exercises/10-capstone-local-coding-agent/tests/run.py --implementation reference --stage 07
python3 exercises/10-capstone-local-coding-agent/tests/run.py --implementation starter --stage 07 --expect-incomplete
python3 exercises/10-capstone-local-coding-agent/tests/run.py --implementation .workspace/local-coding-agent --stage 07
```

starter의 `NotImplementedError`는 durable approval/revocation, authorization-before-retrieval과 policy-first tool gateway의 의도한 미완성 표식입니다. 대표 실패는 approval의 principal·arguments·artifact digest가 달라도 재사용되거나 revoke 뒤 pending effect가 실행되는 경우입니다. 단계 검사는 01부터 누적됩니다. 위 설계 산출물만으로는 완료가 아니며, 구현·canonical test 결과와 allow/deny/revoke decision trace를 함께 제출합니다.

사람 검토 질문:

- model이 우회 문자열을 만들더라도 gateway 바깥에서 effect나 retrieval을 시작할 경로가 없습니까?
- exact approval의 대상·작업·digest·operation ID·expiry와 one-shot 소비가 trace에서 확인됩니까?

## 의도적 비범위

- enterprise IAM 전체
- production cloud credential
- malware analysis sandbox
