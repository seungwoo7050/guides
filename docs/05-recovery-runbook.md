# Git 복구 절차

## 학습 목표

- 공유 범위와 손실 위험에 따라 restore, reset, revert, reflog와 stash를 선택합니다.
- 보존 branch를 만든 뒤 graph·status·test로 복구 결과를 확인합니다.

문제가 생겼을 때 증상과 공유 범위를 기준으로 해결책을 찾는 복구 절차서입니다.

복구 명령을 고르는 가장 중요한 기준은 다음 세 가지입니다.

```text
1. 아직 커밋하지 않은 변경입니까?
2. 로컬에만 있는 커밋입니까?
3. 이미 다른 사람과 공유한 커밋입니까?
```

같은 “되돌리기”라도 세 상태의 해결법은 다릅니다.

---

## 선행 개념

- HEAD·branch·index·working tree·reflog 구분과 local/shared 상태 판별

## 가장 먼저 할 일

문제가 생겼다고 바로 `reset --hard`, `clean -fd`, 강제 푸시를 실행하지 않습니다.

### 현재 상태 보존

```bash
git status
git branch --show-current
git log --oneline --decorate --graph --all -12
git reflog -12
```

오류 메시지, 현재 브랜치와 최근 그래프를 기록합니다. 터미널 출력을 공유할 때 토큰, 내부 URL, 이메일 등 민감한 정보는 제거합니다.

### 안전 지점 만들기

현재 HEAD를 잃을 가능성이 있다면 브랜치를 하나 만듭니다.

```bash
git branch backup/before-recovery-$(date +%Y%m%d-%H%M%S)
```

작업 트리에 중요한 커밋하지 않은 파일이 있다면 Git 명령 외에도 별도 디렉터리 복사를 검토합니다. 미추적 파일은 커밋·브랜치·reflog가 보호하지 않을 수 있습니다.

### 진행 중인 작업 확인

`git status`가 다음 중 하나를 말하는지 확인합니다.

```text
merge in progress
rebase in progress
cherry-pick in progress
revert in progress
```

진행 중인 작업이 있다면 다른 복구를 겹치기 전에 continue 또는 abort를 선택합니다.

---

## 상황별 선택표

| 상황 | 우선 검토할 명령 | 핵심 효과 |
| --- | --- | --- |
| 스테이징하지 않은 추적 수정 취소 | `git restore path/to/file` | 작업 트리 수정 제거 |
| 스테이징만 취소, 수정 유지 | `git restore --staged path/to/file` | 인덱스를 HEAD 기준으로 복원 |
| 마지막 로컬 커밋에 누락 추가 | `git commit --amend` | 마지막 커밋 교체 |
| 마지막 로컬 커밋을 다시 작업 상태로 | `git reset --soft HEAD~1` 또는 `git reset HEAD~1` | 브랜치 이동, 변경 유지 |
| 잘못된 로컬 브랜치에 커밋 | 새 브랜치 생성 또는 cherry-pick | 커밋 보존 후 위치 정리 |
| 이미 푸시한 잘못된 커밋 취소 | `git revert COMMIT_SHA` | 반대 변경을 새 커밋으로 기록 |
| `reset`/`rebase` 후 커밋이 사라짐 | `git reflog` + 복구 브랜치 | 이전 참조 위치 보존 |
| merge/rebase를 중단 | `--abort` | 작업 시작 전 상태로 복귀 시도 |
| 미추적 파일 삭제 전 확인 | `git clean -nd` | 삭제 예정 목록만 표시 |
| 원격 푸시가 거부됨 | `git fetch` + 그래프 확인 | 원격 차이 조사 |

이 표는 출발점입니다. 경로, 브랜치, 공유 여부를 확인하지 않고 복사해서 실행하지 않습니다.

---

## 아직 스테이징하지 않은 추적 수정 취소

### 증상

```bash
git status --short
```

```text
 M src/app.c
```

### 먼저 확인

```bash
git diff -- src/app.c
```

버릴 내용이 정확한지 확인합니다.

### 해결 `[주의]`

```bash
git restore src/app.c
```

이 명령은 기본적으로 인덱스의 내용을 작업 트리에 복원합니다. 해당 파일에 스테이징된 변경이 없다면 인덱스와 HEAD의 내용이 같으므로 결과도 HEAD로 되돌린 것처럼 보입니다. 어느 경우든 스테이징하지 않은 작업 트리 수정은 사라집니다.

### 검증

```bash
git status --short
git diff -- src/app.c
```

### 스테이징된 변경과 스테이징되지 않은 변경이 함께 있는 파일

```text
MM src/app.c
```

`git restore src/app.c`는 스테이징 이후에 다시 수정한 작업 트리 부분만 인덱스 상태로 되돌립니다. 인덱스에 이미 스테이징된 변경은 남습니다.

```bash
git diff -- src/app.c
git diff --staged -- src/app.c
```

무엇을 버리는지 두 diff를 모두 확인합니다.

### 미추적 파일

`git restore`는 일반 미추적 파일을 삭제하지 않습니다. 파일을 직접 백업하거나 삭제 여부를 판단합니다. `git clean`은 15절을 먼저 봅니다.

---

## 스테이징만 취소하고 수정은 유지

### 증상

```text
M  src/app.c
```

### 먼저 확인

```bash
git diff --staged -- src/app.c
```

### 해결

```bash
git restore --staged src/app.c
```

인덱스는 HEAD 기준으로 돌아가지만 작업 트리 수정은 유지됩니다.

### 검증

```bash
git status --short
git diff -- src/app.c
git diff --staged -- src/app.c
```

예상 상태:

```text
 M src/app.c
```

`git restore src/app.c`와 혼동하지 않습니다. `--staged`가 없으면 작업 트리 변경을 버릴 수 있습니다.

---

## 마지막 로컬 커밋 수정

### 조건

- 수정할 대상이 현재 브랜치의 마지막 커밋입니다.
- 아직 다른 사람과 공유하지 않았습니다.

### 누락 파일 추가

```bash
# 파일 수정
git add path/to/file
git diff --staged
git commit --amend --no-edit
```

### 메시지만 수정

```bash
git commit --amend
```

### 검증

```bash
git show --stat --oneline HEAD
git status --short
```

amend는 기존 커밋을 내부에서 고치는 것이 아니라 새 커밋으로 교체합니다. 해시가 바뀝니다. 이미 푸시한 브랜치라면 4편의 이력 재작성 조건을 확인합니다.

---

## 마지막 로컬 커밋을 다시 나누기

### 상황

한 커밋에 서로 다른 두 목적이 섞였고 아직 공유하지 않았습니다.

### 안전 지점

```bash
git branch backup/before-split
```

### 커밋만 취소하고 변경을 인덱스에 유지

```bash
git reset --soft HEAD~1
```

상태:

```text
HEAD          이전 커밋으로 이동
인덱스         취소한 커밋의 전체 변경 유지
작업 트리  그대로
```

스테이징한 내용을 모두 내린 뒤 다시 선택합니다.

```bash
git restore --staged .
git status --short
git diff
```

목적별로 나눕니다.

```bash
git add -p
git diff --staged
# 프로젝트가 지정한 검증 명령 실행
git commit -m "첫 번째 변경 목적 설명"

# 남은 변경
git diff
git add -p
git diff --staged
# 프로젝트가 지정한 검증 명령 실행
git commit -m "두 번째 변경 목적 설명"
```

### `git reset HEAD~1`

옵션 없는 reset은 기본적으로 mixed 방식입니다.

```text
HEAD          이전 커밋으로 이동
인덱스         이전 커밋 기준으로 복원
작업 트리  변경 유지
```

처음부터 변경을 스테이징되지 않은 상태로 받고 싶다면 사용할 수 있습니다.

### `--hard`를 사용하지 않는 이유

`git reset --hard HEAD~1`은 브랜치, 인덱스, 작업 트리를 대상 커밋에 맞추므로 수정 내용까지 잃을 수 있습니다.

---

## 잘못된 브랜치에 로컬 커밋

### 올바른 브랜치가 아직 없는 경우

잘못된 브랜치의 현재 HEAD에서 새 브랜치를 만들어 커밋을 보존합니다.

```bash
git switch -c feature/correct-topic
```

이제 새 브랜치가 해당 커밋을 가리킵니다.

잘못된 원래 브랜치를 되돌립니다. 예를 들어 로컬 `main`에 잘못 커밋했고 원격 main과 같게 만들려는 경우:

```bash
git switch main
git fetch origin
git reset --hard origin/main
```

`reset --hard` 전에 다음을 확인합니다.

```bash
git status --short
git log --oneline origin/main..main
```

새 작업 브랜치가 잘못된 커밋을 보존하는지 확인한 뒤 실행합니다.

### 올바른 브랜치가 이미 있는 경우

커밋 해시를 확인합니다.

```bash
git log -1 --oneline
```

올바른 브랜치로 이동하여 cherry-pick합니다.

```bash
git switch feature/correct-topic
git cherry-pick COMMIT_SHA
```

검증 후 잘못된 브랜치에서 원래 커밋을 제거합니다. 그 브랜치가 공유되었는지에 따라 reset 또는 revert를 선택합니다.

---

## 이미 푸시한 잘못된 커밋 취소

공유된 이력은 기본적으로 reset으로 지우지 않습니다. 반대 변경을 새 커밋으로 기록합니다.

### 먼저 확인

```bash
git fetch origin
git log --oneline --decorate --graph --all -12
git show BAD_COMMIT_SHA
```

### 해결

```bash
git revert BAD_COMMIT_SHA
```

Git이 자동으로 반대 patch를 적용하고 새 커밋을 만듭니다.

충돌이 발생하면:

```bash
git status
# 파일 수정
git add path/to/resolved-file
git revert --continue
```

취소:

```bash
git revert --abort
```

### 검증

```bash
# 프로젝트가 지정한 검증 명령 실행
git show --stat --oneline HEAD
git push
```

### merge 커밋 revert

병합 커밋은 어느 부모를 기준선으로 볼지 지정해야 합니다.

```bash
git revert -m 1 MERGE_COMMIT_SHA
```

`-m 1`을 관례적으로 복사하지 않습니다. 부모 커밋의 순서와 원하는 결과를 `git show --no-patch --pretty=raw MERGE_COMMIT_SHA`로 확인합니다. merge 커밋을 잘못 되돌리면 이후 재병합에도 영향을 주므로 팀과 함께 처리합니다.

---

## 진행 중인 작업 취소

먼저 `git status`로 실제 진행 상태를 확인합니다.

### merge

```bash
git merge --abort
```

merge 시작 전에 커밋하지 않은 변경이 있었다면 완전한 복원이 어려울 수 있습니다.

### rebase

```bash
git rebase --abort
```

HEAD를 rebase 시작 전 브랜치 위치로 되돌립니다.

### cherry-pick

```bash
git cherry-pick --abort
```

### revert

```bash
git revert --abort
```

### 검증

```bash
git status --short --branch
git log --oneline --decorate --graph --all -12
```

`--quit`은 진행 상태만 잊고 인덱스와 작업 트리를 그대로 둘 수 있으므로, 시작 전 상태로 돌아가는 `--abort`와 다릅니다.

---

## reset·rebase 후 사라진 커밋 찾기

reflog는 로컬 저장소에서 브랜치와 HEAD 같은 ref가 이전에 어디를 가리켰는지 기록합니다.

```bash
git reflog --date=local -20
```

예:

```text
8f3c2aa HEAD@{0}: reset: moving to HEAD~1
b91d4e0 HEAD@{1}: 커밋: implement validation
```

사라진 커밋을 찾았다면 즉시 브랜치로 보존합니다.

```bash
git branch recovery/validation b91d4e0
```

내용을 확인합니다.

```bash
git show --stat recovery/validation
git log --oneline --decorate --graph --all -12
```

필요하면 해당 브랜치로 이동합니다.

```bash
git switch recovery/validation
```

reflog는 해당 로컬 복제의 기록입니다. 다른 컴퓨터의 reflog나 삭제된 복제를 대신하지 않으며, 영구 백업도 아닙니다.

---

## detached HEAD에서 만든 커밋 보존

### 확인

```bash
git branch --show-current
git status
git log -1 --oneline --decorate
```

브랜치 이름이 없지만 커밋이 필요하다면 현재 위치에서 브랜치를 만듭니다.

```bash
git switch -c recovery/detached-work
```

이미 다른 브랜치로 이동해 커밋이 보이지 않으면 reflog에서 찾습니다.

```bash
git reflog -20
git branch recovery/detached-work COMMIT_SHA
```

브랜치를 만든 뒤 실제 내용과 테스트를 확인합니다.

---

## 작업을 잠시 보관해야 할 때: stash

stash는 작업 트리와 인덱스의 상태를 임시로 기록하고 변경이 없는 상태로 돌아갈 때 사용합니다.

### 생성

```bash
git stash push -u -m "WIP: investigate parser failure"
```

`-u`는 미추적 파일도 포함합니다. 무시된 파일은 기본적으로 포함하지 않습니다.

### 확인

```bash
git stash list
git stash show -p stash@{0}
```

### 복원

먼저 삭제하지 않고 적용하는 편이 안전합니다.

```bash
git stash apply stash@{0}
```

검증 후 제거합니다.

```bash
git stash drop stash@{0}
```

`git stash pop`은 apply와 성공 시 drop을 함께 수행합니다. 충돌이 나면 stash가 남을 수 있으므로 상태를 확인합니다.

stash는 이름 없는 장기 보관소가 아닙니다. 며칠 이상 유지할 중요한 작업은 명확한 브랜치와 커밋으로 보존하는 편이 낫습니다.

---

## 푸시가 비선형 갱신으로 거부됨

강제 푸시부터 하지 않습니다.

```bash
git fetch origin
git status --short --branch
git log --oneline --decorate --graph --all -15
```

확인할 질문:

```text
원격에 자신이 갖고 있지 않은 커밋이 있습니까?
같은 브랜치를 다른 사람이 사용합니까?
로컬 커밋은 이미 게시된 적이 있습니까?
팀은 merge와 rebase 중 무엇을 요구합니까?
```

원격 커밋을 보존하면서 merge:

```bash
git merge origin/BRANCH
```

게시하지 않은 로컬 커밋을 원격 위로 rebase:

```bash
git rebase origin/BRANCH
```

충돌 해결과 검증 후 일반 푸시를 다시 시도합니다.

이미 게시한 커밋을 rebase했다면 `--force-with-lease`가 필요할 수 있지만, 개인 브랜치·팀 정책·원격 상태를 먼저 확인합니다.

---

## 잘못된 강제 푸시 복구

### 즉시 협업 중단 알림

해당 브랜치에 새 푸시를 멈추고 팀에 상황을 공유합니다. 계속 푸시하면 복구 기준점이 더 복잡해집니다.

### 복구 후보 찾기

강제 푸시 전 복제가 남아 있다면:

```bash
git reflog --date=local -30
git log --oneline --decorate --graph --all -20
```

다른 팀원의 복제에도 이전 커밋이 남아 있을 수 있습니다.

후보를 브랜치로 보존합니다.

```bash
git branch recovery/pre-force-push OLD_SHA
```

### 원격 현재 상태 확인

```bash
git fetch origin
git log --oneline --decorate --graph --all -20
```

### 복구 푸시

팀이 복구 기준 SHA에 합의한 뒤에만 원격 브랜치를 되돌립니다.

```bash
git push \
  --force-with-lease=BRANCH:CURRENT_REMOTE_SHA \
  origin RECOVERY_SHA:BRANCH
```

이 상황은 개인 판단으로 처리하지 않습니다. 브랜치 보호 규칙과 호스팅 서비스 감사 로그도 확인합니다.

---

## 토큰·비밀번호·개인 키를 커밋함

### 1단계: 먼저 폐기·회전

이력에서 파일을 지우는 것보다 인증 정보를 무효화하는 것이 먼저입니다.

```text
토큰 폐기 또는 교체
비밀번호 변경
SSH 키 폐기·재발급
관련 접근 로그 확인
보안 담당자와 저장소 관리자에게 알림
```

이미 푸시했다면 노출된 것으로 간주합니다.

### 2단계: 영향 범위 확인

- 어느 브랜치, 태그, PR, fork에 포함되었습니까?
- 공개 저장소입니까?
- 다른 복제나 CI 캐시에 남아 있습니까?
- 비밀값 탐지 경고가 있습니까?

### 3단계: 이력 정리 여부 결정

`.gitignore` 추가나 최신 커밋에서 파일 삭제만으로 과거 이력이 사라지지 않습니다.

이력 재작성이 필요하면 저장소 관리자와 모든 협업자가 함께 계획합니다. 일반적으로 `git-filter-repo` 같은 전용 도구를 사용하며, 브랜치·태그·PR·fork·서명·복제에 광범위한 영향을 줍니다.

개별 개발자가 즉시 `git push --force --all`을 실행하지 않습니다.

### 4단계: 재발 방지

- 비밀값을 환경변수나 비밀값 관리 도구로 이동
- `.gitignore` 보완
- 푸시 보호 또는 비밀값 탐지 활성화
- 커밋 전 스테이징된 diff 검토

---

## `reset --hard`와 `clean` 실행 전

### `git reset --hard COMMIT_SHA`

다음을 대상 커밋에 맞춥니다.

```text
현재 브랜치
인덱스
작업 트리의 추적 파일
```

실행 전:

```bash
git status --short
git diff
git diff --staged
git log --oneline --decorate -8
git branch backup/before-hard-reset
```

일반 미추적 파일은 reset의 직접 대상이 아니지만, 대상 커밋의 추적 파일을 써야 하는 경로를 가로막는 미추적 파일이나 디렉터리는 삭제될 수 있습니다. 중요한 미추적 파일은 별도로 백업합니다.

### `git clean`

미추적 파일과 디렉터리를 삭제할 수 있습니다. 먼저 모의 실행을 사용합니다.

```bash
git clean -nd
```

무시된 파일까지 포함할 필요가 있는 특수 상황에서는 더 위험합니다.

```bash
git clean -ndx
```

목록을 확인한 뒤에만 실제 삭제를 검토합니다.

```bash
git clean -fd
```

`-x`를 실제 삭제와 함께 사용하면 무시된 빌드 산출물뿐 아니라 로컬 environment 파일도 삭제할 수 있습니다.

---

## 저장소를 다시 복제해야 하는가

대부분의 브랜치, 원격 저장소, reset, rebase 문제는 다시 복제하지 않아도 해결할 수 있습니다.

다시 복제할지 검토하는 상황은 다음과 같습니다.

- `.git` 내부가 실제로 손상되었고 `git fsck`와 백업으로 복구하기 어려움
- 보안 사고 후 관리자가 깨끗한 상태로 다시 복제하기를 요구함
- 매우 복잡한 이력 재작성 후 기존 복제 폐기가 공식 절차임
- 현재 디렉터리가 불완전한 파일 복사본이며 정식 복제가 아님

재복제 전에 반드시 보존할 것:

```text
커밋하지 않은 파일
미추적 파일
로컬 전용 브랜치와 태그
stash
원격 저장소 URL과 로컬 config
필요한 reflog 커밋
```

새 복제는 원인을 해결하지 않고 증상만 숨길 수 있습니다.

---

## 복구 후 검증

모든 복구 뒤에는 같은 절차를 반복합니다.

```bash
git status --short --branch
git branch -vv
git log --oneline --decorate --graph --all -15
git diff
git diff --staged
# 프로젝트가 지정한 검증 명령 실행
```

원격을 바꿨다면:

```bash
git fetch origin
git log --oneline --decorate --graph --all -15
```

다음 질문에 답합니다.

```text
필요한 커밋이 브랜치로 보존되었습니까?
의도하지 않은 파일 손실이 없습니까?
원격에 있는 다른 사람의 커밋을 지우지 않았습니까?
작업 트리와 인덱스가 예상한 상태입니까?
프로젝트 검사가 통과합니까?
```

---

## 공식 참고 문서

- [git-restore](https://git-scm.com/docs/git-restore)
- [git-reset](https://git-scm.com/docs/git-reset)
- [git-revert](https://git-scm.com/docs/git-revert)
- [git-reflog](https://git-scm.com/docs/git-reflog)
- [git-stash](https://git-scm.com/docs/git-stash)
- [git-clean](https://git-scm.com/docs/git-clean)
- [저장소에서 민감한 데이터 제거하기](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)

## 연결 실습

- [복구 5단계](../exercises/README.md#5단계-복구-증거)의 버려도 되는 sandbox에서 reset으로 보이지 않게 된 commit과 detached `HEAD` commit을 명시적 branch로 보존하고, revert·stash의 상태 증거를 재현합니다. 공유 이력 복구는 별도의 `team-app-*`에서 영향 범위를 먼저 확인한 뒤 수행합니다.

## 완료 기준

- 현재 상태와 다음 명령의 영향을 근거와 함께 설명할 수 있습니다.
- 문서의 절차를 격리된 로컬 저장소에서 재현하고 결과를 확인할 수 있습니다.
- 실패했을 때 작업을 보존하는 복구 경로를 선택할 수 있습니다.
