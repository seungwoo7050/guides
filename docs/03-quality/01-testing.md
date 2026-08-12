# 재현 가능한 테스트

## 학습 목표

좋은 검사는 입력 수가 많은 검사가 아니라 어떤 계약과 실패 조건을 확인하는지 설명할 수 있는 검사입니다. `command-checker`의 모든 단계는 이 장의 원칙을 사용합니다.

## 선행 개념

- 순수 로직/외부 process·file boundary와 정상·경계·실패 사례 작성

## 핵심 로직과 부작용을 분리합니다

```python
def normalize_words(text: str) -> list[str]:
    return sorted({word.lower() for word in text.split()})
```

파일과 프로세스 없이 직접 검사할 수 있습니다.

```python
class NormalizeWordsTest(unittest.TestCase):
    def test_removes_duplicates_and_sorts(self) -> None:
        self.assertEqual(normalize_words("B a b"), ["a", "b"])
```

CLI 진입점은 소수의 종단 간 검사로 보완합니다.

## 테스트 층위

| 층위 | 확인하는 것 | 예시 |
|---|---|---|
| 단위 | 함수·타입 하나의 계약 | 출력 채널 비교 |
| 통합 | 여러 모듈과 실제 자원 경계 | JSON 파일과 보고서 저장 |
| 종단 간 | 사용자가 보는 진입점 | `python -m command_checker` |

모든 것을 subprocess로 검사하면 느리고 실패 원인이 모호합니다. 반대로 단위 테스트만 있으면 인자, cwd, 환경과 종료 상태가 빠집니다.

## 경계와 분기를 겨냥합니다

일반적으로 다음을 확인합니다.

- 빈 입력과 최소 입력
- 중복
- 마지막 원소에서만 상태가 바뀌는 경우
- 정상과 오류가 갈리는 바로 앞·뒤 값
- 잘못된 타입과 알 수 없는 필드
- 없는 파일과 권한 오류
- timeout과 출력 한계
- 부분 성공 뒤 정리

샘플을 복사하는 것보다 어떤 분기와 불변식을 공격하는지 적습니다.

## 표 기반 테스트

```python
cases = [
    ("", []),
    ("a", ["a"]),
    ("B a b", ["a", "b"]),
]

for input_text, expected in cases:
    with self.subTest(input_text=input_text):
        self.assertEqual(normalize_words(input_text), expected)
```

실패 메시지에는 입력, 기대값과 실제값이 남아야 합니다.

## 작은 입력의 전수 검사

입력 공간이 작으면 모든 조합을 확인할 수 있습니다.

```python
from itertools import product

for values in product(range(3), repeat=4):
    self.assertEqual(optimized(values), reference(values))
```

입력 크기가 커지면 조합 수가 급격히 증가합니다. 전수 검사 범위를 계산하고 사용합니다.

## 재현 가능한 무작위 검사

```python
import random

rng = random.Random(4242)
for _ in range(500):
    values = [rng.randint(-100, 100) for _ in range(rng.randint(0, 30))]
    self.assertEqual(optimized(values), reference(values))
```

시드를 고정하고 실패 입력도 출력합니다. 전역 난수 상태를 공유하지 않습니다.

## 독립된 기준 구현

빠른 구현과 기준 구현은 명세만 공유하는 편이 좋습니다. 같은 내부 helper를 재사용하면 같은 버그가 양쪽에 숨어 거짓 통과할 수 있습니다.

`command-checker`에서는 실제 프로세스 결과와 기대값을 비교하는 순수 함수가 기준입니다. 프로세스 수집 코드가 비교 규칙을 다시 구현하지 않습니다.

## 실패 주입

정상 경로만 검사하면 정리 계약을 확인할 수 없습니다.

- 파일 쓰기 중 예외
- `os.replace` 실패
- 실행 파일 없음
- 자식이 파이프를 잡고 부모만 종료
- stdout 무한 출력
- worker 한 건의 예외

실패를 결정적으로 만들기 위해 mock, 임시 디렉터리와 전용 fixture를 사용합니다.

## skeleton 검사

`skeleton`이 단순히 모든 검사에서 무작위로 실패해서는 안 됩니다.

- import와 패키지 구조는 유효해야 합니다.
- 첫 미구현 책임에서 `NotImplementedError`가 나와야 합니다.
- 문법 오류나 누락된 fixture 때문에 실패해서는 안 됩니다.
- 한 단계가 통과하면 이전 단계도 계속 통과해야 합니다.

루트 `verify.sh`는 각 stage scaffold를 직접 호출해 정확히 약속한 `NotImplementedError` 메시지에서 멈추는지 확인합니다. `stage-N` 명령은 1단계부터 N단계까지 누적 실행되므로 이전 단계 회귀도 같은 명령에서 거부됩니다.

## 환경 의존 검사

POSIX 프로세스 그룹 검사는 macOS와 Linux에서 수행합니다. 다른 환경에서는 해당 기능이 지원 범위 밖임을 명확히 해야 합니다. 환경 차이로 생략한 검사를 성공으로 위장하지 않습니다.

## 연결 실습

- [단계별 공개 검사](../../exercises/command-checker/README.md)는 학습자가 수정하는 대상이 아니라 workspace와 reference에 같은 행동 계약을 적용하는 repository-owned 검사입니다. 각 mutant가 어느 공개 계약 때문에 거부되는지 확인합니다.

## 완료 기준

- 각 테스트 이름이 계약을 설명합니다.
- 단위·통합·종단 간 검사가 역할별로 나뉩니다.
- 경계와 실패 경로를 재현합니다.
- 무작위 검사는 시드와 실제 실패 입력을 남깁니다.
- skeleton과 reference의 역할을 별도로 검증합니다.

다음은 [프로젝트 구조, 패키징과 타입 검사](02-project-structure-packaging-and-typing.md)입니다.
