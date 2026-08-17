# 함수, 예외 처리와 타입 검증

## 학습 목표

함수는 코드를 줄이는 수단에 그치지 않습니다. 어떤 입력을 받고, 무엇을 반환하며, 어떤 조건에서 실패하는지를 정의하는 단위입니다. 이 장은 [`command-checker` 3단계](../../exercises/command-checker/README.md#3단계-비교와-실패-표현)와 연결됩니다.

## 선행 개념

- 객체의 가변성과 값의 동등성을 구분할 수 있어야 합니다.
- 함수의 인자와 반환값을 확인할 수 있어야 합니다.

## 함수 이름으로 동작을 드러내기

```python
def parse_positive_integers(text: str) -> list[int]:
    ...
```

`process(data)`처럼 범위가 모호한 이름보다 어떤 입력을 처리해 무엇을 반환하는지 알 수 있는 이름이 낫습니다.

한 함수가 다음 작업을 모두 수행하면 실패 원인을 분리하기 어렵습니다.

```text
파일 읽기
→ JSON 파싱
→ 값 검증
→ 외부 프로세스 실행
→ 터미널 출력
```

책임이 다른 작업은 다음처럼 함수로 나눕니다.

```python
def parse_cases(text: str) -> tuple[Case, ...]:
    ...


def run_case(case: Case, command: tuple[str, ...]) -> Result:
    ...
```

핵심 로직은 값을 입력받아 값으로 결과를 반환하도록 작성합니다. 파일, 시간, 프로세스 같은 외부 의존성은 별도의 I/O 계층에서 처리합니다.

## 위치 인자와 키워드 전용 인자

호출 코드에서 의미가 드러나야 하는 설정은 키워드 전용 인자로 만들 수 있습니다.

```python
def read_text(path: str, *, encoding: str = "utf-8") -> str:
    ...
```

```python
content = read_text("README.md", encoding="utf-8")
```

여러 개의 `bool` 값을 위치 인자로 전달하면 각 값의 의미를 파악하기 어렵습니다.

```python
# 각 인자가 무엇을 뜻하는지 알기 어렵습니다.
run_case(case, True, False)
```

이런 경우에는 키워드 인자, 열거형, 이름이 있는 설정 객체를 사용합니다.

## 가변 기본 인자를 피하기

기본 인자는 함수를 호출할 때마다 평가되지 않고 함수가 정의될 때 한 번 평가됩니다.

```python
def append_value(value: int, values: list[int] = []) -> list[int]:
    values.append(value)
    return values
```

위 함수는 여러 호출에서 같은 리스트를 공유합니다. 호출마다 새 리스트가 필요하면 `None`을 기본값으로 사용합니다.

```python
def append_value(value: int, values: list[int] | None = None) -> list[int]:
    if values is None:
        values = []
    values.append(value)
    return values
```

문자열, 숫자, 불변 튜플처럼 변경할 수 없는 기본값에는 이 문제가 없습니다.

## 예외로 실패 원인 보존하기

```python
def parse_port(text: str) -> int:
    try:
        port = int(text)
    except ValueError as error:
        raise ValueError("포트는 정수여야 합니다.") from error

    if not 1 <= port <= 65535:
        raise ValueError("포트 범위는 1..65535입니다.")
    return port
```

예외 연결인 `raise ... from error`를 사용하면 호출자에게 더 적절한 설명을 제공하면서 원래 예외도 보존할 수 있습니다.

### 처리할 수 있는 예외만 잡기

```python
try:
    configuration = load_configuration(path)
except OSError as error:
    ...
except ValueError as error:
    ...
```

다음 코드는 예상하지 못한 프로그래밍 오류까지 숨깁니다.

```python
try:
    work()
except Exception:
    pass
```

예외를 잡았다면 다음 중 하나를 수행해야 합니다.

- 현재 위치에서 복구한다.
- 호출자에게 의미 있는 다른 예외로 바꿔 다시 발생시킨다.
- 최상위 진입점에서 사용자용 오류 메시지와 종료 상태로 변환한다.

아무 처리 없이 예외를 무시하는 것은 오류 처리가 아닙니다.

## 사용자 정의 예외

입력 명세가 잘못된 경우와 검사 대상 프로그램의 결과가 기대와 다른 경우를 구분합니다.

```python
class SpecificationError(ValueError):
    """검사를 시작하기 전에 입력 명세가 잘못되었음을 나타냅니다."""
```

`SpecificationError`는 CLI 진입점에서 종료 상태 2로 변환할 수 있습니다. 반면 검사 대상 프로그램이 정상적으로 실행됐지만 출력이 기대와 다르다면 예외보다 `Result(passed=False, ...)` 같은 결과값으로 표현하는 편이 적절합니다.

```text
검사를 시작할 수 없음 → 예외 → 종료 상태 2
검사는 실행됐지만 결과가 기대와 다름 → 결과값 → 종료 상태 1
모든 결과가 일치함 → 결과값 → 종료 상태 0
```

## 타입 힌트와 실행 시 검증 구분하기

```python
def total(values: list[int]) -> int:
    return sum(values)
```

타입 힌트는 다음 작업에 도움이 됩니다.

- 함수가 받는 값과 반환하는 값을 파악한다.
- `None` 가능성과 컬렉션 원소 타입을 드러낸다.
- 정적 타입 검사기와 편집기가 오류 가능성을 찾도록 한다.
- 모듈 간 인터페이스를 변경할 때 영향을 추적한다.

그러나 JSON, 환경 변수, CLI 인자가 타입 힌트를 따르는지는 Python이 자동으로 검사하지 않습니다.

```python
def require_string(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise SpecificationError(f"{field}는 문자열이어야 합니다.")
    return value
```

외부 입력은 먼저 `object`로 받은 뒤 실행 시 검증을 거쳐 더 구체적인 타입으로 좁힙니다.

## 합 타입과 타입 좁히기

```python
def find_name(identifier: int) -> str | None:
    ...


name = find_name(42)
if name is None:
    raise LookupError("이름을 찾지 못했습니다.")
print(name.upper())
```

결과가 없음을 `None`으로 표현할지 예외로 표현할지는 호출자가 반드시 분기해야 하는 상황인지, 정상적인 결과 중 하나인지에 따라 결정합니다.

## 구조적 인터페이스

함수가 특정 동작만 필요로 한다면 구체 클래스 대신 작은 인터페이스를 받을 수 있습니다.

```python
from typing import Protocol


class Clock(Protocol):
    def monotonic(self) -> float:
        ...
```

테스트에서는 가짜 시계를 주입해 시간에 의존하는 동작을 재현 가능하게 만들 수 있습니다. 모든 코드에 `Protocol`을 추가할 필요는 없지만 시간·파일·네트워크처럼 외부 상태에 의존하는 부분을 교체해야 할 때 유용합니다.

## 순수한 비교 함수

실제 출력과 기대값을 비교하는 로직은 프로세스 실행 코드와 분리합니다.

```python
def compare_channels(
    *,
    expected_code: int,
    expected_stdout: str,
    expected_stderr: str,
    actual_code: int,
    actual_stdout: str,
    actual_stderr: str,
) -> tuple[str, ...]:
    failures: list[str] = []
    if actual_code != expected_code:
        failures.append(
            f"종료 상태: 예상 {expected_code}, 실제 {actual_code}"
        )
    if actual_stdout != expected_stdout:
        failures.append(
            f"표준 출력: 예상 {expected_stdout!r}, 실제 {actual_stdout!r}"
        )
    if actual_stderr != expected_stderr:
        failures.append(
            f"표준 오류: 예상 {expected_stderr!r}, 실제 {actual_stderr!r}"
        )
    return tuple(failures)
```

이 함수는 파일, 환경 변수, 현재 시간에 의존하지 않습니다. 따라서 작은 입력을 빠르게 반복하거나 전수 검사하기 쉽습니다.

## 연결 실습

- [command-checker 3단계](../../exercises/command-checker/README.md#3단계-비교와-실패-표현)에서 종료 상태·표준 출력·표준 오류를 비교하는 순수 함수와 실패 유형을 구현합니다.
- 8단계에서는 공개 함수와 `dataclass` 필드의 타입 어노테이션, 공개 API의 `Any` 금지 규칙을 다시 확인합니다.

## 완료 기준

- 각 함수가 하나의 명확한 책임을 가집니다.
- 외부 입력의 실행 시 검증과 내부 타입 힌트를 구분합니다.
- 명세 오류와 실행 결과 불일치를 서로 다른 방식으로 표현합니다.
- 처리할 수 없는 예외를 숨기지 않습니다.
- 결과 비교 로직을 외부 부작용이 없는 함수로 분리했습니다.

다음은 [반복자, 생성기와 컨텍스트 관리자](04-iterators-generators-and-context-managers.md)입니다.
