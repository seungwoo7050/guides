# 프로젝트 구조, 패키징과 타입 검사

## 학습 목표

프로젝트 구조는 파일 수를 늘리기 위한 규칙이 아닙니다. 변경 이유가 다른 책임을 분리하고 의존 방향을 드러내는 도구입니다. 이 장에서는 단일 파일 Python 프로그램이 여러 모듈과 설치 가능한 패키지로 커질 때 적용할 기준을 다룹니다.

## 선행 개념

- 모듈 간 `import` 방향을 파악할 수 있어야 합니다.
- 공개 API와 내부 구현을 구분할 수 있어야 합니다.
- 타입 힌트와 실행 시 검증의 차이를 이해해야 합니다.

## 프로그램 크기에 맞는 구조 선택하기

한 번만 사용하는 30줄짜리 변환 도구라면 단일 파일로 충분할 수 있습니다.

```text
normalize-log.py
```

다음 책임이 서로 독립적으로 변경되기 시작하면 모듈 분리를 검토합니다.

```text
CLI 인자 파싱
외부 입력 검증
핵심 계산
파일·프로세스 I/O
보고서 직렬화
```

작은 패키지는 다음처럼 구성할 수 있습니다.

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

`src/` 배치는 설치하지 않은 저장소 루트가 우연히 `sys.path`에 포함되어 발생하는 잘못된 `import` 성공을 줄일 수 있습니다. 다만 모든 작은 스크립트에 이 구조를 강제할 필요는 없습니다.

## 모듈 의존 방향 정하기

공통 데이터 모델이 파일 I/O나 CLI 모듈을 `import`하면 순환 의존성이 생기기 쉽습니다.

```text
model ← parser
model ← process
model ← reports
cli → parser, runner, reports
runner → process
```

핵심 데이터와 순수 로직을 담당하는 하위 모듈이 CLI 옵션, 터미널 문구, 보고서 경로 같은 상위 정책을 알지 않도록 합니다.

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

`pyproject.toml`에는 프로젝트 메타데이터, 지원 Python 버전, 빌드 백엔드, 도구 설정을 모을 수 있습니다.

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

제3자 패키지를 사용한다면 다음 항목을 구분해야 합니다.

- 애플리케이션 실행 의존성
- 개발·테스트 의존성
- 직접 선택한 의존성과 전이 의존성
- 허용할 버전 범위와 재현 가능한 잠금 파일

매번 `pip install`로 당시의 최신 버전을 설치하면 실행 환경을 재현할 수 없습니다. 저장소에서 선택한 패키지 관리자와 잠금 파일을 기준으로 준비 명령을 고정해야 합니다.

이 가이드는 제3자 패키지를 요구하지 않습니다. `prepare.sh`는 `.guide/python/venv`만 생성하며, 실습에서 사용하는 작은 저장소 내 PEP 517 빌드 백엔드도 표준 라이브러리만 사용합니다.

다음 명령은 `workspace/`에서 wheel을 만든 뒤 임시 가상 환경에 설치합니다. 이후 저장소 밖의 작업 디렉터리와 빈 `PYTHONPATH`에서 메타데이터, `py.typed`, 콘솔 스크립트, 종단 간 실행을 확인합니다.

```sh
make package-check EXERCISE_IMPL=workspace
```

## 타입 검사를 적용할 위치

타입 힌트는 공개 함수와 여러 모듈이 공유하는 데이터 모델부터 추가합니다.

```python
from collections.abc import Sequence


def run_cases(
    cases: Sequence[Case],
    command: Sequence[str],
    jobs: int,
) -> tuple[Result, ...]:
    ...
```

다음 상황에서 타입 힌트의 가치가 큽니다.

- `None` 가능 여부가 중요한 경우
- 여러 모듈이 같은 데이터 모델을 공유하는 경우
- 콜백이나 `Protocol`을 전달하는 경우
- `dict` 구조가 커져 이름 있는 타입이 필요한 경우

외부 JSON에 곧바로 `cast(Case, raw)`를 적용해서는 안 됩니다. `cast()`는 정적 타입 검사기에만 정보를 제공하며 실행 시 값을 검증하지 않습니다.

실습에서는 제3자 도구가 없어도 다음 명령으로 공개 타입 형식을 검사합니다.

```sh
make type-check EXERCISE_IMPL=workspace
```

이 검사는 AST를 분석해 함수 인자와 반환값의 타입 어노테이션, `dataclass` 필드의 타입 어노테이션, 공개 API의 `Any` 사용 금지, `py.typed` 포함 여부를 확인합니다. 값의 흐름과 타입 호환성까지 분석하는 `mypy`나 `pyright`를 대체하지는 않습니다. 이런 의미 기반 타입 검사기를 추가한다면 저장소의 공통 검증 명령에 연결해야 합니다.

## 값 객체의 가변성 제한하기

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Result:
    name: str
    passed: bool
    failures: tuple[str, ...]
```

불변 데이터는 스레드 사이에서 공유하기 쉽고, 보고서 생성 코드가 실행 결과를 바꾸는 문제를 막아 줍니다.

다만 `frozen=True`인 데이터 클래스 안에 가변 `list`나 `dict`를 넣으면 그 내부 값은 여전히 변경할 수 있습니다. 필드 타입도 가능한 한 불변 구조로 구성합니다.

## `Protocol`로 필요한 동작만 표현하기

```python
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol


class Reporter(Protocol):
    def write(self, path: Path, results: Sequence[Result]) -> None:
        ...
```

테스트에서는 이 인터페이스를 만족하는 작은 가짜 객체를 사용할 수 있습니다. 그러나 구체 구현이 하나뿐이고 교체할 필요도 없다면 추상화를 미리 만들지 않습니다.

## 품질 도구 선택하기

표준 라이브러리 기반 `make type-check`와 설치 검증은 이 실습의 필수 항목입니다. 실제 프로젝트에서는 필요에 따라 다음 도구를 추가할 수 있습니다.

- `ruff`: 린트와 코드 포맷
- `mypy` 또는 `pyright`: 정적 타입 검사
- `pytest`: `fixture`와 매개변수화가 많은 테스트
- `coverage.py`: 테스트가 실행한 코드 경로 측정
- `tox` 또는 `nox`: 여러 Python 환경에서 반복 검증

도구를 많이 추가하는 것보다 모든 개발자가 같은 방식으로 실행할 수 있는 단일 검증 진입점을 먼저 마련해야 합니다.

```sh
./verify.sh
```

제3자 도구를 추가한다면 `prepare.sh`가 저장소 전용 환경에 고정 버전으로 설치하고, `verify.sh`는 그 환경의 도구만 사용해야 합니다.

## 로그와 비밀 정보

라이브러리 모듈이 전역 로깅 설정을 임의로 바꾸지 않도록 합니다. 로그 레벨과 핸들러는 최종 애플리케이션 진입점에서 설정합니다.

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(message)s",
)
```

환경 변수에 저장했다고 해서 값이 자동으로 안전해지는 것은 아닙니다. API 키, 토큰, 전체 환경 변수 `dict`를 로그·예외·보고서에 출력하지 않습니다.

## 호환성과 지원 범위

- 최소 지원 Python 버전을 문서와 자동 검사에 함께 고정합니다.
- 운영체제별 기능은 조건부 `import`나 명시적인 지원 제한으로 표현합니다.
- 내부 구현 세부사항보다 공개 진입점과 결과 형식을 테스트합니다.
- 사용 중단 예정 API를 사용한다면 제거 예정 시점과 대체 방법을 기록합니다.

## 자주 발생하는 구조 문제

### 거대한 `utils.py`

변경 이유가 다른 함수가 한 파일에 모이면 의존 방향과 책임이 보이지 않습니다. 경로 처리, 직렬화, 프로세스 실행, 출력 형식처럼 실제 책임에 따라 모듈을 나눕니다.

### `import` 시 부작용

모듈을 `import`하는 것만으로 파일을 만들거나 환경 변수를 변경하지 않습니다.

### 테스트에서만 통과하는 경로 조작

소스 코드 수준의 단계별 테스트는 `skeleton/`, `workspace/`, `reference/`에 같은 테스트를 적용하기 위해 구현 루트를 명시적으로 지정합니다. 이 테스트만으로 패키지가 실제로 설치 가능하다고 판단해서는 안 됩니다.

별도의 `make package-check`는 격리된 가상 환경에 wheel을 설치하고, 소스 루트와 `PYTHONPATH` 없이 실행해 설치 구성과 콘솔 스크립트 오류를 찾습니다.

### 과도한 추상화

인터페이스, 팩터리, 계층을 실제 변경 요구 없이 추가하지 않습니다. 독립적으로 바뀌는 책임이 확인될 때 분리합니다.

## 연결 실습

- [command-checker 1단계](../../exercises/command-checker/README.md#1단계-패키지와-진입점)에서 제공된 `__main__.py`, `_command_checker_build.py`, `pyproject.toml`, `py.typed`가 `cli.main`을 외부 진입점으로 노출하는 방식을 확인합니다.
- [command-checker 8단계](../../exercises/command-checker/README.md#8단계-병렬-실행과-원자적-보고서)에서 9개 모듈의 허용된 `import` 방향, 공개 타입, 일치하는 버전 메타데이터, 실제 설치 결과를 최종 확인합니다.

## 완료 기준

- 단일 파일을 여러 모듈로 나누는 이유를 변경 책임으로 설명할 수 있습니다.
- 모듈 의존 방향에 순환이 없습니다.
- 지원 Python 버전과 환경 준비 명령이 고정되어 있습니다.
- 타입 힌트와 실행 시 검증을 구분합니다.
- 설치된 `command-checker`가 소스 경로 주입 없이 실행됩니다.
- 저장소 전체를 확인하는 검증 진입점이 하나로 정리되어 있습니다.

다음은 [CLI 검사기 설계](03-cli-test-runner.md)입니다.
