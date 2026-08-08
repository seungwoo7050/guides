# 프로젝트 구조, 패키징과 타입 검사

## 학습 목표

프로젝트 구조는 파일 수를 늘리는 규칙이 아니라 변경 이유가 다른 책임을 분리하는 도구입니다. 이 장은 Python 프로그램이 한 파일에서 여러 모듈로 성장할 때의 기준을 다룹니다.

## 선행 개념

- module import 방향, public API와 type hint/runtime validation의 차이

## 크기에 맞는 구조

일회성 변환 도구가 30줄이라면 한 파일이 충분할 수 있습니다.

```text
normalize-log.py
```

다음 책임이 독립적으로 바뀌기 시작하면 모듈을 나눕니다.

```text
CLI 파싱
외부 입력 검증
핵심 계산
파일·프로세스 I/O
보고서 직렬화
```

작은 패키지 예:

```text
project/
├── pyproject.toml
├── src/
│   └── app/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       └── core.py
└── tests/
    └── test_core.py
```

`src/` 배치는 설치되지 않은 저장소 루트가 우연히 import 경로에 들어가 생기는 오류를 줄일 수 있습니다. 모든 작은 스크립트에 강제할 필요는 없습니다.

## 모듈 의존 방향

공통 데이터 모델이 외부 I/O 모듈을 import하면 순환이 생기기 쉽습니다.

```text
model ← parser
model ← process
model ← reports
cli → parser, runner
runner → process, reports
```

아래쪽의 순수한 모듈이 위쪽 진입점의 출력 문구나 옵션을 알지 않게 합니다.

`command-checker`의 최종 구조는 다음과 같습니다.

```text
pyproject.toml
_command_checker_build.py
command_checker/
├── __init__.py
├── __main__.py
├── cli.py
├── comparison.py
├── model.py
├── specification.py
├── process.py
├── py.typed
├── reports.py
└── runner.py
```

## `pyproject.toml`

프로젝트 메타데이터, 지원 Python 버전과 도구 설정을 한곳에 둘 수 있습니다.

```toml
[build-system]
requires = []
build-backend = "_command_checker_build"
backend-path = ["."]

[project]
name = "command-checker"
version = "0.0.0"
requires-python = ">=3.12"
dependencies = []

[project.scripts]
command-checker = "command_checker.cli:main"
```

외부 패키지를 사용한다면 다음을 구분합니다.

- 애플리케이션 실행 의존성
- 개발·검사 의존성
- 직접 선택한 의존성과 전이 의존성
- 버전 범위와 재현 가능한 lock

`pip install`을 매번 임의 버전으로 실행하는 것은 재현 가능한 환경이 아닙니다. 저장소가 선택한 패키지 관리자와 lockfile을 기준으로 준비 명령을 고정합니다.

이 가이드는 제3자 패키지를 요구하지 않으며 `prepare.sh`는 `.guide/python/venv`만 만듭니다. 실습의 작은 in-tree PEP 517 backend도 표준 라이브러리만 사용합니다. `make package-check EXERCISE_IMPL=workspace`는 임시 venv에 wheel을 설치하고, 저장소 밖 cwd와 비어 있는 `PYTHONPATH`에서 metadata, `py.typed`, console script와 종단 간 실행을 확인합니다.

## 타입 검사 경계

타입 힌트는 공개 함수와 공유 데이터 모델부터 추가합니다.

```python
def run_cases(
    cases: Sequence[Case],
    command: Sequence[str],
    jobs: int,
) -> tuple[Result, ...]:
    ...
```

다음 상황에서 가치가 큽니다.

- `None` 여부가 중요한 경우
- 여러 모듈이 같은 모델을 공유하는 경우
- callback이나 Protocol을 전달하는 경우
- dict의 모양이 커져 이름 있는 타입이 필요한 경우

외부 JSON에 곧바로 `cast(Case, raw)`를 적용하지 않습니다. `cast`는 실행 시 검증하지 않습니다.

실습은 외부 도구 없이도 다음 정적 공개 타입 계약을 항상 실행합니다.

```sh
make type-check EXERCISE_IMPL=workspace
```

이 검사는 AST에서 모든 함수 인자·반환 annotation, dataclass 필드 annotation, 공개 API의 `Any` 금지와 `py.typed`를 확인합니다. 값 흐름의 타입 적합성까지 증명하는 mypy·pyright의 대체물은 아닙니다. 그런 의미 분석 도구를 추가한다면 아래의 고정된 검증 진입점에 연결해야 합니다.

## 값 객체와 가변성

```python
@dataclass(frozen=True, slots=True)
class Result:
    name: str
    passed: bool
    failures: tuple[str, ...]
```

불변 데이터는 thread 사이에 공유하기 쉽고, 보고서 생성이 실행 결과를 바꾸지 않게 합니다.

`frozen=True` 안에 가변 list나 dict를 넣으면 내부 변경은 여전히 가능합니다. 필드 타입까지 불변으로 구성합니다.

## Protocol로 외부 경계를 좁힙니다

```python
class Reporter(Protocol):
    def write(self, path: Path, results: Sequence[Result]) -> None:
        ...
```

테스트에서 작은 fake를 사용할 수 있지만, 구체 구현이 하나뿐이고 교체 필요가 없다면 추상화를 먼저 만들지 않습니다.

## 품질 도구 선택

표준 라이브러리 기반 `make type-check`와 package 설치 검사는 이 실습의 필수 계약입니다. 프로젝트에 따라 다음 도구를 추가로 선택할 수 있습니다.

- `ruff`: lint와 format
- `mypy` 또는 `pyright`: 정적 타입 검사
- `pytest`: fixture와 매개변수화가 많은 검사
- `coverage.py`: 실행 경로 관찰
- `tox` 또는 `nox`: 여러 Python 환경 반복

도구 개수보다 모든 개발자가 실행할 하나의 진입점이 먼저입니다.

```sh
./verify.sh
```

도구가 추가되면 `prepare.sh`가 저장소 로컬 환경에 고정 버전으로 설치하고, `verify.sh`가 그 환경만 사용해야 합니다.

## 로그와 비밀 정보

라이브러리 모듈이 전역 로그 정책을 임의로 설정하지 않습니다. 최종 애플리케이션에서 level과 handler를 구성합니다.

```python
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
```

환경 변수도 자동으로 안전한 저장소가 아닙니다. API 키, token과 전체 환경 dict를 로그·예외·보고서에 출력하지 않습니다.

## 호환성과 지원 범위

- 지원 Python 최솟값을 문서와 검사에서 같이 고정합니다.
- 운영체제별 기능은 조건부 import나 명시적인 지원 제한으로 표현합니다.
- private 구현 세부보다 공개 진입점과 결과 계약을 검사합니다.
- deprecated API를 사용한다면 제거 시점과 대체 경로를 기록합니다.

## 자주 생기는 구조 문제

### 거대한 `utils.py`

변경 이유가 다른 함수가 모여 의존 방향이 사라집니다. 경로, 직렬화, 프로세스와 표시처럼 책임 이름으로 나눕니다.

### import 시 부작용

모듈 import만으로 파일을 만들거나 환경 변수를 바꾸지 않습니다.

### 테스트만 통과하는 경로 조작

source-level 단계 검사는 skeleton, workspace와 reference를 같은 공개 테스트에 연결하기 위해 구현 root를 명시합니다. 이 검사만으로 설치 가능성을 주장하지 않습니다. 별도의 `make package-check`는 격리 venv에 wheel을 설치하고 source root와 `PYTHONPATH` 없이 실행해 설치·console script 오류를 드러냅니다.

### 과도한 추상화

인터페이스, 팩터리와 계층을 변경 이유 없이 추가하지 않습니다. 실제로 독립적으로 바뀌는 경계를 기준으로 분리합니다.

## 연결 실습

- [command-checker 구성](../../exercises/command-checker/README.md)에서 9개 module의 허용 import 방향과 순환 부재를 AST architecture test로 확인하고, stage 1·8에서 실제 설치와 공개 타입 계약을 검사합니다.

## 완료 기준

- 한 파일을 나누는 이유를 변경 책임으로 설명합니다.
- 모듈 의존 방향이 순환하지 않습니다.
- 지원 Python 버전과 준비 명령이 고정되어 있습니다.
- 타입 힌트와 실행 시 검증을 구분합니다.
- 설치된 `command-checker`가 source 경로 주입 없이 실행됩니다.
- 저장소 전체 검증 진입점이 하나입니다.

다음은 [CLI 검사기 설계](03-cli-test-runner.md)입니다.
