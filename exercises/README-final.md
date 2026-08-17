# data-report

CSV 또는 JSON으로 저장된 수치 데이터를 읽어 검증하고 category별 합계와 전체 합계를 생성하는 standalone CLI application입니다.

Python 개발 진입 전에 필요한 기본 구현 경계를 하나의 작은 project에서 연결합니다.

- package와 module 실행
- immutable data model
- CSV/JSON parsing
- 외부 입력 validation
- deterministic aggregation
- text/JSON rendering
- CLI argument boundary
- file output
- project-local tests
- installable console script

`subprocess`, concurrency, network, database는 의도적으로 범위에서 제외합니다.

## Requirements

- Python 3.12+
- runtime dependency 없음

## Input

CSV는 정확히 `category,amount` header를 사용합니다.

```csv
category,amount
books,12.50
games,30
books,7.50
```

JSON은 같은 field를 가진 object 배열을 사용합니다.

```json
[
  {"category": "books", "amount": "12.50"},
  {"category": "games", "amount": 30},
  {"category": "books", "amount": "7.50"}
]
```

`category`는 앞뒤 공백을 제거한 뒤 비어 있지 않아야 합니다. `amount`는 유한한 decimal number여야 합니다. 집계에는 `Decimal`을 사용합니다.

## Usage

source tree에서 바로 실행할 수 있습니다.

```sh
python -m data_report examples/sales.csv
```

기본 출력은 text입니다.

```text
category  count  total
books         2  20.00
games         2  45.25
----------------------
TOTAL         4  65.25
```

JSON 출력:

```sh
python -m data_report examples/sales.csv --format json
```

파일 저장:

```sh
python -m data_report examples/sales.csv --format json --output report.json
```

입력 형식은 `.csv`와 `.json` 확장자로 판별합니다. 지원하지 않는 확장자, 잘못된 schema, 유효하지 않은 `amount`, 파일 I/O 실패는 stderr에 diagnostic을 출력하고 exit status `2`를 반환합니다.

## Installation

```sh
python -m pip install .
data-report examples/sales.csv
```

## Tests

```sh
python -m unittest discover -s tests -v
```

## Architecture

| Component | Responsibility |
|---|---|
| `model.py` | 검증된 `Record`, category 집계값, 전체 `Report` |
| `loaders.py` | CSV/JSON 외부 입력을 `Record`로 변환 |
| `aggregation.py` | category별 deterministic aggregation |
| `rendering.py` | 동일한 `Report`를 text/JSON으로 표현 |
| `cli.py` | argument parsing, filesystem I/O, exit policy |
| `tests/test_data_report.py` | parsing부터 CLI까지 project contract 검증 |

## Implementation Order

| Order | Responsibility | Primary anchor |
|---:|---|---|
| 1 | Package and console entrypoint boundary | `pyproject.toml`, `data_report/__main__.py` |
| 2 | Immutable record and report model | `data_report/model.py` |
| 3 | CSV/JSON validation boundary | `data_report/loaders.py` |
| 4 | Deterministic category aggregation | `data_report/aggregation.py` |
| 5 | Text and JSON rendering | `data_report/rendering.py` |
| 6 | CLI composition and filesystem boundary | `data_report/cli.py` |
| 7 | Project contract verification | `tests/test_data_report.py` |

## Scope

이 project는 작은 local dataset의 batch report 생성만 다룹니다.

포함하지 않는 범위:

- nested JSON schema
- streaming input
- spreadsheet format
- database
- network I/O
- subprocess
- concurrency
- plugin system

범위를 넓히기보다 Python의 실행 구조, 데이터 경계, 예외 처리, 테스트와 packaging을 명확히 연결하는 데 목적이 있습니다.
