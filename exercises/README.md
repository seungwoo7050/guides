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
```

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

```bash
./setup.sh all
../scripts/validate.sh
```
