# Capstone public tests

이 디렉터리의 검사는 capstone starter가 기대하는 공개 API와 storage, election, log, client, snapshot, 누적 KV 계약을 보여 줍니다. canonical starter에서는 harness/storage 11개만 통과하고 protocol transition 18개는 `NotImplementedError`로 실패해야 합니다.

```sh
CAPSTONE_ROOT=.workspace/replicated-kv \
  python3 -m unittest discover -s capstone/tests -v
```

테스트를 수정해 통과시키지 않습니다. 구현 뒤에는 다음 명령으로 공개 테스트, 7개 trace, design dossier를 함께 확인합니다.

```sh
python3 scripts/check-capstone-workspace.py .workspace/replicated-kv
```

`evidence/run-report.json` 형식은 [`capstone/evidence`](../evidence/README.md)에 있습니다. 이 검사는 자동 계약만 확인합니다. safety·liveness 논증, membership·sharding 판단과 simulator의 model gap은 사람 검토 항목입니다.
