# 파일, 구조화된 데이터와 CLI

## 학습 목표

이 장은 파일과 외부 입력을 검증해 명령줄 프로그램의 계약으로 바꾸는 방법을 다룹니다. 연결 실습은 [`command-checker` 4단계](../../exercises/command-checker/README.md#4단계-json-명세와-실행-시-검증)입니다.

## 선행 개념

- `pathlib`·context manager·예외 category와 JSON 문법/계약 검증의 차이

## `pathlib`로 경로 의미를 보존합니다

```python
from pathlib import Path

root = Path(__file__).resolve().parent
config = root / "fixtures" / "cases.json"
```

문자열 덧셈으로 경로를 조립하지 않습니다.

```python
path = Path("notes.txt")
path.write_text("hello\n", encoding="utf-8")
content = path.read_text(encoding="utf-8")
```

작은 설정 파일에는 편리하지만 큰 로그는 줄 단위로 처리합니다.

```python
def error_lines(path: Path):
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            if "ERROR" in line:
                yield line.rstrip("\n")
```

## 텍스트 경계를 명시합니다

파일과 프로세스 경계에서는 bytes와 str 중 하나를 선택해야 합니다.

```python
path.read_text(encoding="utf-8")
```

인코딩을 생략해 운영체제 기본값에 기대지 않습니다. 디코딩할 수 없는 입력을 대체할지 거부할지도 계약으로 정합니다.

## JSON은 파싱 뒤 다시 검증합니다

```python
import json

raw: object = json.loads(path.read_text(encoding="utf-8"))
```

JSON 형식이 맞다고 애플리케이션 계약까지 맞는 것은 아닙니다.

```python
def require_object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise SpecificationError("최상위 값은 객체여야 합니다.")
    return value
```

검증해야 할 항목:

- 최상위 형태
- 필수 필드와 알 수 없는 필드
- 각 필드의 실제 타입
- 숫자 범위와 유한성
- 중복 이름
- 경로 존재와 기준 디렉터리
- 운영체제가 허용하지 않는 NUL

Python에서 `bool`은 `int`의 하위 타입이므로 엄격한 숫자 필드에서는 별도로 제외합니다.

```python
if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
    raise SpecificationError("timeout은 숫자여야 합니다.")
```

## CSV는 `csv` 모듈에 맡깁니다

```python
import csv

with path.open("r", encoding="utf-8", newline="") as stream:
    for row in csv.DictReader(stream):
        print(row["name"])
```

쉼표로 직접 `split()`하면 따옴표, 줄바꿈과 이스케이프를 잘못 처리합니다.

## 임시 디렉터리로 작업을 격리합니다

```python
from tempfile import TemporaryDirectory

with TemporaryDirectory() as directory:
    root = Path(directory)
    output = root / "result.json"
    ...
```

테스트는 사용자의 실제 파일을 수정하지 않아야 합니다.

## 원자적 결과 교체

기존 보고서 경로에 직접 쓰면 중간 실패에서 파일이 잘릴 수 있습니다.

```text
같은 디렉터리에 임시 파일 생성
→ 전체 내용 기록
→ flush와 fsync
→ os.replace로 최종 경로 교체
```

```python
import os
import tempfile


def atomic_write_text(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
```

이 방식은 동일 파일시스템의 이름 교체를 이용해 부분 내용 노출을 줄입니다. 데이터베이스 수준의 전체 내구성을 자동 보장하는 것은 아닙니다.

## CLI는 네 채널을 계약으로 가집니다

```text
인자와 stdin
stdout
stderr
종료 상태
```

일반 규약:

- 정상 결과는 stdout
- 오류와 진단은 stderr
- 성공은 0
- 사용법·명세 오류는 별도 non-zero 상태

```python
import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="JSON 사례로 명령을 검사합니다.")
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    return parser
```

`argparse`의 타입 변환은 모든 실행 시 검증을 대신하지 않습니다. `--jobs 0` 같은 값은 파싱 뒤 계약을 확인해야 합니다.

## `main()`에서 오류를 변환합니다

```python
def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        cases = load_cases(arguments.cases)
    except SpecificationError as error:
        print(error, file=sys.stderr)
        return 2
    ...
```

파일 모듈은 사용자 메시지 형식을 몰라도 됩니다. 예외를 최종 진입점에서 진단과 종료 상태로 바꿉니다.

## 연결 실습

- [command-checker 4단계](../../exercises/command-checker/README.md#4단계-json-명세와-실행-시-검증)에서 JSON 명세, 상대 `cwd`, environment와 usage error를 검증합니다.
- 원자적 결과 교체 절은 [8단계](../../exercises/command-checker/README.md#8단계-병렬-실행과-원자적-보고서)에서 JSON·JUnit writer에 다시 적용합니다.

## 완료 기준

- 경로의 기준 디렉터리를 명시했습니다.
- 외부 JSON을 `object`로 보고 필드마다 검증합니다.
- 파일 인코딩을 지정합니다.
- 기존 결과를 부분 내용으로 바꾸지 않는 저장 절차가 있습니다.
- CLI의 stdout, stderr와 종료 상태를 구분합니다.

다음은 [외부 프로세스와 수명 관리](02-subprocess-and-process-lifecycle.md)입니다.
