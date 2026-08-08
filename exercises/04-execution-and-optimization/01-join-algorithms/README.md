# Join 실행 알고리즘

같은 inner equi-join 의미를 nested-loop, hash join, sort-merge join으로 구현하고 입력 크기·정렬·중복 키에 따라 필요한 전제가 어떻게 달라지는지 비교한다.

## 구현할 계약

- SQL과 같이 `NULL` 키끼리는 일치시키지 않는다.
- 중복 키는 가능한 모든 행 조합을 만든다.
- hash join은 작은 입력을 build side로 선택할 수 있다.
- merge join은 정렬된 입력에서 같은 키의 run 전체를 결합한다.
- 결과 순서가 알고리즘마다 다를 수 있으므로 테스트는 bag 의미로 비교한다.

## 실행

```bash
./scripts/new-workspace.sh exercises/04-execution-and-optimization/01-join-algorithms
PYTHONPATH=exercises/04-execution-and-optimization/01-join-algorithms/workspace \
  python3 -m unittest discover -s exercises/04-execution-and-optimization/01-join-algorithms/tests -v
```

문서: [`docs/04-execution-and-optimization/01-query-execution-joins-and-sorting.md`](../../../docs/04-execution-and-optimization/01-query-execution-joins-and-sorting.md)

## 목표

세 join 알고리즘이 중복과 `NULL`을 포함한 같은 bag 의미를 만들되 서로 다른 자원 전제를 갖는다는 점을 구현한다.

## 완료 기준

- 중복 key의 좌우 조합 수가 곱으로 보존되고 `NULL` key끼리는 결합되지 않는다.
- hash join은 선택한 build side와 무관하게 nested-loop와 같은 bag 결과를 만든다.
- sort-merge join은 동일 key run 전체를 소비하고 입력 경계에서도 행을 빠뜨리지 않는다.

## 자기 설명

1. 출력 list 순서가 아닌 bag으로 알고리즘 동등성을 비교해야 하는 이유는 무엇인가?
2. 심한 key skew가 hash join의 메모리와 실행 시간에 어떤 영향을 주는가?

## 검증

workspace 테스트와 `make python-check`를 실행해 세 구현의 결과 다중집합을 대조한다.
