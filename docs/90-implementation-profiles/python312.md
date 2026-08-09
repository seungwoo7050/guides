# Python 3.12 구현 프로필

이 프로필은 core 개념을 가장 작은 실행 코드로 옮기기 위한 기준입니다. Python 자체의 AST나 bytecode를 compiler 답안으로 사용하는 것이 아니라, Python 표준 라이브러리로 Mica phase를 구현합니다.

## 환경

- Python 3.12 이상
- 외부 package 없음
- `python -m unittest` 또는 표준 `doctest` 선택
- POSIX shell/Make는 저장소 검증에만 사용

## 권장 표현

### Immutable source와 node

```python
@dataclass(frozen=True, slots=True)
class Span:
    source_id: int
    start: int
    end: int
```

AST도 가능하면 frozen dataclass로 만들고 semantic fact는 side table에 둡니다. Mutable cache를 node에 숨기지 않습니다.

### Sum type

```python
Expr = IntExpr | NameExpr | BinaryExpr | CallExpr | ErrorExpr
```

`match`에서 모든 variant를 처리하고 default branch는 internal error로 둡니다. Python runtime은 exhaustiveness를 강제하지 않으므로 test가 필요합니다.

### Enum

TokenKind, diagnostic severity와 opcode는 `Enum`/`IntEnum`을 사용할 수 있습니다. Serialized value는 enum 이름 또는 명시한 stable integer를 사용하고 선언 순서에 우연히 의존하지 않습니다.

## Source byte와 string

Core span은 UTF-8 byte offset입니다. Python `str` index는 Unicode code point 단위이므로 둘을 섞지 않습니다.

선택:

1. source를 `bytes`로 lex하고 필요할 때 UTF-8 decode
2. `str`을 사용하되 code point index↔byte offset table 유지

Mica skeleton은 source 원문을 UTF-8 bytes와 decoded text 둘 다 보관하는 방향을 제안합니다. 잘못된 UTF-8 정책을 명시합니다.

## Error handling

사용자 오류는 exception control flow에 맡기지 않고 diagnostic list에 추가합니다. Internal invariant에는 custom exception 또는 assertion을 사용합니다.

```python
class InternalCompilerError(RuntimeError): ...
```

`except Exception`으로 모두 사용자 오류로 바꾸지 않습니다. CLI boundary에서만 internal error를 code 2로 번역합니다.

## Parser recursion

Recursive descent는 Python recursion limit에 도달할 수 있습니다.

- nesting depth를 명시적으로 검사
- expression loop는 iterative Pratt loop
- arbitrary invalid input에 timeout test
- recursion limit을 전역으로 크게 올려 문제를 숨기지 않음

## Runtime value

Python `bool`은 `int`의 subclass이므로 `isinstance(True, int)`가 true입니다. Target value를 tagged dataclass/enum으로 표현하거나 exact type check를 사용합니다.

Python integer는 arbitrary precision이므로 i64 range와 division policy를 직접 구현합니다.

## Call stack

Tree-walk interpreter를 host Python function recursion으로 구현할 수 있지만 target call-depth, stack trace와 cancellation이 host에 묶입니다. Capstone 핵심에서는 허용하되 명시적 depth counter와 target frame record를 유지합니다. VM 경로에서는 list frame stack을 사용합니다.

## Determinism

- diagnostic과 symbol dump 정렬
- set/dict iteration을 public output 순서로 직접 사용하지 않음
- temp/node id를 invocation-local counter로 생성
- path와 timestamp normalization
- random seed 출력

## Package 구조

```text
pyproject.toml
src/mica/
  __init__.py
  __main__.py
  driver.py
  source.py
  diagnostic.py
  lexer.py
  parser.py
  ...
tests/
```

Editable install 없이도 `PYTHONPATH=src python -m mica`로 실행할 수 있게 하면 capstone runner가 단순합니다.

## Test

- dataclass equality에만 의존하지 않고 public dump/schema 확인
- `subprocess.run(..., timeout=...)`로 CLI 종료와 channel 검사
- temporary directory 사용
- expected stdout/stderr 분리
- hash seed를 바꿔 deterministic output 확인 선택

## Python 표준 모듈 활용 경계

공부할 수 있는 참고 대상:

- `tokenize`: Python lexical tooling의 예
- `ast`: AST와 source location API
- `symtable`: scope 분석 결과
- `dis`: Python bytecode 관찰

Mica grammar와 semantics를 Python parser/compiler에 위임하지 않습니다. 이 모듈은 다른 언어 구현의 public interface를 관찰하는 자료입니다.
