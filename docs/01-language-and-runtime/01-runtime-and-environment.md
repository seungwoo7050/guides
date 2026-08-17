# 실행 환경과 모듈

## 학습 목표

이 장을 마치면 다음 개념을 구분할 수 있어야 합니다.

- Python 인터프리터, 스크립트, 모듈
- 파일 경로를 지정한 실행과 `-m`을 사용한 모듈 실행
- `import`할 수 있는 코드와 프로그램 진입점
- 현재 작업 디렉터리와 소스 파일이 있는 디렉터리
- 시스템 Python과 프로젝트 가상 환경

연결 실습은 [`command-checker` 1단계](../../exercises/command-checker/README.md#1단계-패키지와-진입점)입니다.

## 선행 개념

- 터미널에서 `stdout`, `stderr`, 종료 상태를 확인할 수 있어야 합니다.
- 현재 작업 디렉터리와 파일이 저장된 위치가 다를 수 있음을 이해해야 합니다.

## Python이 적합한 작업

Python은 파일, 데이터, 운영체제 기능, 외부 프로그램을 짧은 코드로 연결하는 데 적합합니다.

- 여러 입력으로 실행 파일을 반복 검증한다.
- 로그와 JSON 데이터를 정규화하거나 비교한다.
- 디렉터리를 순회하며 파일을 일괄 처리한다.
- 작은 기준 모델을 만들어 복잡한 구현과 결과를 대조한다.
- 빌드·배포 결과를 점검하는 도구를 만든다.

매우 짧은 지연 시간, 고정된 메모리 배치, 인터프리터를 포함할 수 없는 배포 환경이 핵심 요구사항이라면 다른 언어가 더 적합할 수 있습니다. 언어는 익숙함보다 필요한 실행 특성에 맞춰 선택해야 합니다.

## 첫 프로그램 실행

다음 파일을 만듭니다.

```python
# hello.py
print("안녕하세요, Python")
```

파일 경로를 지정해 실행합니다.

```sh
python3 hello.py
```

가장 단순한 개발 과정은 다음과 같습니다.

```text
파일을 수정한다
→ 인터프리터로 실행한다
→ stdout, stderr, 종료 상태를 확인한다
→ 실패한 줄과 입력을 기록한다
→ 수정한 뒤 다시 실행한다
```

Python 구현은 실행 과정에서 소스 코드를 바이트코드로 컴파일할 수 있지만, 일반적인 개발 과정에서는 별도의 컴파일 명령이 필요하지 않습니다. 그렇더라도 문법 분석, 모듈 탐색, `import` 과정에서 오류가 발생할 수 있습니다.

## 스크립트 실행과 모듈 실행

다음 패키지 구조를 가정합니다.

```text
project/
└── checker/
    ├── __init__.py
    └── __main__.py
```

패키지는 다음과 같이 모듈로 실행할 수 있습니다.

```sh
python3 -m checker
```

`python3 -m checker`는 현재 `sys.path`에서 `checker` 패키지를 찾은 뒤 `checker/__main__.py`를 실행합니다. 패키지 내부에서 상대 `import`를 사용하는 프로그램은 파일 하나를 직접 실행하는 방식보다 `-m`으로 실행하는 편이 안전합니다.

```python
# checker/__main__.py
from .cli import main

raise SystemExit(main())
```

## 진입점을 함수로 분리하기

```python
# checker/cli.py
from __future__ import annotations

from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    print("검사를 시작합니다.")
    return 0
```

프로세스 종료는 `__main__.py`에서 처리하고, 실제 동작은 정수 종료 상태를 반환하는 함수로 분리합니다.

```python
raise SystemExit(main())
```

이 구조에는 다음과 같은 장점이 있습니다.

- 테스트에서 `main(["--help"])`처럼 인자를 직접 전달할 수 있다.
- 모듈을 `import`해도 프로그램이 자동으로 실행되지 않는다.
- 종료 상태를 명시적인 반환값으로 검사할 수 있다.

라이브러리 모듈의 최상위 코드에서 파일을 삭제하거나 네트워크 요청을 보내는 등 큰 부작용을 일으키지 않습니다. `import`는 모듈을 불러오는 작업이지 프로그램 실행을 요청하는 신호가 아닙니다.

## `__name__`의 의미

파일을 직접 실행하면 `__name__`에는 `"__main__"`이 들어갑니다. 다른 모듈에서 `import`하면 실제 모듈 이름이 들어갑니다.

```python
def main() -> int:
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

작은 단일 파일 프로그램에는 이 구조로 충분합니다. 프로그램이 패키지로 커지면 `__main__.py`와 `cli.py`를 분리하는 편이 책임을 파악하기 쉽습니다.

## 현재 작업 디렉터리와 소스 파일 위치

다음 두 경로는 서로 다른 의미를 가집니다.

```python
from pathlib import Path

working_directory = Path.cwd()
source_directory = Path(__file__).resolve().parent
```

- 사용자가 전달한 상대 경로: 일반적으로 현재 작업 디렉터리를 기준으로 해석
- 소스 코드와 함께 배포한 `fixture`나 기본 설정: 일반적으로 `__file__`을 기준으로 해석

어떤 디렉터리를 기준으로 삼는지 문서와 오류 메시지에 명시해야 합니다. 테스트가 저장소 루트에서만 우연히 통과한다면 경로 기준이 코드에 드러나지 않은 상태일 수 있습니다.

## 가상 환경과 인터프리터 확인

프로젝트마다 독립된 실행 환경을 만듭니다.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -c 'import sys; print(sys.executable)'
python --version
```

위 활성화 명령은 POSIX 셸용입니다. 이 저장소가 공식 지원하는 macOS·Linux 환경에서 `prepare.sh`는 `.guide/python/venv`를 생성합니다. 이 가이드는 제3자 패키지를 요구하지 않으므로 네트워크를 통한 패키지 설치는 수행하지 않습니다.

Python을 하위 프로세스로 다시 실행할 때는 현재 인터프리터 경로를 재사용합니다.

```python
import subprocess
import sys

subprocess.run([sys.executable, "-m", "checker"], check=False)
```

문자열 `"python3"`을 하드코딩하는 것보다 현재 가상 환경과 Python 버전을 정확하게 유지할 수 있습니다.

## 오류 유형부터 구분하기

| 실패 | 의미 | 먼저 확인할 항목 |
|---|---|---|
| `SyntaxError` | 소스 코드를 문법에 맞게 해석할 수 없음 | 표시된 줄과 바로 앞 줄 |
| `ModuleNotFoundError` | 모듈 탐색 경로나 실행 환경에 문제가 있음 | 실행 위치, `-m` 사용 여부, `sys.executable` |
| `NameError` | 현재 범위에 해당 이름이 없음 | 철자, 분기, `import` |
| `TypeError` | 연산이나 함수 호출에 맞지 않는 타입을 사용함 | 실제 타입과 전달한 인자 |
| 0이 아닌 종료 상태 | 프로그램이 오류를 처리한 뒤 실패 상태로 종료함 | `stderr`와 입력 규칙 |

오류 메시지를 지우지 말고 재현 입력과 함께 보존합니다.

## 연결 실습

- [command-checker 1단계](../../exercises/command-checker/README.md#1단계-패키지와-진입점)에서 제공된 `__main__.py`와 패키징 뼈대가 `cli.main`으로 연결되는 방식을 확인합니다.
- `workspace/command_checker/cli.py`에서 도움말과 사용법 오류가 각각 올바른 출력 스트림과 종료 상태를 사용하도록 구현합니다.

## 완료 기준

- 파일 실행과 모듈 실행의 차이를 설명할 수 있습니다.
- 모듈을 불러오는 동작과 프로그램 실행을 분리했습니다.
- `main()`이 정수 종료 상태를 반환합니다.
- 테스트에서 명령줄 인자를 직접 전달할 수 있습니다.
- 현재 사용 중인 Python 인터프리터 경로를 확인할 수 있습니다.

다음은 [객체와 컬렉션](02-objects-and-collections.md)입니다.
