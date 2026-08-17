# 반복자, 생성기와 컨텍스트 관리자

## 학습 목표

자동화 프로그램은 대용량 데이터를 순차적으로 처리하고 파일이나 프로세스 같은 자원을 필요한 동안만 유지해야 하는 경우가 많습니다. 이 장에서는 다음 내용을 다룹니다.

- iterable과 iterator의 차이
- generator를 사용한 지연 처리
- 한 번만 소비되는 데이터의 사용 규칙
- `with`를 사용한 자원 정리
- 여러 자원을 얻는 도중 일부 작업이 실패했을 때의 정리 방법

## 선행 개념

- 함수와 예외의 기본 동작을 이해해야 합니다.
- `for`로 iterable을 순회할 수 있어야 합니다.
- 파일처럼 사용 후 닫아야 하는 자원이 있음을 알아야 합니다.

## iterable과 iterator

`for`문은 인덱스를 직접 증가시키는 문법이 아니라 반복자 프로토콜을 사용합니다.

```python
values = [10, 20, 30]
iterator = iter(values)

print(next(iterator))
print(next(iterator))
```

- iterable: `iter(value)`를 호출해 iterator를 만들 수 있는 객체
- iterator: `next(value)`를 호출해 다음 값을 얻을 수 있는 객체

리스트는 여러 번 순회할 수 있지만 iterator는 일반적으로 한 번 소비됩니다.

```python
iterator = iter([1, 2, 3])
print(list(iterator))  # [1, 2, 3]
print(list(iterator))  # []
```

함수가 iterator를 받는다면 한 번만 순회하는지, 여러 번 순회해야 하므로 내부에서 값을 저장하는지 명확히 해야 합니다.

## 생성기로 값을 지연 생성하기

```python
from collections.abc import Iterator
from pathlib import Path


def nonempty_lines(path: Path) -> Iterator[str]:
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            cleaned = line.rstrip("\n")
            if cleaned:
                yield cleaned
```

`yield`가 들어 있는 함수는 호출하는 순간 본문 전체를 실행하지 않습니다. iterator에서 다음 값을 요청할 때마다 다음 `yield`까지 실행한 뒤 다시 멈춥니다.

생성기를 사용하면 다음과 같은 장점이 있습니다.

- 큰 파일 전체를 메모리에 올리지 않고 처리할 수 있다.
- 데이터 생산 속도와 소비 속도를 자연스럽게 맞출 수 있다.
- 불필요한 중간 리스트를 만들지 않을 수 있다.

다음 사항도 함께 고려해야 합니다.

- 오류가 함수 호출 시점이 아니라 실제 순회 중에 발생할 수 있다.
- 한 번 소비한 generator는 처음부터 다시 사용할 수 없다.
- generator가 파일을 열고 있다면 순회를 중간에 멈췄을 때 파일이 언제 닫히는지 고려해야 한다.

위 예제의 파일은 generator가 끝까지 소비되거나 명시적으로 닫힐 때 닫힙니다. 반복을 중단한 뒤 generator 참조를 계속 보관하면 파일도 열린 채로 남을 수 있습니다.

## 생성기 표현식

```python
squares = (number * number for number in range(1_000_000))
```

리스트 내포와 달리 모든 값을 즉시 만들지 않습니다.

```python
total = sum(number * number for number in range(1_000_000))
```

지연 처리가 항상 더 나은 선택은 아닙니다. 결과가 작고 여러 번 재사용되거나 인덱스로 접근해야 한다면 리스트가 더 단순합니다.

## `yield from`

여러 iterable을 하나의 흐름으로 이어 붙일 수 있습니다.

```python
from collections.abc import Iterable, Iterator
from pathlib import Path


def all_lines(paths: Iterable[Path]) -> Iterator[str]:
    for path in paths:
        yield from nonempty_lines(path)
```

다만 파일 하나를 읽지 못했을 때 나머지 파일을 계속 처리할지 전체 작업을 중단할지는 별도의 오류 처리 규칙으로 정해야 합니다.

## 컨텍스트 관리자로 자원 수명 관리하기

```python
with path.open("r", encoding="utf-8") as stream:
    content = stream.read()
```

`with` 블록을 벗어나면 정상 종료와 예외 발생 여부에 관계없이 파일이 닫힙니다. `with`는 단순한 축약 문법이 아니라 자원의 획득과 정리를 한 범위에 묶는 문법입니다.

```text
자원을 얻는다
→ 블록 안에서 사용한다
→ 정상 종료하거나 예외가 발생한다
→ 자원을 정리한다
```

같은 동작을 `try/finally`로 직접 작성할 수도 있습니다.

```python
stream = path.open("r", encoding="utf-8")
try:
    content = stream.read()
finally:
    stream.close()
```

## 사용자 정의 컨텍스트 관리자

```python
import os
from collections.abc import Iterator
from contextlib import contextmanager


@contextmanager
def temporary_environment(name: str, value: str) -> Iterator[None]:
    previous = os.environ.get(name)
    os.environ[name] = value
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous
```

이 예제는 프로세스 전역 환경 변수를 변경합니다. 컨텍스트 관리자는 원래 값을 복구하지만, 다른 스레드가 동시에 같은 환경 변수를 읽거나 변경하는 경쟁 상태까지 막아 주지는 않습니다. 따라서 병렬 테스트에는 적합하지 않을 수 있습니다.

## 여러 자원과 `ExitStack`

열어야 할 파일 수가 실행 중에 결정된다면 `ExitStack`을 사용할 수 있습니다.

```python
from contextlib import ExitStack


with ExitStack() as stack:
    streams = [
        stack.enter_context(path.open("r", encoding="utf-8"))
        for path in paths
    ]
    ...
```

세 번째 파일을 여는 과정에서 예외가 발생해도 앞서 연 파일은 모두 닫힙니다. 여러 자원을 순서대로 얻는 도중 실패해도 정리 책임이 한곳에 유지됩니다.

## iterator를 반환할 때 자원 수명 확인하기

다음 코드는 올바르게 동작하지 않습니다.

```python
def lines(path: Path):
    with path.open(encoding="utf-8") as stream:
        return iter(stream)
```

함수가 반환되는 순간 `with` 블록이 끝나 파일이 닫힙니다. 반환된 iterator는 닫힌 파일을 읽으려 하므로 사용할 수 없습니다.

생성기 내부에서 `with` 블록을 유지하거나, 파일을 여닫는 책임을 호출자에게 맡겨야 합니다.

```python
from collections.abc import Iterator


def lines(path: Path) -> Iterator[str]:
    with path.open(encoding="utf-8") as stream:
        yield from stream
```

## 연결 실습

- [command-checker 5단계](../../exercises/command-checker/README.md#5단계-외부-프로세스-한-건-실행)에서 프로세스의 입력·출력 스트림을 누가 닫을지 정합니다.
- [command-checker 7단계](../../exercises/command-checker/README.md#7단계-프로세스-수명과-출력-상한)에서 제한 시간 초과, 출력 상한 초과, 일부 자원 획득 실패가 발생해도 이미 연 파이프와 프로세스를 정리하도록 구현합니다.
- 이 실습은 generator 문법 자체보다 iterator의 일회성, 컨텍스트 관리, 자원 정리 원칙을 직접 적용합니다.

## 완료 기준

- iterable과 iterator를 구분합니다.
- 한 번 소비한 iterator를 다시 사용하지 않습니다.
- 큰 입력을 generator로 한 항목씩 처리할 수 있습니다.
- 자원 획득과 정리를 같은 범위에 둡니다.
- 여러 자원을 얻는 도중 실패해도 이미 얻은 자원을 정리합니다.

다음은 [파일, 구조화된 데이터와 CLI](../02-automation/01-files-structured-data-and-cli.md)입니다.
