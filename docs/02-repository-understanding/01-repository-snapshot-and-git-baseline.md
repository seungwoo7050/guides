# 저장소 snapshot과 Git 기준점

## 목표

에이전트가 읽고 수정하는 대상이 무엇인지 변경 전에 고정합니다. 사용자 작업을 덮어쓰거나, 다른 branch의 코드를 기준으로 판단하거나, resume 뒤 다른 tree에 patch를 적용하는 일을 막습니다.

## 시작 시 확인할 상태

```text
repository root
Git 여부와 object database 위치
HEAD commit 또는 unborn branch
현재 branch·detached HEAD
index 상태
working tree 변경
untracked·ignored file
submodule·worktree
sparse checkout
line ending·file mode 설정
```

`git status --short` 한 줄만으로 모든 상태를 표현하지 않습니다. agent가 만든 변경과 session 시작 전에 존재한 변경을 구분할 baseline이 필요합니다.

## RepositorySnapshot

예시:

```text
snapshot_id
canonical_root
vcs_type
head_commit
branch_name
index_tree
tracked_worktree_digest_map
initial_untracked_manifest
submodule_commits
repository_config_digest
instruction_manifest
created_at
```

큰 저장소에서 모든 file hash를 즉시 계산하기 어렵다면 Git tree와 index를 정본으로 사용하고, 읽거나 수정한 file만 content digest를 추가합니다.

## dirty workspace 정책

다음 중 하나를 명시적으로 선택합니다.

### 사용자 workspace에서 직접 작업

- 기존 변경을 보존합니다.
- agent 변경과 사용자 변경이 같은 file에서 겹칠 수 있습니다.
- rollback이 어렵습니다.
- interactive pair-programming에 적합하지만 자동화에는 위험합니다.

### 별도 worktree 또는 clone

- 기준 commit에서 격리된 작업 공간을 만듭니다.
- 사용자 dirty state와 분리합니다.
- agent change set을 쉽게 폐기할 수 있습니다.
- submodule, LFS, local dependency와 untracked config를 별도로 준비해야 합니다.

### ephemeral snapshot

- container나 copy-on-write filesystem에 저장소를 복제합니다.
- 강한 격리와 재현성을 얻습니다.
- 대용량 repository와 cache 비용이 큽니다.

Capstone은 기본적으로 별도 worktree 또는 disposable copy를 권장합니다.

## 기준점 변경

session 중 다음 사건은 repository identity를 바꿉니다.

- `checkout`, `switch`, `reset`, `rebase`, `merge`
- 외부 process의 file 변경
- dependency install이 lockfile 또는 generated source 변경
- formatter가 넓은 file set 수정
- submodule update

에이전트가 기준점을 바꾸려면 별도 action과 승인이 필요합니다. 단순 command runner를 통해 암묵적으로 branch를 바꾸지 않습니다.

## 낙관적 동시성

읽은 file에는 digest 또는 blob identity를 붙입니다.

```text
read_file(path) → content + digest
apply_patch(path, expected_digest, patch)
```

적용 시 digest가 다르면 stale write로 거절하고 다시 읽습니다. 여러 file을 하나의 change set으로 적용할 때는 전체 precondition을 먼저 검사한 뒤 원자적 또는 rollback 가능한 순서로 처리합니다.

## resume 검증

session 재개 시 다음을 확인합니다.

1. canonical root가 같은지
2. HEAD·branch·worktree identity가 같은지
3. session이 수정한 file의 digest가 receipt와 같은지
4. 외부 변경이 있는지
5. pending patch의 precondition이 아직 유효한지
6. instruction과 build environment가 바뀌었는지

다르면 자동 계속보다 `REBASE_REQUIRED`, `WORKSPACE_DIVERGED`, `MANUAL_REVIEW` 같은 상태로 이동합니다.

## 실패 조건

- dirty workspace에서 모든 변경을 agent 결과로 보고합니다.
- `git reset --hard`나 `clean`으로 사용자의 기존 작업을 지웁니다.
- worktree 생성 뒤 repository-local config와 submodule 상태를 확인하지 않습니다.
- resume가 session ID만 보고 같은 저장소라고 판단합니다.
- line ending이나 file mode 변화가 의미 없는 대규모 diff를 만듭니다.

## 완료 조건

- session 시작 전·후 change set을 정확히 구분합니다.
- 사용자 변경을 보존하는 정책과 격리 작업 공간 정책을 각각 설명합니다.
- stale patch와 workspace divergence를 재현하고 자동 거절할 수 있습니다.
- 최종 결과가 어떤 commit과 initial dirty state에서 만들어졌는지 기록합니다.
