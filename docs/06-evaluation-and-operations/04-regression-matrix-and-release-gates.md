# 회귀 행렬과 release gate

## 목표

코딩 에이전트의 model·prompt·context·tool·policy·runtime 변경이 어떤 능력과 위험을 바꿨는지 분리해서 평가하고, 배포 가능한 기준을 정합니다.

## 변화 축

```text
model snapshot·reasoning profile
model adapter·stream parser
system instruction·context template
repository discovery·search ranker
compaction·memory
file·patch·process·Git tool
sandbox·permission·approval policy
agent loop·failure classifier
verifier·evaluation environment
```

여러 축을 한 번에 바꾸면 개선 원인을 알기 어렵습니다.

## regression matrix

행은 task category, 열은 위험·품질 축으로 구성할 수 있습니다.

| 과제 | 해결 | 회귀 | 정책 위반 | 평균 turn | 비용 | 사용자 개입 | resume |
|---|---:|---:|---:|---:|---:|---:|---:|
| 단일 file bug |  |  |  |  |  |  |  |
| 다중 file feature |  |  |  |  |  |  |  |
| test 생성 |  |  |  |  |  |  |  |
| build 조사 |  |  |  |  |  |  |  |
| 잘못된 issue |  |  |  |  |  |  |  |
| prompt injection |  |  |  |  |  |  |  |
| crash/resume |  |  |  |  |  |  |  |

평균만 보지 않고 심각한 tail failure를 따로 봅니다.

## gate 유형

### Correctness gate

- 필수 task set resolved rate가 기준 이상
- known regression 0 또는 승인된 예외
- gold/known-good verifier 통과

### Safety gate

- forbidden path·network·secret effect 0
- approval bypass 0
- verifier/answer 접근 0
- cancellation cleanup 통과

안전 gate는 평균 점수로 상쇄하지 않습니다.

### Reliability gate

- tool result schema error 한도
- crash/resume 성공률
- process leak 0
- evaluation environment error 한도

### Cost·latency gate

- task category별 budget
- p50뿐 아니라 p95 wall-clock·cost
- 해결률을 낮추는 단순 제한이 아닌지 확인

### UX gate

- 질문·승인의 적절성
- final evidence completeness
- 사용자가 diff를 이해하고 통제할 수 있는지

## staged release

```text
local deterministic fixtures
→ offline real-model evaluation
→ trusted internal repositories read-only
→ workspace edit with approval
→ bounded command execution
→ selected users/repositories
→ wider release
```

각 단계에서 permission과 blast radius를 독립적으로 확대합니다. model 성능이 좋아졌다고 network와 remote write를 동시에 열지 않습니다.

## canary와 rollback

- runtime·model·policy version pinning
- session cohort
- feature flag
- old checkpoint compatibility
- rollback artifact
- active session 처리
- metrics와 alert

새 runtime이 오래된 session을 resume할 수 없으면 자동 migration보다 기존 version에 고정하거나 manual review로 이동합니다.

## evaluation set 유지

- production incident를 anonymized fixture로 추가
- 같은 template 과도 중복 제거
- 공개 benchmark와 private holdout 분리
- test flakiness와 evaluator error 정기 검토
- model training leakage 가능성 기록
- retired task와 이유 보존

## 실패 조건

- resolved rate가 올랐다는 이유로 policy violation 증가를 허용합니다.
- model과 runtime을 동시에 바꾸고 원인을 단정합니다.
- 평균 비용만 보고 특정 task의 폭증을 놓칩니다.
- release 뒤 active session checkpoint 호환을 확인하지 않습니다.
- production incident가 회귀 case로 이어지지 않습니다.

## 완료 조건

- capability, safety, reliability, cost와 UX gate를 분리합니다.
- task category별 regression matrix를 유지합니다.
- permission 확대와 model/runtime 배포를 단계적으로 분리합니다.
- rollback 시 active session과 checkpoint를 처리하는 절차가 있습니다.
