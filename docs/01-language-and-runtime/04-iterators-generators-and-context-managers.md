# 반복자, 생성기와 컨텍스트 관리자

## 학습 목표

자동화 프로그램은 데이터와 자원을 한꺼번에 소유하지 않고 순차적으로 처리하는 경우가 많습니다. 이 장은 다음을 다룹니다.

- iterable과 iterator
- 지연 처리와 generator
- 한 번만 소비되는 데이터의 계약
- `with`와 자원 정리
- 여러 자원의 부분 획득 실패

## 선행 개념

- 함수·예외·iterable과 파일 같은 자원의 명시적 close

## iterable과 iterator

`for`는 인덱스를 증가시키는 문법이 아니라 반복자 프로토콜을 사용합니다.

```python
values = [10, 20, 30]
iterator = iter(values)

print(next(iterator))
print(next(iterator))
```

- iterable: `iter(value)`로 반복자를 만들 수 있는 객체
- iterator: `next(value)`로 다음 값을 돌려주는 객체

목록은 여러 번 순회할 수 있지만 iterator는 보통 한 번 소비됩니다.

```python
iterator = iter([1, 2, 3])
print(list(iterator))  # [1, 2, 3]
print(list(iterator))  # []
```

함수가 iterator를 받는다면 한 번 소비하는지, 다시 순회해야 하는지 계약에 적습니다.

## 생성기는 값을 필요할 때 만듭니다

```python
def nonempty_lines(path: Path):
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            cleaned = line.rstrip("\n")
            if cleaned:
                yield cleaned
```

`yield`가 있는 함수는 호출 즉시 본문 전체를 실행하지 않습니다. 반복할 때마다 다음 `yield`까지 진행합니다.

장점:

- 큰 파일 전체를 메모리에 올리지 않는다.
- 데이터 생산과 소비 속도를 자연스럽게 연결한다.
- 중간 목록을 줄인다.

주의:

- 오류가 함수 호출 시점이 아니라 반복 중에 발생할 수 있다.
- 한 번 소비된 generator를 다시 사용할 수 없다.
- generator가 파일을 소유하면 반복을 중간에 멈췄을 때 정리 시점을 고려해야 한다.

## 생성기 표현식

```python
squares = (number * number for number in range(1_000_000))
```

목록 내포와 달리 값을 즉시 모두 만들지 않습니다.

```python
total = sum(number * number for number in range(1_000_000))
```

지연 처리가 항상 더 좋은 것은 아닙니다. 작은 결과를 여러 번 재사용하거나 인덱스로 접근해야 한다면 목록이 더 명확합니다.

## `yield from`

여러 iterable을 한 흐름으로 연결할 수 있습니다.

```python
def all_lines(paths: list[Path]):
    for path in paths:
        yield from nonempty_lines(path)
```

하지만 실패한 파일을 건너뛸지 전체를 중단할지 같은 정책은 별도로 정해야 합니다.

## 컨텍스트 관리자는 자원 수명을 표현합니다

```python
with path.open("r", encoding="utf-8") as stream:
    content = stream.read()
```

블록을 벗어나면 정상·예외 경로 모두에서 파일이 닫힙니다. `with`는 단순한 축약 문법이 아니라 다음 계약을 묶습니다.

```text
자원 획득
→ 블록에 소유권 제공
→ 정상 또는 실패
→ 정리
```

직접 `try/finally`로 같은 의미를 만들 수 있습니다.

```python
stream = path.open("r", encoding="utf-8")
try:
    content = stream.read()
finally:
    stream.close()
```

## 사용자 정의 컨텍스트 관리자

```python
from contextlib import contextmanager
from collections.abc import Iterator


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

이 예시는 전역 환경을 변경하므로 병렬 테스트에는 적합하지 않을 수 있습니다. 컨텍스트 관리자가 정리를 보장해도 공유 상태 경쟁까지 해결하지는 않습니다.

## 여러 자원과 `ExitStack`

파일 수가 런타임에 정해질 때 사용합니다.

```python
from contextlib import ExitStack


with ExitStack() as stack:
    streams = [
        stack.enter_context(path.open("r", encoding="utf-8"))
        for path in paths
    ]
    ...
```

세 번째 파일을 여는 중 실패해도 앞서 연 파일을 정리합니다. 부분 획득 실패에서 소유권이 흩어지지 않습니다.

## iterator를 반환할 때 수명에 주의합니다

다음 코드는 잘못되었습니다.

```python
def lines(path: Path):
    with path.open(encoding="utf-8") as stream:
        return iter(stream)
```

함수가 돌아갈 때 파일이 닫혀 반복자가 사용할 수 없습니다. 생성기 안에서 `with`를 유지하거나, 호출자가 파일을 소유하도록 합니다.

```python
def lines(path: Path):
    with path.open(encoding="utf-8") as stream:
        yield from stream
```

## 연결 실습

- [command-checker 5·7단계](../../exercises/command-checker/README.md)에서 process stream 수명과 실패 시 정리를 추적합니다.

## 완료 기준

- iterable과 iterator를 구분합니다.
- 한 번 소비되는 값을 재사용하지 않습니다.
- 큰 입력을 generator로 줄 단위 처리할 수 있습니다.
- 자원 획득과 정리를 같은 컨텍스트로 묶습니다.
- 부분 획득 실패에서 이미 얻은 자원을 정리합니다.

다음은 [파일, 구조화된 데이터와 CLI](../02-automation/01-files-structured-data-and-cli.md)입니다.
