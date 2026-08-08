# Git 상황별 빠른 참조

이 문서는 명령을 처음 배우는 튜토리얼이 아닙니다. 작업 중 현재 상태와 안전한 다음 행동을 빠르게 찾는 용도입니다.

위험한 명령은 경로, 브랜치와 공유 여부를 확인한 뒤 실행합니다.

---

## 현재 위치와 상태

```bash
# 저장소 루트
git rev-parse --show-toplevel

# 현재 브랜치
git branch --show-current

# 브랜치와 파일 상태
git status --short --branch

# 로컬 브랜치, upstream과 앞선·뒤처진 커밋 수
git branch -vv

# 원격 저장소 URL
git remote -v

# 최근 그래프
git log --oneline --decorate --graph --all -12

# 최근 참조 이동
git reflog -12
```

문제가 생기면 `status → log --graph → reflog` 순서로 확인합니다.

---

## 변경 비교

```bash
# 스테이징하지 않은 변경: 작업 트리 ↔ 인덱스
git diff

# 다음 커밋에 들어갈 변경: 인덱스 ↔ HEAD
git diff --staged

# 전체 변경: 작업 트리 ↔ HEAD
git diff HEAD

# 특정 파일
git diff -- path/to/file
git diff --staged -- path/to/file

# 변경량 요약
git diff --stat
git diff --staged --stat

# 공백 오류
git diff --check
git diff --staged --check
```

`git diff`가 비어 있어도 스테이징된 변경이 있을 수 있습니다.

---

## 스테이징과 커밋

```bash
# 파일 단위 스테이징
git add path/to/file

# 변경 조각 단위 스테이징
git add -p path/to/file

# 스테이징만 취소하고 수정은 유지
git restore --staged path/to/file

# 커밋
git commit

# 마지막 로컬 커밋 수정
git commit --amend

# 커밋 결과 확인
git show --stat --oneline HEAD
```

커밋 전 최소 확인:

```bash
git status --short
git diff --staged
```

이어서 해당 저장소가 지정한 테스트와 정적 분석 명령을 실행합니다.

---

## 작업 브랜치 시작

```bash
# 원격 정보 갱신
git fetch origin

# 최신 원격 main에서 브랜치 생성
git switch --no-track -c feature/TOPIC origin/main

# 기존 브랜치로 이동
git switch feature/TOPIC

# 현재 브랜치 확인
git branch --show-current
```

기본 브랜치가 `develop` 또는 `trunk`라면 실제 이름으로 바꿉니다.

---

## 원격 협업

```bash
# 원격 갱신과 사라진 원격 추적 브랜치 정리
git fetch --prune origin

# 최초 푸시와 upstream 설정
git push -u origin HEAD

# 이후 푸시
git push

# 원격에만 있는 커밋
git log --oneline HEAD..origin/BRANCH

# 현재 브랜치에만 있는 커밋
git log --oneline origin/BRANCH..HEAD

# 그래프로 양쪽 차이 확인
git log --oneline --decorate --graph --all -15
```

`git pull`은 fetch 후 현재 브랜치에 통합합니다. 통합 방식이 불명확하면 fetch와 그래프 확인을 먼저 합니다.

---

## 로컬 기본 브랜치 갱신

작업 트리에 변경이 없는지 먼저 확인합니다.

```bash
git status --short
```

fast-forward만 허용하여 갱신합니다.

```bash
git fetch origin
git switch main
git merge --ff-only origin/main
```

로컬 main에 독자적인 커밋이 있으면 `--ff-only`가 실패합니다. 그 커밋의 소유권을 확인하지 않고 재설정하지 않습니다.

---

## merge와 rebase

```bash
# 기준 브랜치 변경을 현재 브랜치에 병합
git fetch origin
git merge origin/main

# 개인 브랜치를 최신 기준 브랜치 위로 rebase
git fetch origin
git rebase origin/main
```

선택 질문:

```text
이 브랜치를 다른 사람이 사용합니까?
로컬 커밋이 이미 게시되었습니까?
팀은 merge와 rebase 중 무엇을 요구합니까?
분기 이력을 보존해야 합니까?
```

---

## 충돌

```bash
# 현재 작업과 병합되지 않은 파일 확인
git status

# 파일을 수정한 뒤 공백 오류 확인
git diff --check

# 이어서 저장소가 지정한 테스트와 정적 분석 명령 실행

# 해결한 파일 스테이징
git add path/to/resolved-file

# 계속
git rebase --continue
# 또는
git merge --continue

# 시작 전 상태로 취소
git rebase --abort
# 또는
git merge --abort
```

충돌 중 새로운 pull, merge, rebase를 겹치지 않습니다.

---

## 복구 결정표

| 상황 | 명령 | 주의 |
| --- | --- | --- |
| 스테이징되지 않은 추적 수정 취소 | `git restore path/to/file` | 작업 트리 변경 삭제 |
| 스테이징만 취소 | `git restore --staged path/to/file` | 수정은 유지 |
| 마지막 로컬 커밋 수정 | `git commit --amend` | 해시 변경 |
| 마지막 로컬 커밋 취소, 스테이징 유지 | `git reset --soft HEAD~1` | 공유 전 사용 |
| 마지막 로컬 커밋 취소, 스테이징되지 않은 유지 | `git reset HEAD~1` | 기본 mixed 방식 |
| 공유한 커밋 취소 | `git revert COMMIT_SHA` | 반대 변경의 새 커밋 생성 |
| 사라진 커밋 찾기 | `git reflog` | 해당 로컬 복제의 기록 |
| detached HEAD 커밋 보존 | `git switch -c recovery/NAME` | 현재 위치에서 즉시 브랜치 생성 |

---

## reflog 복구

```bash
git reflog --date=local -20

# 찾은 커밋을 즉시 브랜치로 보존
git branch recovery/NAME COMMIT_SHA

# 내용 확인
git show --stat recovery/NAME
git log --oneline --decorate --graph --all -12
```

reflog는 영구 백업이나 다른 컴퓨터의 기록이 아닙니다.

---

## 강제 푸시 전

```bash
git fetch origin
git status --short --branch
git log --oneline --decorate --graph --all -15
```

확인:

```text
[ ] 개인 작업 브랜치입니까?
[ ] 다른 사람이 이전 이력 위에 작업하지 않았습니까?
[ ] 팀 정책이 이력 재작성을 허용합니까?
[ ] 리뷰어에게 해시 변경 영향을 알렸습니까?
[ ] 현재 원격 참조가 예상한 값입니까?
```

허용된 상황에서:

```bash
git push --force-with-lease origin HEAD:BRANCH
```

일반 `--force`를 기본 선택으로 사용하지 않습니다. `--force-with-lease`도 브랜치 보호 규칙과 협업자 간 합의를 대신하지 않습니다.

---

## 데이터 삭제 가능 명령

```bash
# 추적 파일을 대상 커밋에 맞춤
git reset --hard COMMIT_SHA

# 미추적 파일의 삭제 예정 목록만 확인
git clean -nd

# 무시된 파일도 포함한 삭제 예정 목록
git clean -ndx

# 미추적 파일과 디렉터리 실제 삭제
git clean -fd
```

실행 전:

```bash
git status --short
git diff
git diff --staged
git branch backup/before-destructive-change
```

미추적 파일은 브랜치와 reflog가 보호하지 않습니다.

---

## stash

```bash
# 미추적 파일을 포함해 임시 보관
git stash push -u -m "WIP: 보관 이유"

# 목록과 내용
git stash list
git stash show -p stash@{0}

# 삭제하지 않고 적용
git stash apply stash@{0}

# 확인 후 삭제
git stash drop stash@{0}
```

중요한 장기 작업은 이름 있는 브랜치와 커밋으로 보존합니다.

---

## fork와 upstream

```bash
# 자신의 fork를 복제한 뒤 원본 저장소 추가
git remote add upstream \
  https://github.com/ORIGINAL_OWNER/REPOSITORY.git

# 확인
git remote -v

# 원본 최신 상태 가져오기
git fetch upstream

# 최신 원본 main에서 기여 브랜치 생성
git switch --no-track -c fix/TOPIC upstream/main

# 자신의 fork에 푸시
git push -u origin HEAD
```

관례:

```text
origin    내 fork
upstream  원본 저장소
```

---

## PR 전 체크리스트

```text
[ ] 기준 저장소·브랜치와 비교 저장소·브랜치가 맞습니까?
[ ] 관련 없는 변경이 없습니까?
[ ] 스테이징된 차이와 최종 브랜치 차이를 확인했습니까?
[ ] 프로젝트 테스트와 정적 분석을 실행했습니까?
[ ] 변경 이유와 검증 결과를 적었습니까?
[ ] 의도적으로 제외한 범위를 밝혔습니까?
[ ] CI가 통과했거나 기존 실패를 구분해 설명했습니까?
[ ] 비밀값, 개인 키, 내부 URL이 없습니까?
```

확인 명령:

```bash
git fetch origin
git log --oneline origin/main..HEAD
git diff --stat origin/main...HEAD
git diff origin/main...HEAD
```

---

## 팀 정책 체크리스트

```text
[ ] 기본 브랜치
[ ] 브랜치 naming
[ ] direct 푸시 허용 여부
[ ] fork 또는 공유 저장소 방식
[ ] merge/rebase 정책
[ ] PR 승인 수와 CODEOWNERS
[ ] 필수 검사
[ ] merge 방식
[ ] 커밋 message 규칙
[ ] 강제 푸시 허용 브랜치
[ ] signed 커밋, DCO, CLA
[ ] 비밀값 및 보안 신고 절차
```

저장소 규칙을 정리할 때는 [Git 정책 점검 항목](repository-policy.md)을 참고합니다.
