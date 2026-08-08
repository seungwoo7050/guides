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

## 직접 실행

```sh
python3 reference/manifest_check.py /path/to/release-manifest.json
python3 tests/verify_manifest.py reference/manifest_check.py
```

저장소 전체 `./verify.sh`는 reference의 정상·오류 사례를 모두 확인하고, 같은 검사에서 skeleton이 실패하는지도 확인합니다.

## 완료 기준

검사에 통과한 작업 디렉터리에서는 빌드가 끝날 때까지 다음이 고정되어야 합니다.

```text
repository name, path and remote
annotated tag
peeled commit SHA
clean detached worktree
```

빌드 산출물의 digest와 배포 환경 조합은 이 명세를 소비하는 다음 단계에서 추가합니다.
