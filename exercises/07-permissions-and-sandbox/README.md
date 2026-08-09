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

## 의도적 비범위

- enterprise IAM 전체
- production cloud credential
- malware analysis sandbox
