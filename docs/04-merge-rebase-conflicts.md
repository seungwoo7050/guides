# merge·rebase와 충돌 해결

## 학습 목표

- merge와 rebase가 그래프를 바꾸는 방식을 예측하고 충돌 상태를 읽습니다.
- 양쪽 의도를 보존해 해결한 뒤 lease 보호 push 조건을 검증합니다.

이 글의 목표는 다음 세 가지입니다.

1. merge와 rebase가 커밋 그래프에 미치는 차이를 설명합니다.
2. 충돌을 “한쪽을 선택하는 작업”이 아니라 “두 변경 의도를 통합하는 작업”으로 처리합니다.
3. 해결할 수 없으면 시작 전 상태로 안전하게 돌아갑니다.

실습에서는 같은 YAML 목록에 두 개발자가 서로 다른 필드를 추가하여 실제 충돌을 만듭니다.

---

## 선행 개념

- 공통 조상과 branch tip으로 분기 그래프를 읽고 일반 push 조건 설명하기

## 상태를 읽는 기준

공통 시작점 `B`에서 main과 feature가 갈라졌다고 가정합니다.

```text
A──B──C        main
    \
     D──E      feature
```

### merge

feature에서 main을 merge하면 기존 커밋을 유지하고 두 이력을 연결하는 merge 커밋을 만들 수 있습니다.

```text
A──B──C────M   feature
    \      /
     D────E
```

특징:

- 기존 `C`, `D`, `E`의 해시를 바꾸지 않습니다.
- 분기와 통합 사실이 그래프에 남습니다.
- 통합 결과를 나타내는 merge 커밋이 생길 수 있습니다.

### rebase

feature를 main 위로 rebase하면 `D`, `E`의 변경을 `C` 위에 다시 적용합니다.

```text
A──B──C──D'──E'   feature
```

특징:

- `D'`, `E'`는 원래 커밋과 다른 새 커밋입니다.
- 해시가 바뀝니다.
- 이미 게시한 브랜치를 rebase하면 원격 갱신에 이력 재작성이 필요합니다.

### 선택 기준

| 상황 | 일반적으로 검토할 선택 |
| --- | --- |
| 여러 사람이 함께 쓰는 공유 브랜치 | merge 또는 팀이 정한 비재작성 방식 |
| 아직 게시하지 않은 개인 작업 브랜치 | rebase 가능 |
| 게시했지만 작성자만 사용하는 PR 브랜치 | 팀 정책과 리뷰 상태를 확인한 뒤 rebase 가능 |
| 장기 보존할 분기 맥락이 중요 | merge 검토 |
| base 위에 개인 커밋을 선형으로 정리 | rebase 검토 |

merge가 항상 안전하고 rebase가 항상 깔끔한 것은 아닙니다. **브랜치를 누가 사용하고 있는지**가 가장 중요한 판단 기준입니다.

---

## 충돌은 왜 생기는가

Git은 공통 조상, 현재 쪽 변경, 통합할 쪽 변경을 비교합니다.

```text
base:    title, 상태
change A: title, 상태, priority
change B: title, 상태, assignee
```

두 변경이 같은 영역을 수정하면 Git이 최종 순서와 의미를 결정할 수 없을 수 있습니다.

충돌은 Git이 고장 난 상태가 아닙니다.

> 자동으로 결정할 근거가 부족하므로 사람이 최종 결과를 결정해야 하는 상태입니다.

충돌을 해결할 때는 표시를 지우기 전에 다음 질문에 답해야 합니다.

```text
각 변경은 왜 필요했습니까?
둘 다 유지해야 합니까?
최종 파일은 유효합니까?
테스트는 통과합니까?
```

---

## 실습 환경 초기화

이번 실습은 고정된 그래프가 필요하므로 기존 연습 작업을 삭제하고 다시 만듭니다.

```bash
./exercises/setup.sh --reset team
```

터미널 A:

```bash
cd exercises/workspace/team-app-dev-a
```

터미널 B:

```bash
cd exercises/workspace/team-app-dev-b
```

터미널 M:

```bash
cd exercises/workspace/team-app-maintainer
```

초기 상태:

```yaml
fields:
  - title
  - status
```

---

## 개발자 B가 먼저 브랜치와 원격 커밋 만들기

터미널 B:

```bash
git fetch origin
git switch --no-track -c feature/add-assignee origin/main
```

`config/task-fields.yml`을 수정합니다.

```yaml
fields:
  - title
  - status
  - assignee
```

검사·커밋·푸시합니다.

```bash
./scripts/check.sh
git add config/task-fields.yml
git diff --staged
git commit -m "feat: add assignee task field"
git push -u origin HEAD
```

현재 그래프를 확인합니다.

```bash
git log --oneline --decorate --graph --all -8
```

B의 커밋은 원격 작업 브랜치에는 있지만 main에는 없습니다.

---

## 개발자 A가 다른 변경을 main에 반영

터미널 A:

```bash
git fetch origin
git switch --no-track -c feature/add-priority origin/main
```

같은 파일을 다음처럼 수정합니다.

```yaml
fields:
  - title
  - status
  - priority
```

```bash
./scripts/check.sh
git add config/task-fields.yml
git commit -m "feat: add priority task field"
git push -u origin HEAD
```

로컬 실습에서 유지관리자가 PR 병합 상태를 재현합니다.

터미널 M:

```bash
git fetch origin
git switch main
git merge --ff-only origin/main
git merge --no-ff origin/feature/add-priority \
  -m "merge: feature/add-priority 병합"
./scripts/check.sh
git push origin main
```

실제 팀 저장소에서는 PR, 리뷰, CI와 브랜치 보호 규칙을 따릅니다. 위 직접 푸시는 이 연습 환경에서만 사용합니다.

---

## rebase 전에 결과를 예상하기

터미널 B에서 다음 질문에 답합니다.

```text
Q1. 로컬 `feature/add-assignee`는 어느 main을 기준으로 만들어졌습니까?
Q2. origin/main에는 어떤 새 변경이 있습니까?
Q3. rebase하면 B의 커밋 해시는 유지됩니까?
Q4. 같은 YAML 목록 끝을 수정했으므로 충돌 가능성이 있습니까?
```

원격 상태를 갱신하고 그래프를 봅니다.

```bash
git fetch origin
git log --oneline --decorate --graph --all -12
```

B의 로컬 브랜치와 `origin/feature/add-assignee`는 아직 같은 이전 커밋을 가리키고, `origin/main`은 priority 변경을 포함합니다.

---

## rebase로 충돌 재현

터미널 B:

```bash
git rebase origin/main
```

충돌이 발생하면 즉시 다른 Git 명령을 연속으로 실행하지 않습니다.

```bash
git status
```

확인할 내용:

- rebase가 진행 중인지
- 현재 적용 중인 커밋
- 병합되지 않은 경로
- 계속하거나 중단하는 명령

충돌 파일을 엽니다.

```text
 <<<<<<< HEAD
  - priority
 =======
  - assignee
 >>>>>>> <커밋>
```

표시의 정확한 배치는 Git 버전과 앞뒤 문맥에 따라 다를 수 있습니다.

rebase 중 `HEAD`는 새 기준점 쪽 상태를 나타내고, 다시 적용 중인 커밋은 `REBASE_HEAD`로 확인할 수 있습니다.

```bash
git show HEAD:config/task-fields.yml
git show REBASE_HEAD:config/task-fields.yml
```

`ours`, `theirs`라는 단어를 사람 A와 B의 고정된 이름처럼 암기하지 않습니다. merge와 rebase에서 관점이 달라져 혼동하기 쉽습니다.

---

## 두 변경 의도를 보존하여 해결

최종 파일을 다음처럼 만듭니다.

```yaml
fields:
  - title
  - status
  - priority
  - assignee
```

표시가 남아 있지 않은지 확인하고 프로젝트 검사를 실행합니다.

```bash
git diff --check
./scripts/check.sh
```

해결한 파일을 스테이징합니다.

```bash
git add config/task-fields.yml
```

현재 상태를 다시 읽습니다.

```bash
git status
git diff --staged
```

rebase를 계속합니다.

```bash
GIT_EDITOR=true git rebase --continue
```

환경에 따라 커밋 메시지 편집기가 열릴 수 있습니다. 기존 메시지를 유지한다면 저장하고 종료합니다.

최종 상태를 확인합니다.

```bash
./scripts/check.sh
git status --short --branch
git log --oneline --decorate --graph --all -12
```

B의 새 커밋 해시가 원래 `origin/feature/add-assignee`와 달라졌음을 확인합니다.

---

## rebase 후 일반 푸시가 거부되는 이유

먼저 일반 푸시를 시도하여 실패를 관찰합니다.

```bash
git push
```

원격 작업 브랜치는 이전 커밋을 가리키고 로컬 브랜치는 rebase로 만든 새 커밋을 가리킵니다. 두 이력은 fast-forward 관계가 아니므로 일반 푸시가 거부됩니다.

확인합니다.

```bash
git fetch origin
git log --oneline --decorate --graph --all -12
```

이 브랜치를 작성자 한 명만 사용하고, 리뷰 정책이 이력 재작성를 허용하며, 원격이 예상한 이전 커밋 그대로임을 확인한 뒤 갱신합니다.

```bash
git push --force-with-lease origin HEAD:feature/add-assignee
```

`--force-with-lease`는 원격 참조가 예상한 값일 때만 강제 갱신하도록 검사합니다. 일반 `--force`보다 안전하지만 다음을 대신하지는 않습니다.

- 공유 브랜치 사용 금지 판단
- 최신 원격 그래프 확인
- 리뷰어에게 이력 변경 알림
- 브랜치 보호

IDE나 도구가 백그라운드 `fetch`를 수행하면 로컬 원격 추적 참조가 갱신될 수 있습니다. 중요한 작업에서는 푸시 직전에 원격 상태를 다시 확인하고, 팀이 요구한다면 예상 SHA를 명시하는 더 엄격한 보호 조건을 사용합니다.

```bash
git push \
  --force-with-lease=feature/add-assignee:EXPECTED_OLD_SHA \
  origin HEAD:feature/add-assignee
```

이 고급 형식은 저장소 정책과 실제 이전 SHA를 이해할 때만 사용합니다.

---

## 해결하지 않고 rebase 취소하기

충돌 해결 방향이 불명확하거나 base 선택이 잘못되었다면 중단합니다.

```bash
git rebase --abort
```

`HEAD`와 브랜치는 rebase 시작 전 상태로 돌아가야 합니다.

```bash
git status --short --branch
git log --oneline --decorate --graph --all -10
```

`--abort`를 사용할 수 있도록 rebase 전에 unrelated 작업 트리 변경을 정리하는 습관이 중요합니다.

---

## 같은 상황을 merge로 통합하면

실습을 초기화한 뒤 같은 A·B 변경을 만들고, B에서 다음을 실행할 수 있습니다.

```bash
git fetch origin
git merge origin/main
```

충돌 해결 절차는 비슷합니다.

```bash
git status
# 파일 수정
git diff --check
./scripts/check.sh
git add config/task-fields.yml
git merge --continue
```

취소:

```bash
git merge --abort
```

merge는 기존 feature 커밋을 다시 만들지 않으므로 일반적으로 해결 후 정상 푸시가 가능합니다.

```bash
git push
```

단, merge 시작 전에 커밋하지 않은 변경이 있었다면 `merge --abort`가 원래 변경을 완전히 복원하지 못할 수 있습니다. 통합 전 작업 트리에 변경이 없도록 정리합니다.

---

## 충돌 해결 표준 절차

```bash
# 1. 현재 작업 확인
git status

# 2. 그래프와 양쪽 의도 확인
git log --oneline --decorate --graph --all -12

# 3. 파일 수정
# 충돌 표시 제거와 최종 동작 설계

# 4. 기본 오류 확인
git diff --check

# 5. 프로젝트 검증
./scripts/check.sh

# 6. 해결 파일 스테이징
git add path/to/resolved-file

# 7. 다시 상태 확인
git status
git diff --staged

# 8. 진행 중인 작업에 맞게 계속
git rebase --continue
# 또는
git merge --continue

# 9. 최종 확인
git status --short --branch
git log --oneline --decorate --graph --all -12
```

해결 방향이 틀렸다면 계속하기 전에 중단합니다.

```bash
git rebase --abort
# 또는
git merge --abort
```

---

## 자주 하는 실수

### 표시만 삭제함

문법적으로 표시가 없어도 한쪽 기능이 사라질 수 있습니다. 양쪽 변경 목적과 최종 테스트를 확인합니다.

### 충돌 중 `git pull`을 다시 실행함

진행 중인 병합이나 리베이스를 먼저 완료하거나 중단합니다. 새로운 통합을 겹치지 않습니다.

### 모든 파일에 ours 또는 theirs를 적용함

바이너리나 명확한 생성 파일이 아니라면 파일별 의도를 확인합니다. 일괄 선택은 조용한 기능 손실을 만들 수 있습니다.

### 공유 브랜치를 rebase함

다른 사람이 해당 커밋 위에 작업했을 수 있습니다. 브랜치 소유권과 팀 정책을 확인합니다.

### 충돌 해결 후 테스트를 생략함

Git은 text를 합칠 뿐 도메인 규칙을 검증하지 않습니다.

### 일반 `--force`를 사용함

원격에 새로 생긴 다른 사람의 커밋까지 덮어쓸 수 있습니다. 허용된 개인 브랜치에서만 `--force-with-lease`를 검토합니다.

---

## 충돌을 줄이는 협업 방식

- 작업 브랜치를 오래 방치하지 않습니다.
- 큰 공용 파일 변경은 먼저 역할과 인터페이스를 합의합니다.
- 기능 변경과 광범위한 formatting을 같은 PR에 섞지 않습니다.
- 공통 스키마, 의존성 파일과 빌드 파일 변경을 팀에 일찍 알립니다.
- 작은 PR로 통합 주기를 짧게 유지합니다.
- 충돌을 피하려고 설계 문제를 숨기지 않습니다. 공통 인터페이스가 충돌한다면 사람 간 합의가 먼저입니다.

---

## 공식 참고 문서

- [git-merge](https://git-scm.com/docs/git-merge)
- [git-rebase](https://git-scm.com/docs/git-rebase)
- [`git push`](https://git-scm.com/docs/git-push)
- [GitHub의 보호된 브랜치](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)

## 연결 실습

- [team-app 실습](../exercises/README.md)에서 priority와 assignee를 충돌시키고 rebase/merge 결과를 비교합니다.

## 완료 기준

- 현재 상태와 다음 명령의 영향을 근거와 함께 설명할 수 있습니다.
- 문서의 절차를 격리된 로컬 저장소에서 재현하고 결과를 확인할 수 있습니다.
- 실패했을 때 작업을 보존하는 복구 경로를 선택할 수 있습니다.
