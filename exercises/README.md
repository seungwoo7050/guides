# Exercise 로드맵

Exercise는 두 종류로 나뉜다.

1. **서술형 분석**: 계약·비용·불변식·증명을 rubric으로 검토한다.
2. **실행형 구현**: skeleton을 구현하고 독립 기준 계산과 자동 비교한다.

## 진행 순서

| 단계 | 경로 | 결과물 |
|---:|---|---|
| 1 | `01-analysis-and-counterexamples` | 계약, 기준 풀이, 최소 반례 |
| 2 | `02-data-structures` | prefix sum, lower bound, 레드블랙 검증 |
| 3 | `03-design-techniques` | knapsack, interval selection, LCS |
| 4 | `04-graphs` | BFS, shortest path, MST, max flow |
| 5 | `05-strings` | KMP |
| 6 | `06-complexity` | 하한·certificate·reduction 설명 |
| 7 | `07-verified-algorithms-capstone` | 전체 API와 결함 fixture 검증 |

## 구현 workspace

```sh
scripts/new-workspace.sh exercises/07-verified-algorithms-capstone
cd exercises/07-verified-algorithms-capstone
```

생성 도구는 저장소의 `exercises/` 아래 실제 디렉터리만 허용하고, 기존 workspace와 symbolic link를 덮어쓰지 않는다. 다시 시작하려고 기존 학습 결과를 자동 삭제하지 않으므로 필요한 backup과 제거는 학습자가 명시적으로 결정한다.

단계별 실행:

```sh
python3 check.py --impl workspace --stage data-structures --expect pass
python3 check.py --impl workspace --stage design-techniques --expect pass
python3 check.py --impl workspace --stage graphs --expect pass
python3 check.py --impl workspace --stage strings --expect pass
python3 check.py --impl workspace --stage all --expect pass
```

`reference`는 자신의 구현을 끝낸 뒤 비교한다. 먼저 reference를 복사하면 구현은 빨라지지만 상태와 불변식을 직접 설계하는 연습은 사라진다.
