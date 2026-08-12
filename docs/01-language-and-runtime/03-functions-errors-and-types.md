# 함수, 예외와 타입 경계

## 학습 목표

함수는 단순히 코드를 줄이는 장치가 아니라 입력, 결과와 실패를 구분하는 계약입니다. 이 장은 [`command-checker` 3단계](../../exercises/command-checker/README.md#3단계-비교와-실패-표현)와 연결됩니다.

## 선행 개념

- 객체의 mutability/equality 구분과 함수 인자·반환값 관찰

## 함수 이름은 계약을 드러냅니다

```python
def parse_positive_integers(text: str) -> list[int]:
    ...
```

`process(data)`보다 무엇을 받고 무엇을 돌려주는지 명확합니다.

한 함수가 다음을 모두 수행하면 실패 원인을 분리하기 어렵습니다.

```text
파일 읽기
→ JSON 해석
→ 값 검증
→ 외부 프로세스 실행
→ 터미널 출력
```

다음처럼 경계를 나눕니다.

```python
def parse_cases(text: str) -> tuple[Case, ...]:
    ...


def run_case(case: Case, command: tuple[str, ...]) -> Result:
    ...
```

핵심 계산은 값으로 받고 값으로 돌려주며, 파일·시간·프로세스는 바깥 경계에서 다룹니다.

## 위치 인자와 키워드 전용 인자

호출에서 의미가 드러나야 하는 설정은 키워드 전용으로 만들 수 있습니다.

```python
def read_text(path: str, *, encoding: str = "utf-8") -> str:
    ...
```

```python
content = read_text("README.md", encoding="utf-8")
```

여러 개의 `bool` 위치 인자는 의미를 숨깁니다.

```python
# 의미를 읽기 어렵습니다.
run_case(case, True, False)
```

열거형, 이름 있는 설정 객체나 키워드 인자를 검토합니다.

## 가변 기본 인자를 사용하지 않습니다

기본 인자는 함수 정의 시 한 번 평가됩니다.

```python
def append_value(value: int, values: list[int] = []) -> list[int]:
    values.append(value)
    return values
```

호출 사이에 목록이 공유됩니다. `None`을 사용해 호출마다 만듭니다.

```python
def append_value(value: int, values: list[int] | None = None) -> list[int]:
    if values is None:
        values = []
    values.append(value)
    return values
```

불변 기본값인 문자열, 숫자와 튜플은 이 문제가 없습니다.

## 예외는 실패 종류를 보존합니다

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

예외 연결(`raise ... from error`)은 외부 계약에 맞는 설명을 제공하면서 원래 원인을 보존합니다.

### 잡을 수 있는 예외만 잡습니다

```python
try:
    configuration = load_configuration(path)
except OSError as error:
    ...
except ValueError as error:
    ...
```

다음 코드는 프로그래밍 오류까지 숨깁니다.

```python
try:
    work()
except Exception:
    pass
```

예외를 잡았다면 다음 중 하나를 해야 합니다.

- 복구한다.
- 더 적절한 경계 예외로 바꿔 다시 발생시킨다.
- 사용자 진단과 종료 상태로 변환한다.

아무것도 하지 않는 것은 오류 처리가 아닙니다.

## 사용자 정의 예외

외부 명세가 잘못된 실패와 실행 결과 불일치를 구분합니다.

```python
class SpecificationError(ValueError):
    """검사를 시작하기 전에 입력 계약이 깨졌음을 나타냅니다."""
```

`SpecificationError`는 종료 상태 2로 변환할 수 있습니다. 반대로 검사 대상 프로그램의 출력 불일치는 정상적으로 실행된 검사 결과이므로 예외가 아니라 `Result(passed=False, ...)`로 표현하는 편이 낫습니다.

```text
검사 자체를 시작할 수 없음 → 예외 → 종료 상태 2
검사는 실행됐으나 기대와 다름 → 결과 값 → 종료 상태 1
모두 일치함 → 결과 값 → 종료 상태 0
```

## 타입 힌트는 실행 시 검증이 아닙니다

```python
def total(values: list[int]) -> int:
    return sum(values)
```

타입 힌트는 다음에 유용합니다.

- 함수의 입력과 결과를 읽는다.
- `None` 가능성과 컬렉션 원소 타입을 드러낸다.
- 정적 검사기와 편집기가 오류 후보를 찾는다.
- 모듈 사이 계약을 변경할 때 영향을 추적한다.

하지만 JSON, 환경 변수와 CLI 인자는 실행 시 타입 힌트를 따르지 않습니다.

```python
def require_string(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise SpecificationError(f"{field}는 문자열이어야 합니다.")
    return value
```

외부 입력은 먼저 `object`로 보고 검증 뒤 좁은 타입으로 바꿉니다.

## 합 타입과 좁히기

```python
def find_name(identifier: int) -> str | None:
    ...


name = find_name(42)
if name is None:
    raise LookupError("이름을 찾지 못했습니다.")
print(name.upper())
```

`None`을 정상적인 결과 없음으로 쓸지, 예외로 쓸지는 호출자가 반드시 구분해야 하는지에 따라 정합니다.

## 구조적 인터페이스

함수가 특정 동작만 필요하다면 구체 클래스보다 작은 인터페이스를 요구할 수 있습니다.

```python
from typing import Protocol


class Clock(Protocol):
    def monotonic(self) -> float:
        ...
```

테스트에서는 가짜 시계를 넣어 시간 경계를 결정적으로 만들 수 있습니다. 모든 코드에 Protocol을 추가할 필요는 없지만 시간·파일·네트워크처럼 외부 상태를 읽는 경계에서는 유용합니다.

## 순수 비교 함수

실제 출력과 기대값 비교는 프로세스 실행과 분리합니다.

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

이 함수는 파일, 환경과 현재 시간에 의존하지 않으므로 작은 입력을 빠르게 전수 검사할 수 있습니다.

## 연결 실습

- [command-checker 3단계](../../exercises/command-checker/README.md)에서 세 결과 채널의 순수 비교와 실패 category를 구현합니다.
- 8단계에서 공개 함수·dataclass annotation과 `Any` 금지 계약을 다시 적용합니다.

## 완료 기준

- 함수가 하나의 변경 이유를 갖습니다.
- 외부 입력 검증과 내부 타입을 구분합니다.
- 명세 오류와 실행 결과 불일치를 다른 방식으로 표현합니다.
- 처리할 수 없는 예외를 숨기지 않습니다.
- 핵심 비교를 부작용 없는 함수로 분리했습니다.

다음은 [반복자, 생성기와 컨텍스트 관리자](04-iterators-generators-and-context-managers.md)입니다.
