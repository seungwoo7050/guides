# command-checker

`command-checker`는 JSON으로 정의한 동작 계약에 따라 외부 CLI 프로그램을 실행하고 `returncode`, `stdout`, `stderr`를 검증하는 dependency-free Python 도구입니다. 단순 출력 비교뿐 아니라 timeout, stream별 출력 상한, process group 종료, 병렬 실행, JSON/JUnit 보고서까지 하나의 실행 모델로 처리합니다.

## 주요 기능

- JSON case specification 검증 및 immutable `Case` 모델 변환
- 호출 시점에 target executable identity를 한 번 결정해 case별 `cwd`/`env.PATH`가 실행 파일을 바꾸지 못하도록 고정
- `stdin`, `stdout`, `stderr`, `returncode`의 정확 비교
- POSIX process group 기반 timeout 및 descendant cleanup
- non-blocking pipe I/O와 `stdout`/`stderr`별 byte limit
- `ThreadPoolExecutor` 기반 bounded concurrency와 입력 순서 보존
- 동일한 `Result` sequence에서 JSON/JUnit 보고서 생성
- 같은 directory의 임시 파일과 `os.replace`를 이용한 atomic report replacement
- dependency-free PEP 517 wheel build와 `command-checker` console script

## 구조

```text
command-checker/
├── README.md
├── pyproject.toml
├── _command_checker_build.py
├── command_checker/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── comparison.py
│   ├── model.py
│   ├── process.py
│   ├── reports.py
│   ├── runner.py
│   ├── specification.py
│   └── py.typed
├── examples/
│   ├── line_sort.py
│   └── sort_cases.json
└── tests/
    ├── fixture_program.py
    └── test_command_checker.py
```

모듈 책임은 다음과 같습니다.

| Module | Responsibility |
|---|---|
| `model.py` | immutable `Case`, `Result`, boundary exceptions |
| `comparison.py` | process I/O와 독립적인 pure result comparison |
| `specification.py` | JSON field/type/path/environment validation |
| `process.py` | process group, pipe, deadline, signal lifecycle |
| `runner.py` | executable selection, sequential/parallel orchestration, output policy |
| `reports.py` | JSON/JUnit rendering과 atomic replacement |
| `cli.py` | CLI contract, diagnostics, final composition |
| `_command_checker_build.py` | deterministic dependency-free wheel build |

## 요구 환경

- Python 3.12 이상
- process-group timeout/descendant cleanup은 POSIX 환경(macOS, Linux) 기준

Runtime dependency는 없습니다.

## 설치

프로젝트 directory에서:

```sh
python3 -m pip install .
command-checker --help
```

설치하지 않고 module로 실행할 수도 있습니다.

```sh
python3 -m command_checker --help
```

## 사용법

기본 interface:

```text
command-checker --cases CASES [--jobs N]
                [--json-report PATH]
                [--junit-report PATH]
                -- COMMAND [ARG ...]
```

포함된 example:

```sh
python3 -m command_checker \
  --cases examples/sort_cases.json \
  --jobs 2 \
  -- \
  python3 examples/line_sort.py
```

모든 case가 일치하면 각 case의 `PASS`와 summary를 stdout에 출력하고 0으로 종료합니다.

## Case specification

최상위 JSON 값은 비어 있지 않은 array여야 합니다.

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

지원 field:

| Field | Type | Default |
|---|---|---|
| `name` | non-empty string | required |
| `args` | array of strings | `[]` |
| `stdin` | string | `""` |
| `stdout` | string | `""` |
| `stderr` | string | `""` |
| `returncode` | integer | `0` |
| `timeout` | finite positive number | `2.0` |
| `output_limit` | positive integer bytes | `1048576` |
| `cwd` | non-empty relative path or `null` | `null` |
| `env` | string-to-string object | `{}` |

`cwd`가 생략되거나 `null`이면 `command-checker` process의 working directory를 상속합니다. 문자열 `cwd`는 case file이 위치한 directory를 기준으로 resolve되며 absolute path는 거부합니다.

`env`는 inherited environment 위에 override됩니다. 다만 target executable은 모든 case를 실행하기 전에 호출 context에서 한 번 선택하고 absolute path로 고정합니다. 따라서 case별 `cwd` 또는 `env.PATH` 변경은 이미 선택된 executable identity를 바꾸지 않습니다.

## 종료 상태

| Exit status | Meaning |
|---:|---|
| `0` | 모든 case가 일치 |
| `1` | 실행은 완료됐지만 하나 이상의 case가 불일치 |
| `2` | specification, executable, process-management, report-write 오류 |

한 case의 assertion mismatch는 다른 case 실행을 중단하지 않습니다. 반면 process 시작 자체를 수행할 수 없는 infrastructure-level 오류는 status 2로 처리합니다.

## Process lifecycle

각 target은 `start_new_session=True`로 별도 process group에서 시작합니다. `stdin`, `stdout`, `stderr`는 non-blocking descriptor로 전환하고 하나의 selector가 deadline과 stream state를 관리합니다.

Timeout 또는 output-limit 초과 시 해당 process group에 `SIGTERM`을 보내고 짧은 grace period 뒤 필요하면 `SIGKILL`을 사용합니다. 부모 process가 먼저 종료했지만 descendant가 pipe를 계속 보유하는 경우에도 descriptor가 닫힐 때까지 추적하며 deadline을 넘으면 같은 process group cleanup 정책을 적용합니다.

## 보고서

```sh
python3 -m command_checker \
  --cases examples/sort_cases.json \
  --json-report artifacts/result.json \
  --junit-report artifacts/result.xml \
  -- \
  python3 examples/line_sort.py
```

JSON과 JUnit은 terminal output과 동일한 `Result` sequence에서 생성됩니다. Report는 destination과 같은 directory에 임시 파일을 완성하고 `fsync`한 뒤 `os.replace`로 교체합니다. JUnit dynamic text는 XML 1.0에서 허용되지 않는 code point를 replacement character로 바꿉니다.

## 테스트

Project-local test suite는 표준 라이브러리 `unittest`만 사용합니다.

```sh
python3 -m unittest discover -s tests -v
```

검증 범위에는 specification validation, stream/status comparison, timeout, output limit, bounded concurrency의 input-order guarantee, report rendering, end-to-end module CLI가 포함됩니다.

Wheel 자체도 dependency-free backend로 build할 수 있습니다.

```sh
python3 -m pip wheel --no-deps . -w dist
```

## 주요 설계 결정

### Immutable case/result boundary

Validation이 끝난 input과 execution result는 `frozen=True`, `slots=True` dataclass로 고정합니다. Worker 간 공유되는 값의 mutation 가능성을 제거하고 process I/O와 comparison을 분리합니다.

### Exact output contract

`stdout`과 `stderr`는 whitespace와 newline을 포함해 exact match합니다. Normalization을 암묵적으로 수행하지 않습니다.

### Executable identity pinning

Bare command는 호출 environment의 `PATH`에서 한 번 resolve하고, path separator가 있는 command는 호출 working directory 기준으로 absolute path를 고정합니다. Case runtime context가 target executable을 바꾸는 것을 방지합니다.

### Bounded concurrency with stable result order

`ThreadPoolExecutor(max_workers=jobs)`로 동시에 실행할 case 수를 제한하고 `executor.map`을 사용해 completion order와 관계없이 input order로 `Result`를 반환합니다.

## Implementation Order

아래 순서는 file order나 runtime call order가 아니라, 완성된 project를 처음부터 구축할 때의 architecture-driven construction sequence입니다. 별도 framework scaffold나 persistent bootstrap command가 없으므로 `Implementation 0`은 사용하지 않습니다.

| Order | Responsibility | Primary anchor |
|---:|---|---|
| `1` | Package and runtime contract | `pyproject.toml` |
| `1-1` | Module entry-point delegation | `command_checker/__main__.py` |
| `2` | Immutable case model | `command_checker/model.py:Case` |
| `2-1` | Immutable result model | `command_checker/model.py:Result` |
| `2-2` | Boundary error taxonomy | `command_checker/model.py` |
| `3` | Pure observation comparison | `command_checker/comparison.py:compare_observation` |
| `4` | Untrusted JSON value normalization | `command_checker/specification.py` |
| `4-1` | Case contract validation | `command_checker/specification.py:_case` |
| `4-2` | Specification file boundary | `command_checker/specification.py:load_cases` |
| `5` | Executable identity selection | `command_checker/runner.py:validate_executable` |
| `5-1` | Per-case process execution boundary | `command_checker/process.py:run_case` |
| `6` | Sequential orchestration baseline | `command_checker/runner.py:run_cases` |
| `6-1` | Result presentation policy | `command_checker/runner.py:print_results` |
| `6-2` | Match exit-status policy | `command_checker/runner.py:exit_status` |
| `7` | Process-group termination ownership | `command_checker/process.py:_terminate_group` |
| `7-1` | Non-blocking pipe and deadline collection | `command_checker/process.py:_collect_process` |
| `7-2` | Process-group cleanup guarantee | `command_checker/process.py:run_case` |
| `8` | Atomic report replacement | `command_checker/reports.py:atomic_write_text` |
| `8-1` | Deterministic JSON report rendering | `command_checker/reports.py:render_json` |
| `8-2` | XML-safe JUnit report rendering | `command_checker/reports.py:xml_text` |
| `9` | Bounded concurrent execution | `command_checker/runner.py:run_cases` |
| `10` | CLI parser and usage-error boundary | `command_checker/cli.py:CommandCheckerArgumentParser` |
| `10-1` | Public CLI contract | `command_checker/cli.py:build_parser` |
| `10-2` | CLI argument normalization | `command_checker/cli.py:parse_arguments` |
| `10-3` | Application composition and status mapping | `command_checker/cli.py:main` |
| `10-4` | Build metadata ownership | `_command_checker_build.py:_project` |
| `10-5` | Deterministic wheel publication | `_command_checker_build.py:build_wheel` |
| `11` | Behavioral verification suite | `tests/test_command_checker.py:CommandCheckerTests` |

## 범위와 제한

- Python 3.12 이상을 대상으로 합니다.
- Windows native process-tree termination은 지원 범위가 아닙니다.
- `cwd`는 sandbox가 아니라 case-file-relative execution context입니다. `..`를 허용하므로 격리 경계로 사용하면 안 됩니다.
- Output comparison은 binary protocol용이 아니라 UTF-8 text CLI용입니다. Decode할 수 없는 byte는 replacement character로 처리합니다.
- Report replacement는 file-level atomicity를 제공하지만 여러 report를 하나의 transaction으로 묶지는 않습니다.
