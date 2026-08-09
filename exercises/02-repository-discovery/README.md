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

## 실행 파일과 판정

- 구현 경계: [starter `repository.py`](../10-capstone-local-coding-agent/starter/coding_agent/repository.py)
- 비교 구현: [reference `repository.py`](../10-capstone-local-coding-agent/reference/coding_agent/repository.py)
- 공개 판정: [`test_stage_02_repository.py`](../10-capstone-local-coding-agent/tests/test_stage_02_repository.py)

```sh
python3 exercises/10-capstone-local-coding-agent/tests/run.py --implementation reference --stage 02
python3 exercises/10-capstone-local-coding-agent/tests/run.py --implementation starter --stage 02 --expect-incomplete
python3 exercises/10-capstone-local-coding-agent/tests/run.py --implementation .workspace/local-coding-agent --stage 02
```

starter의 `NotImplementedError` 메시지에 있는 `stage-02`는 의도한 미완성 표식입니다. 대표 실패는 snapshot 뒤 바뀐 파일을 그대로 읽거나 workspace 밖 path를 허용하는 경우입니다. 단계 검사는 01부터 누적됩니다. 위 설계 산출물만으로는 완료가 아니며, 같은 불변식을 구현한 learner module, canonical test 결과, 정상·대표 실패 trace를 함께 제출합니다.

사람 검토 질문:

- 초기 dirty change와 agent effect를 어떤 identity와 시점으로 구분합니까?
- README·CI·lockfile의 command나 runtime 정보가 충돌할 때 선택과 보류 근거가 manifest에 남습니까?

## 의도적 비범위

- source code 수정
- dependency 설치
- 실제 test 실행
- semantic code index 전체
