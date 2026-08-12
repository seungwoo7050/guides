# Git 가이드

Git은 파일의 현재 모습만 저장하는 도구가 아니라, 프로젝트에서 일어난 변경을 검토 가능한 단위로 기록하고 여러 작업 흐름을 안전하게 합치는 도구입니다. 이 가이드는 명령을 나열하는 대신 다음 작업을 독립적으로 수행하는 데 필요한 상태 모델과 확인 절차를 다룹니다.

```text
올바른 저장소와 기준점 확인
→ 변경 목적 분리
→ 다음 커밋 검토
→ 원격 브랜치 게시
→ 리뷰 가능한 변경 제안
→ merge·rebase와 충돌 처리
→ 손실을 줄이는 복구
```

전체 범위와 권장 경로는 [Git 가이드 학습 지도](docs/00-roadmap.md)에서 먼저 확인합니다.

## 이 가이드를 마친 뒤 할 수 있어야 하는 일

- 현재 저장소, 브랜치, upstream과 원격 기준점을 명령으로 확인합니다.
- 작업 트리, 인덱스와 `HEAD`의 차이를 읽고 한 목적의 커밋을 만듭니다.
- 작업 브랜치를 원격에 게시하고 Pull Request의 base와 head를 구분합니다.
- merge와 rebase가 그래프에 미치는 차이를 설명하고 충돌을 해결하거나 중단합니다.
- 변경이 공유되었는지에 따라 `restore`, `reset`, `revert`, `reflog`를 구분합니다.
- 위험한 명령 전에 영향 범위와 복구 지점을 확인합니다.

## 학습 순서와 실습 지도

문서를 모두 읽은 뒤 실습을 한번에 시작하지 않습니다. 각 행의 문서를 읽고 연결된 상태 전이를 직접 수행한 뒤, 기대 증거를 확인하고 다음 행으로 이동합니다.

| 순서 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 뒤 비교·다음 |
|---:|---|---|---|---|---|---|
| 0 | [Git 가이드 학습 지도](docs/00-roadmap.md) | — | 지원 환경과 완료 조건 확인 | — | `git --version`, `python3 --version` | 준비 조건 확인 → [1편](docs/01-workspace-basics.md) |
| 1 | [작업 공간과 브랜치 준비](docs/01-workspace-basics.md) | — | [`sample` 1단계](exercises/README.md#1단계-작업-공간과-브랜치) | `exercises/workspace/sample-app` 내 Git 상태 | 저장소 root에서 `cd exercises/workspace/sample-app && ./scripts/test.sh`, 이후 상태 명령 | 1단계 기대 증거 확인 → [2편](docs/02-commit-workflow.md) |
| 2 | [변경 검토와 커밋 구성](docs/02-commit-workflow.md) | — | [`sample` 2단계](exercises/README.md#2단계-변경-검토와-커밋) | `exercises/workspace/sample-app` 소스·테스트·README·index | `sample-app`에서 `./scripts/test.sh`, `git diff --staged --check`, `git log origin/main..HEAD` | 2단계 기대 증거 확인 → [3편](docs/03-remote-pr-workflow.md) |
| 3 | [원격 협업과 풀 리퀘스트](docs/03-remote-pr-workflow.md) | — | [`team` 3단계](exercises/README.md#3단계-원격-협업) | `exercises/workspace/team-app-dev-a`, `team-app-dev-b`, `team-app-maintainer` | 각 `team-app-*`에서 `./scripts/check.sh`, `git branch -vv`, `git log --all --graph` | 3단계 기대 증거 확인 → [4편](docs/04-merge-rebase-conflicts.md) |
| 4 | [merge·rebase와 충돌 해결](docs/04-merge-rebase-conflicts.md) | — | [`team` 4단계](exercises/README.md#4단계-충돌-해결) | `exercises/workspace/team-app-*` 내 충돌 파일·index·refs | 작업 중인 `team-app-*`에서 `./scripts/check.sh`, `git status`, `git log --all --graph` | 4단계 기대 증거 확인 → [5편](docs/05-recovery-runbook.md) |
| 5 | [Git 복구 절차](docs/05-recovery-runbook.md) | — | [버려도 되는 5단계 복구 sandbox](exercises/README.md#5단계-복구-증거) | `exercises/workspace/recovery-lab.*`의 working tree·index·refs·stash·reflog | 생성된 `recovery-lab.*`에서 `git status`, `git log --all --graph`, `git reflog`, `git show` | 5단계 기대 증거 확인 → 필수 과정 종료 |
| 선택 90 | [오픈소스에 작은 변경 기여하기](docs/90-open-source-contribution.md) | — | [공유 원격 연습과 실제 fork 확인](exercises/README.md#선택-90-오픈소스-기여) | `exercises/workspace/team-app-*` 또는 실제 fork 작업 브랜치 | 프로젝트 검사, `git remote -v`, PR 변경·검증 기록 | 선택 기대 증거 및 저장소 정책 확인 → 가이드 종료 |

이 브랜치에는 독립 `examples/`가 없습니다. `setup.sh`가 만드는 작은 애플리케이션은 Git 상태 전이를 위한 **실습 fixture**이지 완성 구현 예제가 아닙니다. 따라서 소스 답안 대신 `status`, `diff`, graph, ref와 명령 종료 상태를 [단계별 기대 증거](exercises/README.md#단계별-실습과-기대-증거)와 비교합니다.

root-level `reference/`는 exercise 답안이 아닙니다. 자신의 상태 증거를 먼저 확인한 뒤, 명령을 빠르게 찾을 때는 [상황별 빠른 참조](reference/quick-reference.md)를, 브랜치·검증·병합 정책을 점검할 때는 [저장소 정책 점검 항목](reference/repository-policy.md)을 사용합니다.

## 로컬 실습 환경

[로컬 Git 연습 환경](exercises/README.md)은 GitHub 계정이나 네트워크 없이도 clone, fetch, push, 원격 추적 브랜치, 충돌, rebase와 `reflog`를 재현합니다. 실제 작업 저장소에서 위험한 복구 명령을 시험하지 않아도 됩니다.

저장소 루트에서 필요한 환경만 생성합니다.

```bash
./exercises/setup.sh sample
./exercises/setup.sh team
```

기존 실습을 다시 만들 때는 삭제될 범위를 확인한 뒤 필요한 환경만 초기화합니다.

```bash
./exercises/setup.sh --reset sample
./exercises/setup.sh --reset team
```

`sample`은 1·2편과 개인 작업 복구에 사용하고, `team`은 3·4편의 원격 협업과 충돌 재현에 사용합니다. 실습 작업은 `exercises/workspace/`에 생성되며 Git이 추적하지 않습니다.

## 저장소 준비와 전체 검사

overlay를 적용한 직후에는 저장소 루트에서 다음 순서로 실행합니다.

```bash
./prepare.sh
./verify.sh
```

`prepare.sh`는 source tree와 Git index를 변경하지 않고 최종 구조, 도구와 fingerprint를 확인해 `.guide/git/prepared.json`을 기록합니다. 학습자의 `exercises/workspace/`는 삭제하지 않습니다.

`verify.sh`는 준비가 끝난 최종 파일 구조, 문서 링크, 셸 문법과 전체 격리 Git 시나리오를 한 번에 검사합니다. `verify.sh`는 `prepare.sh`를 대신 실행하지 않으므로 준비되지 않은 구조가 남아 있으면 실패합니다.

## 일상 작업에서 먼저 확인할 상태

명령을 실행하기 전에는 현재 위치와 변경 상태부터 확인합니다.

```bash
git rev-parse --show-toplevel
git status --short --branch
git branch -vv
git remote -v
```

커밋하기 전에는 작업 트리와 인덱스를 따로 읽습니다.

```bash
git diff
git diff --staged
git diff --staged --check
```

원격 변경을 합치거나 문제를 복구할 때는 그래프와 최근 참조 이동을 함께 확인합니다.

```bash
git fetch origin
git log --oneline --decorate --graph --all -12
git reflog -10
```

공유 브랜치의 이력을 다시 쓰거나 파일을 지우는 명령을 실행하기 전에는 저장소 정책, 영향 범위와 복구 지점을 먼저 확인합니다.
