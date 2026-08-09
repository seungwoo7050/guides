# Runtime semantics 관찰 예제

이 예제는 checked i64 arithmetic, short-circuit, step/call-depth budget의 공개 결과를 작은 함수로 고정합니다.

```sh
python3 examples/runtime-semantics/runtime.py --self-test
python3 examples/runtime-semantics/runtime.py
```

OS sandbox나 메모리 격리를 제공하지 않으며 GC, closure와 실제 call frame은 capstone에서 별도로 구현합니다. `INT64_MIN`은 허용된 양의 literal에서 `-INT64_MAX - 1`로 구성된 runtime 값이라고 가정합니다.
