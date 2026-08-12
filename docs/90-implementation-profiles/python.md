# Python 구현 프로필

## 목적

이 문서는 알고리즘 개념을 다시 가르치지 않는다. 핵심 문서의 계약과 의사코드를 Python으로 옮길 때 필요한 실행·자료형·검증 경계만 정리한다.

## 기준 환경

- Python 3.12 이상
- 표준 라이브러리만으로 capstone 실행
- type hint는 계약 설명에 사용하지만 runtime validation을 대신하지 않음

## 자료구조 대응

| 알고리즘 개념 | Python 도구 | 주의점 |
|---|---|---|
| 동적 배열 | `list` | 앞쪽 pop은 `O(n)` |
| queue/deque | `collections.deque` | 양 끝 `O(1)` |
| min-heap | `heapq` | decrease-key 대신 lazy entry |
| set/map | `set`, `dict` | 기대 비용, mutable key 금지 |
| binary search | `bisect` | 반환 경계 계약 확인 |
| 무한대 | `math.inf` 또는 `None` | 정수와 비교·덧셈 규칙 |

## 정수와 재귀

Python 정수는 임의 정밀도지만 숫자가 커지면 연산 비용도 커진다. 고정 폭 overflow가 없다는 사실을 다른 언어의 계약에 그대로 일반화하지 않는다.

기본 recursion limit은 깊은 DFS나 편향 tree에 충분하지 않을 수 있다. 단순히 limit을 크게 올리기보다 명시적 stack을 검토한다.

## heap의 결정성

동점에서 비교할 수 없는 객체를 tuple 두 번째에 두면 오류가 날 수 있다.

```python
heapq.heappush(heap, (priority, sequence, item))
```

증가하는 `sequence`를 tie-break로 사용하면 결정적인 순서를 만들 수 있다.

## 모듈과 실행

알고리즘 함수와 입출력 entry point를 분리한다.

```python
def solve(data: str) -> str:
    ...

if __name__ == "__main__":
    import sys
    sys.stdout.write(solve(sys.stdin.read()))
```

함수 검사는 문자열 입출력보다 domain API를 우선한다.

## 복사와 mutable 상태

- 2차원 배열은 `[[0] * width for _ in range(height)]`로 만든다.
- default mutable argument를 사용하지 않는다.
- backtracking에서 list를 append한 뒤 반드시 pop하거나 새 상태를 만든다.
- 기준 구현과 후보 구현에 같은 mutable 입력을 공유하지 않는다.

## 검증

고정 시드 generator를 사용한다.

```python
source = random.Random(20260201)
```

실패하면 seed뿐 아니라 실제 입력을 출력하고 regression case로 고정한다.

## 성능 경계

- 문자열 반복 덧셈 대신 list에 모아 `"".join`
- queue에 `list.pop(0)` 대신 `deque.popleft`
- membership에 list 선형 탐색이 의도인지 확인
- slicing은 복사 비용이 있음
- tuple·object 생성량도 큰 상태 공간에서는 비용이 됨

## Capstone

학습자 구현은 `workspace/algorithms.py`에 둔다. 저장소 루트에서 workspace를 한 번 만들고, Part 2–5의 구현을 같은 파일에 누적한다.

```sh
scripts/new-workspace.sh exercises/07-verified-algorithms-capstone
cd exercises/07-verified-algorithms-capstone
python3 check.py --impl workspace --stage data-structures --expect pass
python3 check.py --impl workspace --stage design-techniques --expect pass
python3 check.py --impl workspace --stage graphs --expect pass
python3 check.py --impl workspace --stage strings --expect pass
python3 check.py --impl workspace --stage all --expect pass
```

생성 도구는 기존 학습자 파일을 덮어쓰지 않는다. `skeleton/`은 read-only 시작 계약이며 `reference/`는 workspace의 `all` 통과 뒤에만 읽는다. 이후 다음 명령으로 repository-owned baseline도 같은 공개 검사를 통과하는지 확인하고 자신의 상태·불변식 선택과 비교한다.

```sh
python3 check.py --impl reference --stage all --expect pass
```
