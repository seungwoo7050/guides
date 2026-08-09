# Capstone evidence contract

완성한 learner workspace에는 `evidence/manifest.json`과
`evidence/run-report.json`을 둡니다. 형식은 다음 파일을 사용합니다.

- `manifest.schema.json`: source, runtime, configuration, initial state, seed와
  schedule bundle identity
- `run-report.schema.json`: 정확히 7개 run, replay 결과, trace digest,
  invariant/history 근거와 축소한 counterexample
- `manifest.example.json`, `run-report.example.json`: 값과 artifact 경로를
  learner 실행 결과로 교체할 시작 예시
- `trace.example.json`: canonical 14-field event envelope 예시

`capstone/scenarios/schedules.json`의 `actions`는 완성한 protocol에 전달할
`Cluster.run_schedule` 입력입니다. `capstone/oracle/corpus.py`가 만드는
reference trace는 oracle과 schema를 검증하는 독립 fixture이며, 미완성
canonical starter가 그 schedule을 실행했다는 뜻이 아닙니다.

검사 명령:

```sh
python3 scripts/check-capstone-workspace.py .workspace/replicated-kv
```

검사기는 빈 trace, 여러 scenario가 공유하는 trace, run/scenario identity
불일치, hash-chain 단절, 실행 digest 불일치와 선언만 있는 invariant PASS를
거부합니다. 자동 검사 뒤에도 safety·liveness 논증, membership·sharding과
simulator model gap은 사람이 검토합니다.
