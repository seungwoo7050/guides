# Exercise 로드맵

Exercise는 두 종류로 나뉜다.

1. **서술형 분석**: 계약·비용·불변식·증명을 rubric으로 검토한다.
2. **실행형 구현**: read-only skeleton으로 workspace를 만든 뒤 learner-owned 구현을 독립 기준 계산과 자동 비교한다.

저장소가 제공하는 실행형 skeleton과 checker는 Python 3.12용이다. C++20으로 같은
개념을 구현할 수는 있지만, 별도 harness 결과는 이 저장소의 capstone PASS를
대신하지 않는다.

서술형 분석은 저장소 밖 개인 학습 노트에 기록한다. repository에는 한 가지 문장 정답을 추가하지 않으며 rubric과 짝 검토가 의미 검증을 맡는다. `make docs-check`는 답안의 정확성을 자동 채점하지 않는다.

아래 숫자 1–7은 **학습 단계**다. `data-structures`, `design-techniques`, `graphs`, `strings`, `all`은 capstone checker가 선택하는 **checker stage**이며 같은 종류의 번호가 아니다.

## 진행 순서

| 학습 단계 | 경로 | 결과물 | 검증·다음 |
|---:|---|---|---|
| 1 | `01-analysis-and-counterexamples` | 개인 노트의 계약, 기준 풀이, 최소 반례 초안 | 수동 rubric; Part 2–4 뒤 A·B·C 재방문 |
| 2 | `02-data-structures` | workspace의 prefix sum, lower bound, 레드블랙 검증과 개인 노트의 DSU trace | `data-structures` checker stage 뒤 3단계 |
| 3 | `03-design-techniques` | 같은 workspace의 knapsack, interval selection, LCS와 DP 반례 | `design-techniques` checker stage 뒤 4단계 |
| 4 | `04-graphs` | 같은 workspace의 BFS, shortest path, MST, max flow와 서술 trace | `graphs` checker stage 뒤 5단계 |
| 5 | `05-strings` | 같은 workspace의 KMP와 문자열 상태 trace | `strings` checker stage 뒤 6단계 |
| 6 | `06-complexity` | 개인 노트의 하한·안정성·certificate·reduction 설명 | 수동 rubric 뒤 7단계 |
| 7 | `07-verified-algorithms-capstone` | 누적 workspace 전체 API와 개인 노트의 실패·회귀 증거 | `all` 통과 뒤 reference·결함 fixture 비교 |

## 구현 workspace

```sh
scripts/new-workspace.sh exercises/07-verified-algorithms-capstone
```

생성 도구는 저장소의 `exercises/` 아래 실제 디렉터리만 허용하고, 기존 workspace와 symbolic link를 덮어쓰지 않는다. 다시 시작하려고 기존 학습 결과를 자동 삭제하지 않으므로 필요한 backup과 제거는 학습자가 명시적으로 결정한다.

직접 수정하는 파일은 `exercises/07-verified-algorithms-capstone/workspace/algorithms.py`뿐이다. tracked `skeleton/`, `reference/`, `tests/`, `broken/`과 `check.py`는 learner 답안을 작성하는 위치가 아니다.

단계별 실행:

```sh
make stage-check STAGE=data-structures
make stage-check STAGE=design-techniques
make stage-check STAGE=graphs
make stage-check STAGE=strings
make stage-check STAGE=all
```

각 checker stage는 해당 함수군만 선택하지만 구현은 하나의 workspace에 누적한다. 마지막 `all` 검사가 앞 함수군의 회귀까지 확인한다.

`reference`는 workspace의 `all` 검사가 통과한 뒤 비교한다. 먼저 reference를 복사하면 구현은 빨라지지만 상태와 불변식을 직접 설계하는 연습은 사라진다.
