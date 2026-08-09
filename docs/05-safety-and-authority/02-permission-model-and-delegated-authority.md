# 권한 모델과 delegated authority

## 목표

에이전트가 사용자의 계정과 권한 전체를 상속하지 않게 하고, 이번 task에 필요한 resource와 action만 제한된 기간 동안 위임합니다.

## principal 분리

```text
user_principal       작업을 요청하고 승인하는 사용자
agent_session        이번 실행의 identity
runtime_service      tool과 state를 관리하는 service
sandbox_process      실제 command를 실행하는 OS principal
verifier             결과를 독립 판정하는 principal
remote_connector     GitHub·issue tracker 등 선택적 외부 principal
```

모델 자체는 credential을 가진 principal이 아닙니다. model output은 agent session이 요청한 action candidate입니다.

## resource grant

예:

```text
repository snapshot: repo-123@commit
read roots: workspace/** excluding secrets/**
write roots: workspace/src/**, workspace/tests/**
commands: discovered check profiles
network: deny
Git: status·diff only
expires: 2 hours
max change paths: 20
```

권한은 tool name뿐 아니라 arguments와 resource에 묶입니다.

## permission decision

```text
principal
+ session/task
+ tool/effect class
+ canonical resource
+ arguments digest
+ current phase
+ policy version
+ prior approval
→ allow | deny | require approval
```

모델의 reason이나 confidence는 권한 입력이 아닙니다.

## deny 우선

allow와 deny가 겹치면 deny를 우선합니다.

예:

```text
allow read workspace/**
deny  read workspace/.env
deny  read workspace/evaluation/hidden/**
```

path pattern은 canonical path와 file type 확인 뒤 적용합니다.

## permission mode

제품 UI 이름과 무관하게 설계상 다음 profile을 둘 수 있습니다.

### Plan/read-only

조사와 계획만 허용합니다. file edit와 command 실행을 막거나 read-only command만 허용합니다.

### Workspace edit

허용 path의 patch를 적용할 수 있지만 command·network·Git effect는 별도 승인합니다.

### Controlled execution

등록된 build/test command를 sandbox에서 실행합니다.

### Elevated task

dependency install, network, commit 등 특정 effect를 task-scoped grant로 허용합니다.

### Unrestricted

격리된 disposable environment에서만 명시적으로 선택합니다. 권장 기본값이 아닙니다.

## approval과 permission

permission은 가능한 행동의 상한이고 approval은 특정 행동에 대한 사용자 결정입니다.

- policy가 deny한 행동은 승인으로 허용하지 않을 수 있습니다.
- session grant 밖 resource는 broad approval 문장으로 열지 않습니다.
- approval은 exact patch/command 또는 명확한 pattern과 expiry를 가집니다.
- 사용자가 permission을 revoke하면 pending action과 credential을 무효화합니다.

## credential

가능하면 task별 short-lived credential을 broker에서 발급합니다.

- 모델 context에 원문을 넣지 않습니다.
- process env에 필요한 command에만 주입합니다.
- scope·expiry·audience를 제한합니다.
- 사용 receipt를 남깁니다.
- session 종료와 revoke 시 폐기합니다.

기본 Capstone은 remote credential 없이 완성합니다.

## 권한 확대

에이전트는 직접 policy file을 수정하거나 permission mode를 바꾸지 못합니다.

필요한 경우:

1. 차단된 action과 이유를 설명합니다.
2. 필요한 최소 resource·effect·기간을 제안합니다.
3. 사용자가 승인합니다.
4. 새 grant revision을 만듭니다.
5. 기존 plan과 risk를 재평가합니다.

## 실패 조건

- agent process가 사용자 home credential을 상속합니다.
- `Bash`를 허용하면 모든 command와 shell operator가 허용됩니다.
- permission rule이 symlink와 canonical path를 무시합니다.
- 승인 문장 하나로 session 전체 권한을 영구 확대합니다.
- verifier와 agent가 같은 write credential을 공유합니다.

## 완료 조건

- principal, resource, action과 approval을 별도 model로 표현합니다.
- read, edit, command, dependency, Git, network가 다른 권한을 가집니다.
- revoke와 expiry가 실제 tool 실행 전에 강제됩니다.
- 에이전트가 권한 부족을 우회하지 않고 최소 확대를 요청합니다.
