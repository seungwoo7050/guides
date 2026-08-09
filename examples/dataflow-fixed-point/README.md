# Data-flow fixed point

`dataflow.py`는 작은 CFG에서 backward liveness를 계산합니다.

```text
OUT[n] = union(IN[s]) for successors s
IN[n]  = USE[n] union (OUT[n] - DEF[n])
```

```sh
python3 examples/dataflow-fixed-point/dataflow.py
python3 examples/dataflow-fixed-point/dataflow.py --self-test
```

예제의 목적은 식 암기가 아니라 다음을 확인하는 것입니다.

- lattice 원소는 변수 집합입니다.
- join은 union이며 monotone합니다.
- 변화가 있는 predecessor만 worklist에 다시 넣습니다.
- node 방문 순서는 달라도 least fixed point 결과는 같습니다.
- successor나 transfer를 잘못 정의한 known-bad는 기대 결과에서 거부됩니다.
