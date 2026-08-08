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
