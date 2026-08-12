# 누적 실습: `command-checker`

## 목표

- 외부 명령의 입력, 출력, 오류, 종료 상태와 수명을 명시적인 계약으로 구현합니다.
- 단계별 실패를 이용해 데이터 모델에서 병렬 보고서까지 누적 완성합니다.

`command-checker`는 JSON에 기록한 사례로 외부 명령줄 프로그램을 실행하고 `returncode`, `stdout`, `stderr`를 비교합니다. 한 사례의 실패가 뒤 사례를 막지 않아야 하며, 제한 시간을 넘기거나 출력을 끝없이 만드는 프로세스는 자식까지 정리합니다.

학습 개념은 Python 3.12 이상을 기준으로 설명합니다. 이 저장소의 공식 workspace·검증 흐름과 최종 구현은 macOS·Linux의 POSIX 프로세스 그룹과 non-blocking descriptor를 사용합니다. Windows native workflow와 process-tree 종료는 지원 범위에 포함하지 않습니다.

## 작업 원칙

```text
처음 한 번 skeleton을 workspace로 복사한다
→ 현재 단계 문서를 읽는다
→ workspace에서 한 책임만 구현한다
→ 현재 단계까지의 누적 검사
→ 실패 원인을 설명한다
→ 수정한다
→ 1~7단계는 검사 성공을 expected evidence로 남긴다
→ 8단계 전체 검사가 성공한 뒤 최종 reference와 비교한다
```

`reference/`는 단계별 snapshot이 아니라 이후 단계까지 포함한 최종 구현입니다. 처음부터 복사하거나 중간 단계에서 같은 파일을 비교하면 순수 비교에서 프로세스 수명 제어로 성장하는 판단 과정을 잃습니다.

## 구성

```text
command-checker/
├── README.md
├── fixtures/
├── skeleton/{pyproject.toml, command_checker/}
├── workspace/  # 생성 뒤 학습자가 수정하며 Git에서 제외
├── reference/{pyproject.toml, command_checker/}
└── tests/
```

`fixtures/`는 입력과 프로세스 수명 재현 도구이며 관찰 example이나 답안이 아닙니다. 독립 `examples/`는 두지 않습니다.

최종 모듈 책임:

| 모듈 | 책임 |
|---|---|
| `model.py` | 불변 `Case`, `Result`와 경계 예외 |
| `comparison.py` | 실제 관찰과 기대값의 순수 비교 |
| `specification.py` | JSON·필드·경로·환경 값 검증 |
| `process.py` | 프로세스·파이프·deadline·신호 수명 |
| `reports.py` | JSON·JUnit과 원자적 파일 교체 |
| `runner.py` | 순차·병렬 실행, 결과 순서와 종료 정책 |
| `cli.py` | argparse, 사용자 진단과 최종 조립 |

## 작업 공간

저장소 루트에서 실행합니다.

```sh
scripts/new-workspace.sh exercises/command-checker
```

기존 `workspace/`가 있으면 실패하며 덮어쓰지 않습니다.

각 `make stage-N EXERCISE_IMPL=workspace`는 1단계부터 N단계까지를 누적 검사합니다. `EXERCISE_IMPL`을 생략한 learner-facing 명령도 `workspace`를 선택하고, `make reference-check`만 정답을 명시적으로 선택합니다. source-level 단계 검사는 구현 경로를 명시적으로 사용하지만, package 검사는 별도의 임시 venv에 설치한 뒤 source 경로 주입 없이 실행합니다.

## 최종 인터페이스

```text
command-checker --cases CASES [--jobs N]
                [--json-report PATH]
                [--junit-report PATH]
                -- COMMAND [ARG ...]
```

가장 작은 사례:

```json
[
  {
    "name": "ascending",
    "stdin": "3 1 2\n",
    "stdout": "1\n2\n3\n",
    "stderr": "",
    "returncode": 0
  }
]
```

지원 필드:

| 필드 | 타입 | 기본값 |
|---|---|---|
| `name` | 비어 있지 않은 문자열 | 필수 |
| `args` | 문자열 배열 | `[]` |
| `stdin` | 문자열 | `""` |
| `stdout` | 문자열 | `""` |
| `stderr` | 문자열 | `""` |
| `returncode` | 정수 | `0` |
| `timeout` | 유한한 양수 | `2.0` |
| `output_limit` | 양의 정수 바이트 수 | `1048576` |
| `cwd` | 사례 파일 기준의 비어 있지 않은 상대 경로 | `null` |
| `env` | 문자열 키·값 객체 | `{}` |

`cwd`가 생략되거나 `null`이면 `command-checker`를 호출한 작업 디렉터리를 상속합니다. 문자열이면 사례 파일이 있는 디렉터리를 기준으로 해석하며 `.`과 `..`를 사용할 수 있지만 절대 경로와 빈 문자열은 거부합니다. 이는 sandbox가 아니라 재사용 가능한 명세의 경로 기준입니다.

검사 대상 실행 파일은 사례를 시작하기 전에 한 번 선택합니다. separator가 있는 상대 명령은 `command-checker` 호출 디렉터리, bare 명령은 호출 환경의 `PATH`에서 찾은 뒤 절대 경로로 고정합니다. 각 사례의 `cwd`와 `env.PATH`는 실행 context만 바꾸며 이미 선택한 실행 파일을 다른 파일로 바꾸지 않습니다.

## 1단계: 패키지와 진입점

관련 문서: [실행 환경과 모듈](../../docs/01-language-and-runtime/01-runtime-and-environment.md)

제공된 packaging scaffold:

- `__main__.py`가 `cli.main`에 위임하는 module 진입점
- `_command_checker_build.py`와 `pyproject.toml`의 dependency-free build/console-script 연결
- 빈 `py.typed` marker와 package version 자리

이 파일들은 Stage 1에서 새로 구현하지 않고 `package-entrypoint` 검사로 연결을 관찰합니다. 학습자가 수정할 위치는 `workspace/command_checker/cli.py`입니다.

구현:

- `build_parser()`, `parse_arguments()`, `main(argv)`
- 도움말은 stdout과 종료 상태 0
- 사용법 오류는 stderr와 종료 상태 2
- import만 했을 때 부작용 없음

```sh
make stage-01 EXERCISE_IMPL=workspace
```

이 검사는 임시 venv에 workspace를 실제 설치하고 `command-checker --help`를 실행합니다. 1단계를 마친 workspace를 준비된 로컬 venv에 계속 사용하려면 다음처럼 설치합니다.

```sh
make install-workspace
.guide/python/venv/bin/command-checker --help
```

## 2단계: 데이터 모델

관련 문서: [객체와 컬렉션](../../docs/01-language-and-runtime/02-objects-and-collections.md)

구현:

- `Case`, `Result`
- `frozen=True`, `slots=True`
- 가변 `dict` 대신 정렬된 환경 변수 튜플
- `SpecificationError`, `ExecutionError`

```sh
make stage-02 EXERCISE_IMPL=workspace
```

## 3단계: 비교와 실패 표현

관련 문서: [함수, 예외와 타입 경계](../../docs/01-language-and-runtime/03-functions-errors-and-types.md)

구현:

- returncode, stdout, stderr의 정확 비교
- 공백과 줄바꿈도 계약에 포함
- timeout과 출력 초과를 별도 실패로 표현
- 파일·프로세스에 의존하지 않는 순수 함수

```sh
make stage-03 EXERCISE_IMPL=workspace
```

## 4단계: JSON 명세와 실행 시 검증

관련 문서: [파일, 구조화된 데이터와 CLI](../../docs/02-automation/01-files-structured-data-and-cli.md)의 JSON·경로·CLI 입력 부분. 원자적 결과 교체 부분은 8단계에서 다시 적용합니다.

구현:

- 비어 있지 않은 JSON 배열
- 허용 필드와 실제 타입
- 중복 이름
- 유한한 양수 timeout
- 양의 output limit
- 사례 파일 기준의 비어 있지 않은 상대 `cwd`; 누락·`null`은 호출 디렉터리 상속
- NUL과 `=`을 거부하는 환경 변수 키

```sh
make stage-04 EXERCISE_IMPL=workspace
```

## 5단계: 외부 프로세스 한 건 실행

관련 문서: [외부 프로세스와 수명 관리](../../docs/02-automation/02-subprocess-and-process-lifecycle.md)의 실행 부분, [반복자, 생성기와 컨텍스트 관리자](../../docs/01-language-and-runtime/04-iterators-generators-and-context-managers.md)의 stream·resource 수명 부분

먼저 사례 한 건을 실행합니다.

- 명령과 `args`의 인자 경계 보존
- stdin 전달
- stdout·stderr·returncode 수집
- cwd와 환경 override
- 실행 파일 오류는 `ExecutionError`

```sh
make stage-05 EXERCISE_IMPL=workspace
```

## 6단계: 전체 사례와 종료 정책

별도 개념 문서를 추가하지 않습니다. 이 절의 집계·표시·종료 계약을 직접 구현하고, 최종 [CLI 검사기 설계](../../docs/03-quality/03-cli-test-runner.md)에서 전체 의존 방향을 다시 검토합니다.

구현:

- 한 사례가 실패해도 다음 사례 실행
- 실행 파일은 호출 context에서 한 번 선택해 모든 사례가 같은 identity 사용
- 입력 순서로 결과 반환
- 통과는 stdout, 실패 세부는 stderr
- 모든 사례 일치 0, 불일치 1, 시작 불가 2

```sh
make stage-06 EXERCISE_IMPL=workspace
```

## 7단계: 프로세스 수명과 출력 상한

관련 문서: [외부 프로세스와 수명 관리](../../docs/02-automation/02-subprocess-and-process-lifecycle.md)의 timeout·pipe·process group 부분, [반복자, 생성기와 컨텍스트 관리자](../../docs/01-language-and-runtime/04-iterators-generators-and-context-managers.md)의 정리 책임 부분

구현:

- `start_new_session=True`
- non-blocking stdin·stdout·stderr
- timeout 시 프로세스 그룹에 SIGTERM, 유예 뒤 SIGKILL
- 부모가 먼저 끝나도 파이프를 보유한 자식 추적
- stdout·stderr 각각 `output_limit` 적용

```sh
make stage-07 EXERCISE_IMPL=workspace
```

## 8단계: 병렬 실행과 원자적 보고서

관련 문서: [동시성, 취소와 자원 한계](../../docs/02-automation/03-concurrency-and-cancellation.md), [재현 가능한 테스트](../../docs/03-quality/01-testing.md), [프로젝트 구조, 패키징과 타입 검사](../../docs/03-quality/02-project-structure-packaging-and-typing.md), [CLI 검사기 설계](../../docs/03-quality/03-cli-test-runner.md), [파일 문서의 원자적 결과 교체](../../docs/02-automation/01-files-structured-data-and-cli.md#원자적-결과-교체)

구현:

- `ThreadPoolExecutor`의 제한된 worker 수
- 완료 순서와 무관하게 입력 순서 보존
- 같은 `Result`에서 JSON·JUnit 생성
- 같은 디렉터리의 임시 파일을 완성한 뒤 `os.replace`
- XML 1.0에서 허용하지 않는 문자를 대체
- 공개 함수와 dataclass 필드의 annotation, 공개 API의 `Any` 금지
- 빈 `py.typed`, 일치하는 package/module version, metadata와 설치된 `command-checker` 종단 간 실행

```sh
make stage-08 EXERCISE_IMPL=workspace
```

## Reference 구현 순서

이 절은 전체 workspace 검사가 성공한 뒤 `reference/`를 읽을 때 사용합니다. 번호는 Git history나 runtime 순서가 아니라 프로젝트 전체의 학습용 recommended construction order입니다. 파일마다 다시 시작하지 않으며 한 단계가 여러 파일을 연결하거나 같은 파일을 나중에 다시 방문할 수 있습니다. 이 프로젝트에는 application logic 이전의 별도 framework·dependency bootstrap이 없으므로 0번 단계가 없습니다.

| 번호 | 파일·symbol | 책임과 다음 연결 |
|---|---|---|
| `1` | `reference/pyproject.toml` | dependency-free build, Python 최솟값, console script와 공개 타입 경계를 먼저 고정 |
| `1-1` | `reference/command_checker/__main__.py` | module 실행을 `cli.main`과 같은 종료 상태 계약에 연결 |
| `2` | `reference/command_checker/model.py:Case` | 검증된 입력과 worker 공유 상태를 불변 값으로 소유 |
| `2-1` | `reference/command_checker/model.py:Result` | 관찰 결과와 timeout·출력 초과 수명 상태를 하나의 값으로 고정 |
| `2-2` | `reference/command_checker/model.py`의 예외 | 명세·실행 경계 실패를 분리하고 결과 불일치는 `Result`에 남김 |
| `3` | `reference/command_checker/comparison.py:compare_observation` | I/O 없이 세 결과 채널과 수명 실패를 비교 |
| `4` | `reference/command_checker/specification.py`의 scalar helpers | 신뢰하지 않는 JSON scalar·배열·환경 값을 먼저 정규화 |
| `4-1` | `reference/command_checker/specification.py:_case` | field whitelist, 기본값과 상대 `cwd`를 불변 `Case`로 변환 |
| `4-2` | `reference/command_checker/specification.py:load_cases` | 파일·JSON·중복 이름 경계를 소유하고 tuple로 publish |
| `5` | `reference/command_checker/runner.py:validate_executable` | 호출 context에서 실행 파일 identity를 한 번 선택 |
| `5-1` | `reference/command_checker/process.py:run_case` | 한 사례의 env·cwd·spawn·관찰 결과를 소유 |
| `6` | `reference/command_checker/runner.py:run_cases` | 순차 baseline과 입력 순서 계약을 먼저 완성 |
| `6-1` | `reference/command_checker/runner.py:print_results` | 불변 결과를 stdout·stderr 사용자 채널로 route |
| `6-2` | `reference/command_checker/runner.py:exit_status` | 전체 결과에서 0·1 상태를 한 번만 결정 |
| `7` | `reference/command_checker/process.py:_terminate_group` | TERM→grace→KILL→reap 수명 invariant 고정 |
| `7-1` | `reference/command_checker/process.py:_collect_process` | selector 하나가 pipe, deadline과 stream별 byte 상한을 소유 |
| `7-2` | `reference/command_checker/process.py:run_case` 정리 경계 | 예외·취소에서도 소유한 process group을 남기지 않음 |
| `8` | `reference/command_checker/reports.py:atomic_write_text` | 같은 디렉터리의 완성된 임시 파일만 최종 경로로 교체 |
| `8-1` | `reference/command_checker/reports.py:render_json` | 같은 `Result` sequence에서 결정적인 JSON summary 생성 |
| `8-2` | `reference/command_checker/reports.py:xml_text`, `render_junit` | 동적 text를 XML 1.0에 맞춘 뒤 같은 결과로 JUnit 생성 |
| `9` | `reference/command_checker/runner.py:run_cases` 병렬 경계 | bounded worker를 추가하되 완료 순서와 입력 순서를 분리 |
| `10` | `reference/command_checker/cli.py:KoreanArgumentParser` | 사용자 usage 진단의 단일 owner 고정 |
| `10-1` | `reference/command_checker/cli.py:build_parser` | 외부 CLI surface 선언 |
| `10-2` | `reference/command_checker/cli.py:parse_arguments` | 부작용 전에 `--`, worker 수와 빈 명령을 정규화·거부 |
| `10-3` | `reference/command_checker/cli.py:main` | 명세·실행·보고서를 조립하고 0·1·2 종료 상태로 변환 |
| `10-4` | `reference/_command_checker_build.py:_project` | metadata와 console entrypoint drift를 wheel 생성 전에 거부 |
| `10-5` | `reference/_command_checker_build.py:build_wheel` | module·marker·metadata·RECORD를 재현 가능한 wheel로 묶음 |
| `10-6` | `reference/command_checker/py.typed`, `reference/command_checker/__init__.py`, `reference/pyproject.toml` version | [Implementation 10-6] `py.typed`는 비워 두고 package/module version을 일치시켜 최종 배포 계약을 닫음 |

## 전체 검사

workspace 전체:

```sh
make exercise-check EXERCISE_IMPL=workspace
```

이 명령이 성공하고 자기 설명을 마친 뒤 처음으로 `reference/` 전체를 비교합니다. reference 비교 뒤 완성한 workspace 명령을 준비된 local venv에 설치하려면 `make install-workspace`를 사용합니다.

저장소의 reference, skeleton, 문서와 스크립트까지:

```sh
./verify.sh
```

전체 검증은 정상 구현만 통과시키는 데서 끝나지 않습니다. 상대 `cwd`와 실행 파일 identity 오류, 결과 채널 비교 누락, 숫자형 검증 오류, 출력 상한 제거, 병렬 실행 제거·결과 순서 역전, XML 제어 문자 누락, 금지 의존성, 공개 타입 annotation 제거와 console script 변경을 주입하고 각각 올바른 검사에서 거부하는지 확인합니다.

## 완료 기준

- import와 실행 진입점이 분리되어 있습니다.
- 격리 설치 뒤 `command-checker`가 source 경로 주입 없이 실행됩니다.
- 공개 API annotation과 `py.typed` 계약을 정적으로 확인합니다.
- 공유 데이터 모델이 불변입니다.
- 명세 오류와 결과 불일치를 구분합니다.
- 세 결과 채널을 정확히 비교합니다.
- 모든 사례를 실행하고 순서를 결정적으로 유지합니다.
- timeout과 출력 초과 뒤 자식 프로세스가 남지 않습니다.
- 병렬 worker가 보고서 파일을 직접 수정하지 않습니다.
- 기존 보고서는 완성된 새 파일이 있을 때만 교체됩니다.

## 자기 설명

- timeout과 출력 상한은 왜 단순한 결과 불일치가 아니라 프로세스 수명 계약입니까?
- 병렬 완료 순서와 사용자에게 보여 줄 결과 순서를 어떻게 분리합니까?

## 검증

```sh
make stage-01 EXERCISE_IMPL=workspace
make exercise-check EXERCISE_IMPL=workspace
./verify.sh
```
