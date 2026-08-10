# IR pipeline 관찰 예제

`ir_pipeline.py`는 작은 SSA-like CFG를 검증하고 reachability를 고정점으로 계산한 뒤, checked constant folding과 unreachable block 제거를 수행합니다.

```sh
python3 examples/ir-pipeline/ir_pipeline.py --self-test
python3 examples/ir-pipeline/ir_pipeline.py
```

`DIV_CHECKED x, x`를 `1`로 바꾸는 known-bad는 `x = 0`의 trap을 제거하므로 거부됩니다. 이 예제는 phi, dominance, effect lattice를 모두 구현하는 production IR이 아닙니다.
