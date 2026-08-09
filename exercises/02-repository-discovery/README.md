# 실습 02: Repository discovery

## 목표

처음 보는 저장소에서 Git 기준점, 지시, 구조, runtime, build와 test 경로를 읽기 전용으로 복원하는 explorer를 설계합니다.

## fixture 요구사항

직접 작은 fixture를 설계합니다.

```text
monorepo 또는 두 package
root와 nested instruction
두 종류의 test command
생성물 directory
vendor 또는 cache
초기 dirty file 하나
오래된 README 명령과 현재 CI 명령의 충돌
```

## 설계할 책임

- `RepositorySnapshot`
- `InstructionManifest`
- `EnvironmentManifest`
- top-level tree summary
- command catalog
- generated/vendor/secret classification
- discovery budget
- conflict report

## 필수 시나리오

### 정상

- root·HEAD·branch·dirty state 확인
- target path에 적용되는 nested instruction 발견
- lockfile과 CI에서 test command 발견
- generated source와 정본 source 구분

### 경계

- detached HEAD
- unborn branch
- submodule
- sparse checkout
- same repository의 다른 worktree
- README와 manifest의 runtime version 불일치

### 실패

- Git repository 아님
- broken symlink instruction
- command source 없음
- permission denied path
- discovery budget 초과
- 저장소 file이 discovery 중 변경

## 필수 산출물

```text
repository-snapshot.md
instruction-precedence.md
environment-manifest.md
discovery-algorithm.md
conflict-report.md
fixture-layout.md
```

## 검증 계획

- fixture의 모든 정본 command와 applicable instruction을 찾습니다.
- initial dirty change를 agent change로 분류하지 않습니다.
- stale README를 무조건 선택하지 않습니다.
- forbidden secret과 hidden evaluation path를 manifest에 content 없이 분류합니다.
- discovery는 workspace를 바꾸지 않습니다.

## 의도적 비범위

- source code 수정
- dependency 설치
- 실제 test 실행
- semantic code index 전체
