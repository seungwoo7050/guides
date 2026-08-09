# Safety invariant

각 invariant를 simulator state에 대한 executable predicate로 옮깁니다.

- Election Safety: `TODO`
- Vote Safety: `TODO`
- Log Matching: `TODO`
- Leader Completeness: `TODO`
- Commit Monotonicity: `TODO`
- Apply Bound: `TODO`
- State Machine Safety: `TODO`
- Client At-Most-Once Effect: `TODO`
- Snapshot Equivalence: `TODO`
- One Write Authority Per Shard Epoch: `TODO`

각 항목에 invariant가 처음 깨지는 최소 trace와 oracle diagnostic ID를 함께 기록합니다.

각 항목에는 다음을 추가합니다.

```text
검사할 state
위반 message
최소 counterexample 예상 길이
검사하지 못하는 범위
```
