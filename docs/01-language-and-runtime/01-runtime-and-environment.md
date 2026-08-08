# 실행 환경과 모듈

## 학습 목표

이 장을 마치면 다음을 구분할 수 있어야 합니다.

- Python 인터프리터, 스크립트와 모듈
- 파일 경로 실행과 `-m` 모듈 실행
- import 가능한 코드와 프로그램 진입점
- 현재 작업 디렉터리와 소스 파일 위치
- 시스템 Python과 프로젝트 가상환경

연결 실습은 [`command-checker` 1단계](../../exercises/command-checker/README.md#1단계-패키지와-진입점)입니다.

## 선행 개념

- 터미널에서 stdout·stderr·exit status를 확인하고 cwd와 파일 위치를 구분하기

## Python이 잘 맞는 작업

Python은 파일, 데이터, 운영체제와 외부 프로그램을 짧은 코드로 연결하는 데 강합니다.

- 여러 입력으로 실행 파일을 반복 검증한다.
- 로그와 JSON을 정규화하거나 비교한다.
- 디렉터리를 순회하며 일괄 작업한다.
- 작은 참조 모델을 만들어 복잡한 구현과 대조한다.
- 빌드·배포 결과를 점검하는 도구를 만든다.

매우 낮은 지연 시간, 고정된 메모리 배치, 인터프리터를 둘 수 없는 배포 환경이 핵심이라면 다른 언어가 더 적합할 수 있습니다. 언어 선택은 익숙함보다 실행 계약을 기준으로 합니다.

## 첫 실행 반복

다음 파일을 만듭니다.

```python
# hello.py
print("안녕하세요, Python")
```

실행합니다.

```sh
python3 hello.py
```

가장 작은 개발 반복은 다음과 같습니다.

```text
파일을 수정한다
→ 인터프리터로 실행한다
→ stdout, stderr와 종료 상태를 확인한다
→ 실패한 줄과 입력을 고정한다
→ 다시 실행한다
```

Python은 실행 전에 소스를 바이트코드로 변환할 수 있지만, 일반적인 개발자는 별도 컴파일 명령을 먼저 실행하지 않습니다. 그렇다고 문법 오류와 import 오류가 사라지는 것은 아닙니다.

## 스크립트 실행과 모듈 실행

다음 구조를 생각합니다.

```text
project/
└── checker/
    ├── __init__.py
    └── __main__.py
```

패키지를 모듈로 실행합니다.

```sh
python3 -m checker
```

`python3 -m checker`는 import 규칙으로 `checker`를 찾은 뒤 `checker/__main__.py`를 실행합니다. 패키지 내부 상대 import가 있는 프로그램은 파일 하나를 직접 실행하는 방식보다 `-m`이 안정적입니다.

```python
# checker/__main__.py
from .cli import main

raise SystemExit(main())
```

## 진입점을 함수로 분리합니다

```python
# checker/cli.py
from __future__ import annotations

from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    print("검사를 시작합니다.")
    return 0
```

프로세스를 끝내는 책임은 `__main__.py`에 두고, 실제 정책은 반환값이 있는 함수에 둡니다.

```python
raise SystemExit(main())
```

이 구조는 다음을 가능하게 합니다.

- 테스트에서 `main(["--help"])`처럼 인자를 주입한다.
- import만 했을 때 프로그램이 자동 실행되지 않는다.
- 종료 상태를 명시적인 값으로 검사한다.

라이브러리 모듈의 최상위에서 파일을 지우거나 네트워크 요청을 보내는 것처럼 큰 부작용을 실행하지 않습니다. import는 코드 재사용과 검사 단계이기도 합니다.

## `__name__`의 의미

파일을 직접 실행하면 `__name__`은 `"__main__"`입니다. import하면 모듈 이름이 들어갑니다.

```python
def main() -> int:
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

작은 단일 파일에서는 이 형태가 충분합니다. 패키지로 성장하면 `__main__.py`와 `cli.py`를 분리하는 편이 명확합니다.

## 현재 작업 디렉터리와 파일 위치

다음 두 경로는 다릅니다.

```python
from pathlib import Path

working_directory = Path.cwd()
source_directory = Path(__file__).resolve().parent
```

- 사용자가 전달한 상대 경로: 보통 현재 작업 디렉터리 기준
- 소스 옆 fixture나 내장 설정: 보통 `__file__` 기준

어느 기준인지 문서와 오류 메시지에 드러내야 합니다. 테스트가 우연히 저장소 루트에서만 통과한다면 경로 계약이 숨겨져 있을 수 있습니다.

## 가상환경과 인터프리터 확인

프로젝트별 실행 환경을 분리합니다.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -c 'import sys; print(sys.executable)'
python --version
```

이 저장소의 `prepare.sh`는 `.guide/python/venv`를 만듭니다. 제3자 패키지를 요구하지 않으므로 네트워크 설치는 수행하지 않습니다.

외부 Python 프로세스를 다시 실행할 때는 현재 인터프리터를 재사용합니다.

```python
import subprocess
import sys

subprocess.run([sys.executable, "-m", "checker"], check=False)
```

문자열 `"python3"`보다 가상환경과 버전을 정확히 보존합니다.

## 오류를 먼저 분류합니다

| 실패 | 의미 | 첫 확인 |
|---|---|---|
| `SyntaxError` | 소스를 해석할 수 없음 | 표시된 줄과 그 앞 줄 |
| `ModuleNotFoundError` | import 경로 또는 환경 문제 | 실행 위치, `-m`, `sys.executable` |
| `NameError` | 현재 범위에 이름이 없음 | 철자, 분기, import |
| `TypeError` | 연산 계약과 값 종류가 맞지 않음 | 실제 타입과 호출 인자 |
| 종료 상태만 비정상 | 프로그램이 오류를 처리해 종료함 | stderr와 입력 계약 |

오류 메시지를 지우기보다 재현 입력과 함께 보존합니다.

## 연결 실습

- [command-checker 1단계](../../exercises/command-checker/README.md)에서 import와 `python -m` 진입점, help/usage 채널을 확인합니다.

## 완료 기준

- 파일 실행과 모듈 실행의 차이를 설명할 수 있습니다.
- import와 프로그램 실행을 분리했습니다.
- `main()`이 정수 종료 상태를 반환합니다.
- 테스트에서 인자를 주입할 수 있습니다.
- 현재 사용하는 인터프리터 경로를 확인할 수 있습니다.

다음은 [객체와 컬렉션](02-objects-and-collections.md)입니다.
