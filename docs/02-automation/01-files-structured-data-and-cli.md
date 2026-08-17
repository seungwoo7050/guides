# 파일, 구조화된 데이터와 CLI

## 학습 목표

이 장에서는 파일과 외부 입력을 검증해 명령줄 프로그램이 사용할 내부 데이터로 변환하는 방법을 다룹니다. 연결 실습은 [`command-checker` 4단계](../../exercises/command-checker/README.md#4단계-json-명세와-실행-시-검증)입니다.

## 선행 개념

- `pathlib`로 경로를 다룰 수 있어야 합니다.
- 컨텍스트 관리자로 파일을 열고 닫을 수 있어야 합니다.
- 예외 유형을 구분할 수 있어야 합니다.
- JSON 문법 검증과 애플리케이션 데이터 검증이 다른 작업임을 이해해야 합니다.

## `pathlib`로 경로 의미 보존하기

```python
from pathlib import Path

root = Path(__file__).resolve().parent
config = root / "fixtures" / "cases.json"
```

경로를 문자열 덧셈으로 조립하지 않습니다. `Path`를 사용하면 운영체제별 경로 구분자를 직접 처리하지 않아도 되고, 경로가 문자열 데이터와 구분됩니다.

```python
path = Path("notes.txt")
path.write_text("hello\n", encoding="utf-8")
content = path.read_text(encoding="utf-8")
```

`read_text()`와 `write_text()`는 작은 설정 파일을 처리할 때 편리합니다. 큰 로그 파일은 한 번에 읽지 말고 줄 단위로 처리합니다.

```python
from collections.abc import Iterator


def error_lines(path: Path) -> Iterator[str]:
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            if "ERROR" in line:
                yield line.rstrip("\n")
```

## 텍스트와 바이트 경계 명시하기

파일이나 프로세스에서 데이터를 읽을 때는 `bytes`와 `str` 중 어떤 형태로 처리할지 정해야 합니다.

```python
content = path.read_text(encoding="utf-8")
```

텍스트를 읽을 때 인코딩을 생략해 운영체제 기본값에 의존하지 않습니다. 잘못된 바이트를 만나면 오류로 처리할지 대체 문자로 바꿀지도 프로그램의 입력 규칙으로 정합니다.

## JSON은 파싱한 뒤 다시 검증하기

```python
import json

raw: object = json.loads(path.read_text(encoding="utf-8"))
```

JSON 문법이 올바르다는 사실은 애플리케이션이 요구하는 데이터 구조까지 올바르다는 뜻이 아닙니다.

```python
def require_object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise SpecificationError("최상위 값은 객체여야 합니다.")
    return value
```

외부 JSON에서 일반적으로 확인해야 할 항목은 다음과 같습니다.

- 최상위 값의 형태
- 필수 필드와 허용하지 않은 필드
- 각 필드의 실제 타입
- 숫자의 범위와 유한성
- 중복 이름
- 경로의 존재 여부와 기준 디렉터리
- 운영체제 API가 허용하지 않는 NUL 문자

Python에서 `bool`은 `int`의 하위 타입입니다. 따라서 정수나 실수를 엄격하게 받아야 하는 필드에서는 `bool`을 별도로 제외해야 합니다.

```python
if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
    raise SpecificationError("timeout은 숫자여야 합니다.")
```

## CSV는 `csv` 모듈로 처리하기

```python
import csv

with path.open("r", encoding="utf-8", newline="") as stream:
    for row in csv.DictReader(stream):
        print(row["name"])
```

CSV 한 줄을 쉼표로 직접 `split()`하면 따옴표 안의 쉼표, 여러 줄 필드, 이스케이프 규칙을 올바르게 처리할 수 없습니다. CSV 형식은 표준 라이브러리의 `csv` 모듈에 맡깁니다.

## 임시 디렉터리로 작업 격리하기

```python
from pathlib import Path
from tempfile import TemporaryDirectory

with TemporaryDirectory() as directory:
    root = Path(directory)
    output = root / "result.json"
    ...
```

테스트나 중간 작업은 사용자의 실제 파일을 수정하지 않도록 임시 디렉터리에서 수행합니다. 컨텍스트가 끝나면 임시 디렉터리와 내부 파일이 정리됩니다.

## 원자적 결과 교체

기존 보고서 파일에 직접 덮어쓰면 기록 도중 실패했을 때 파일이 일부만 남을 수 있습니다. 같은 파일 시스템 안에서 다음 순서를 사용하면 불완전한 결과가 최종 경로에 노출되는 일을 줄일 수 있습니다.

```text
최종 파일과 같은 디렉터리에 임시 파일을 만든다
→ 전체 내용을 기록한다
→ flush와 fsync로 파일 내용을 반영한다
→ os.replace로 최종 경로를 교체한다
```

```python
import os
import tempfile
from pathlib import Path


def atomic_write_text(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
    )
    temporary = Path(name)

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
            newline="",
        ) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
```

`os.replace()`는 같은 파일 시스템 안에서 완성된 임시 파일을 최종 이름으로 교체합니다. 이 방식은 중간 내용이 보이는 문제를 줄이지만, 디렉터리 항목까지 포함한 데이터베이스 수준의 트랜잭션이나 모든 장애 상황에서의 내구성을 자동으로 보장하지는 않습니다.

## CLI에서 관찰해야 할 요소

명령줄 프로그램의 외부 동작은 다음 다섯 요소로 나누어 확인합니다.

```text
명령줄 인자
stdin
stdout
stderr
종료 상태
```

일반적인 규칙은 다음과 같습니다.

- 정상 결과는 `stdout`에 출력한다.
- 오류와 진단 메시지는 `stderr`에 출력한다.
- 성공은 종료 상태 0으로 나타낸다.
- 사용법 오류나 입력 명세 오류는 별도의 0이 아닌 종료 상태로 나타낸다.

```python
import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="JSON 사례로 명령을 검사합니다."
    )
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    return parser
```

`argparse`가 타입을 변환해 준다고 해서 모든 값이 유효해지는 것은 아닙니다. 예를 들어 `--jobs 0`은 정수로 파싱되지만 허용 가능한 작업자 수는 아니므로 파싱 후 추가 검증이 필요합니다.

## `main()`에서 예외를 사용자 오류로 변환하기

```python
import sys
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        cases = load_cases(arguments.cases)
    except SpecificationError as error:
        print(error, file=sys.stderr)
        return 2
    ...
```

파일 파싱 모듈이나 검증 모듈은 터미널 출력 형식까지 알 필요가 없습니다. 하위 모듈은 의미 있는 예외를 발생시키고, 최상위 CLI 진입점에서 오류 메시지와 종료 상태로 변환합니다.

## 연결 실습

- [command-checker 4단계](../../exercises/command-checker/README.md#4단계-json-명세와-실행-시-검증)에서 JSON 명세, 상대 `cwd`, 환경 변수, 사용법 오류를 검증합니다.
- 이 문서의 원자적 파일 교체 방식은 [8단계](../../exercises/command-checker/README.md#8단계-병렬-실행과-원자적-보고서)에서 JSON·JUnit 보고서를 저장할 때 다시 사용합니다.

## 완료 기준

- 상대 경로를 어떤 디렉터리 기준으로 해석하는지 명시했습니다.
- 외부 JSON을 `object`로 받은 뒤 필드별로 실행 시 검증합니다.
- 텍스트 파일의 인코딩을 명시합니다.
- 기존 결과 파일을 불완전한 내용으로 덮어쓰지 않는 저장 절차가 있습니다.
- CLI의 인자, 표준 입력, 표준 출력, 표준 오류, 종료 상태를 구분합니다.

다음은 [외부 프로세스와 수명 관리](02-subprocess-and-process-lifecycle.md)입니다.
