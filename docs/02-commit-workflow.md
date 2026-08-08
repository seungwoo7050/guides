# 변경 검토와 커밋 구성

## 학습 목표

- working tree와 index에서 목적별 변경 조각을 선택해 검증 가능한 커밋으로 만듭니다.
- 잘못 stage한 변경을 작업 내용 손실 없이 되돌리고 다시 분리합니다.

수정한 파일을 그대로 묶어 저장하기 전에 변경 목적을 구분하고, 다음 커밋의 내용을 정확히 확인해야 합니다. 이 글은 변경을 나누고 검토해 커밋하는 흐름을 다룹니다.

```text
여러 변경을 읽습니다
→ 목적이 같은 변경끼리 묶는다
→ 다음 커밋에 들어갈 내용을 정확히 확인합니다
→ 테스트합니다
→ 리뷰 가능한 커밋을 만듭니다
```

1편을 완료했다면 현재 브랜치는 `feature/title-validation`이고 작업 트리에는 변경이 없습니다.

독립적으로 시작하려면:

저장소 루트에서 실행합니다.

```bash
./exercises/setup.sh --reset sample
cd exercises/workspace/sample-app
git fetch origin
git switch --no-track -c feature/title-validation origin/main
```

---

## 선행 개념

- [작업 공간과 상태](01-workspace-basics.md)의 working tree/index 구분과 변경 전후 테스트

## 이번 실습

한 작업 디렉터리에 다음 변경을 의도적으로 섞습니다.

```text
A. 제목 검증 기능 구현
B. 기능 테스트 추가
C. README의 제목 정책 갱신
D. README의 무관한 오탈자 수정
E. 개인 디버그 메모 생성
```

최종 커밋은 다음처럼 나눕니다.

```text
커밋 1: 제목 검증 기능 + 테스트 + 관련 문서
커밋 2: README 오탈자 수정
제외:     개인 디버그 메모
```

파일 수가 아니라 **변경 목적**으로 커밋을 나누는 것이 핵심입니다.

---

## 최소 상태 모델

Git에서 일상적으로 구분해야 할 영역은 세 개입니다.

```text
작업 트리   현재 파일 내용
인덱스          다음 커밋으로 준비한 스냅샷
HEAD           현재 브랜치의 마지막 커밋
```

흐름:

```text
파일 수정
  ↓
작업 트리
  ↓ git add
인덱스
  ↓ git 커밋
새 커밋, HEAD 이동
```

### 비교 명령

```bash
git diff             # Working Tree ↔ Index
git diff --staged    # Index ↔ HEAD
git diff HEAD        # Working Tree 전체 상태 ↔ HEAD
```

`git diff`가 비어 있어도 스테이징된 변경이 있을 수 있습니다. 다음 커밋의 실제 내용은 `git diff --staged`로 확인합니다.

### `git status --short`의 두 칸

예:

```text
MM README.md
 M src/validate_title.sh
?? notes/debug.txt
```

일반적인 상황에서 첫 번째 칸은 인덱스, 두 번째 칸은 작업 트리 상태입니다.

```text
M  파일   스테이징된 수정
 M 파일   스테이징되지 않은 수정
MM 파일   스테이징한 뒤 같은 파일을 다시 수정
?? 파일   미추적 파일
```

모든 코드를 외우기보다 `git status`의 긴 출력과 `diff`로 확인합니다.

---

## 실습 변경 만들기

### 제목 검증 구현

`src/validate_title.sh`를 다음 내용으로 바꿉니다.

```sh
#!/usr/bin/env sh

is_valid_title()
{
    [ "$#" -eq 1 ] || return 1

    title=$1
    length=${#title}

    [ "$length" -ge 3 ] && [ "$length" -le 60 ]
}
```

### 테스트 추가

`tests/test_validate_title.sh`를 다음 내용으로 바꿉니다.

```sh
#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
. "$ROOT/src/validate_title.sh"

expect_valid()
{
    if ! is_valid_title "$1"; then
        echo "유효한 제목으로 예상했지만 거부되었습니다: $1" >&2
        exit 1
    fi
}

expect_invalid()
{
    if is_valid_title "$1"; then
        echo "유효하지 않은 제목으로 예상했지만 허용되었습니다: $1" >&2
        exit 1
    fi
}

expect_valid "로그인 리디렉션 수정"
expect_invalid ""
expect_invalid "ab"
expect_invalid "1234567890123456789012345678901234567890123456789012345678901"

printf '%s\n' "제목 유효성 검사: 통과"
```

실행 권한이 유지되는지 확인합니다.

```bash
ls -l src/validate_title.sh tests/test_validate_title.sh
```

### README에 관련 변경과 무관한 변경을 함께 만듭니다

`README.md`에서 두 곳을 수정합니다.

관련 변경:

```diff
- 현재 예제는 비어 있지 않은 모든 제목을 허용합니다.
+ 제목은 3자 이상 60자 이하여야 합니다.
```

무관한 오탈자 수정:

```diff
- 외부 의존썽이 없습니다.
+ 외부 의존성이 없습니다.
```

### 개인 메모 만들기

```bash
mkdir -p notes
printf '%s\n' '유니코드 경계 사례를 추가로 확인' > notes/debug.txt
```

---

## 실행 전에 상태를 예상하기

다음 질문에 답한 뒤 확인합니다.

```text
Q1. 수정된 추적 파일은 몇 개입니까?
Q2. 미추적 파일은 무엇입니까?
Q3. 아직 인덱스에 들어간 변경이 있습니까?
Q4. git diff --staged는 무엇을 보여 줍니까?
```

예상:

```text
추적 수정: src/validate_title.sh, tests/test_validate_title.sh, README.md
미추적:     notes/debug.txt
스테이징된 변경: 없음
스테이징된 diff:   비어 있음
```

확인합니다.

```bash
git status --short
git diff --stat
git diff
git diff --staged
```

미추적 파일의 내용은 일반 `git diff`에 나타나지 않습니다. `status`로 존재를 확인하고 직접 열어 봅니다.

---

## 커밋 단위를 먼저 결정하기

스테이징하기 전에 각 변경을 한 문장으로 설명합니다.

### 첫 번째 커밋

```text
3~60자 제목만 허용하도록 검증 규칙을 추가합니다.
```

포함:

- `src/validate_title.sh`
- `tests/test_validate_title.sh`
- README의 제목 정책 변경

### 두 번째 커밋

```text
README의 의존성 오탈자를 수정합니다.
```

포함:

- README의 오탈자 변경 조각

### 제외

```text
notes/debug.txt는 개인 메모이며 공유할 필요가 없습니다.
```

다음 질문에 답할 수 없다면 스테이징하지 않습니다.

> 이 커밋을 독립적으로 리뷰하거나 되돌려도 하나의 목적이 유지됩니까?

---

## 첫 번째 커밋을 스테이징하기

파일 전체가 첫 번째 목적에 해당하는 두 파일부터 스테이징합니다.

```bash
git add src/validate_title.sh tests/test_validate_title.sh
```

README에는 두 목적이 섞여 있으므로 변경 조각을 대화형으로 고르는 방식을 사용합니다.

```bash
git add -p README.md
```

각 변경 조각에서 최소한 다음 입력만 알면 됩니다.

```text
y  이 변경 조각을 스테이징
n  스테이징하지 않음
s  가능한 경우 더 작은 변경 조각로 분리
q  종료
?  도움말
```

제목 정책 변경 조각에는 `y`, 오탈자 변경 조각에는 `n`을 선택합니다.

### 결과를 예상하기

```text
인덱스:
  제목 검증 구현
  테스트
  README 제목 정책

작업 트리에 남음:
  README 오탈자
  notes/debug.txt
```

확인합니다.

```bash
git status --short
git diff --staged
git diff
```

README는 첫 번째 칸과 두 번째 칸이 모두 `M`일 수 있습니다.

```text
MM README.md
```

이는 같은 파일의 일부는 인덱스에 있고 다른 일부는 작업 트리에 남아 있다는 뜻입니다.

---

## 잘못 스테이징했을 때

파일 수정은 유지하고 인덱스에서만 내립니다.

```bash
git restore --staged path/to/file
```

예:

```bash
git restore --staged README.md
```

그 뒤 다시 선택합니다.

```bash
git add -p README.md
```

`git restore README.md`는 작업 트리의 수정 자체를 버릴 수 있습니다. `--staged` 유무를 혼동하지 않습니다.

### 통제된 실패: 전부 스테이징했다가 되돌리기

현재 인덱스 상태를 확인한 뒤 다음 실험을 해도 됩니다.

```bash
git add -A
git status --short
git diff --staged --stat
```

의도하지 않은 메모까지 들어갔음을 확인한 뒤 스테이징만 모두 취소합니다.

```bash
git restore --staged .
```

작업 트리의 수정은 남아 있어야 합니다.

```bash
git status --short
git diff
```

그 뒤 6절의 방식으로 다시 스테이징합니다. 이 실험은 `git add .`가 잘못된 명령이라는 뜻이 아닙니다. **검토 없이 포괄적으로 스테이징하는 습관**이 문제입니다.

---

## 다음 커밋의 정확한 내용 검토

다음 세 가지를 모두 확인합니다.

```bash
git status --short
git diff --staged --check
git diff --staged
```

- `status`: 포함·제외 상태
- `--check`: 줄 끝 공백 등 기본적인 공백 오류
- 스테이징된 차이: 커밋될 정확한 변경

다음 질문에 답합니다.

```text
[ ] 기능과 테스트가 함께 들어 있습니까?
[ ] README의 관련 변경만 들어 있습니까?
[ ] 오탈자 수정과 개인 메모는 제외되었습니까?
[ ] 예상하지 못한 파일 삭제나 권한 변경이 없습니까?
```

`git commit`은 특별한 옵션을 사용하지 않는 한 인덱스의 내용을 기록합니다.

---

## 테스트하고 첫 번째 커밋 만들기

```bash
./scripts/test.sh
```

성공한 뒤 커밋합니다.

```bash
git commit -m "feat: validate task title length"
```

`feat:` 형식은 Conventional Commits를 사용하는 저장소의 예입니다. Git 자체는 이 형식을 요구하지 않습니다. 팀 규칙이 없다면 다음처럼 명확한 명령형 제목도 충분합니다.

```text
Validate task title length
```

좋은 커밋 메시지는 작업 과정이 아니라 결과와 의도를 설명합니다.

피할 메시지:

```text
update files
work in progress
fix stuff
```

검증합니다.

```bash
git show --stat --oneline HEAD
git show --format=fuller --no-ext-diff HEAD
git status --short
```

첫 번째 커밋 뒤에는 README 오탈자와 개인 메모만 남아 있어야 합니다.

---

## 두 번째 커밋 만들기

남은 추적 변경을 확인합니다.

```bash
git diff README.md
```

오탈자 수정만 있다면 스테이징하고 검토합니다.

```bash
git add README.md
git diff --staged
```

커밋합니다.

```bash
git commit -m "docs: fix dependency spelling"
```

최근 이력을 확인합니다.

```bash
git log --oneline --decorate -3
git status --short
```

개인 메모는 여전히 미추적 상태여야 합니다.

---

## 개인 파일과 ignore

### 모든 개발자가 무시해야 하는 파일

빌드 산출물, 공통 IDE 파일처럼 저장소 전체에 적용할 규칙은 `.gitignore`에 기록하고 커밋합니다.

```gitignore
build/
.env.local
```

### 나만 무시할 파일

개인 메모처럼 팀에 공유할 필요가 없는 규칙은 `.git/info/exclude`에 둘 수 있습니다.

```bash
printf '%s\n' 'notes/' >> .git/info/exclude
git status --short
```

`.git/info/exclude`는 현재 복제에만 적용되며 커밋되지 않습니다.

### 이미 추적 중인 파일

`.gitignore`는 이미 추적 중인 파일을 자동으로 untrack하지 않습니다. 팀이 실제로 추적을 중단하기로 합의했다면 별도의 변경이 필요합니다.

---

## 마지막 로컬 커밋 수정

마지막 커밋에 작은 누락을 발견했고 아직 푸시하지 않았다면 amend할 수 있습니다.

```bash
# 파일 수정
git add path/to/file
git diff --staged
git commit --amend --no-edit
```

메시지도 바꿀 때:

```bash
git commit --amend
```

amend는 기존 커밋을 수정하는 것이 아니라 새 커밋으로 교체합니다. 따라서 해시가 바뀝니다.

```bash
git log -1 --oneline --decorate
```

이미 게시된 커밋을 amend하면 원격 브랜치를 갱신하기 위해 이력 재작성이 필요합니다. 팀 정책과 4편의 `--force-with-lease` 절차를 확인하기 전에는 수행하지 않습니다.

---

## 표준 커밋 절차

```bash
# 상태와 변경 읽기
git status --short --branch
git diff

# 목적에 맞는 변경 선택
git add path/to/file
git add -p path/to/file

# 다음 커밋 검토
git diff --staged --check
git diff --staged

# 프로젝트가 지정한 검증 실행
./scripts/test.sh

# 커밋
git commit

# 결과 확인
git show --stat --oneline HEAD
git status --short
```

---

## 변형 실습

### A. 한 파일에 두 기능이 섞인 경우

`git add -p`의 `s`로 변경 조각을 나눠 봅니다. 자동 분할이 불가능하면 변경을 직접 더 작게 편집하거나 패치 편집 명령인 `e`를 사용할 수 있습니다. 처음에는 변경을 파일에서 직접 분리하는 편이 실수를 줄입니다.

### B. 파일 전체 삭제가 포함된 경우

다음 커밋에 삭제가 의도된 것인지 확인합니다.

```bash
git status --short
git diff --staged --stat
git diff --staged -- path/to/file
```

### C. 마지막 커밋을 두 개로 나누기

이 작업은 [복구 절차의 “마지막 로컬 커밋을 다시 나누기”](05-recovery-runbook.md#마지막-로컬-커밋을-다시-나누기)에서 다룹니다.

---

## 공식 참고 문서

- [`git status`](https://git-scm.com/docs/git-status)
- [git-diff](https://git-scm.com/docs/git-diff)
- [git-add](https://git-scm.com/docs/git-add)
- [git-restore](https://git-scm.com/docs/git-restore)
- [`git commit`](https://git-scm.com/docs/git-commit)
- [gitignore](https://git-scm.com/docs/gitignore)
- [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/)

## 연결 실습

- [sample-app 실습](../exercises/README.md)에서 코드·문서·개인 메모를 두 목적별 커밋과 미추적 파일로 분리합니다.

## 완료 기준

- 현재 상태와 다음 명령의 영향을 근거와 함께 설명할 수 있습니다.
- 문서의 절차를 격리된 로컬 저장소에서 재현하고 결과를 확인할 수 있습니다.
- 실패했을 때 작업을 보존하는 복구 경로를 선택할 수 있습니다.
