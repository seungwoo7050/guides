# Git, worktree, rollback과 change set

## 목표

Git을 단순히 diff 출력 도구로 사용하지 않고, coding-agent session의 기준점·변경 격리·검토·복구 계약으로 사용합니다.

## Git adapter의 책임

- repository와 worktree identity 확인
- HEAD·branch·index·working tree 상태 읽기
- agent 전용 worktree 또는 branch 생성
- baseline과 current diff 생성
- path별 stage 상태 구분
- user pre-existing change 보존
- agent change set rollback
- 선택적으로 commit 준비

remote push, PR와 merge는 핵심 Capstone 밖에 둡니다.

## worktree 전략

### 사용자 worktree 공유

대화형 pair mode에서 빠르지만 충돌과 복구 위험이 큽니다.

### agent 전용 worktree

```text
원본 repository object database
+ 기준 commit
+ agent session 전용 worktree
+ 독립 branch 또는 detached state
```

장점:

- 사용자 working tree를 건드리지 않습니다.
- session별 diff와 cleanup이 명확합니다.
- 동일 repository에서 여러 agent task를 병렬로 분리할 수 있습니다.

주의:

- 같은 branch를 두 worktree에서 checkout할 수 없는 제약
- repository-level config와 hooks
- untracked local config
- submodule·LFS
- shared object database와 GC

## index 사용

에이전트가 file을 수정하는 것과 stage하는 것을 분리합니다.

- 기본 local agent는 working tree만 수정합니다.
- stage는 사용자가 review할 boundary가 될 수 있습니다.
- partial staging은 diff 해석을 복잡하게 만듭니다.
- session 시작 전 staged change가 있으면 별도 baseline에 포함합니다.

## change set identity

```text
change_set_id
base_commit
initial_index_tree
initial_worktree_manifest
agent_operations[]
current_diff_digest
changed_paths
created_at
```

formatter나 command가 만든 예상 밖 변경도 change set에 포함하되 origin을 구분합니다.

## rollback 수준

### 마지막 edit 되돌리기

inverse patch 또는 file receipt를 사용합니다.

### 마지막 plan 단위 되돌리기

change set checkpoint로 복구합니다.

### session 전체 폐기

agent worktree를 제거합니다. object·process·cache cleanup을 확인합니다.

### 사용자에게 적용

최종 patch, branch, commit 또는 file copy 방식 중 하나를 선택합니다. 적용 전 target workspace divergence를 다시 검사합니다.

## commit 계약

commit을 선택 기능으로 제공할 때:

- 검증이 끝난 change set만 대상으로 합니다.
- user identity와 agent attribution 정책을 정합니다.
- commit message는 실제 변경과 test evidence를 반영합니다.
- secret·generated artifact·unrelated file을 제외합니다.
- pre-commit hook의 코드 실행과 permission을 고려합니다.
- commit 성공을 task 성공과 동일시하지 않습니다.

## Git command 안전성

다음은 별도 high-risk action으로 분류합니다.

```text
reset --hard
clean
checkout/switch with overwrite
rebase
merge
commit --amend
submodule update
remote add
push --force
```

모델이 범용 process runner로 이 동작을 우회하지 못하게 command policy와 Git adapter를 함께 설계합니다.

## 실패 조건

- 사용자 dirty change와 agent change를 하나의 diff로 보고합니다.
- rollback에 `git reset --hard`를 사용합니다.
- hook이 실행됐는지 기록하지 않습니다.
- worktree cleanup 전에 background process가 해당 path를 사용합니다.
- final patch를 다른 base commit에 무검증 적용합니다.
- commit을 만들었다는 이유로 test 완료를 주장합니다.

## 완료 조건

- session 시작 전 staged·unstaged·untracked 상태를 보존합니다.
- agent 전용 worktree 생성·폐기와 실패 복구 절차를 문서화합니다.
- agent operation과 formatter·command mutation을 diff에서 구분합니다.
- final change set을 사용자 workspace에 적용하기 전 base와 conflict를 검사합니다.
