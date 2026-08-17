# data-report

CSV 또는 JSON으로 저장된 수치 데이터를 읽고 category별 합계를 생성하는 standalone CLI application입니다.

이 프로젝트는 Python 개발에 진입하기 전에 필요한 기본 구현 경계를 하나의 작은 project에서 연결하는 것을 목표로 합니다.

## Purpose

초기 범위에서는 다음 흐름을 구현합니다.

```text
CSV / JSON input
→ validation
→ immutable data model
→ aggregation
→ report output
```

`subprocess`, concurrency, network, database 같은 후속 주제는 포함하지 않습니다.

## Planned Interface

```sh
data-report INPUT [--format text|json] [--output PATH]
```

입력 파일은 다음 두 형식을 대상으로 합니다.

- `.csv`
- `.json`

각 record는 다음 값을 가집니다.

- `category`
- `amount`

## Initial Architecture

프로젝트는 다음 책임을 기준으로 구성합니다.

- package and console entrypoint
- immutable record model
- CSV/JSON validation
- category aggregation
- text/JSON rendering
- CLI composition
- project-local verification

## Requirements

- Python 3.12+
- runtime dependency 없음

## Scope

이 프로젝트는 작은 local dataset의 batch report 생성만 다룹니다.

다음 영역은 의도적으로 제외합니다.

- subprocess
- concurrency
- network I/O
- database
- streaming input
- spreadsheet format

구현이 완료되면 실제 CLI 사용법, 입력 contract, architecture, tests와 Implementation Order를 이 문서에 반영합니다.
