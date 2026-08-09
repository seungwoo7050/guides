# Logical clock 예제

이 예제는 process-local event와 send/receive edge에서 Lamport clock과 vector clock을 계산합니다. clock 값 자체를 실제 시간처럼 해석하지 않고 causality를 보존하는 순서 정보로 사용합니다.

## 실행

```sh
python3 examples/logical-clocks/logical_clocks.py \
  exercises/01-model-and-time/01-causality-trace/trace.json
```

출력에는 event별 clock과 fixture의 candidate cut이 consistent cut인지에 대한 판정이 포함됩니다.

## 관찰할 것

- 같은 process의 clock은 event마다 증가합니다.
- receive clock은 local clock과 message clock을 모두 반영합니다.
- `L(a) < L(b)`만으로 `a → b`를 역으로 결론내릴 수 없습니다.
- vector clock이 서로 비교되지 않으면 두 event는 concurrent합니다.
- receive를 포함하면서 대응 send를 제외한 cut은 consistent하지 않습니다.
