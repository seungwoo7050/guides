# 순회 순서와 공간 지역성 비교

같은 2차원 배열을 같은 횟수만큼 더하되, 메모리에 연속한 방향과 큰 간격을 만드는 방향으로 각각 순회합니다. 두 함수의 검사 합계가 같아야 하며 실행 시간은 관찰값으로만 사용합니다.

```sh
make check
make benchmark
```

이 예제는 [성능식과 측정](../../docs/01-representation-and-isa/03-performance-cpi-and-amdahl.md)에서 처음 사용하고 [캐시, 지역성과 AMAT](../../docs/03-memory-hierarchy/06-cache-locality-and-amat.md)에서 다시 해석합니다. 관찰을 마치면 해당 장의 `processor-model` checkpoint로 돌아갑니다.

## 권장 구현 순서

다음 번호는 Git history가 아니라 이 독립 예제를 다시 만들 때의 권장 구성 순서입니다. C compiler는 선행 환경이고 별도 project bootstrap이 없으므로 0 단계는 없습니다.

| 번호 | 파일·symbol | 먼저 고정하는 책임 |
|---|---|---|
| 1 | `layout_benchmark.c::sum_row_major` | 연속 주소를 소비하는 기준 순회와 누적형 |
| 1-1 | `layout_benchmark.c::sum_column_major` | 주소식과 작업량을 보존한 loop 순서 비교군 |
| 2 | `layout_benchmark.c::main` | 크기 검증, 결정적 입력, 독립 timing과 checksum gate |
| 3 | `Makefile::$(TARGET)` | 같은 compiler contract를 쓰는 check·benchmark build interface |

C의 행 우선 배열에서 `matrix[row * columns + column]`은 `column`을 늘릴 때 연속 주소를 읽습니다. 반대로 `row`를 안쪽 반복으로 두면 접근 간격이 `columns * sizeof(uint32_t)`가 됩니다. 작업량이 같아도 캐시 라인 하나에서 실제로 소비하는 바이트 수와 미리 가져오기 장치가 예측하기 쉬운 정도가 달라집니다.

실행 시간의 절대값과 두 순회의 비율을 정답으로 고정하지 마세요. CPU, 캐시 크기, 컴파일러 최적화, 전원 상태와 실행 중인 다른 작업에 따라 달라집니다. 다음을 함께 기록해야 비교에 의미가 생깁니다.

- 행·열·반복 횟수
- 컴파일러와 최적화 옵션
- 각 방식의 검사 합계
- 여러 번 실행한 분포
- 가능하면 `perf stat`의 캐시 관련 계수기

행렬 전체가 상위 cache에 들어갈 정도로 작게 만들거나 `columns=1`로 바꾸면 차이가 왜 줄어드는지 설명해 보세요.
