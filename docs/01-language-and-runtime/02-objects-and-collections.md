# 객체와 컬렉션

## 학습 목표

이 장은 Python의 이름, 객체와 가변성을 기준으로 기본 문법과 컬렉션을 설명합니다. 연결 실습은 [`command-checker` 2단계](../../exercises/command-checker/README.md#2단계-데이터-모델)입니다.

## 선행 개념

- Python module 실행, 함수 호출 관찰과 이름·값·타입의 기본 관계

## 이름은 객체를 가리킵니다

```python
first = [1, 2, 3]
second = first
second.append(4)

print(first)  # [1, 2, 3, 4]
```

대입은 목록을 복사하지 않습니다. 두 이름이 같은 객체를 가리킵니다.

```python
second = first.copy()
```

이는 얕은 복사입니다. 중첩 객체는 여전히 공유할 수 있습니다.

```python
left = [[1], [2]]
right = left.copy()
right[0].append(9)
print(left)  # [[1, 9], [2]]
```

깊은 복사를 먼저 선택하기보다 공유가 필요한 구조인지, 불변 값으로 바꿀 수 있는지 검토합니다.

## 가변 객체와 불변 객체

대표적인 가변 객체:

- `list`
- `dict`
- `set`
- 대부분의 사용자 정의 인스턴스

대표적인 불변 객체:

- `int`, `float`, `bool`
- `str`, `bytes`
- `tuple`, `frozenset`

불변 객체의 메서드나 연산은 보통 새 객체를 만듭니다.

```python
text = "hello"
upper = text.upper()
```

공유되는 설정이나 실행 사례처럼 생성 뒤 바뀌면 안 되는 값은 불변 구조가 오류 범위를 줄입니다.

## `==`와 `is`

- `==`: 값의 동등성
- `is`: 같은 객체인지

```python
left = [1, 2]
right = [1, 2]

assert left == right
assert left is not right
```

`None`은 `is`로 비교합니다.

```python
if result is None:
    ...
```

문자열이나 정수를 `is`로 비교하지 않습니다.

## 조건과 반복

```python
def classify(value: int) -> str:
    if value < 0:
        return "negative"
    if value == 0:
        return "zero"
    return "positive"
```

```python
for number in range(5):
    print(number)
```

```python
remaining = 3
while remaining > 0:
    remaining -= 1
```

Python은 들여쓰기가 블록 구조입니다. 탭과 공백을 섞지 않고 공백 4칸을 기본으로 사용합니다.

다음 값은 조건식에서 거짓으로 평가됩니다.

```text
False, None, 0, 0.0, "", 빈 list·tuple·dict·set
```

그러나 `0`과 값 없음이 다른 계약에서는 명시적으로 구분합니다.

```python
result: int | None = 0
if result is None:
    print("결과 없음")
else:
    print(result)
```

## 주요 컬렉션과 비용

| 구조 | 용도 | 주요 비용과 주의점 |
|---|---|---|
| `list` | 순서가 있는 가변 배열 | 끝 추가·삭제는 상각 `O(1)`, 중간 삽입·삭제는 `O(n)` |
| `tuple` | 순서가 있는 불변 묶음 | 원소가 해시 가능하면 dict/set 키가 될 수 있음 |
| `dict` | 키-값 조회 | 평균 조회·삽입·삭제 `O(1)`, 삽입 순서 유지 |
| `set` | 존재 여부와 중복 제거 | 평균 조회·삽입·삭제 `O(1)`, 정렬 계약 없음 |
| `deque` | 양끝 큐 | `append`, `popleft` 등이 `O(1)` |

비용 표기는 평균 또는 상각 계약입니다. 실제 객체 크기, 해시 충돌과 입력 분포에 따라 상수 비용은 달라집니다.

### 목록

```python
values = [3, 1, 4]
values.append(2)
ordered = sorted(values)
```

`sorted`는 새 목록을 만들고, `list.sort()`는 기존 목록을 변경합니다. 반복 슬라이싱도 새 목록을 만듭니다.

### 사전

```python
counts: dict[str, int] = {}
for word in ["a", "b", "a"]:
    counts[word] = counts.get(word, 0) + 1
```

외부 입력에서 읽은 키가 반드시 존재한다고 가정하지 않습니다. 누락이 오류인지 기본값인지 계약으로 정합니다.

### 집합

```python
seen: set[str] = set()
for name in names:
    if name in seen:
        raise ValueError(f"중복 이름: {name}")
    seen.add(name)
```

집합 순회 순서를 출력 계약으로 사용하지 않습니다. 결정적인 출력이 필요하면 입력 순서를 보존하거나 정렬합니다.

### 튜플과 구조 분해

```python
point = (10, 20)
x, y = point
```

변하지 않는 작은 레코드에는 튜플이 적합할 수 있지만, 필드 의미가 중요하면 `dataclass`처럼 이름 있는 타입이 더 명확합니다.

## 반복 도구

```python
for index, name in enumerate(names):
    print(index, name)
```

```python
for name, score in zip(names, scores, strict=True):
    print(name, score)
```

`strict=True`는 길이가 달라서는 안 된다는 계약을 조용히 잃지 않게 합니다.

내포 표현식은 한눈에 읽히는 경우에만 사용합니다.

```python
normalized = [item.strip().lower() for item in raw_items if item.strip()]
```

중첩 분기와 부작용이 들어가면 일반 반복문으로 바꿉니다.

## 불변 데이터 모델

실행 사례는 여러 모듈과 스레드가 공유하므로 생성 뒤 수정되지 않는 편이 좋습니다.

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Case:
    name: str
    args: tuple[str, ...]
    cwd: Path | None
```

`frozen=True`는 필드 재대입을 막습니다. 내부에 가변 `dict`를 넣으면 얕은 불변일 뿐이므로, 환경 변수는 정렬된 튜플 쌍처럼 표현할 수 있습니다.

```python
env: tuple[tuple[str, str], ...]
```

필요한 경계에서만 새 `dict`로 변환합니다.

## 연결 실습

- [command-checker 2단계](../../exercises/command-checker/README.md)에서 immutable `Case`·`Result`와 tuple 공유 상태를 구현합니다.

## 완료 기준

- 대입과 복사의 차이를 설명할 수 있습니다.
- `==`와 `is`를 구분합니다.
- `None`과 거짓으로 평가되는 정상값을 구분합니다.
- 출력 순서가 필요한 곳에서 set/dict의 우연한 순서에 기대지 않습니다.
- 공유되는 실행 계약을 불변 데이터로 표현합니다.

다음은 [함수, 예외와 타입 경계](03-functions-errors-and-types.md)입니다.
