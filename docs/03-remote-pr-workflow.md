# 원격 협업과 풀 리퀘스트

## 학습 목표

- fetch, upstream, push와 Pull Request가 갱신하는 상태를 구분합니다.
- 리뷰어가 범위·이유·검증을 재현할 수 있는 협업 단위를 만듭니다.

로컬 작업을 원격 브랜치에 게시하고 다른 개발자와 상태를 공유한 뒤, 리뷰 가능한 풀 리퀘스트로 변경을 제안하는 흐름을 살펴봅니다.

```text
최신 원격 기준 확인
→ 작업 브랜치 생성
→ 커밋
→ 최초 푸시와 upstream 설정
→ 풀 리퀘스트
→ 리뷰·CI 반영
→ 병합 후 정리
```

GitHub의 풀 리퀘스트 화면은 로컬 실습에서 재현할 수 없습니다. 실습 환경에서는 저장소 복제, 원격 갱신, 푸시, 원격 추적 브랜치와 비선형 갱신 거부를 실제 Git 동작으로 확인합니다.

---

## 선행 개념

- local/remote-tracking branch의 차이와 `fetch` 뒤 분기 상태 읽기

## 최소 원격 모델

### 로컬 브랜치와 원격 추적 브랜치

```text
feature/add-priority          내 로컬 브랜치
origin/feature/add-priority   마지막 fetch/푸시에서 확인한 원격 브랜치의 로컬 기록
```

두 이름은 같은 브랜치가 아닙니다. 로컬 브랜치에서 새 커밋을 만들어도 푸시하기 전에는 원격 브랜치가 이동하지 않습니다.

### fetch, pull, 푸시

| 명령 | 주된 효과 | 현재 브랜치·작업 트리 |
| --- | --- | --- |
| `git fetch` | 원격 객체와 원격 추적 브랜치 갱신 | 자동 통합하지 않음 |
| `git pull` | fetch 후 현재 브랜치에 통합 | merge/rebase/ff-only 정책에 따라 바뀔 수 있음 |
| `git push` | 로컬 ref와 객체를 원격에 게시 | 원격 갱신이 거부될 수 있음 |

불확실하면 `pull`부터 실행하지 않고 `fetch` 후 차이를 읽습니다.

### upstream

upstream은 로컬 브랜치가 기본적으로 비교·pull·푸시할 상대 브랜치입니다.

```bash
git push -u origin feature/add-priority
```

최초 푸시에서 `-u`를 사용하면 이후 다음 명령에 인자를 생략할 수 있습니다.

```bash
git push
git status
git branch -vv
```

---

## 실습 환경 준비

이번 글은 같은 원격 저장소를 사용하는 세 개의 복제를 사용합니다.

```text
team-app-dev-a          변경 작성자
team-app-dev-b          다른 개발자
team-app-maintainer     PR 병합 상태를 재현하는 관리자 복제
```

처음 상태가 필요하면 다음 명령을 실행합니다.

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

모든 복제에서 초기 검사를 실행합니다.

```bash
./scripts/check.sh
git status --short --branch
```

---

## 개발자 A가 작업 브랜치 만들기

터미널 A:

```bash
git fetch origin
git switch --no-track -c feature/add-priority origin/main
```

`config/task-fields.yml`을 다음처럼 수정합니다.

```yaml
fields:
  - title
  - status
  - priority
```

검사하고 커밋합니다.

```bash
./scripts/check.sh
git diff
git add config/task-fields.yml
git diff --staged
git commit -m "feat: add priority task field"
```

### 푸시 전에 예상하기

```text
Q1. origin/feature/add-priority가 이미 존재합니까?
Q2. 개발자 B가 fetch 없이 이 커밋을 볼 수 있습니까?
Q3. 현재 로컬 브랜치에 upstream이 있습니까?
```

정답:

```text
A1. 아직 없습니다.
A2. 볼 수 없습니다.
A3. 아직 없습니다.
```

확인합니다.

```bash
git branch -vv
git branch -r
git log -1 --oneline --decorate
```

---

## 최초 푸시와 upstream 설정

터미널 A:

```bash
git push -u origin HEAD
```

`HEAD`는 현재 브랜치를 뜻하므로 브랜치명을 중복해서 입력하지 않아도 됩니다.

확인합니다.

```bash
git status --short --branch
git branch -vv
git log -1 --oneline --decorate
```

예상 관계:

```text
HEAD → feature/add-priority
          ↕ upstream
origin/feature/add-priority
```

현재 상태가 같다면 `status`에 앞서거나 뒤처진 커밋 수가 표시되지 않습니다.

---

## 개발자 B가 fetch 전후를 비교하기

터미널 B에서 먼저 확인합니다.

```bash
git branch -r
git log --oneline --decorate --all -8
```

A가 푸시한 뒤에도 B가 fetch하지 않았다면 새 원격 추적 브랜치가 보이지 않을 수 있습니다.

이제 fetch합니다.

```bash
git fetch origin
```

다시 확인합니다.

```bash
git branch -r
git log --oneline --decorate --all -8
git show --stat origin/feature/add-priority
```

실행 결과에서 볼 점:

```text
A의 푸시
→ 원격 브랜치 이동
→ B의 로컬 상태는 자동 변경되지 않음
→ B의 fetch
→ B의 origin/* 갱신
```

`origin/*`가 서버를 실시간으로 읽는 이름이 아니라는 사실을 직접 확인한 것입니다.

---

## Pull Request가 하는 일

Pull Request는 한 브랜치의 변경을 다른 브랜치에 병합하자는 제안입니다.

```text
기준 브랜치:  main
비교 브랜치:  feature/add-priority
```

GitHub에서는 PR에 다음 맥락이 모입니다.

- 변경 설명과 대화
- 포함된 커밋
- 전체 diff
- 자동 테스트와 정적 분석 결과
- 리뷰와 승인 상태

PR을 만들었다고 Git 커밋이 새로 생기지는 않습니다. PR은 이미 원격에 게시된 비교 브랜치와 기준 브랜치의 관계를 협업 화면으로 구성합니다.

### GitHub 웹에서 생성

저장소의 “Compare & pull request” 또는 “New pull request”에서 base와 compare 브랜치를 확인합니다.

### GitHub CLI로 생성

```bash
gh pr create \
  --base main \
  --head feature/add-priority \
  --title "작업 우선순위 필드 추가" \
  --web
```

`--web`은 base와 head를 지정한 상태로 브라우저의 작성 화면을 엽니다. `gh`가 없거나 조직 정책이 다르면 웹 UI에서 같은 방향을 직접 선택합니다.

---

## 리뷰 가능한 PR 작성

좋은 PR 본문은 diff를 다시 나열하는 대신 변경 이유와 검증 근거를 제공합니다.

```markdown
## 변경

- task schema에 `priority` field를 추가했습니다.

## 이유

- 작업 우선순위를 정렬·표시하기 위한 최소 schema가 필요합니다.

## 검증

- `./scripts/check.sh`
- 기존 필수 field 유지 확인
- 중복 field 없음 확인

## 리뷰 요청

- `priority` 이름과 schema 위치가 기존 규칙에 맞는지 확인해 주세요.

## 범위 밖

- priority 값의 enum과 UI 표시는 포함하지 않았습니다.
```

### PR을 만들기 전 범위 확인

```bash
git fetch origin
git log --oneline origin/main..HEAD
git diff --stat origin/main...HEAD
git diff origin/main...HEAD
```

`...` 비교는 두 브랜치의 merge base부터 현재 브랜치까지의 변경을 보는 데 유용합니다.

### 초안 PR

작업 방향을 일찍 공유해야 하지만 아직 정식 리뷰 준비가 되지 않았다면 draft를 사용합니다. draft는 “미완성도 병합해 달라”는 뜻이 아니라, 협업 맥락을 일찍 공유하는 수단입니다.

---

## 리뷰 의견 반영

리뷰 수정은 일반 커밋과 같습니다.

```bash
# 파일 수정
./scripts/check.sh
git diff
git add path/to/file
git diff --staged
git commit -m "fix: address priority schema review"
git push
```

### 새 커밋과 amend 중 선택

- 리뷰 과정이 진행 중이고 변경 과정을 보존할 가치가 있으면 새 커밋을 추가할 수 있습니다.
- 팀이 최종적으로 squash merge한다면 중간 커밋이 반드시 완벽할 필요는 없습니다.
- 게시된 커밋을 amend 또는 interactive rebase하면 이력 재작성와 강제 푸시가 필요합니다.

리뷰어가 확인 중인 브랜치를 다시 쓸 때는 팀 정책과 시점을 먼저 확인합니다.

---

## CI 실패 대응

CI 실패를 “GitHub 문제”로 묶지 않습니다.

먼저 다음을 구분합니다.

```text
내 변경으로 재현되는 테스트 실패
환경·의존성 차이
flaky test
권한 또는 비밀값 누락
기준 브랜치 변경으로 인한 실패
```

가능하면 CI가 실행한 명령을 로컬에서 재현합니다.

```bash
./scripts/check.sh
```

PR에는 다음을 설명합니다.

- 실패한 job과 단계
- 로컬 재현 여부
- 원인으로 좁힌 변경
- 수정 후 실행한 검증

실패를 무시하고 재실행만 반복하지 않습니다.

---

## 통제된 실패: 비선형 갱신 푸시

이 실험은 두 개발자가 같은 원격 작업 브랜치에 서로 다른 커밋을 만든 상황을 재현합니다. 실제 팀에서는 개인 작업 브랜치를 공동 편집하는 정책인지 먼저 확인합니다.

### 개발자 B가 A의 브랜치를 가져와 새 커밋을 푸시

터미널 B:

```bash
git fetch origin
git switch --track -c feature/add-priority origin/feature/add-priority
printf '%s\n' '' '작업 스키마에 우선순위가 추가되었습니다.' >> README.md
git add README.md
git commit -m "docs: describe priority field"
git push
```

### 개발자 A가 원격 갱신을 모른 채 다른 커밋을 만듦

터미널 A:

```bash
printf '%s\n' '' '스키마를 바꾸면 저장소 검사를 실행해야 합니다.' >> README.md
git add README.md
git commit -m "docs: note schema validation"
git push
```

일반 푸시는 거부되어야 합니다. 원격 브랜치에 A가 갖고 있지 않은 B의 커밋이 있기 때문입니다.

오류 뒤에는 먼저 확인합니다.

```bash
git status --short --branch
git fetch origin
git log --oneline --decorate --graph --all -10
```

두 커밋을 보존하려면 팀 정책에 따라 merge 또는 rebase합니다.

개인 작업 브랜치에서 rebase를 허용한다고 가정한 예:

```bash
git rebase origin/feature/add-priority
# 충돌이 있으면 해결 후 git add, git rebase --continue
./scripts/check.sh
git push
```

이 경우 rebase 대상은 아직 A가 푸시하지 않은 로컬 커밋이므로 정상 푸시가 가능합니다. 원격에 이미 게시한 자신의 커밋을 다시 썼다면 4편의 `--force-with-lease`가 필요합니다.

---

## 실습에서 PR 병합 상태 재현

실제 저장소에서는 보호된 기준 브랜치와 PR 화면을 사용합니다. 로컬 실습에서는 유지관리자 복제에서 merge 커밋을 만들어 PR 병합 후 상태만 재현합니다.

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

이 직접 푸시는 **실습 전용**입니다. 실제 팀 저장소에서는 브랜치 보호, 필수 리뷰와 CI 정책을 따릅니다.

---

## 병합 후 정리

터미널 A:

```bash
git fetch --prune origin
git switch main
git merge --ff-only origin/main
git branch -d feature/add-priority
```

원격 작업 브랜치도 삭제되었다면 `fetch --prune`이 사라진 원격 추적 브랜치를 정리합니다.

브랜치 삭제가 거부되면 Git이 로컬 브랜치가 현재 로컬 이력에 병합되지 않았다고 판단한 것입니다. 무조건 `-D`를 사용하지 말고 먼저 확인합니다.

```bash
git log --oneline --decorate --graph --all -12
git branch --contains feature/add-priority
```

squash merge를 사용한 저장소에서는 원래 작업 커밋이 기준 브랜치에 그대로 포함되지 않으므로 `git branch -d`가 거부될 수 있습니다. PR이 실제로 병합되었고 브랜치의 독립 작업을 보존할 필요가 없는지 확인한 뒤 삭제합니다.

---

## 표준 PR 업무 흐름

```bash
# 최신 원격 상태 확인
git fetch origin

# 작업 브랜치 생성
git switch --no-track -c feature/TOPIC origin/main

# 작업, 검토, 커밋
git status --short
git diff
git add -p
git diff --staged
./scripts/check.sh
git commit

# 최초 게시
git push -u origin HEAD

# PR 범위 확인
git log --oneline origin/main..HEAD
git diff origin/main...HEAD

# 리뷰 반영 후
git push

# 병합 후 정리
git fetch --prune origin
git switch main
git merge --ff-only origin/main
```

---

## 신뢰할 수 있는 협업자의 기준

- PR 제목과 본문이 변경 이유를 설명합니다.
- 관련 없는 변경을 한 PR에 섞지 않습니다.
- 리뷰 전에 테스트와 diff를 직접 확인합니다.
- CI 실패를 숨기거나 재실행만 반복하지 않습니다.
- 기준 브랜치가 바뀌었다고 무조건 강제 푸시하지 않습니다.
- 리뷰 중 이력를 다시 쓸 때 영향을 먼저 알립니다.
- merge 방식과 브랜치 정리는 저장소 정책을 따릅니다.

---

## 공식 참고 문서

- [git-fetch](https://git-scm.com/docs/git-fetch)
- [git-pull](https://git-scm.com/docs/git-pull)
- [`git push`](https://git-scm.com/docs/git-push)
- [GitHub Pull Requests](https://docs.github.com/en/pull-requests/reference/pull-requests)
- [GitHub의 보호된 브랜치](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)

## 연결 실습

- [team-app 실습](../exercises/README.md)에서 최초 push, fetch 전후, review 수정과 merge 후 정리를 재현합니다.

## 완료 기준

- 현재 상태와 다음 명령의 영향을 근거와 함께 설명할 수 있습니다.
- 문서의 절차를 격리된 로컬 저장소에서 재현하고 결과를 확인할 수 있습니다.
- 실패했을 때 작업을 보존하는 복구 경로를 선택할 수 있습니다.
