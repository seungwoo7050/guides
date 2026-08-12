# 작업 공간과 브랜치 준비

## 학습 목표

- 작업 트리, index, local branch와 remote-tracking branch의 상태를 구분합니다.
- 작업 전에 저장소·원격·작성자 정보와 복구 지점을 확인합니다.

이 글의 목표는 코드를 수정하기 전에 다음 상태를 만드는 것입니다.

```text
올바른 저장소
+ 올바른 커밋 작성자 정보
+ 의도한 원격 저장소
+ 최신 원격 기본 브랜치
+ 변경이 없는 작업 트리
+ 작업 전용 로컬 브랜치
```

Git 작업은 코드 수정부터 시작하지 않습니다. 저장소와 기준점을 잘못 선택하면 이후 명령을 정확히 실행해도 잘못된 곳에 올바른 작업을 쌓게 됩니다.

## 선행 개념

- 터미널의 cwd·exit status와 파일 수정/Git 기록의 차이

## 작업을 시작할 기준

이 글을 마치면 다음 질문에 명령으로 답할 수 있어야 합니다.

- 현재 어느 저장소에서 작업 중입니까?
- 이 저장소는 어느 원격 저장소와 연결되어 있습니까?
- 커밋에는 어떤 이름과 이메일이 기록됩니까?
- 현재 브랜치와 upstream은 무엇입니까?
- `origin/main`은 언제 갱신되었습니까?
- 작업 브랜치는 어느 커밋에서 시작했습니까?
- 지금 코드를 수정해도 됩니까?

---

## 시작 전에 팀에 확인할 것

Git은 여러 작업 방식을 허용합니다. 다음은 도구의 기능이 아니라 저장소의 정책입니다.

```text
[ ] 저장소 URL과 호스트
[ ] 기본 브랜치 이름
[ ] 조직 저장소에 직접 푸시하는지, fork를 사용하는지
[ ] 브랜치 이름 규칙
[ ] 회사 이메일 또는 noreply 이메일 사용 여부
[ ] HTTPS, SSH, SSO 등 인증 방식
[ ] 작업 브랜치에 강제 푸시가 허용되는지
```

본문에서는 다음 예시를 사용합니다.

```text
원격 저장소:       origin
기본 브랜치: main
작업 브랜치: feature/title-validation
```

실제 저장소에서는 팀 규칙으로 바꿉니다.

---

## 상태를 읽는 기준

### 로컬 저장소와 원격 저장소

로컬 저장소는 현재 컴퓨터에 있는 Git 저장소입니다. 원격 저장소는 `fetch`하거나 푸시할 다른 저장소의 별칭과 URL 입니다.

```text
로컬 저장소
  └── origin → https://github.com/example/sample-app.git
```

`origin`은 GitHub를 뜻하는 예약어가 아니라 복제한 출처에 기본적으로 붙는 관례적인 이름입니다.

### 로컬 브랜치와 원격 추적 브랜치

```text
main          현재 컴퓨터의 로컬 브랜치
origin/main   마지막 fetch에서 확인한 원격 main의 로컬 기록
```

`origin/main`은 서버 상태를 실시간으로 조회하는 이름이 아닙니다. 다른 사람이 원격 `main`을 갱신해도 내가 원격 정보를 갱신하기 전까지 로컬 `origin/main`은 그대로입니다.

### HEAD

HEAD는 현재 작업 기준을 가리킵니다.

```text
HEAD → feature/title-validation → 커밋 C
```

새 커밋을 만들면 현재 브랜치가 앞으로 이동합니다.

### 작성자 정보와 인증 계정

둘은 서로 다릅니다.

```text
커밋 작성자 정보
  git config user.name / user.email
  → 커밋 안에 기록되는 작성자 정보

인증 계정
  HTTPS 인증 정보 또는 SSH 키
  → 원격 저장소 접근 권한을 증명하는 계정
```

인증에 성공했다고 커밋 작성자 정보가 올바른 것은 아닙니다.

---

## 로컬 실습 준비

실제 저장소로 진행해도 되지만, 처음에는 제공된 로컬 실습 환경이 안전합니다.

저장소 루트에서 실행합니다.

```bash
./exercises/setup.sh sample
cd exercises/workspace/sample-app
```

이미 실습 환경이 있다면 기존 작업을 보존할지 먼저 판단합니다. 처음 상태로 다시 만들 때만 다음 명령을 사용합니다.

```bash
./exercises/setup.sh --reset sample
cd exercises/workspace/sample-app
```

`--reset sample`은 `sample-app` 실습 저장소와 해당 bare 원격 저장소만 삭제하고 다시 만듭니다.

---

## Git과 작성자 정보 확인

### Git 설치 `[확인]`

```bash
git --version
```

Git을 찾을 수 없다면 회사나 개발 환경이 지정한 방식으로 설치합니다.

### 작성자 정보 `[확인]`

```bash
git config --show-origin --get user.name
git config --show-origin --get user.email
```

`--show-origin`은 값과 함께 어느 설정 파일에서 읽었는지 보여 줍니다.

실제 저장소에서 값이 없거나 잘못되었다면 팀 정책에 맞게 저장소별로 설정할 수 있습니다.

```bash
git config --local user.name "Seungwoo Kim"
git config --local user.email "seungwoo7050@naver.com"
```

개인·회사 작성자 정보를 함께 사용하는 컴퓨터에서는 로컬 설정이 전역 설정을 잘못 상속하는 문제를 줄여 줍니다.

실습 환경은 사용자의 전역 설정을 바꾸지 않고 각 복제에 테스트용 로컬 작성자 정보를 설정합니다.

---

## 저장소와 원격 저장소 검증

다음 명령을 순서대로 실행합니다.

```bash
git rev-parse --show-toplevel
git remote -v
git status --short --branch
git branch --show-current
git branch -vv
git log -1 --oneline --decorate
```

### 저장소 루트 `[확인]`

```bash
git rev-parse --show-toplevel
```

현재 디렉터리가 속한 작업 트리의 최상위 경로를 보여 줍니다. 여러 복제나 터미널을 동시에 사용할 때 디렉터리 이름만 믿지 않습니다.

### 원격 저장소 URL `[확인]`

```bash
git remote -v
```

확인할 내용:

- 저장소 소유자와 이름
- 회사 Git 호스트인지 공개 GitHub인지
- HTTPS 또는 SSH가 팀 안내와 일치하는지
- fetch와 푸시 URL이 의도한 값인지

URL이 틀렸다면 팀 문서로 정답을 확인한 뒤 수정합니다.

```bash
git remote set-url origin CORRECT_URL
```

### 현재 상태 `[확인]`

```bash
git status --short --branch
```

변경이 없는 상태의 예:

```text
## main...origin/main
```

변경이 있는 예:

```text
## main...origin/main
 M config/app.yml
?? .env.로컬
```

새 작업을 시작하기 전에 예상하지 못한 변경의 소유권을 확인합니다. 바로 `restore`, `clean`, 커밋을 실행하지 않습니다.

### 브랜치와 upstream `[확인]`

```bash
git branch -vv
```

예:

```text
* main <COMMIT> [origin/main] chore: 실습 fixture 구성
```

- `*`: 현재 브랜치
- `<COMMIT>`: 브랜치가 가리키는 축약 커밋 해시이며 fixture를 만들 때마다 달라질 수 있음
- `[origin/main]`: upstream

---

## fetch 전에 결과를 예상하기

다음 질문에 먼저 답합니다.

```text
Q1. `git fetch origin`은 현재 브랜치를 이동시킵니까?
Q2. 작업 트리의 파일을 원격 버전으로 덮어씁니까?
Q3. origin/main은 갱신될 수 있습니까?
```

정답:

```text
A1. 이동시키지 않습니다.
A2. 덮어쓰지 않습니다.
A3. 원격 main이 바뀌었다면 갱신됩니다.
```

이제 실행합니다.

```bash
git fetch origin
```

실행 뒤 확인합니다.

```bash
git status --short --branch
git log -1 --oneline --decorate origin/main
git branch -vv
```

`fetch`는 원격의 객체와 refs를 가져와 원격 추적 브랜치를 갱신합니다. 현재 로컬 브랜치와 작업 트리를 자동으로 통합하지 않습니다.

---

## 최신 원격 기준에서 작업 브랜치 만들기

작업 브랜치를 원격 기본 브랜치의 최신 커밋에서 직접 만듭니다.

```bash
git switch --no-track -c feature/title-validation origin/main
```

명령의 의미:

```text
git switch
  --no-track                         origin/main을 upstream으로 자동 등록하지 않음
  -c feature/title-validation       새 로컬 브랜치 생성
  origin/main                       시작 커밋
```

작업 브랜치의 올바른 원격 counterpart는 나중에 최초 푸시로 만드는 같은 이름의 브랜치입니다.

```text
로컬:   feature/title-validation
원격 저장소:  origin/feature/title-validation
```

따라서 시작점인 `origin/main`을 작업 브랜치의 upstream으로 두지 않습니다.

### 결과를 예상하기

실행 직후 예상 상태:

```text
HEAD → feature/title-validation
feature/title-validation과 origin/main은 같은 커밋을 가리킴
작업 브랜치의 upstream은 아직 없음
작업 트리에 변경 없음
```

검증합니다.

```bash
git branch --show-current
git status --short --branch
git branch -vv
git log -1 --oneline --decorate
```

예:

```text
## feature/title-validation
```

```text
<COMMIT> (HEAD -> feature/title-validation, origin/main, origin/HEAD) chore: 실습 fixture 구성
```

이 상태에서 코드를 수정합니다.

---

## 통제된 실패: 같은 브랜치를 다시 만들기

같은 명령을 다시 실행합니다.

```bash
git switch -c feature/title-validation origin/main
```

Git은 기존 브랜치를 덮어쓰지 않고 실패해야 합니다.

```text
fatal: a 브랜치 named 'feature/title-validation' already exists
```

이 실패는 안전장치입니다. 다음 명령으로 기존 브랜치를 조사합니다.

```bash
git branch -vv
git log --oneline --decorate -5 feature/title-validation
```

기존 작업 브랜치가 맞다면 이동만 합니다.

```bash
git switch feature/title-validation
```

다음 명령은 기존 브랜치를 새 시작점으로 강제 재설정할 수 있으므로 조사 없이 사용하지 않습니다.

```bash
git switch -C feature/title-validation origin/main
```

---

## 자주 막히는 상황

### `fatal: not a git repository`

현재 디렉터리가 저장소 밖에 있습니다.

```bash
pwd
ls
git rev-parse --show-toplevel
```

올바른 복제본으로 이동합니다. 오류 해결을 위해 반복해서 다시 복제하지 않습니다.

### 복제 직후 변경 파일이 보임

```bash
git status
git diff
```

가능한 원인은 IDE 생성 파일, 줄 끝 형식, 실행 권한, 초기화 스크립트입니다. 원인을 확인하기 전에 `git restore .` 또는 `git clean -fd`를 실행하지 않습니다.

### 현재 브랜치 이름이 비어 있음

```bash
git branch --show-current
git status
```

detached HEAD일 수 있습니다. 아직 커밋하지 않았다면 최신 기본 브랜치에서 작업 브랜치를 만듭니다. detached HEAD에서 이미 커밋했다면 [복구 절차](05-recovery-runbook.md#detached-head에서-만든-커밋-보존)을 먼저 봅니다.

### 인증 오류

원격 저장소 URL 방식과 인증 경로를 함께 확인합니다.

```bash
git remote -v
```

- HTTPS URL은 HTTPS 인증 정보를 사용합니다.
- SSH URL은 SSH key를 사용합니다.
- 권한이나 조직 SSO가 없으면 인증 명령을 반복해도 해결되지 않습니다.

토큰이나 개인 키를 화면 공유, 문서, 채팅에 붙여 넣지 않습니다.

---

## 실제 업무의 표준 시작 절차

```bash
# 저장소와 원격 저장소
git rev-parse --show-toplevel
git remote -v

# identity
git config --show-origin --get user.name
git config --show-origin --get user.email

# 현재 상태
git status --short --branch
git branch -vv

# 원격 기준점 갱신
git fetch origin

# 최신 원격 기본 브랜치에서 작업 브랜치 생성
git switch --no-track -c feature/TOPIC origin/main

# 결과 검증
git branch --show-current
git status --short --branch
git log -1 --oneline --decorate
```

기본 브랜치가 `develop`이나 `trunk`라면 `origin/main`을 실제 이름으로 바꿉니다.

---

## 변형 실습

### A. 로컬 main이 뒤처진 상태

다음 두 시작 방식의 차이를 설명합니다.

```bash
git switch -c feature/example
```

```bash
git switch --no-track -c feature/example origin/main
```

첫 번째는 현재 HEAD, 두 번째는 명시한 원격 기준점에서 시작합니다.

### B. fork 작업 흐름

외부 프로젝트에서는 다음 구조가 일반적입니다.

```text
origin    → 내 fork
upstream  → 원본 저장소
```

이 경우 작업 브랜치는 `upstream/main`에서 시작할 수 있습니다. 자세한 절차는 [오픈 소스 기여 선택 경로](90-open-source-contribution.md)에서 다룹니다.

### C. 작업 트리에 변경이 남아 있음

새 작업을 시작하기 전에 변경이 다음 중 무엇인지 분류합니다.

```text
기존 작업의 일부
일시적인 로컬 설정
자동 생성 파일
버려도 되는 실험
소유권을 모르는 변경
```

분류하지 못한 변경은 삭제하거나 새 커밋에 섞지 않습니다.

---

## 공식 참고 문서

- [`git status`](https://git-scm.com/docs/git-status)
- [git-switch](https://git-scm.com/docs/git-switch)
- [git-fetch](https://git-scm.com/docs/git-fetch)
- [git-config](https://git-scm.com/docs/git-config)

## 연결 실습

- [로컬 Git 연습 환경의 1단계](../exercises/README.md#1단계-작업-공간과-브랜치)에서 `sample`을 만들고 `status`, `branch -vv`, `remote -v` 결과를 예측한 뒤 기대 증거와 비교합니다.

## 완료 기준

- 현재 상태와 다음 명령의 영향을 근거와 함께 설명할 수 있습니다.
- 문서의 절차를 격리된 로컬 저장소에서 재현하고 결과를 확인할 수 있습니다.
- 실패했을 때 작업을 보존하는 복구 경로를 선택할 수 있습니다.
