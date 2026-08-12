# 로컬 Git 연습 환경

## 목표

- 격리된 로컬 원격 저장소에서 커밋, 협업, 충돌과 복구 흐름을 재현합니다.
- 명령을 실행하기 전에 바뀔 참조와 작업 트리 상태를 예측합니다.

이 디렉터리는 GitHub 계정 없이도 저장소 복제, 원격 갱신, 브랜치 게시, 원격 추적 브랜치, 브랜치 분기, 충돌과 `reflog`를 재현합니다.

필요한 도구:

```text
Git
Bash
POSIX shell
Python 3.12 이상
```

문서의 일반 Git 명령과 별개로, `setup.sh`의 원자적 workspace publish는 macOS와 Linux를 지원합니다. Windows에서 전체 실습을 진행할 때는 WSL2의 Linux 환경을 사용합니다.

`setup.sh`가 만드는 `sample-app`과 `team-app-*`는 Git 상태를 바꾸고 관찰하기 위한 **exercise fixture**입니다. 애플리케이션 구현 답을 따라 만드는 실습이 아니므로 독립 example, skeleton과 reference implementation이 없습니다. 완료 여부는 아래의 `status`, diff, graph, ref와 프로젝트 검사 결과로 확인합니다.

---

## 생성

전체 환경을 만들려면:

```bash
cd exercises
./setup.sh
```

필요한 환경만 먼저 만들 수도 있습니다.

```bash
./setup.sh sample   # 1·2편
./setup.sh team     # 3·4편
```

이미 존재하는 환경은 덮어쓰지 않습니다. 이 경우 2절의 선택적 초기화를 사용합니다.

생성 결과:

```text
workspace/
├── remotes/
│   ├── sample-app.git
│   └── team-app.git
├── sample-app/
├── team-app-dev-a/
├── team-app-dev-b/
└── team-app-maintainer/
```

- `remotes/*.git`: 작업 트리가 없는 로컬 저장소이며 원격 저장소 역할을 합니다.
- `sample-app`: 1·2편의 개인 작업 흐름에 사용합니다.
- `team-app-dev-a`, `team-app-dev-b`: 같은 원격을 사용하는 두 개발자입니다.
- `team-app-maintainer`: Pull Request가 병합된 상태를 로컬 병합으로 재현합니다.

각 복제에는 테스트용 로컬 작성자 정보가 설정됩니다. 사용자의 전역 `user.name`, `user.email`은 바꾸지 않습니다.

---

## 초기화

필요한 실습만 다시 만들 수 있습니다.

```bash
./setup.sh --reset sample   # 1·2편 환경만 재생성
./setup.sh --reset team     # 3·4편 환경만 재생성
./setup.sh --reset all      # 전체 환경 재생성
```

인자가 없는 `./setup.sh --reset`도 `--reset all`과 같습니다.

선택된 환경의 커밋, 브랜치, stash, reflog와 미추적 파일은 모두 삭제됩니다. 다른 환경은 유지됩니다. 예를 들어 `--reset sample`은 `team-app-*` 저장소를 건드리지 않습니다.

보존할 내용이 있다면 별도 브랜치, bundle, 패치 또는 파일 복사로 백업합니다. 스크립트는 기존 `workspace/`를 자동으로 덮어쓰지 않으며, `exercises/workspace/` 밖의 경로를 삭제하지 않도록 대상 경로를 제한합니다.

---

## sample-app 실습 데이터

```bash
cd workspace/sample-app
./scripts/test.sh
git status --short --branch
```

초기 파일:

```text
src/validate_title.sh
tests/test_validate_title.sh
scripts/test.sh
README.md
.gitignore
```

1·2편에서 다음을 수행할 수 있습니다.

- 저장소, 원격 저장소와 작성자 정보 확인
- 최신 `origin/main`에서 작업 브랜치 생성
- 제목 길이 검증과 테스트 추가
- 같은 README의 관련 변경과 오탈자를 별도 커밋으로 분리
- 개인 메모를 로컬 제외 목록에 추가
- `amend`, `reset`, `reflog` 실습

실습 데이터는 Git 상태 학습용이며 특정 제품의 완성 구현이 아닙니다.

---

## team-app 실습 데이터

세 터미널을 엽니다.

터미널 A:

```bash
cd workspace/team-app-dev-a
git config user.name
git remote -v
./scripts/check.sh
```

터미널 B:

```bash
cd workspace/team-app-dev-b
git config user.name
git remote -v
./scripts/check.sh
```

터미널 M:

```bash
cd workspace/team-app-maintainer
git config user.name
git remote -v
./scripts/check.sh
```

복제본마다 다음 상태는 독립적입니다.

```text
작업 트리
인덱스
로컬 브랜치
stash
reflog
원격 추적 브랜치의 마지막 갱신 시점
```

초기 스키마:

```yaml
fields:
  - title
  - status
```

4편에서는 두 개발자가 같은 영역을 서로 다르게 수정합니다.

```text
개발자 A: priority 추가
개발자 B: assignee 추가
```

`scripts/check.sh`는 다음을 확인합니다.

- 충돌 표시가 없음
- 필수 필드인 `title`, `status`가 있음
- 같은 필드가 중복되지 않음

---

## 단계별 실습과 기대 증거

기대 증거는 정답 파일이 아니라 학습자가 명령을 실행한 뒤 설명해야 하는 관찰 상태입니다. 먼저 자신의 예상과 결과를 기록한 뒤 아래 항목과 비교합니다. root-level `reference/`는 명령과 정책을 빠르게 찾는 자료이며 실습 답안이 아닙니다.

### 1단계 작업 공간과 브랜치

- **직접 수행:** 저장소 root에서 `./exercises/setup.sh sample`로 fixture를 만든 뒤 [1편](../docs/01-workspace-basics.md)의 상태 확인과 작업 브랜치 생성을 따라합니다.
- **수정 위치:** `exercises/workspace/sample-app`의 로컬 branch, `HEAD`, upstream과 원격 추적 ref입니다. 이 단계에서는 애플리케이션 파일을 변경하지 않습니다.
- **검증:** 먼저 `cd exercises/workspace/sample-app`로 이동한 뒤 `./scripts/test.sh`, `git status --short --branch`, `git branch -vv`, `git remote -v`, `git log -1 --decorate`를 실행합니다.
- **기대 증거:** 작업 트리가 깨끗하고 `feature/title-validation`의 `HEAD`가 예상한 `origin/main` 기준점에 있으며, 로컬 bare 저장소가 `origin`으로 보입니다.
- **다음:** 이 상태를 설명한 뒤 [2편](../docs/02-commit-workflow.md)으로 이동합니다.

### 2단계 변경 검토와 커밋

- **직접 수행:** [2편](../docs/02-commit-workflow.md)의 제목 검증·테스트·README 변경과 개인 메모를 만든 뒤 목적별로 나누어 커밋합니다.
- **수정 위치:** `sample-app/src/`, `sample-app/tests/`, `sample-app/README.md`, index와 로컬 exclude 상태입니다.
- **검증:** `sample-app`에서 `./scripts/test.sh`, `git status --short`, `git diff`, `git diff --staged --check`, `git log --oneline origin/main..HEAD`를 실행합니다.
- **기대 증거:** 기능·테스트·관련 문서가 하나의 커밋, 무관한 오탈자가 다른 커밋이며, 개인 메모는 커밋에 없습니다. 각 커밋의 diff와 실행 검사가 같은 목적을 설명합니다.
- **다음:** 커밋 수와 남은 working tree 상태를 설명한 뒤 [3편](../docs/03-remote-pr-workflow.md)으로 이동합니다.

### 3단계 원격 협업

- **직접 수행:** 저장소 root에서 `./exercises/setup.sh team`으로 세 복제를 만든 뒤 [3편](../docs/03-remote-pr-workflow.md)의 작업 브랜치 게시, fetch 전후 비교, 리뷰 반영과 유지관리자 merge를 재현합니다.
- **수정 위치:** `team-app-dev-a`, `team-app-dev-b`, `team-app-maintainer`의 로컬 branch·upstream·remote-tracking ref와 `config/task-fields.yml`입니다.
- **검증:** 각 `team-app-*` 복제 안에서 `./scripts/check.sh`, `git status --short --branch`, `git branch -vv`, `git log --oneline --decorate --graph --all -12`를 실행합니다.
- **기대 증거:** 최초 push 뒤 upstream이 설정되고, 다른 복제의 remote-tracking ref는 fetch 전후로 달라지며, 유지관리자 graph에 예상한 merge 결과가 보입니다.
- **다음:** 로컬 branch와 remote-tracking ref의 차이를 설명한 뒤 [4편](../docs/04-merge-rebase-conflicts.md)으로 이동합니다.

### 4단계 충돌 해결

- **직접 수행:** 이전 `team` 상태를 보존할 필요가 없는지 확인한 뒤 저장소 root에서 `./exercises/setup.sh --reset team`으로 고정 graph를 다시 만들고 [4편](../docs/04-merge-rebase-conflicts.md)을 따라합니다.
- **수정 위치:** `team-app-dev-a`/`team-app-dev-b`의 `config/task-fields.yml`, index, rebase/merge 상태와 원격 작업 브랜치입니다.
- **검증:** 작업 중인 `team-app-*` 복제 안에서 `./scripts/check.sh`, `git status`, `git diff --check`, `git log --oneline --decorate --graph --all -12`와 일반 push의 비선형 갱신 거부를 확인합니다.
- **기대 증거:** 해결된 YAML이 `priority`와 `assignee`를 모두 보존하고 검사를 통과합니다. rebase 뒤 커밋 해시가 바뀌고, 일반 push는 거부되며, 예상한 원격 ref에만 `--force-with-lease`가 성공합니다.
- **다음:** merge와 rebase의 graph 차이를 설명한 뒤 [5편](../docs/05-recovery-runbook.md)으로 이동합니다.

### 5단계 복구 증거

- **직접 수행:** 아래 명령으로 버려도 되는 `recovery-lab.*` 저장소를 만들고 [5편](../docs/05-recovery-runbook.md)의 로컬 reset, detached `HEAD`, revert와 stash를 서로 구분해 연습합니다. 공유 branch 복구는 이 sandbox가 아니라 `team-app-*`에서 영향 범위를 먼저 확인한 뒤 별도로 수행합니다.
- **수정 위치:** 새 `exercises/workspace/recovery-lab.*`의 working tree·index·refs·stash·reflog입니다. `sample-app`과 `team-app-*`의 기존 학습 이력은 건드리지 않습니다.
- **검증:** 생성된 `recovery-lab.*`에서 `git status --short --branch`, `git log --oneline --decorate --graph --all -15`, `git reflog -15`, `git branch --list 'recovery/*'`, `git stash list`, `git show recovery/reset:reset.txt`, `git show recovery/detached:detached.txt`를 확인합니다.
- **기대 증거:** reset으로 보이지 않게 된 커밋과 detached `HEAD`의 커밋이 명시적 `recovery/*` branch에 보존됩니다. revert는 기존 이력을 지우지 않고 새 커밋으로 이전 tree를 복원하며, stash는 의도한 tracked·untracked 상태를 복원합니다. 마지막에 tree, refs와 working tree 상태를 다시 확인합니다.
- **다음:** 각 복구 명령을 고른 근거가 공유 범위와 보존 조건에 맞는지 설명하면 필수 과정이 끝납니다.

#### 버려도 되는 복구 sandbox 만들기

저장소 root에서 실행합니다. `mktemp`가 출력한 절대 또는 상대 경로를 기록합니다. 이 저장소는 학습용이며 `./exercises/setup.sh --reset all`을 실행하면 함께 삭제됩니다.

```bash
RECOVERY_LAB=$(mktemp -d exercises/workspace/recovery-lab.XXXXXX)
git init "$RECOVERY_LAB"
git -C "$RECOVERY_LAB" config user.name 'Guide Recovery Learner'
git -C "$RECOVERY_LAB" config user.email 'guide-recovery@example.invalid'
printf 'base\n' > "$RECOVERY_LAB/state.txt"
git -C "$RECOVERY_LAB" add state.txt
git -C "$RECOVERY_LAB" commit -m 'base'
git -C "$RECOVERY_LAB" branch -M main

# reset 뒤 reflog의 commit을 즉시 branch로 보존합니다.
printf 'reset target\n' > "$RECOVERY_LAB/reset.txt"
git -C "$RECOVERY_LAB" add reset.txt
git -C "$RECOVERY_LAB" commit -m 'reset target'
RESET_TARGET=$(git -C "$RECOVERY_LAB" rev-parse HEAD)
git -C "$RECOVERY_LAB" reset --hard HEAD^
git -C "$RECOVERY_LAB" branch recovery/reset "$RESET_TARGET"
git -C "$RECOVERY_LAB" show recovery/reset:reset.txt

# detached HEAD의 commit도 main으로 돌아가기 전에 식별자를 기록합니다.
git -C "$RECOVERY_LAB" switch --detach main
printf 'detached\n' > "$RECOVERY_LAB/detached.txt"
git -C "$RECOVERY_LAB" add detached.txt
git -C "$RECOVERY_LAB" commit -m 'detached target'
DETACHED_TARGET=$(git -C "$RECOVERY_LAB" rev-parse HEAD)
git -C "$RECOVERY_LAB" switch main
git -C "$RECOVERY_LAB" branch recovery/detached "$DETACHED_TARGET"
git -C "$RECOVERY_LAB" show recovery/detached:detached.txt

# revert 전후 tree가 같고 이력에는 되돌림 commit이 남는지 확인합니다.
TREE_BEFORE=$(git -C "$RECOVERY_LAB" write-tree)
printf 'temporary change\n' > "$RECOVERY_LAB/revert.txt"
git -C "$RECOVERY_LAB" add revert.txt
git -C "$RECOVERY_LAB" commit -m 'change to revert'
git -C "$RECOVERY_LAB" revert --no-edit HEAD
test "$(git -C "$RECOVERY_LAB" write-tree)" = "$TREE_BEFORE"

# tracked와 untracked 변경을 함께 stash하고 다시 적용합니다.
printf 'tracked edit\n' >> "$RECOVERY_LAB/state.txt"
printf 'untracked\n' > "$RECOVERY_LAB/untracked.txt"
git -C "$RECOVERY_LAB" stash push -u -m 'recovery exercise'
test -z "$(git -C "$RECOVERY_LAB" status --porcelain)"
git -C "$RECOVERY_LAB" stash apply --index
git -C "$RECOVERY_LAB" status --short
```

### 선택 90 오픈소스 기여

- **직접 수행:** `team-app` 하나의 공유 원격으로는 작은 branch, push, 리뷰 반영까지만 연습합니다. `origin` fork와 `upstream` 원본을 구분하는 전체 경로는 [90편](../docs/90-open-source-contribution.md)에 따라 실제 hosting fork 또는 따로 준비한 two-remote sandbox에서 수행합니다.
- **수정 위치:** `team-app-dev-a` 작업 branch 또는 실제 fork 작업 브랜치이며, 한 가지 목적의 작은 변경만 다룹니다.
- **검증:** 프로젝트 검사, `git remote -v`, `git status --short`, base…head diff, PR에 기록한 변경 이유·검증 결과를 확인합니다.
- **기대 증거:** 실제 fork 경로에서는 `origin` URL이 자신의 fork, `upstream` URL이 원본 저장소를 가리킵니다. PR의 base·head, 한 가지 목적의 diff, 검증 근거와 범위 밖을 설명할 수 있습니다.
- **다음:** 저장소 기여 정책을 다시 확인하고 선택 경로를 종료합니다.

---

## 로컬 원격 저장소와 호스팅 서비스의 차이

재현 가능한 Git 동작:

- `clone`
- `fetch`
- `push`
- 원격 추적 브랜치
- upstream
- 비선형 갱신 거부
- `merge`와 `rebase`
- 충돌
- reflog와 reset

재현하지 않는 서비스 기능:

- 풀 리퀘스트 화면
- 리뷰 승인
- 브랜치 보호 규칙
- 필수 상태 검사
- 조직 권한과 SSO
- CI 서비스
- fork 네트워크

로컬 실습에서 `main` 직접 푸시가 가능하더라도 실제 팀 정책을 모방한 것은 아닙니다. 문서의 유지관리자 푸시는 PR 병합 후 Git 그래프를 재현하기 위한 실습 전용 절차입니다.

---

## 초기 검증

setup 직후:

```bash
cd workspace/sample-app
./scripts/test.sh

cd ../team-app-dev-a
./scripts/check.sh

cd ../team-app-dev-b
./scripts/check.sh

cd ../team-app-maintainer
./scripts/check.sh
```

모든 명령이 성공해야 합니다.

---

## 유용한 확인 명령

```bash
git status --short --branch
git branch -vv
git branch -a
git remote -v
git log --oneline --decorate --graph --all -12
git reflog -10
```

여러 복제에서 같은 명령을 실행하고 결과를 비교하면 로컬 상태와 원격 상태의 차이를 확인할 수 있습니다.

---

## 문제 발생 시

### 기존 디렉터리 때문에 설정이 실패

정상적인 보호 동작입니다.

```text
선택한 실습 환경이 이미 있습니다
```

보존할 것이 없을 때 필요한 범위만 초기화합니다.

```bash
./setup.sh --reset sample
./setup.sh --reset team
# 둘 다 필요하면: ./setup.sh --reset all
```

### 커밋 작성자 정보 오류

```bash
git config --show-origin --get user.name
git config --show-origin --get user.email
```

각 복제의 로컬 설정이 보여야 합니다.

### 그래프가 문서와 다름

이전 실습 커밋이 남아 있을 수 있습니다.

```bash
git log --oneline --decorate --graph --all -20
```

문서와 같은 초기 상태가 필요하고 기존 작업이 불필요하다면 reset 옵션으로 환경을 다시 만듭니다.

### 전역 Git 설정의 영향

사용자의 별칭, diff 도구, pager, autocrlf, 인증 정보 설정 등은 일부 출력이나 파일 상태에 영향을 줄 수 있습니다. 실습 환경은 작성자 정보와 커밋 서명만 로컬 설정으로 고정합니다. 예상과 다르면 다음으로 설정 출처를 확인합니다.

```bash
git config --show-origin --list
```

## 완료 기준

- sample과 team 환경을 기존 작업을 덮어쓰지 않고 생성할 수 있습니다.
- 목적별 커밋, 원격 동기화와 충돌 해결을 격리된 저장소에서 재현할 수 있습니다.
- reflog와 안전한 참조 생성으로 복구 경로를 설명하고 검증할 수 있습니다.

## 자기 설명

- `fetch` 전후에 어떤 참조가 바뀌며 작업 트리는 왜 그대로입니까?
- `--force-with-lease`가 일반 강제 푸시보다 보존하는 안전 조건은 무엇입니까?

## 검증

### 학습자 단계 검증

학습자의 완료 여부를 한 번에 자동 판정하는 명령은 없습니다. 각 단계의 프로젝트 검사와 Git 상태 명령을 실행하고 [기대 증거](#단계별-실습과-기대-증거)에 맞는지 설명합니다. `setup.sh`를 다시 실행하면 기존 workspace를 덮어쓰지 않고 실패하므로, 범위별 `--reset`은 현재 이력을 버려도 된다는 것을 확인한 뒤만 사용합니다.

### 저장소 자체 검증

아래 명령은 가이드 자체의 setup·문서·검증 계약을 임시 디렉터리에서 재현합니다. 학습자의 `exercises/workspace/`나 그 안의 커밋 이력을 검사하지 않으므로 학습 완료 증거를 대신하지 않습니다.

```bash
# 저장소 root에서
./scripts/validate.sh
./prepare.sh
./verify.sh
```
