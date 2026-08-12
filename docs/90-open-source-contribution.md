# 오픈소스에 작은 변경 기여하기

## 학습 목표

- fork, origin과 upstream 역할을 구분해 최신 기준에서 작은 기여를 만듭니다.
- 정책, DCO/CLA와 검증 근거를 확인해 유지보수 가능한 Pull Request를 작성합니다.

이 문서는 필수 Git 과정 이후의 선택 경로입니다. 낯선 저장소에 변경을 제안할 때 프로젝트 규칙을 조사하고, 검토하기 쉬운 범위를 선택하며, 자신의 fork와 원본 저장소를 혼동하지 않는 과정을 다룹니다.

```text
저장소 규칙 조사
→ 기여 범위 선택
→ fork와 upstream 구성
→ 기준 상태 검증
→ 작은 변경과 커밋
→ 자신의 fork에 푸시
→ 원본 저장소로 Pull Request
→ 리뷰 반영
→ 병합 또는 종료 뒤 정리
```

오픈소스 기여의 핵심은 복잡한 Git 명령이 아닙니다.

> 처음 보는 프로젝트에서 필요한 정보를 스스로 찾고, 범위 밖 변경을 만들지 않으며, 유지보수자가 검토하고 되돌리기 쉬운 제안을 만드는 능력입니다.

## 선행 개념

- remote/upstream/Pull Request 흐름과 CONTRIBUTING·license·검증 명령 읽기

## 선행조건

다음 문서를 먼저 완료합니다.

- [작업 공간과 브랜치 준비](01-workspace-basics.md)
- [변경 검토와 커밋 구성](02-commit-workflow.md)
- [원격 협업과 풀 리퀘스트](03-remote-pr-workflow.md)
- [merge·rebase와 충돌 해결](04-merge-rebase-conflicts.md)
- [Git 복구 절차](05-recovery-runbook.md)

이 글은 GitHub의 일반적인 fork 기반 흐름을 예로 사용합니다. 실제 프로젝트의 `CONTRIBUTING.md`와 저장소 정책이 이 문서보다 우선합니다.

## 수정하기 전에 읽을 것

저장소 루트와 `.github/`에서 다음 파일을 찾습니다.

```text
README.md
CONTRIBUTING.md
SECURITY.md
CODE_OF_CONDUCT.md
LICENSE 또는 LICENSE.md
이슈 템플릿
Pull Request 템플릿
```

| 문서 | 확인할 내용 |
|---|---|
| README | 프로젝트 목적, 지원 범위, 빌드와 테스트 |
| CONTRIBUTING | 개발 환경, 이슈·브랜치·커밋·PR 규칙 |
| SECURITY | 취약점의 비공개 신고 방법 |
| Code of Conduct | 커뮤니티 행동 기준 |
| LICENSE | 코드와 문서를 사용할 수 있는 조건 |
| 템플릿 | 유지보수자가 요구하는 재현·검증 정보 |

`CONTRIBUTING.md`가 없다고 임의의 대형 변경을 시작하지 않습니다. 기존 Issue, 최근 병합된 PR, CI 설정과 릴리스 정책에서 실제 관례를 확인합니다.

### 보안 문제

취약점, 개인 키, 토큰이나 다른 비밀값을 발견했다면 공개 Issue나 PR에 먼저 붙이지 않습니다. `SECURITY.md` 또는 호스팅 서비스가 제공하는 비공개 신고 절차를 사용합니다.

## 첫 기여 범위 고르기

좋은 첫 기여 후보:

- 재현 가능한 작은 버그
- 명백한 문서 오류나 깨진 링크
- 기존 동작을 고정하는 작은 테스트
- 유지보수자가 `good first issue` 등으로 표시한 작업
- 공개 API를 바꾸지 않는 국소적인 정리

사전 논의가 필요한 후보:

- 공개 API와 데이터 형식 변경
- 의존성 또는 빌드 시스템 교체
- 전체 서식·이름 변경
- 새 아키텍처나 주요 기능
- 큰 성능 최적화
- 지원 플랫폼과 호환성 정책 변경

작업을 선택하기 전에 확인합니다.

```text
같은 문제가 이미 보고되었습니까?
누군가 작업 중이라고 밝혔습니까?
유지보수자가 원하는 해결 방향이 있습니까?
PR 전에 Issue나 설계 논의를 요구합니까?
재현 가능한 실패와 완료 조건이 있습니까?
```

“내 방식이 더 좋아 보인다”는 이유만으로 프로젝트 전체 관례를 바꾸지 않습니다.

## fork와 upstream 모델

원본 저장소에 직접 푸시 권한이 없다면 일반적인 관계는 다음과 같습니다.

```text
원본 저장소
    ↑ upstream
로컬 복제
    ↓ origin
내 fork
```

```text
origin    내가 푸시할 fork
upstream  변경을 가져올 원본 저장소
```

`origin`과 `upstream`은 예약어가 아니지만, 널리 쓰이는 관례를 따르면 명령과 리뷰 설명을 이해하기 쉽습니다.

## fork, clone과 upstream 구성

GitHub에서 원본 저장소를 자신의 계정이나 기여용 조직으로 fork합니다. private 저장소는 조직 정책에 따라 fork가 제한될 수 있습니다.

자신의 fork를 복제합니다.

```bash
git clone https://github.com/YOUR_ACCOUNT/REPOSITORY.git
cd REPOSITORY
```

원본 저장소를 `upstream`으로 추가합니다.

```bash
git remote add upstream \
  https://github.com/ORIGINAL_OWNER/REPOSITORY.git
```

관계를 확인합니다.

```bash
git remote -v
git branch -vv
git status --short --branch
```

기대 구조:

```text
origin    https://github.com/YOUR_ACCOUNT/REPOSITORY.git
upstream  https://github.com/ORIGINAL_OWNER/REPOSITORY.git
```

푸시 대상과 변경을 가져올 대상을 추측하지 않습니다.

## 최신 upstream에서 작업 브랜치 만들기

원본 저장소의 최신 참조를 가져옵니다.

```bash
git fetch upstream
```

원본 기본 브랜치가 `main`인 예:

```bash
git switch --no-track \
  -c fix/documentation-link \
  upstream/main
```

검증합니다.

```bash
git status --short --branch
git branch -vv
git log -1 --oneline --decorate
```

작업 브랜치는 `upstream/main`에서 시작했지만 아직 upstream을 갖지 않습니다. 최초 푸시에서 자신의 fork에 같은 이름의 원격 브랜치를 만들고 연결합니다.

fork의 로컬 `main`을 먼저 갱신해야 작업 브랜치를 만들 수 있는 것은 아닙니다. 시작점을 `upstream/main`으로 직접 지정하면 기준이 명확합니다.

## 변경 전에 기준 상태 검증

코드를 수정하기 전에 프로젝트가 지정한 설치, 빌드, 테스트와 정적 분석 명령을 그대로 실행합니다.

기록할 내용:

```text
운영체제와 주요 도구 버전
정확히 실행한 명령
성공·실패 결과
기존 실패가 있는지
```

기준 상태가 이미 실패한다면 자신의 변경이 만든 실패와 구분해 Issue나 PR에 적습니다. 기준 실패를 임의로 고치면서 원래 작업과 한 PR에 섞지 않습니다.

## 작고 독립적인 변경 만들기

기여 브랜치에서는 다음 원칙을 사용합니다.

- 합의한 문제만 수정합니다.
- 관련 없는 formatting과 rename을 섞지 않습니다.
- 기존 코드 스타일과 테스트 구조를 따릅니다.
- 동작 변경에는 가능한 범위의 테스트를 추가합니다.
- 생성 파일은 프로젝트 절차가 요구할 때만 갱신합니다.
- 필요한 문서와 테스트를 “PR을 작게 보이게 하려고” 제외하지 않습니다.

커밋 전:

```bash
git status --short
git diff
git add -p
git diff --staged --check
git diff --staged
```

그다음 프로젝트가 지정한 검증을 실행하고 커밋합니다.

```bash
git commit
```

한 커밋을 독립적으로 리뷰하거나 되돌렸을 때 하나의 목적이 유지되는지 확인합니다.

## CLA, DCO, sign-off와 서명 구분

프로젝트가 요구할 때만 해당 절차를 따릅니다. 서로 대체할 수 있는 기능이 아닙니다.

### CLA

Contributor License Agreement입니다. 별도의 웹 서비스나 bot을 통해 동의를 요구할 수 있습니다.

### DCO와 `Signed-off-by`

Developer Certificate of Origin을 사용하는 프로젝트는 커밋에 sign-off trailer를 요구할 수 있습니다.

```bash
git commit -s
```

`-s`는 암호학적 서명이 아닙니다. 현재 커밋 작성자 정보로 DCO 취지에 동의한다는 trailer를 추가합니다.

### GPG 또는 SSH 커밋 서명

```bash
git commit -S
```

`-S`는 커밋 객체에 암호학적 서명을 추가합니다. CLA, DCO sign-off와 커밋 서명은 각각 다른 요구입니다.

## 자신의 fork에 게시하기

현재 브랜치를 자신의 fork에 최초 게시합니다.

```bash
git push -u origin HEAD
```

확인합니다.

```bash
git status --short --branch
git branch -vv
git remote -v
```

관계는 다음과 같아야 합니다.

```text
로컬 fix/documentation-link
      ↕ upstream
origin/fix/documentation-link

작업 기준 후보
upstream/main
```

원본 저장소의 `main`에 직접 푸시하려 하지 않습니다.

## 원본 저장소로 Pull Request 만들기

작성 화면에서 네 방향을 확인합니다.

```text
base 저장소: original-owner/repository
base 브랜치: main
head 저장소: your-account/repository
compare 브랜치: fix/documentation-link
```

fork와 원본 방향을 바꾸면 의도하지 않은 PR이 됩니다.

PR 본문은 diff를 다시 나열하기보다 문제, 변경 범위와 검증 근거를 설명합니다.

```markdown
## 문제

설치 문서의 링크가 이동된 페이지를 가리켜 신규 사용자가 404를 봅니다.

## 변경

- 링크를 현재 공식 페이지로 교체했습니다.
- 주변 문장과 문서 구조는 바꾸지 않았습니다.

## 검증

- 프로젝트의 문서 검사 실행
- 렌더링과 링크 대상 확인

## 범위 밖

- 설치 절차 자체의 재작성은 포함하지 않았습니다.

## 관련 이슈

Closes #123
```

`Closes #123`은 실제로 닫아야 할 Issue인지 확인합니다. 방향을 먼저 확인해야 한다면 draft PR을 사용할 수 있지만, 프로젝트가 구현 전 Issue 논의를 요구하면 해당 정책이 우선합니다.

## upstream 변경 동기화

먼저 최신 원본 참조를 가져옵니다.

```bash
git fetch upstream
```

프로젝트 정책에 따라 작업 브랜치에 merge하거나 rebase합니다.

```bash
git merge upstream/main
```

또는:

```bash
git rebase upstream/main
```

이미 fork에 게시한 커밋을 rebase했다면 이력 재작성이므로 원격 상태와 리뷰 정책을 확인합니다.

```bash
git push --force-with-lease origin HEAD
```

유지보수자가 “Update branch” 기능이나 특정 통합 방식을 요구하면 그 방식을 따릅니다.

fork의 로컬 기본 브랜치를 fast-forward로 동기화하는 예:

```bash
git fetch upstream
git switch main
git merge --ff-only upstream/main
git push origin main
```

fork의 `main`에 독립 커밋이 있다면 무조건 reset하지 말고 보존 필요성을 먼저 판단합니다.

## 리뷰 의견 반영

리뷰 의견을 다음처럼 나눕니다.

```text
명백한 결함 또는 누락
프로젝트 관례에 따른 요청
설계 선택에 대한 질문이나 대안
```

수정할 때는 일반 변경과 같은 검토 절차를 사용합니다.

```bash
git diff
git add -p
git diff --staged
```

프로젝트 검증을 실행한 뒤 새 커밋을 만들거나, 저장소 정책이 요구할 때만 이력을 정리합니다.

```bash
git commit -m "fix: address review feedback"
git push
```

요청을 그대로 적용하기 어렵다면 조용히 무시하지 않습니다. 현재 제약, 검토한 대안, 선택한 이유와 후속 작업을 설명합니다.

## 다른 사람의 PR을 로컬에서 확인할 때

GitHub CLI를 사용할 수 있다면 다음처럼 체크아웃할 수 있습니다.

```bash
gh pr checkout PR_NUMBER
```

그다음 현재 브랜치와 커밋을 확인하고 프로젝트 검증을 실행합니다.

```bash
git status --short --branch
git log --oneline --decorate -5
```

낯선 PR의 빌드·패키지·테스트 스크립트는 임의 코드를 실행할 수 있습니다. 신뢰 경계가 분리된 환경에서만 실행하고 비밀값이나 개인 작업 디렉터리를 노출하지 않습니다.

## 병합 또는 종료 뒤 정리

원본과 fork의 삭제된 원격 브랜치 정보를 정리합니다.

```bash
git fetch --prune upstream
git fetch --prune origin
```

작업 브랜치가 더 이상 필요하지 않고 보존할 독립 작업이 없다면 삭제합니다.

```bash
git switch main
git branch -d fix/documentation-link
git push origin --delete fix/documentation-link
```

squash merge 때문에 `git branch -d`가 거부될 수 있습니다. PR 병합 여부와 브랜치에 남은 독립 커밋을 확인한 뒤 삭제합니다. 계속 기여할 계획이라면 fork 자체를 삭제할 필요는 없습니다.

## 유지보수자가 신뢰하기 쉬운 기여

- 작업 전에 저장소 규칙과 기존 논의를 읽습니다.
- PR 하나에 하나의 문제를 다룹니다.
- 변경 이유와 검증 근거를 제공합니다.
- 요청하지 않은 대규모 정리를 섞지 않습니다.
- CI 실패와 리뷰 의견을 방치하지 않습니다.
- 일정을 지키기 어렵다면 작업 점유 상태를 알립니다.
- 자신의 선호보다 프로젝트의 일관성을 우선합니다.
- 작은 변경도 테스트, 문서와 정리까지 완결합니다.

## 작은 기여 연습

이 `guide-git` 저장소에서 다음과 같은 작은 후보를 찾을 수 있습니다.

```text
오탈자 한 개 수정
깨진 공식 링크 교체
불명확한 명령 전제조건 보완
검사 스크립트의 오류 메시지 개선
```

진행 순서:

```text
1. CONTRIBUTING.md를 읽습니다.
2. 기존 Issue와 PR을 검색합니다.
3. fork와 upstream을 구성합니다.
4. upstream/main에서 작은 브랜치를 만듭니다.
5. 한 가지 목적의 변경과 검증을 수행합니다.
6. 범위 밖을 명시한 PR을 만듭니다.
```

첫 기여에서 전체 문체나 디렉터리 구조를 바꾸지 않습니다.

## 연결 실습

- [선택 90 연습](../exercises/README.md#선택-90-오픈소스-기여)에서 `team-app` 하나의 공유 원격으로 작은 branch와 review update를 연습합니다. `origin` fork와 `upstream` 원본의 두 원격은 실제 hosting fork 또는 따로 준비한 two-remote sandbox에서 확인합니다.

## 완료 기준

- 원본 저장소와 자신의 fork에서 `origin`, `upstream`의 방향을 설명할 수 있습니다.
- 최신 `upstream/main`에서 작업 브랜치를 만들 수 있습니다.
- 변경 전 기준 검증 결과를 기록할 수 있습니다.
- 하나의 문제만 다루는 커밋과 PR을 만들 수 있습니다.
- CLA, DCO sign-off와 커밋 서명을 구분할 수 있습니다.
- 게시한 브랜치를 rebase할 때 필요한 보호 조건을 설명할 수 있습니다.
- 리뷰 의견을 반영한 뒤 검증 근거를 갱신할 수 있습니다.
- 병합 또는 종료 뒤 로컬 브랜치와 원격 브랜치를 안전하게 정리할 수 있습니다.

## 공식 참고 문서

- [GitHub Forks](https://docs.github.com/en/pull-requests/reference/forks)
- [fork에 원본 저장소 추가하기](https://docs.github.com/en/pull-requests/how-tos/work-with-forks/configuring-a-remote-repository-for-a-fork)
- [fork 동기화](https://docs.github.com/en/pull-requests/how-tos/work-with-forks/syncing-a-fork)
- [fork에서 Pull Request 만들기](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request-from-a-fork)
- [저장소 기여 지침 설정](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/setting-guidelines-for-repository-contributors)
- [Developer Certificate of Origin](https://developercertificate.org/)
