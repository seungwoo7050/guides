# 다중 저장소 릴리스 명세

## 목표

여러 저장소의 현재 작업 디렉터리가 아니라 **검증된 태그·커밋 조합**을 하나의 릴리스 입력으로 고정합니다.

## 입력 형식

검사기는 다음 JSON을 받습니다.

```json
{
  "repositories": [
    {
      "name": "contracts",
      "path": "/absolute/path/to/contracts",
      "remote": "https://github.com/example/contracts.git",
      "tag": "v1.4.0",
      "commit": "40-character-commit-sha"
    }
  ]
}
```

각 항목은 다음 조건을 만족해야 합니다.

- 저장소 이름과 실제 경로는 명세 안에서 각각 한 번만 나타납니다.
- `origin` 원격 URL이 명세의 remote와 같습니다.
- 작업 디렉터리는 추적 파일과 미추적 파일 모두 깨끗합니다.
- 현재 HEAD는 브랜치가 아닌 detached HEAD입니다.
- 현재 HEAD가 명세의 commit과 같습니다.
- tag는 lightweight tag가 아니라 annotated tag입니다.
- tag를 peel한 commit이 명세의 commit과 같습니다.

## 실패 조건

skeleton은 JSON 필드와 현재 commit만 확인합니다. 중복된 저장소, 잘못된 원격 URL, 변경 파일, 브랜치 checkout과 lightweight tag도 통과시키므로 재현 가능한 릴리스 입력을 보장하지 못합니다.

## 작업

안전한 workspace를 만든 뒤 `.workspace/release-manifest/manifest_check.py`에 입력 계약과 Git 상태 검증을 구현합니다. reference는 완료 검증과 자기 설명 뒤 비교할 정본입니다.

## 권장 구현 순서

아래 번호는 실제 과거 작성 순서가 아니라, 이 reference 전체를 이해하기 위한 권장 학습용 구성 순서입니다.

| 번호 | 구현 대상 | 책임과 연결 |
|---|---|---|
| Implementation 1 | `ManifestError` | 입력 계약과 Git 상태 실패를 하나의 CLI 오류 경계로 전달합니다. |
| Implementation 2 | `git` | subprocess exit code와 stderr를 명세 오류로 변환합니다. |
| Implementation 3 | `normalize_remote` | 허용할 URL 표기 차이만 정규화합니다. |
| Implementation 3-1 | `require_string` | 공통 필수 문자열 invariant를 한곳에서 검사합니다. |
| Implementation 4 | `verify_repository` | 저장소 하나의 remote, clean detached HEAD, annotated tag 연결을 검증합니다. |
| Implementation 5 | `verify_manifest` | manifest 전체의 이름·경로 uniqueness와 저장소 순회를 소유합니다. |
| Implementation 6 | `main` | 사용법, exit code, 사람이 읽는 검증 증거를 제공합니다. |

## 완료 기준

검사에 통과한 작업 디렉터리에서는 빌드가 끝날 때까지 다음이 고정되어야 합니다.

- manifest의 저장소 경로·origin·commit이 실제 checkout과 일치합니다.
- annotated tag의 peeled commit과 detached HEAD가 같은 SHA를 가리킵니다.
- tracked·untracked 변경이 없는 상태에서만 릴리스 입력 승인이 기록됩니다.

```text
repository name, path and remote
annotated tag
peeled commit SHA
clean detached worktree
```

빌드 산출물의 digest와 배포 환경 조합은 이 명세를 소비하는 다음 단계에서 추가합니다.

## 자기 설명

- branch 이름보다 peeled commit SHA를 입력으로 고정해야 하는 이유는 무엇입니까?
- clean detached worktree가 재현 가능한 릴리스 근거에 필요한 이유는 무엇입니까?

## 검증

처음 한 번 안전한 학습자 workspace를 만듭니다. 이미 같은 경로가 있으면 덮어쓰지 않고 실패합니다.

```sh
./scripts/new-workspace.sh release-manifest
```

학습자 복사본은 다음 정본 명령으로 검사합니다.

```sh
python3 exercises/04-release-and-evidence/01-release-manifest/tests/verify_manifest.py .workspace/release-manifest/manifest_check.py
```

workspace 검증을 통과하고 위 자기 설명에 답한 뒤에만 reference를 직접 실행하거나 정본 검사로 비교합니다.

```sh
python3 exercises/04-release-and-evidence/01-release-manifest/reference/manifest_check.py \
  /path/to/release-manifest.json
python3 exercises/04-release-and-evidence/01-release-manifest/tests/verify_manifest.py \
  exercises/04-release-and-evidence/01-release-manifest/reference/manifest_check.py
```

저장소 전체 `./verify.sh`는 reference의 정상·오류 사례를 모두 확인하고, 같은 검사에서 skeleton이 실패하는지도 확인합니다.

- reference는 정상 manifest와 각 오류 fixture를 정확히 구분합니다.
- skeleton은 commit 일치만으로 불완전한 manifest를 승인하지 못합니다.
- 저장소 전체 검증은 임시 저장소만 사용하고 학습자 checkout을 변경하지 않습니다.
