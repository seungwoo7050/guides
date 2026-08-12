# 예측 가능한 분기와 불규칙한 분기 관찰

같은 비교문을 정렬된 패턴과 의사 난수 패턴에 적용합니다. 정렬된 입력은 한동안 참이다가 한동안 거짓이고, 난수 입력은 결과가 자주 바뀝니다.

```sh
make check
make benchmark
make assembly
```

이 예제는 [성능식과 측정](../../docs/01-representation-and-isa/03-performance-cpi-and-amdahl.md)에서 compiler 최적화를 확인하고 [파이프라인과 위험 요소](../../docs/02-in-order-execution/05-pipeline-hazards-and-branching.md)에서 실제 branch 명령과 predictor 가정을 구분하는 데 사용합니다. 관찰을 마치면 해당 `processor-model` checkpoint로 돌아갑니다.

## 권장 구현 순서

다음 번호는 Git history가 아니라 이 독립 예제를 다시 만들 때의 권장 구성 순서입니다. C compiler는 선행 환경이고 별도 project bootstrap이 없으므로 0 단계는 없습니다.

| 번호 | 파일·symbol | 먼저 고정하는 책임 |
|---|---|---|
| 1 | `branch_benchmark.c::count_selected` | 두 입력에 동일하게 적용할 selection workload |
| 2 | `branch_benchmark.c::main` | 결정적 입력 두 종류, 같은 threshold, timing과 count gate |
| 3 | `Makefile::$(TARGET)` | check·benchmark·assembly가 공유하는 build interface |

이 예제는 난수 입력이 몇 배 느린지를 정답으로 고정하지 않습니다. 컴파일러가 `if`를 조건 이동이나 벡터 비교로 바꾸면 실제 조건 분기가 사라질 수 있습니다. `make assembly`로 `count_selected`의 기계어를 먼저 확인하고, Linux에서 사용할 수 있다면 다음 계수기를 함께 관찰하세요.

```sh
perf stat -e cycles,instructions,branches,branch-misses ./build/branch_benchmark 16000000
```

`branch-misses`는 CPU와 권한 설정에 따라 제공되지 않을 수 있습니다. 계수기를 얻지 못했다면 실행 시간만으로 분기 예측기의 내부 동작을 단정하지 마세요.

threshold를 거의 항상 참 또는 거의 항상 거짓이 되도록 바꾸고, 입력 배열을 읽는 메모리 비용이 분기 비용보다 커지는 지점도 찾아보세요.
